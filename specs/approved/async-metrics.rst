..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==================================
Collect sensor data asynchronously
==================================

https://bugs.launchpad.net/ironic/+bug/2117178

This specification proposes modifying the sensor data collection to process
each node in parallel using Python's AsyncIO_. The initial implementation will
target Redfish only.

Moving any significant parts of Ironic to asynchronous code is out of the scope
of this proposal.

.. _asyncio: https://docs.python.org/3/library/asyncio.html

Problem description
===================

There is renewed interest for sensor data collection among deployers. It is
driven on one hand by the desire to have a uniform metrics interface that does
not depend on the operating systems. On the other - by limitations of in-band
sensor data collection and lack of desire to provide BMC credentials into the
running instance.

What is unusual about sensor collection, compared to any other process in
Ironic, is that the operators want to see sensor information **quickly** even
in the presence of hundreds or thousands of nodes per conductor. For instance,
OpenShift's deployment of Ironic expects a single conductor to handle up to
3500 nodes, while operators want to collect sensor data every minute to be able
to raise alerts as quickly as possible.

The current implementation in Ironic is an obvious bottleneck here. Sensor data
is collected for all nodes sequentially in 4 worker threads. Even for pretty
humble 200 nodes per conductor, each thread will handle 50 nodes one after the
other. Only if each node is processed for no more than a second is it possible
to hit the 1 minute deadline.

Unfortunately, the collection via Redfish is not that fast in real life. For
each node, several GET requests are needed, each taking 1-2 seconds on average
and up to 20 seconds in certain pathological cases. Hitting the expectations
for thousands of nodes requires either cranking up the workers threads to
unreasonable values or deploying significantly more conductors.

As an aside, a similar problem exists in the power synchronization loop.

Proposed change
===============

We will provide a way for sensor data to be collected asynchronously using
AsyncIO_. The feature will be opt-in for developers of *management interfaces*
and the initial implementation will target Redfish only. A new event loop will
be created on each iteration of the sensor collection periodic task in the
conductor, so that the rest of Ironic does not become asynchronous for now.

Detailed conductor workflow
---------------------------

Conductor will run the new method ``management.get_sensor_data_async``. If a
*future* is returned, it will be processed on the event loop asynchronously. If
``NotImplementedError`` is raised, the node will be handled in worker threads
as before. Or in pseudo-Python:

.. code-block:: python

    sync_queue = queue.Queue()
    async_tasks = []

    for node_uuid in nodes_for_conductor:
        # NOTE(dtantsur): operators may want to opt out of the asynchronous
        # collection because of its RAM requirements.
        if CONF.sensor_data.enable_async_collection:
            with task_manager.acquire(node_uuid, shared=True) as task:
                try:
                    # NOTE(dtantsur): cannot pass a *task* here since it's not
                    # async-compatible. We might even choose to pass the node
                    # as a JSON to make sure no database methods are used.
                    fut = task.management.get_sensor_data_async(task.node)
                except (NotImplementedError, AttributeError):
                    # NOTE(dtantsur): the existing code relies on creating new
                    # tasks inside worker threads, thus only storing the UUID.
                    sync_queue.put(task.node.uuid)
                else:
                    async_tasks.append(fut)
        else:
            sync_queue.put(node_uuid)

In both cases, we end up with a list of futures, just futures of different
kinds, and they will be handled a bit differently. While threaded workers
will handle sending sensor data to the messaging bus themselves, for
asynchronous workers the conductor will need to handle sending since the
messaging bus is not asynchronous.

.. code-block:: python

    futures = []
    for thread_number in range(number_of_threads):
        futures.append(
            self._spawn_worker(self._sensors_nodes_task,
                               context, sync_queue))

    if async_tasks:
        sensor_data = asyncio.run(_run_async_sensor_data(async_tasks))
        self._send_sensor_data(sensor_data)


The simplest implementation of the asynchronous part awaits every future:

.. code-block:: python

    async def _run_async_sensor_data(async_tasks):
        tasks = [asyncio.create_task(task) for task in async_tasks]
        return await asyncio.gather(*tasks)

The prototype_ is more complex: it creates a configurable number of
asynchronous workers that pick tasks from an input queue and put results into
an output queue. The upside is being able to control the number of simultaneous
tasks without a rogue node blocking the execution. The downside is much more
complex logic on the controller task.

In my experiments, running 3500 tasks did not put any larger strain on the CPU
and memory than batches of 500. As a result, I'd prefer to start with a simple
approach and modify it based on the operator feedback.

Redfish implementation
----------------------

Sushy_ is a synchronous Redfish client and thus cannot be used directly for an
asynchronous implementation. While the initial discussions of this topic
revolved around making Sushy support both approaches, this specification
suggests introducing a lightweight asynchronous Redfish client to Ironic
itself. The reasoning is twofold:

* There is an ongoing discussion about moving Sushy into Ironic and no longer
  maintaining it as a separate library.
