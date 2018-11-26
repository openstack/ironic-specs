..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==============
Allocation API
==============

https://storyboard.openstack.org/#!/story/2004341

This spec proposed creating of API for *allocation* of nodes for deployment.

Problem description
===================

The users of standalone ironic do not have an out-of-box means to find a
suitable node to deploy onto. The metalsmith_ project was created to add this
gap short-term, but it is not suitable for consumer code that is not written in
Python. A potential consumer is a K8S provider for standalone ironic.

The API user story is as follows:

   Given a resource class and, optionally, a list of required traits, return me
   an available bare metal node and set ``instance_uuid`` on it to make it as
   reserved.

Proposed change
===============

Overview
--------

This RFE proposed a new ReST API endpoint ``/v1/allocations`` that will
initially allow creating and deleting *Allocation* resources.

Two implementations of the allocation process are planned:

#. Via the database, similar to how metalsmith_ now operates.
#. Via the Placement_ service, similar to how nova currently operates.

This spec concentrates on the API design and the first (standalone) case.

Allocation process
------------------

An allocation happens as follows:

#. An API client sends a ``POST /v1/allocations`` request, specifying a
   resource class, and optionally traits and node UUID.

#. The allocation request is routed to a random available conductor.

#. The conductor creates an *Allocation* object in the database with
   ``state=allocating`` and ``conductor_affinity=<host name>``.

#. A thread is spawned for the remaining allocation process, and the allocation
   object is returned to the caller.

Allocation: database backend
----------------------------

The following actions are done by the conductor handling the allocation when
database is used as backend (the only option in this spec):

#. Fetch list of nodes from the database with:

   * ``provision_state=available``
   * ``maintenance=False``
   * ``power_state!=None``

     .. note::
      This is required for compatibility with really old API versions that
      allow creating nodes directly in the ``available`` state.

   * ``instance_uuid=None``
   * ``resource_class=<requested resource class>``
   * ``uuid`` in the list of candidate nodes (if provided)
   * requested traits are a superset of node traits

#. If the list is empty, set allocation's ``state`` to ``error`` and
   ``last_error`` to the explanation.

#. Shuffle the list, so that several processes do not try reserving nodes in
   the same order.

#. Acquire a lock on the first node. If locking succeeds, check that the
   assumptions are still valid about this node, and reserve it by setting its
   ``instance_uuid`` to the ``uuid`` of the allocation. In the same database
   transaction:

   * set allocation's ``node_id`` to the node's ID,
   * set allocation's ``state`` to ``active``,
   * set node's ``allocation_id`` to the allocation's ID,
   * add matched traits to node's ``instance_info``.

   .. note::
      Since the conductor may not have the hardware type for the selected node,
      we will update TaskManager to avoid constructing the ``driver`` object.

#. If something fails on the previous step, proceed to the next node.
   If no more nodes are left, set the allocation's ``state`` to ``error`` and
   ``last_error`` to the explanation.

Deallocation: database backend
------------------------------

The deallocation process will in one transation:

* unset node's ``instance_uuid``,
* unset node's ``allocation_id``,
* delete the allocation.

The deallocation is triggered either explicitly via API or when a node is torn
down (at the same time when node's ``instance_uuid`` and ``instance_info`` are
purged).

.. note::
   In the future we might consider supporting *sticky allocations* which
   survive node's tear down. This is outside the scope of this spec.

There is one important difference between using just ``instance_uuid`` and
using the allocation API: ``instance_uuid`` can be set and unset for ``active``
nodes, while for allocations it will be forbidden. The reason is that with the
future Placement backend removing an allocation would mark the node as
available in Placement.

HA and take over
----------------

* When a conductor restarts, it fetches allocations with

  * ``conductor_affinity=<host name>``
  * ``state=allocating``

  and starts the allocation procedure for each of them.

* If the conductor handling an allocation stops without a replacement, the
  reservation becomes orphaned. All conductors periodically fetch list of
  allocations belonging to dead conductors and each tries to resume them.

  First, it tries to update the ``conductor_affinity`` by doing something
  like::

     UPDATE allocations SET conductor_affinity=<new host name>
        WHERE id=<allocation ID> AND conductor_affinity=<dead host name>

  If the query updated 1 row, we know that the new conductor now manages the
  allocation. Otherwise we know that another conductor took it over.

* To avoid rare races with this take over procedure, the normal update will
  also look like::

    UPDATE allocations SET <new values>
        WHERE id=<allocation ID> AND conductor_affinity=<current host name>

Alternatives
------------

* Make each consumer invent their own allocation procedure or use metalsmith_.

