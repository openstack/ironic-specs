..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==================================
Support baremetal inspection abort
==================================

https://bugs.launchpad.net/ironic/+bug/1703089

This spec aims to support aborting node inspection from ironic API. A
dependency of ``inspect wait`` state in [#]_ is required for this spec to
continue.

Problem description
===================

Currently, we can't abort the process of node inspection from ironic API.
When a node is not properly setup under inspection network, admins can only
wait it to fail after specified timeout, or abort the inspection process
from ironic inspector API/CLI (if the in-band inspect interface ``inspector``
is in use).

Although the inspection state will be synchronized to ironic by periodic task,
it's not consistent for an operation started from ironic, then stopped by
inspector, furthermore, it creates a little delay of time. Node state is
inconsistent between ironic and inspector until next state synchronization.
The default time interval for ironic-inspector state synchronization is 60
seconds, it may vary depending on user configuration.


Proposed change
===============

Add state transition of ``inspect wait`` to ``inspect failed`` to state
machine, add support to ironic to allow the verb ``abort`` can be requested
when node in ``inspect wait`` state.

Add a method named ``abort`` into ``InspectInterface``, so that inspect
interface can provide implementation to support inspection abort. The default
behavior is to raise an ``UnsupportedDriverExtension`` exception. Implement the
abort operation for ``inspector`` inspect interface.

When an abort operation is requested from ironic API, and the node in the
state of ``inspect wait``, ironic calls ``abort`` method from inspect
interface of driver API, and moves node state to ``inspect failed`` if the
method executed successfully.

Note that, the abort request to ironic-inspector is asynchronous, ironic will
move node to ``inspect failed`` once the request is accepted (202), disregard
if the operation at ironic-inspector is performed successfully. This reduces
the design complexity for this feature by handling failure at the side of
ironic-inspector.

From the point of view of ironic-inspector, every inspect request will refresh
local cache for the node, it assures that node state is in sync when starting
node inspection. However, inconsistent node state do exist if abort request
is accepted but not performed successfully at ironic-inspector. This
inconsistency will be eliminated by ironic-inspector node cache clean up when
timeout is reached.


Involved changes are:

* Add a method named ``abort()`` to base inspect interface (InspectInterface).

* Implement ``abort()`` for ``inspector`` inspect interface.

* Implement the logic for ironic handling the verb ``abort`` when provisioning
  state is ``inspect wait``.


Alternatives
------------

* Wait for ``inspect fail`` after specified timeout value.

* Request through ironic-inspector api or
  ``openstack baremetal introspection abort`` command. Be aware that it's only
  viable when using ironic inspector as inspect interface. Other inspect
  interfaces like out-of-band inspection may have different approach to achieve
  the same goal, that is beyond the scope of this spec.


Data model impact
-----------------

None


State Machine Impact
--------------------

Add a state transition of ``inspect wait`` to ``inspect failed`` with event
``abort`` to ironic state machine.

REST API impact
---------------

Modify provision state API to support the transition described in this spec.
API microversion will be bumped. For clients with earlier microversion, the
verb ``abort`` is not allowed when a node is in ``inspect wait`` state.

* PUT /v1/nodes/{node_ident}/states/provision

  * The same JSON Schema is used to ``abort`` a node in ``inspecting`` state::

      {
        "target": "abort"
      }

  * For client with earlier microversion, 406 (Not Acceptable) is returned

  * For client with supported microversion

    * 202 (Accepted) is returned if request accepted
    * 400 (Bad Request) is returned if current inspect interface does not
      support abort


Client (CLI) impact
-------------------

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

A new method ``abort`` will be added to ``InspectInterface`` in base.py, the
default behavior is to raise the exception ``UnsupportedDriverExtension``::

    def abort(self, task):
        raise exception.UnsupportedDriverExtension(
            driver=task.node.inspect_interface,
            extension='abort')


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

For multiple nodes under inspection in a notable scale, it will reduce a little
time costs in case of inspection retry.


Performance Impact
------------------

None


Other deployer impact
---------------------

Deployers can abort hardware introspection through ironic API/CLI, besides
the inspector API/CLI, for nodes using inspector as the (in-band) inspection
interface.


Developer impact
----------------

None


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  kaifeng


Work Items
----------

* Add transition of ``inspect wait`` to ``inspect failed`` via ``abort``.
* Add a new method ``abort()`` to the base inspect interface.
* Add the abort implementation to ironic ``inspector.Inspector``.
* Implement the abort logic in ironic conductor.


Dependencies
============

None


Testing
=======

Tempest test will be added to test the REST API change.


Upgrades and Backwards Compatibility
====================================

API will be bumped for backward compatibility. Client requests with
microversion before this feature will be treated identically.


Documentation Impact
====================

Related documents and state machine diagram will be updated accordingly.


References
==========

.. [#] https://specs.openstack.org/openstack/ironic-specs/specs/approved/inspect-wait-state.html
