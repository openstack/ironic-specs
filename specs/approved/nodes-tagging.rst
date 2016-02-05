..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=============
Nodes tagging
=============

https://bugs.launchpad.net/ironic/+bug/1526266

This aims to add support for tagging nodes.

Problem description
===================

Ironic should have tags field for every node, which can be used to
divide the nodes to some groups. then we can do list by tag to
get a group of nodes with same properties like hardware specs.

Proposed change
===============

* Add APIs that allows a user to add, remove, and list tags for a node.

* Add tag filter parameter to node list API to allow searching for nodes
  based on one or more string tags.

Alternatives
------------

Current chassis object is kind of an alternative for grouping nodes.

Data model impact
-----------------

A new `ironic.objects.tags.NodeTagList` object would be added to the
object model.

The `ironic.objects.tags.NodeTagList` field in the python object model
will be populated on-demand (i.e. not eager-loaded).

A tag should be defined as a Unicode string no longer than 255 characters
in length, with an index on this field.

Tags are strings attached to an entity with the purpose of classification
into groups. To simplify requests that specify lists of tags, the comma
character is not allowed to be in a tag name.

For the database schema, the following table constructs would suffice ::

    CREATE TABLE node_tags (
        node_id INT(11) NOT NULL,
        tag VARCHAR(255) CHARACTER SET utf8 NOT NULL,
        PRIMARY KEY (node_id, tag),
        KEY (tag),
        FOREIGN KEY (node_id)
          REFERENCES nodes(id)
          ON DELETE CASCADE,
    )


REST API impact
---------------

We will follow the `API Working Group's specification for tagging`_, rather
than invent our own.

.. _API Working Group's specification for tagging: http://specs.openstack.org/openstack/api-wg/guidelines/tags.html

Will support addressing individual tags.


RPC API impact
--------------

None

State Machine Impact
--------------------

None

Client (CLI) impact
-------------------

Add tags CRUD operations commands:

* ironic node-tag-list <node uuid>
* ironic node-tag-update <node uuid> <op> <tags>

<op> Operation: 'add' or 'remove'

For individual tag:
* ironic node-tag-add <node uuid> <tag>
* ironic node-tag-remove <node uuid> <tag>

Add tag-list filtering support to node-list command:

* ironic node-list --tag tag1 --tag tag2
* ironic node-list --tag-any tag1 --tag-any tag2
* ironic node-list --not-tag tag3

Multiple --tag will be used to filter results in an AND expression, and
--tag-any for OR expression, allowing for exclusionary tags via the
--not-tag option.

Driver API impact
-----------------

None

Nova driver impact
------------------

The tags information can be used for nova but it's not being
considered as part of this spec, and may be addressed at a
later time.

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
  niu-zglinux

Work Items
----------

* Add `node_tags` table with a migration.
* Add DB API layer for CRUD operations on node tags.
* Added DB API layer for node tag-list filtering support.
* Add NodeTag, NodeTagList objects and a new tags field to Node object.
* Add REST API for CRUD operations on node tags.
* Add REST API for node tag-list filtering support.
* python-ironicclient additions and modifications.


Dependencies
============

None


Testing
=======

Add unit tests.
Add tempest API tests.


Upgrades and Backwards Compatibility
====================================

Add a migration script for DB.


Documentation Impact
====================

Ironic API and python-ironicclient will need to be updated to accompany
this change.


References
==========

1. http://specs.openstack.org/openstack/api-wg/guidelines/tags.html
