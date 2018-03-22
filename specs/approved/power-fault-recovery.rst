..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

====================
Power fault recovery
====================

https://bugs.launchpad.net/ironic/+bug/1596107

This spec proposes adding a new node field to differentiate different
maintenance types. And, if possible, recover node from maintenance
state if the node is in maintenance due to power sync failure, and power
sync is succeed.


Problem description
===================

Currently, ironic's API and data model makes no differentiation between ironic
setting maintenance on a node (for instance, when cleaning fails, or when the
power status loop cannot contact the BMC) and an operator setting maintenance
on a node (an explicit API action).

This situation makes it difficult to apply any power fault recovery mechanism.

Proposed change
===============

A string field named ``maintenance_type`` will be added to ironic data model,
it will be used to record different maintenance types.

The field will be set to following values in different cases:

* ``manual``: when a node is explicitly put into maintenance from ironic API.
* ``power failure``: when a node is entering maintenance due to power sync
  failure exceeded max retries.
* ``clean failure``: when a node is entering maintenance due to failure of a
  cleaning operation.
* ``rescue abort failure``: when a node is entering maintenance due to failure
  of cleaning up during rescue abort.

The field will be set to None if not in maintenance.

Add a periodic task to conductor to filter out nodes in maintenance and
``maintenance_type`` is ``power failure``, trying to get power status, and
bring nodes out of maintenance once the power status is retrieved
successfully.

Add a new integer option named ``[conductor]power_failure_recovery_interval``
to config how many seconds between each run of periodic task. Set to 0 will
disable power fault recovery, the default value is 300 (5 minutes).


Alternatives
------------

Proposals have already been made and rejected to use the combination of
maintenance being set and a given maintenance_reason or last_error to do
self-healing due to inconsistency.

Specific faults support [#]_ is proposed but it's too big and doesn't reach
a consensus.

Data model impact
-----------------

A string field named ``maintenance_type`` will be added to ironic node table.

The field will be added to ``Node`` object, object version will be increased.

State Machine Impact
--------------------

None

REST API impact
---------------

The field ``maintenance_type`` will be added to ``Node`` API object, ironic
API version will be bumped.

Node related API endpoints will be affected:

* POST /v1/nodes
* GET /v1/nodes
* GET /v1/nodes/detail
* GET /v1/nodes/{node_ident}
* PATCH /v1/nodes/{node_ident}

For clients with older microversion, the ``maintenance_type`` is hidden from
the response, this will be done in the ``hide_fields_in_newer_versions``.

Field ``maintenance_type`` is read only from API, and can only be modified
internally. Any POST/PATCH request to Node with ``maintenance_type`` set will
get 400 (Bad Request).

There is no other impact to API behaviors.


Client (CLI) impact
-------------------

"ironic" CLI
~~~~~~~~~~~~

None

"openstack baremetal" CLI
~~~~~~~~~~~~~~~~~~~~~~~~~

The CLI will be updated to support field ``maintenance_type``, guarded
by ironic API microversion.

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

* Update db layer to include the ``maintenance_type`` field.
* Change places where nodes entering/leaving maintenance to set
  ``maintenance_type`` accordingly.
* Add ``[conductor]power_failure_recovery_interval`` option to ironic
  configuration, add periodic task to handle power recovery.
* API change.
* Handle maintenance data migration on db upgrade.

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

dbsync and db api will be updated to facilitate populating the
``maintenance_type`` field to ``manual`` during data migration for nodes
previously been put under maintenance.

Documentation Impact
====================

* Update api-reference.
* New option will generated by config generator.

References
==========

.. [#] https://review.openstack.org/#/c/334113/
