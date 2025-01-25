..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

====================
Driver Internal Info
====================

https://blueprints.launchpad.net/ironic/+spec/driver-internal-info

Problem description
===================

Driver should have its own infos which cannot manipulated by user/admin.
These infos are not input from admin like driver_info and they may vary
during the deployment process. They can only be used by driver itself.

One example is ipmitool. Not all IPMI firmware support set boot device
persistent, so we need to save this locally.

Proposed change
===============

* Add a new internal attribute ``driver_internal_info`` in nodes table,
  which cannot modify by Admin/user by calling node.update API

* Modify node.update to clear ``driver_internal_info`` when update driver via
  node.update API.

Alternatives
------------

Saving these infos in a new table named driver_interal_info.

Data model impact
-----------------

Add a new internal attribute ``driver_internal_info`` in ``node`` table. This
field is a json dict.

REST API impact
---------------

The ``driver_internal_info`` field should be added to the node details API.

RPC API impact
--------------
None

Driver API impact
-----------------
None

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
None

Performance Impact
------------------
None

Other deployer impact
---------------------
None

Developer impact
----------------

Other drivers should save their own infos into the new attribute.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  tan-lin-good

Work Items
----------

* Add ``driver_internal_info`` to the nodes table with a migration.
* Update object Node.
* Support clean a node's driver_internal_infos when it changes its driver.
* Update some drivers with this feature.

Dependencies
============
None


Testing
=======

Add unit tests.

Upgrades and Backwards Compatibility
====================================
Add a migration script for DB.

Documentation Impact
====================
Update the developer documentation.


References
==========
None
