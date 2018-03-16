..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

======================
Add Inspect Wait State
======================

https://bugs.launchpad.net/ironic/+bug/1725211

The spec proposes adding a new ``inspect wait`` state to ironic state machine.

Problem description
===================

The in-band inspection is an asynchronous process [#]_ that isn't currently
handled through a "waiting" state. This is a discrepancy from the rest of
the asynchronous **ironic** states and may comprise a problem for future
features such as aborting the introspection [#]_ or merging **ironic** and
**ironic-inspector** [#]_;

Proposed change
===============

Let's therefore have a new passive state in the **ironic** state machine, the
``inspect wait`` state.

For asynchronous inspection like ironic inspector driver, ironic conductor
will move node from ``manageable`` to ``inspecting`` state when an inspect
request is issued, then the ironic conductor moves node to ``inspect-wait``
state if ``InspectInterface.inspect_hardware`` returns ``INSPECTING``.

Add a new option ``[conductor]inspect_wait_timeout`` to guard the
``inspect wait`` state, the default value is 1800 seconds as same as
``[conductor]inspect_timeout``. If the hardware inspection is timed out in the
state of ``inspect wait``, node will be moved from ``inspect wait`` to
``inspect failed``.

The existing ``[conductor]inspect_timeout`` will be deprecated.

The ``inspect wait`` state will be set as an allowed state when updating
ironic node, port and portgroup.

As ironic-inspector checks node provision state before starting inspection,
the ``inspect wait`` state needs to be added to ironic-inspector as a valid
state.

Alternatives
------------

There are no alternatives to this feature.

Data model impact
-----------------

None

State Machine Impact
--------------------

A new unstable state ``inspect wait`` will be added to ironic state machine.

Following state transitions will be added:

#. ``inspecting`` to ``inspect wait`` with event ``wait``.
#. ``inspect wait`` to ``inspect failed`` with event ``fail``.
#. ``inspect wait`` to ``manageable`` with event ``done``.

REST API impact
---------------

API microversion will be bumped to hide the new ``inspect wait`` state to
clients with older microversion, this will be done in the
``update_state_in_older_versions``.

Node related API endpoints will be affected:

* POST /v1/nodes
* GET /v1/nodes
* GET /v1/nodes/detail
* GET /v1/nodes/{node_ident}
* PATCH /v1/nodes/{node_ident}

For clients with older microversion, the provision state of ``inspect wait``
will be changed to ``inspecting``, there is no other impact to API behaviors.

Client (CLI) impact
-------------------

As the compatibility is handled at ironic API, CLI is not affected.

"ironic" CLI
~~~~~~~~~~~~

None

"openstack baremetal" CLI
~~~~~~~~~~~~~~~~~~~~~~~~~

None

RPC API impact
--------------

None

Driver API impact
-----------------

None

Nova driver impact
------------------

None

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

None

Other deployer impact
---------------------

Add a new option ``[conductor]inspect_wait_timeout`` to guard timeout of state
``inspecting``, defaults to 150 seconds.

Developer impact
----------------

This feature has no impact on synchronous inspection, that includes most of
OOB drivers. For in-band inspection, the new state has to be considered.

After this spec is implemented, drivers based on asynchronous inspection have
to be changed accordingly, that includes in-band inspection and out-of-band
inspection (if there is any).

``OneViewInspect`` in the tree is implemented based on ironic inspector
interface, its state transition from ``inspecting`` to ``inspect wait`` is
handled by ironic inspector, but ``inspect wait`` state needs to be added to
status checking.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  kaifeng

Other contributors:
  vetrisko

Work Items
----------

#. Add ``inspect wait`` state and state transitions to ironic state machine.
#. Apply state change in the ``_check_status`` of ironic inspector and
   ``OneViewInspect`` driver.
#. Add new option ``inspect_wait_timeout``, and deprecate ``inspect_timeout``.
#. Handle timeout of state ``inspect wait`` in the conductor periodic task
   ``_check_inspect_timeouts``, allow updating node, port and portgroup when
   node is in the ``inspect wait`` state.
#. Handle API microversion compatibility.
#. Add ``inspect wait`` to ironic-inspector as a valid state.
#. Update documents, see `Documentation Impact`_ for details.

Dependencies
============

None

Testing
=======

Unit tests will be added, API change will be covered by tempest tests.

Upgrades and Backwards Compatibility
====================================

The API backwards compatibility is guarded by microvision.

Documentation Impact
====================

The state diagram will be automatically generated from source.
Update ironic states document to address the new state, and the semantic
change of current ``inspecting`` state.

References
==========

.. [#] https://docs.openstack.org/ironic-inspector/pike/user/http-api.html#start-introspection
.. [#] https://review.openstack.org/#/c/482867/16/specs/approved/inspection-abort.rst
.. [#] https://etherpad.openstack.org/p/inspector-queens-virtual-ptg
