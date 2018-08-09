..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=============================
Ownership Information Storage
=============================

https://storyboard.openstack.org/#!/story/2001814

In many large businesses with hardware fleets, there may be a variety of
ownership of the underlying hardware for tracking purposes. A good example
of this is in a hybrid service provider scenario where an operator may
directly own a portion of the hardware, may have the hardware on lease,
and may ultimately have customer owned hardware.

We simply cannot model this with existing node fields, since there may
be resource sharing agreements also in place between the owners of the
hardware. And as such, we need some way to store and represent the end
owner of the hardware for tracking and logistical purposes.

Problem description
===================

While scenarios differ, ultimately there is a need to be able to store
information in a top level fashion about who owns a given piece of hardware.

Information of this sort can be vital when it comes time for tax asset
inventories, or just simple tracking of where the hardware came from.

Providing the ability to search and return the hardware that is known
to be owned by a particular group allows for faster correlation of the
disposition of the hardware for auditing and accounting purposes.

Proposed change
===============

Proposing to add a new informational field to the node object that can be
queried via the REST API, and stored in the database. No other initial use
of this field is expected.

Future use could also be automatic in the scenario if there is a driver
that is aggregating a number of management systems, however that is out of
scope.

Alternatives
------------

An operator could potentially store this information in extra, however then
they would still need to dump all of the nodes out to obtain a list of nodes
with the specific information that is needed. The operator would begin to
hit limits with the number of responses from the API, and would need to
likely create their own tooling around list processing.

Data model impact
-----------------

A ``owner`` field would be added to the nodes table as a ``VARCHAR(255)``
and will have a default value of ``null`` in the database.

State Machine Impact
--------------------

None

REST API impact
---------------

An ``owner`` field will be returned as part of the node. The API shall be
updated to allow a user to set and unset the value via the API.

Additionally the GET syntax for the nodes list will be updated to allow a
list of matching nodes to be returned.

POST/PATCH operations to the field will be guarded by a new microversion.
The field shall not be returned unless the sufficient microversion is supplied
for GET operations.

Client (CLI) impact
-------------------

"ironic" CLI
~~~~~~~~~~~~

None

"openstack baremetal" CLI
~~~~~~~~~~~~~~~~~~~~~~~~~

A corresponding change will be necessary to enable the ability for a user
to set/unset the value from a command line.

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

None

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  TheJulia - juliaashleykreger@gmail.com

Other contributors:
  None

Work Items
----------

* Add database field.
* Add object field.
* Add REST API functionality and microversion.
* Update REST API documentation.
* Update python-ironicclient.

Dependencies
============

None

Testing
=======

Basic API CRUD testing will be added. There is no need for additional testing
as this is an informational field for the API user/baremetal operator.

Upgrades and Backwards Compatibility
====================================

Field will be created as part of the upgrade process with a default value in
the database schema.

Documentation Impact
====================

REST API documentation will need to be updated.

References
==========

None
