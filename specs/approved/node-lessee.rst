..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

====================
Allow Leasable Nodes
====================

https://storyboard.openstack.org/#!/story/2006506

A large bare metal deployment may consist of hardware owned by multiple
owners who lease their nodes to users - lessees - who gain temporary and
limited access to specific nodes. Ironic understands the concept of a
hardware owner: a node can set its ``owner`` field to a project, and that
project can gain API access to that node through the use of an updated
policy file. However, Ironic does not understand the concept of a node
lessee.

This spec describes a solution that accommodates the notion of a node
lessee.

Problem description
===================

Ironic currently supports two classes of users: administrators, who
control the entire inventory of hardware; and owners, who have
policy-limited API access to the nodes that they own. However, Ironic
does not support non-administrative users - users who can deploy
upon a node, and perhaps have access to an extremely limited subset
of the API (such as node power functions).

Proposed change
===============

Node lessees can be supported with the following changes:

* Add a new ``lessee`` field to the node object. This field must either
  be empty or set to a Keystone project id.

* Update the node controller so that policy checks pass in a node's
  ``lessee`` information. Note that Ironic already does that with node
  owners [0]_.

* Update Ironic's default generated policy file to include an
  ``is_node_lessee`` rule:

   *  "is_node_lessee": "project_id:%(node.lessee)s"

  The remainder of the policy file will stay the same, so that there is
  no change to default API access.

* Update the node list function so that projects with access to
  ``baremetal:node:list`` are returned nodes with matching ``owner`` or
  ``lessee`` fields.

* Update Ironic allocations so that allocations with owners can match
  nodes by a node's ``owner`` or ``lessee``.

Note that this work does not add any new scheduling responsibilities in
Ironic. A new Nova filter, such as an updated version of the
proposed NodeOwnerFilter [1]_, would be desirable; and Blazar could
integrate with the ``lessee`` field as they see fit. However, the
proposed work does integrate well with the existing ability to create
a restricted allocation.

Further down the line when Ironic creates a Deployment API, we can have
the new Deployment API actions default to being accessible to node
lessees.

Alternatives
------------

Lessee information could be stored in a dictionary field such as
``properties`` or ``extras``. However this makes updating database queries
far more difficult, and the non-administrative user concept feels distinct
enough to warrant a new field.

Data model impact
-----------------

A ``lessee`` field will be added to the nodes table as a ``VARCHAR(255)``
with a default value of ``null``.

State Machine Impact
--------------------

None

REST API impact
---------------

* A ``lessee`` field will be returned with the node object.

* The REST API will pass in the ``lessee`` for node policy checks.

* The API will be updated to allow a user to set/unset the value
  through the API.

* The node list API will be updated to allow filtering by ``lessee``.

* The limited ``baremetal:node:list`` action will be updated to
  match nodes by both lessee and owner.

* A new API microversion will be introduced for the new node ``lessee``
  field.

Client (CLI) impact
-------------------

None

"ironic" CLI
~~~~~~~~~~~~

None

"openstack baremetal" CLI
~~~~~~~~~~~~~~~~~~~~~~~~~

An update will be needed to enable a user to set/unset ``lessee`` from the
command line.

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

This change allows functionality to be exposed to additional users. However
this access is blocked off by default; it requires an update to the Oslo
policy file, and can be adjusted as an administrator desires.

Other end user impact
---------------------

None

Scalability impact
------------------

None

Performance Impact
------------------

Some functionality that previously matched nodes by ``owner`` will now
have to match both ``owner`` and ``lessee``. This should be doable at
the database query level.

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

Primary assignees:
* tzumainn - tzumainn@redhat.com

Work Items
----------

* Add database field.
* Add object field.
* Add REST API functionality and microversion.
* Update REST API documentation.
* Update python-ironicclient.
* Update node controller.
* Update allocations conductor.
* Write tests.
* Write documentation detailing usage.

Dependencies
============

None

Testing
=======

We will add unit tests and Tempest tests.

Upgrades and Backwards Compatibility
====================================

The ``lessee`` node field will be created as part of the upgrade process
with a default value in the database schema. This change has no end-user
impact if the policy file is not updated.

Documentation Impact
====================

REST API documentation will be updated.

References
==========

.. [0] https://opendev.org/openstack/ironic/src/branch/master/ironic/api/controllers/v1/utils.py#L1178
.. [1] https://review.opendev.org/#/c/697331/