* Adding this feature into an existing stable library implies committing to a
  certain API interface very early, while aiming for maximum performance may
  require changing the client as we measure the actual behavior.

As to the lightweight part, I'm proposing getting rid of the structures and
using string-based access instead. Most fields are only used once or twice in
Ironic, creating typed structures for them adds more work with little benefit,
as long as we don't treat the resulting client as a public deliverable (like
Sushy itself currently is).

The prototype_ shows how the API surface may look like. The ``Connection`` and
authenticator classes are straightforward adaptations to ``async``/``await``.
The new ``AsyncResource`` provides a simplified yet convenient approach to
fields, subresources and actions:

.. code-block:: python

    system = AsyncResource(connector, '/redfish/v1/Systems/1')
    await system.refresh()

    # Get simple fields
    manufacturer = system.field('Manufacturer')

    # Get nested fields with slash notation
    boot_target = system.field('Boot/BootSourceOverrideTarget')

    # Apply adapters to field values (can be enums too!)
    power_state = system.field('PowerState', adapter=str.lower)

    # Execute actions
    await system.action('Reset', {'ResetType': 'ForceRestart'})

    # PATCH resources
    await system.patch({'AssetTag': 'new-tag'})

    # Navigate to subresources
    bios = await system.link('Bios')
    boot_mode = bios.field('BootMode')

A resource can be converted into an ``AsyncResourceCollection`` that allows
(async) iteration and other convenient methods:

.. code-block:: python

    # A normal collection, e.g. for systems
    systems_collection = (await client.resource(
        '/redfish/v1/Systems'
    )).collection()
    print(systems_collection.paths)

    # Fetch resources in the collection
    async for system in systems:
        print(system.field('Manufacturer'))

    # Collections linked under a different name
    storage = await client.resource('/redfish/v1/Systems/1/Storage/1')
    drives_collection = storage.collection('Drives')
    drives = await drives_collection.get_all()

Once we have an asynchronous Redfish client, the implementation of
``get_sensor_data_async`` is a straightforward port of the existing code to
``async``/``await``, replacing attribute accesses with dictionary lookups.

.. _sushy: https://opendev.org/openstack/sushy

Session cache
-------------

Ironic currently maintains a cache with all Redfish connections using a tuple
of (address, user name, TLS validation, hashed password) as a key. The cache
contains synchronous connection objects from Sushy and thus cannot be used by
asynchronous code directly. The tricky part is that we want to avoid having
several sessions opened against the same BMC because some hardware has pretty
small limits on the number of sessions.

The initial implementation will have two nearly identical session caches:
synchronous and asynchronous. The existing synchronous cache will remain
unchanged. The asynchronous cache will additionally use locking to prevent
creating two sessions for the same BMC. To avoid contention around one global
lock, a temporary lock will be created for a session key. The logic will rely
on the fact that two asynchronous tasks cannot run in parallel between yield
points and will look roughly like this:

.. code-block:: python

    # This is the asynchronous session cache, separate from the existing
    # synchronous Sushy cache. Values are either AsyncConnection objects
    # or temporary asyncio.Lock instances used to prevent duplicate sessions.
    #
    # These operations do not yield, so there is no concurrency
    session_or_lock = self._async_sessions.get(session_key)
    if isinstance(session_or_lock, AsyncConnection):
        # Short-circuit, return the connection
        return session_or_lock

    if session_or_lock is None:
        # No session and no thread is working on it, create a lock
        session_or_lock = asyncio.Lock()
        self._async_sessions[session_key] = session_or_lock
        # Now a lock is cached and serves as a mark that the current thread
        # will be working on the session. Since no yield points have happened
        # so far, this thread is the first to take the lock. Even if it isn't,
        # the isinstance check under the lock will handle it.

    # This is the first yield point, now the code is actually asynchronous.
    async with session_or_lock:
        new_session = self._async_sessions[session_key]
        if isinstance(new_session, asyncio.Lock):
            # This thread is the first to take the lock, create the session.
            new_session = await AsyncConnection(...)
            # After this point, other threads will see the session and will be
            # able to use it.
            self._async_sessions[session_key] = new_session

    # At this point, other threads trying to acquire the lock will be
    # notified and will see the session in place.
    return new_session

This implementation ensures that waiting for a lock will be rather uncommon.

Prototype
---------

The prototype consists of two parts: the proof-of-concept asynchronous API_ and
a `demo script`_ that demonstrates collecting sensor data similarly to how the
conductor would do it.

.. _API: https://review.opendev.org/c/openstack/ironic/+/970450
.. _demo script: https://review.opendev.org/c/openstack/ironic/+/970842

Alternatives
------------

We have two major alternatives:

* Stick to native threading, create very large number of threads. While modern
  Linux on a powerful machine can handle a lot of threads, the required memory
  may be very large. Even more importantly, the current threading
  implementation is simply not designed to launch a large number of threads
  quickly. In my experiments, even after removing any limits on the number of
  threads, it still oscillated between 200 and 500, sometimes even dropping to
  two-digit numbers, all while the sensor collection seemed to never finish.

