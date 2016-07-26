..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

======================================================
Add notifications about resources CRUD and node states
======================================================

https://bugs.launchpad.net/ironic/+bug/1606520

This spec proposes addition of new notifications to ironic: CRUD (create,
update, or delete) of resources and node state changes for provision state,
maintenance and console state.

Problem description
===================

Resource indexation services like Searchlight [#]_ require notifications about
creation, update or deletion of a resource. Currently CRUD notifications are
not implemented in ironic. Creating an efficient plugin for Searchlight is
impossible without these notifications.
Ironic node notifications for provision state, maintenance and console
state also could be used by Searchlight plugin in order to keep Searchlight's
index of ironic resources up-to-date.

Proposed change
===============

Node CRUD notifications
-----------------------

The following event types will be added:

* "baremetal.node.create.success";

* "baremetal.node.update.start";

* "baremetal.node.update.end";

* "baremetal.node.update.error";

* "baremetal.node.delete.start";

* "baremetal.node.delete.end";

* "baremetal.node.delete.error".

Priority level - INFO or ERROR (for "error" status). Payload contains all
fields from base ``NodePayload`` with additional fields: ``chassis_uuid``,
``instance_info``, ``driver_info``. Secrets in the node fields will be masked.
``raid_config`` and ``target_raid_config`` fields are excluded because they can
contain low-level disk and vendor information. If/when there is a use case for
them, they can be added in the future. All these notifications will be
implemented at the API level.

Port CRUD notifications
-----------------------

The following event types will be added:

* "baremetal.port.create.success";

* "baremetal.port.update.start";

* "baremetal.port.update.end";

* "baremetal.port.update.error";

* "baremetal.port.delete.start";

* "baremetal.port.delete.end";

* "baremetal.port.delete.error".

Priority level - INFO or ERROR (for "error" status).
Payload contains these fields: ``uuid``, ``node_uuid``, ``address``, ``extra``,
``local_link_connection``, ``pxe_enabled``, ``created_at``, ``updated_at``.
These notifications will be implemented at the API level. In addition,
"baremetal.port.create.success" will be emitted by the ironic-conductor service
when driver creates a port (examples are [#]_ and [#]_).

Chassis CRUD notifications
--------------------------

The following event types will be added:

* "baremetal.chassis.create.success";

* "baremetal.chassis.update.success";

* "baremetal.chassis.delete.success".

Priority level - INFO. Payload contains these fields: ``uuid``, ``extra``,
``description``, ``created_at``, ``updated_at``. All these notifications will
be implemented at the API level.

Node provision state notifications
----------------------------------

Will be implemented via TaskManager methods (and emitted by the
ironic-conductor service).

Types of events for node provision state:

* "baremetal.node.provision_set.start";

* "baremetal.node.provision_set.end";

* "baremetal.node.provision_set.error";

* "baremetal.node.provision_set.success".

Types of state changing in ironic and corresponding events:

* Start transition, spawning a working thread: "start" notification with
  INFO level.

* End transition, cleaning ``target_provision_state``: "end" notification with
  INFO level.

* Error events processing: "error" notification with ERROR level.

* Change ``provision_state`` without starting a worker that is not "end" or
  "error": "success" notification with INFO level. Examples are
  DEPLOYING <-> DEPLOYWAIT, AVAILABLE -> MANAGEABLE.

Payload contains all fields from base ``NodePayload`` with additional fields:
``instance_info``, ``previous_provision_state``,
``previous_target_provision_state``, ``event`` (FSM event that triggered the
state change).
To efficiently use the provision state notifications all related node changes
(like setting of ``last_error``, ``maintenance``) should be done before event
processing.

Node maintenance notifications
------------------------------

The following event types will be added:

* "baremetal.node.maintenance_set.start";

* "baremetal.node.maintenance_set.end";

* "baremetal.node.maintenance_set.error".

Priority level - INFO or ERROR (for "error" status). Payload contains all
fields from base ``NodePayload``. All these notifications will be implemented
at the API level and reflect maintenance changes to a node due to a user
request. There won't be any explicit node maintenance notifications for
maintenance changes done internally by ironic. Since these internal changes
occur as a result of trying to change the node's state (e.g. provision, power),
one of the other notifications that is emitted will "cover" these internal
maintenance changes.

Node console notifications
--------------------------

The following event types will be added:

* "baremetal.node.console_set.start";

* "baremetal.node.console_set.end";

* "baremetal.node.console_set.error".

Priority level - INFO or ERROR (for "error" status). Payload contains all
fields from base ``NodePayload``. All these notifications will be implemented
in the ironic-conductor, because setting of a node's console is an asynchronous
request, so ironic-conductor can easily emit notifications for the start/end of
the change.

Alternatives
------------

Periodically polling ironic resources via API.

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

If notifications are enabled, they can create high load on the message bus
during node deployments on large environments.

Performance Impact
------------------

None

Other deployer impact
---------------------

Deployers should set already existing ``notification_level`` config options
properly.

Developer impact
----------------

* If developer creates resources in the driver, proper notification should be
  emitted.

* For provision state change all related node updates should be done before
  event processing.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  * yuriyz

Other contributors:
  * vdrok
  * mariojv

Work Items
----------

* Implement node provision state change notifications.

* Implement CRUD notifications and node maintenance notifications.

* Implement console notifications.

* Add notifications to the current ironic code that creates resources in the
  drivers.

* Fix ironic code with node updates after event processing.

Dependencies
============

Patch with base ``NodePayload`` [#]_.

Testing
=======

Unit tests will be added.

Upgrades and Backwards Compatibility
====================================

None

Documentation Impact
====================

New notifications feature will be documented.

References
==========

.. [#] https://wiki.openstack.org/wiki/Searchlight
.. [#] https://github.com/openstack/ironic/blob/master/ironic/drivers/modules/irmc/inspect.py#L177
.. [#] https://github.com/openstack/ironic/blob/master/ironic/drivers/modules/ilo/inspect.py#L56
.. [#] https://review.openstack.org/#/c/321865/