* Write a new service for managing reservations (probably based on metalsmith_
  code base).

* Make the API blocking and avoid having states for allocations. Such an
  approach would result in easier API and implementation, but it can be
  problematic when using an external system, such as Placement_, as a backend,
  since the requests to it make block the RPC thread.

  Additionally, the asynchronous design will make it easier to introduce a bulk
  allocation API in the future, if we decide so.

Data model impact
-----------------

Introduce a new database/RPC object *Allocation* with the following fields:

* ``id`` internal integer ID, not exposed to users.
* ``uuid`` unique UUID of the allocation.
* ``name`` unique name of the allocation, follows the same format as node's
  names.

  .. note:: This field is useful, for example, for systems using host names,
            like metalsmith_.

* ``node_id`` reserved node ID (can be ``null``) - foreign key to the ``nodes``
  table.
* ``updated_at``/``created_at`` standard update/creation date time fields.
* ``resource_class`` mandatory requested resource class.
* ``candidate_nodes`` list of node UUIDs to choose from (can be ``null``).

  .. note:: This allows a caller to pre-filter nodes by arbitrary criteria.

* ``state`` allocation state, see `State Machine Impact`_.
* ``last_error`` last error message.
* ``conductor_affinity`` internal field, specifying which conductor currently
  handles this allocation.

Introduce a helper table ``allocation_traits`` mapping an allocation to its
requested traits (very similar to ``node_traits``).

Update the ``nodes`` table with a new foreign key ``allocation_id``. It will be
set to a ID of a corresponding allocation. Unlike ``instance_uuid``, it will
only be set when an allocation is created. If ``allocation_id`` is not empty,
``instance_uuid`` will hold the UUID of the corresponding allocation (the
opposite is not necessary true).

State Machine Impact
--------------------

No impact on the node state machine.

This RFE introduces a simple state machine for *Allocation* objects, consisting
of three states:

* ``allocating`` allocation is in progress (initial state).
* ``active`` allocation active.
* ``error`` allocation failed.

In the initial version only the following paths are possible:

* from ``allocating`` to ``active`` on success.
* from ``allocating`` to ``error`` on failure.

In the future we may allow moving from ``error`` back to ``allocating`` to
retry the allocation.

REST API impact
---------------

* ``POST /v1/allocations`` create an allocation.

  The API accepts a JSON object. The following field is mandatory:

  * ``resource_class`` requested node's resource class.

  The following fields are accepted:

  * ``uuid`` to create an allocation with the specific UUID.
  * ``candidate_nodes`` to limit the query to one of these nodes.

    .. note:: This value is converted from names to UUIDs internally.

  * ``traits`` list of requested traits.
  * ``name`` allocation name.

  The normal response is HTTP CREATED with the response body being the created
  allocation representation. An allocation is created in the ``allocating``
  state.

  Error codes:

  * 400 Bad Request if

    * any node from ``candidate_nodes`` cannot be found (by name or UUID).
    * the ``resource_class`` value is invalid.
    * ``traits`` is provided and is not a list of valid trait strings.
    * ``name`` is not an accepted name.

  * 406 Conflict if

    * the provided ``uuid`` is not unique or matches ``instance_uuid`` of any
      node.

    * the provided ``name`` is not unique.

* ``GET /v1/allocations`` list allocations.

  Parameters:

  * ``fields`` list of fields to retrieve for each allocation.
  * ``state`` filter allocations by the state.
  * ``resource_class`` filter allocations by resource class.
  * ``node`` filter allocations by node UUID or name.

  Error codes:

  * 400 Bad Request if

    * ``state`` is invalid.
    * ``resource_class`` is invalid.
    * ``node`` does not exist.
    * any of the requested fields is invalid.

* ``GET /v1/allocations/<uuid or name>`` retrieve an allocation.

  Parameters:

  * ``fields`` list of fields to retrieve.

  Error codes:

  * 400 Bad Request if any of the requested fields is invalid.
  * 404 Not Found if the allocation is not found.

* ``DELETE /v1/allocations/<uuid or name>`` remove the allocation and release
  the node.

  No request or response body. Response code is HTTP 204 No Content.

  Error codes:

  * 404 Not Found if the allocation is not found.
  * 409 Conflict if the corresponding node is ``active`` or is in a state where
    updates are not allowed.

  .. note::
      This request will succeed only for real allocations. It will not be
      possible to unset ``instance_uuid`` created without an allocation (i.e.
      by direct ``PATCH`` to a node) using this API.

