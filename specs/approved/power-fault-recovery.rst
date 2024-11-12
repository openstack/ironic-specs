..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

====================
Power fault recovery
====================

https://storyboard.openstack.org/#!/story/1596107

This spec proposes adding a new node field to reflect any faults detected
by the system. For nodes put into maintenance mode due to power-sync
failures, this proposes a mechanisms to try to recover the nodes from
the failure.

Problem description
===================

Currently, ironic's API and data model do not differentiate between ironic
setting maintenance on a node (for instance, when cleaning fails, or when the
power status loop cannot contact the BMC) and an operator setting maintenance
on a node (an explicit API action).

This situation makes it difficult to apply any power fault recovery mechanism.

Proposed change
===============

A string field named ``fault`` will be added to ironic's data model for a Node.
It will be used to record any detected faults.

The field will be set to one of the following values, depending on the
situation (when ironic puts the node into maintenance due to one of these):

* ``power failure``: when a node is put into maintenance due to power sync
  failures that exceed max retries.
* ``clean failure``: when a node is put into maintenance due to failure of a
  cleaning operation.
* ``rescue abort failure``: when a node is put into maintenance due to failure
  of cleaning up during rescue abort.
* None: there is no fault detected for the node; this is the default value.
  Since the field is set to a fault when ironic puts the node into maintenance
  due to a fault, it gets set to None when the node is taken out of
  maintenance (by ironic or the user).

  For nodes that were in maintenance prior to upgrading to this release,
  the field will also be None, since we don't know for sure, if (or what)
  there had been a fault. Even if there had been, we don't know whether the
  operator wants the node in maintenance for other reasons as well.

A periodic task will be added to the conductor. This will operate on nodes
with ``node.fault == power failure``. It will try to get the node's power
state. If successful, the node will be taken out of maintenance.

An integer configuration option named
``[conductor]power_failure_recovery_interval`` will be added. This is the
interval (number of seconds) between each run of the periodic task. The
default value is 300 seconds (5 minutes). Setting it to 0 will disable
power fault recovery.


Alternatives
------------

Proposals have already been made and rejected to use a combination of
maintenance being set and a given maintenance_reason or last_error to do
self-healing due to inconsistency.

Specific faults support [#]_ is proposed but it's too big and to-date, no
consensus has been reached on it.

An earlier version of this spec had proposed a ``maintenance_type``
field for the node, instead of a ``fault`` field. We prefer the
``fault`` field since it better reflects that it is about faults.
``maintenance_type`` caused the field to be tied in with the
existing ``maintenance`` and ``maintenance_reason`` fields.
Using ``fault`` makes it distinct from ``maintenance``; it will
make it easier to move forward in the future, should we decide to
provide more enhancements that are fault-related, or to separate
the notion and handling of faults from maintenance (which some
would argue should only be operator-initiated).

Data model impact
-----------------

A string field named ``fault`` will be added to ironic's node table.

The field will be added to ``Node`` object; object version will be
incremented.

State Machine Impact
--------------------

None

REST API impact
---------------

The field ``fault`` will be added to ``Node`` API object, ironic
API version will be bumped.

Node-related API endpoints will be affected:

* POST /v1/nodes
* GET /v1/nodes
* GET /v1/nodes/detail
* GET /v1/nodes/{node_ident}
* PATCH /v1/nodes/{node_ident}

For requests with older microversion, ``node.fault`` is hidden from
the response. This will be done in the ``hide_fields_in_newer_versions()``.

Field ``fault`` is read-only from the API, and can only be modified
internally. Any POST/PATCH request to Node with ``fault`` set will
get 400 (Bad Request).

There is no other impact to API behaviors.


Client (CLI) impact
-------------------

"ironic" CLI
~~~~~~~~~~~~

None

"openstack baremetal" CLI
~~~~~~~~~~~~~~~~~~~~~~~~~

The CLI will be updated to support field ``fault``, guarded
by ironic API microversion.

RPC API impact
--------------

None

Driver API impact
-----------------

None

Nova driver impact
------------------

None, although we should update the ironic-virt driver code to
also look at this new node.fault field, in addition to the
``node.maintenance`` field.

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

If the periodic task for recovery is enabled, it will consume some resources
on conductor node.

More will be consumed in an environment containing some nodes in maintenance
due to power failure.

Other deployer impact
---------------------

A new option ``[conductor]power_failure_recovery_interval`` is introduced to
support power failure recovery. The default value is 300 (5 minutes), you
have to set to 0 if this feature is not needed.

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  kaifeng

Other contributors:
  dtantsur

Work Items
----------

* Update db layer to include the ``fault`` field.
* Change places where nodes enter/leave maintenance, to set
  ``fault`` accordingly.
* Add ``[conductor]power_failure_recovery_interval`` option to ironic
  configuration, add periodic task to handle power recovery.
* API change.

Dependencies
============

None


Testing
=======

The feature will be covered by unit tests, API change will be covered by
tempest test.


Upgrades and Backwards Compatibility
====================================

ironic API change is guarded by microversion.

When upgrading, any nodes in maintenance will have ``node.fault`` set to None.
This is because there is no easy/guaranteed way to determine if a node had
been (previously) put into maintenance due to one of our internal faults.
Furthermore, even if we could determine whether it was due to a fault, we don't
know whether the operator wants to keep the node in maintenance for other
reasons besides the fault.

Should the operator want to take advantage of the power fault recovery
mechanism, they could take the nodes out of maintenance. If there are still
issues, ironic will do its thing -- detect the fault and try to recover.


Documentation Impact
====================

* Update api-reference.
* New option will be generated by config generator.

References
==========

.. [#] https://review.opendev.org/#/c/334113/