* Do not support more than roughly 500 nodes per conductor, at least in this
  scenario. This will be a major setback for adoption of Ironic in the Metal3
  world, where multi-conductor deployments are not common and where thousands
  of nodes (like 3500 in the OpenShift case) are already routinely handled.
  Outside of large classic OpenStack clusters, we cannot expect operators to
  deploy as many replicas of Ironic as we'd prefer.

Possible variations
~~~~~~~~~~~~~~~~~~~

* Reimplement Sushy one-to-one either as a new deliverable, or as part of Sushy
  itself, or inside Ironic. Since we haven't decided to move the entire Redfish
  support in Ironic to asynchronous execution, I'd prefer to limit the amount
  of work on the new client. Keeping it private inside Ironic gives us freedom
  to change the API in the future without a painful deprecation process.

* Provide a limit on the number of concurrently processed nodes. One of the
  benefits of the asynchronous approach is that you don't need to do this.
  As seen in the prototype_, handling asynchronous workers can quickly lead to
  convoluted code.

  * We *may* need to limit the number of requests that hit the same
    ``redfish_address`` to avoid overloading BMCs that handle multiple nodes:
    see `session cache`_ for reasoning.

* Modify the existing session cache to handle both synchronous and asynchronous
  callers. This will be a desired future addition if we decide to expand the
  asynchronous code. It's too much of an effort for a single opt-in feature.

Data model impact
-----------------

None

State Machine Impact
--------------------

None

REST API impact
---------------

None

Client (CLI) impact
-------------------

None

"openstack baremetal" CLI
~~~~~~~~~~~~~~~~~~~~~~~~~
None

"openstacksdk"
~~~~~~~~~~~~~~
None

RPC API impact
--------------

None

Driver API impact
-----------------

A new method will be added to ``ManagementInterface``:

.. code-block:: python

    def get_sensor_data_async(self, node):
        """Collect sensor data asynchronously if supported.

        If implemented, this method must be functionally equivalent to its
        synchronous counterpart (which still **should** be present in case
        of operator disabling asynchronous collection).

        :return: an awaitable that yields collected sensor data.
        :raises: NotImplementedError if asynchronous collection is not
            supported. The exception must be raised synchronously!
        """
        raise NotImplementedError

.. note::
   The base implementation is not marked as ``async``. This is on purpose,
   otherwise the exception won't be raised until the executor runs the task.
   Real implementation may be marked as ``async`` or return an awaitable
   in any other way.

Nova driver impact
------------------

None

Ramdisk impact
--------------

None

Security impact
---------------

Enrolling a large number of nodes per conductor is already a reliable way of
making Ironic inoperational, this proposal does not change this aspect.

Other end user impact
---------------------

None

Scalability impact
------------------

The feature is opt-in, so nothing changes by default.

An option to run sensor collection asynchronously allows operators to trade
memory and CPU for a (much) higher parallelism. Currently, collecting sensors
for hundreds (let alone thousands) of nodes on a single conductor is either
very slow or requires an enormous number of native threads, with increasing the
number of conductors being the only alternative.

Performance Impact
------------------

The feature is opt-in, so nothing changes by default.

In my experiments, collecting sensor data from 3500 of fake nodes is very
resource intensive. The prototype_ script consumed a whole CPU core and 2-3 GiB
of RAM depending on the batch size (interestingly, collecting from all nodes at
once was not where the RAM consumptions peaked, it was rather around batches of
1000). The operators will need to be prepared (and we'll need to document it
thoroughly) that high parallelism does not come for free.

Other deployer impact
---------------------

A new option will be added:

* ``[sensor_data]enable_async_collection`` (boolean, defaults to ``false``).
  This option will enable the logic proposed in this specification.

  Changing the default to ``true`` in the future is possible but is outside of
  the scope of this specification.

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  dtantsur

Other contributors:
  <IRC handle, email address, None>

Work Items
----------

* Add an asynchronous Redfish client to Ironic.
* Add an asynchronous session cache.
* Implement ``get_sensor_data_async`` for Redfish.
* Update the scaling guide.

Dependencies
============

None

Testing
=======

Since Bifrost already has support for ironic-prometheus-exporter_, we can use
it as a testing platform. I would like to add support for completely fake nodes
(using the sushy-tools' fake backend) and create a job with thousands of them.

I will advocate for the feature to be enabled in Metal3 when the sensor
collection is enabled (it's off by default). With its single conductor in the
most common configuration, Metal3 cannot reasonably handle a large number of
nodes otherwise.

Real world testing on the expected scale is out of reach for the community.

.. _ironic-prometheus-exporter: https://opendev.org/openstack/ironic-prometheus-exporter

Upgrades and Backwards Compatibility
====================================

The new feature will be opt-in and will not affect upgrades.

Documentation Impact
====================

The scaling guide will need to be updated with the considerations from this
specification, as well as any new findings. We'll make sure that an operator
can make an informed decision and whether to enable this feature or not.

References
==========