* ``GET /v1/nodes/<node UUID or name>/allocation`` get allocation associated
  with the node.

  Parameters:

  * ``fields`` list of fields to retrieve.

  The response body is the *Allocation* object representation.

  Error codes:

  * 404 Not Found if

    * the node cannot be found.
    * there is no allocation for the node.

  * 400 Bad Request if

    * node has ``instance_uuid`` that does not correspond to any allocation.
    * any of the requested fields is invalid.

* Update ``GET /v1/nodes``, ``GET /v1/nodes/detail`` and ``GET /v1/nodes/<node
  UUID or name``:

  Expose the new ``allocation_uuid`` field (converted from the node's
  ``allocation_id``).

* Update ``PATCH /v1/nodes/<node UUID or name>``:

  If ``instance_uuid`` is unset and the current value corresponds to an
  allocation:

  * if node is ``active`` or in a state that disallows updates, and
    ``maintenance`` mode is off, return HTTP 409 Conflict,
  * otherwise delete the allocation.

  If ``instance_uuid`` is set, do NOT create an allocation, keep the previous
  behavior.

  .. note::
      This is needed to avoid affecting the nova virt driver. This decision may
      be revisited in future API versions.

  The ``allocation_uuid`` field is read-only, an attempt to change it directly
  will result in HTTP 400 (Bad Request).

* Update ``DELETE /v1/nodes/<node UUID or name>``:

  If a node is deleted with allocation (possible only in maintenance mode), the
  allocation is deleted as well.

Client (CLI) impact
-------------------

"ironic" CLI
~~~~~~~~~~~~

None.

"openstack baremetal" CLI
~~~~~~~~~~~~~~~~~~~~~~~~~

The matching commands will be created::

   openstack baremetal allocation create --resource-class <class> \
      [--trait <trait>] [--trait <trait>] [--uuid <uuid>] [--name <name>]
   openstack baremetal allocation list [--state <state>] [--fields <fields>]
      [--resource-class <class>] [--node <UUID or name>]
   openstack baremetal allocation get <uuid or name> [--fields <fields>]
   openstack baremetal allocation delete <uuid or name>

The ``allocation_uuid`` field will be exposed.

RPC API impact
--------------

Two new RPC calls are introduced:

* Creating an allocation

  .. code-block:: python

      def create_allocation(self, context, allocation):
         """Create an allocation.

         Creates the provided allocation in the database, then starts a thread
         to process it.

         :param context: context
         :param allocation: allocation object.
         """

* Deleting an allocation

  .. code-block:: python

      def destroy_allocation(self, context, allocation):
         """Destroy an allocation.

         Removes the allocation from the database and releases the node.

         :param context: context
         :param allocation: allocation object.
         """

metalsmith impact
-----------------

The metalsmith_ project implements a superset of the proposed feature on a
client side. After this API is introduced, metalsmith will switch the
``reserve_node`` call to using it in the following way:

* If the request contains a ``resource_class`` and, optionally, ``traits`` and
  candidate nodes, the new API will be used.

* If the request contains anything not supported by the new API, metalsmith
  will continue client-side node filtering, and will create an allocation with
  a list of suitable nodes.

Driver API impact
-----------------

None

Nova driver impact
------------------

None

In the future we may use the allocation API in the nova driver, but there are
no plans for it now. Currently going through the allocation API will result in
an attempt of double allocation in Placement_ if Placement is used as an
allocation backend.

Ramdisk impact
--------------

None

Security impact
---------------

None

Other end user impact
---------------------

None

Scalability impact
------------------

None

Performance Impact
------------------

A new periodic task will run on each conductor to periodically check for
stalled reservations belonging to dead conductors. The default period will be
60 seconds. It will be possible to disable it, in which case the allocations
may get stuck forever if their assigned conductor dies.

Other deployer impact
---------------------

None

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  dtantsur

Work Items
----------

* Add new tables and the *Allocation* RPC object.

* Add RPC for allocating/deallocating.

* Add API for allocations creation and deletion, and API reference.

* Update conductor starting procedure to check for unfinished allocations.

* Add a periodic task to check for orphaned unfinished allocations.

Dependencies
============

None

Testing
=======

* Unit tests and Tempest API will be provided.

* The standalone integration tests will be updated to use the new API.

* We can add support for the new API to bifrost_ (e.g. via metalsmith), and
  test it in a bifrost CI job.

Upgrades and Backwards Compatibility
====================================

This change is fully backward compatible. Code using ``instance_uuid`` for
allocations is not affected.

Documentation Impact
====================

API reference will be provided.

References
==========

.. _metalsmith: https://docs.openstack.org/metalsmith/latest/
.. _Placement: https://docs.openstack.org/nova/latest/user/placement.html
.. _bifrost: https://docs.openstack.org/bifrost/latest/
