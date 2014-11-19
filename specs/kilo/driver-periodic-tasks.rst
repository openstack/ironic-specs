..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==============================================
Allow drivers to have their own periodic tasks
==============================================

https://blueprints.launchpad.net/ironic/+spec/driver-periodic-tasks

This spec suggests allowing Ironic drivers to define their own periodic tasks.

Problem description
===================

Currently Ironic conductor can run periodic tasks in a green thread. However,
if some driver requires a driver-specific task to be run, it needs to patch
conductor manager, which is not acceptable.

Proposed use cases:

* For `in-band inspection using discoverd`_ driver-specific periodic task
  would be used to poll discoverd for inspection status.

* For DRAC RAID implementation driver-specific periodic task may be used again
  to poll status information from BMC.

* For deploy drivers supporting long-running ramdisks (e.g. IPA)
  a driver-specific periodic task may be used to poll for dead ramdisks
  when nothing is deployed on a node.

.. _in-band inspection using discoverd: http://specs.openstack.org/openstack/ironic-specs/specs/kilo/inband-properties-discovery.html

Proposed change
===============

* Create a new decorator ``@ironic.drivers.base.driver_periodic_task`` to mark
  driver-specific periodic tasks. It will mostly delegate it's job to
  ``@periodic_task.periodic_task`` with the exception of additional argument
  ``parallel`` defaulting to ``True``.

  Until `parallel periodic tasks`_ is implemented in Oslo, ``parallel=True``
  will be implemented by wrapping the task into a function calling
  ``eventlet.greenthread.spawn_n`` to make it run in a new thread. It will
  also use Eventlet semaphore to prevent several instances of the same task
  from running simultaneously.

* Modify ``ConductorManager.__init__`` to collect periodic tasks from each
  present interface of each driver. It should use existing markers added by
  ``@periodic_task.periodic_task`` to a method to detect periodic task.
  Information about a periodic tasks should be placed in ``_periodic_spacing``
  ``_periodic_last_run`` and ``_periodic_tasks`` attributes of the conductor.

* The future modification should be adding something like ``add_periodic_task``
  to a ``PeriodicTasks`` class in Oslo. The only thing that prevents me from
  suggesting it is that ``PeriodicTasks`` class is under
  `graduation into a new oslo.service`_ now. No changes are allowed
  at the moment.  This should be done as a refactoring step later.

* Once ``oslo.service`` is graduated and `parallel periodic tasks`_ are
  implemented there, get rid of the work around inside
  ``driver_periodic_task``, and switch to using parallel periodic tasks from
  Oslo.

.. _graduation into a new oslo.service: https://review.openstack.org/#/c/142659/
.. _parallel periodic tasks: https://review.openstack.org/#/c/134303/

Alternatives
------------

* Each time modify conductor when we need a periodic task. That requires a
  consensus on how to make it in a generic way.

* Just use ``LoopingCall``. I believe that this approach is less controlable
  (in terms of how many threads we run, how many requests we make to e.g. DRAC
  BMC etc) and leads to code duplication.

Data model impact
-----------------

None

REST API impact
---------------

None

RPC API impact
--------------

None

Driver API impact
-----------------

No impact for the driver API itself.

Nova driver impact
------------------

None

Security impact
---------------

None

Other end user impact
---------------------

None

Scalability impact
------------------

None expected

Performance Impact
------------------

This will allow large number of periodic tasks to be added to Ironic.
Defaulting to ``parallel=True`` should minimize effect on performance.
The decision of whether to add or not a new tasks is anyway to be done on a
case-by-case basis.

Other deployer impact
---------------------

None.

Note that periodic_max_workers and rpc_thread_pool_size configuration options
are not affecting driver-specific periodic tasks.

Developer impact
----------------

Driver developers can mark any method as a ``@driver_periodic_task``.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Dmitry Tantsur, LP: divius, IRC: dtantsur

Work Items
----------

* Add ``ironic.drivers.base.driver_periodic_task`` decorator

* Modify ``ConductorManager.__init__``.

* Propose ``add_periodic_task`` to ``oslo.service``.

Dependencies
============

* `parallel periodic tasks`_ are nice to have, but is not a hard
  dependency.

Testing
=======

Unit testing will be conducted.

Upgrades and Backwards Compatibility
====================================

None

Documentation Impact
====================

Update driver interface documentation to mention how to create periodic tasks.

References
==========

Parallel periodic tasks spec: https://review.openstack.org/#/c/134303/
