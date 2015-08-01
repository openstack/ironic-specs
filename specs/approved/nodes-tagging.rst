..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=============
Nodes tagging
=============

https://blueprints.launchpad.net/ironic/+spec/nodes-tagging

This blueprint aims to add support for tagging nodes.

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

A new `ironic.objects.tags.TagList` object would be added to the
object model, and will add a `tags` field to the `node` table of
type `ironic.objects.tags.TagList` that would be populated on-demand
(i.e. not eager-loaded).

A tag should be defined as a Unicode string no longer than 255 bytes
in length.

For the database schema, the following table constructs would suffice ::

    CREATE TABLE tags (
        resource_id INT(11) NOT NULL PRIMARY KEY,
        tag VARCHAR(255) NOT NULL CHARACTER SET utf8
        COLLATION utf8_ci PRIMARY KEY
    );

REST API impact
---------------

The tag CRUD operations API extension would look like the following:

Return list of tags for a node ::

    GET /v1/nodes/{node_id}/tags

returns ::

    [
        'tag1',
        'tag2'
    ]

Add set of tags on a node ::

    POST /v1/nodes/{node_id}/tags

with request body ::

    [
        'tag1',
        'tag2'
    ]

Add a single tag on a node ::

    PUT /v1/nodes/{node_id}/tags/{tag}

Remove a single tag on a node ::

    DELETE /v1/nodes/{node_id}/tags/{tag}

Get all nodes tags::

    GET /v1/nodes/tags

returns ::

    [
        'tag1',
        'tag2',
        'tag3'
    ]

The API that would allow searching/filtering of the `GET /v1/nodes`
REST API call would add a `tag` query parameter:

Get all nodes having a single tag ::

    GET /v1/nodes?tag={tag}

Get all nodes having *both* tag A and tag B::

    GET /v1/nodes?tag={tag_a}&tag={tag_b}

RPC API impact
--------------

None

State Machine Impact
--------------------

None

Client (CLI) impact
-------------------

Add tags CRUD operations commands:

* ironic node-list-tags <node uuid>
* ironic node-update-tags <node uuid> <op> <tag>

<op> Operation: 'add' or 'remove'

Add tag-list filtering support to node-list command:

* ironic node-list --tag tag1 --tag tag2

multiple --tag will be used to filter results in an
AND expression.

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

* Add `tags` table with a migration.
* Add DB API layer for CRUD operations on node tags.
* Added DB API layer for node tag-list filtering support.
* Add Tag, TagList objects and a new tags field to Node object.
* Add REST API for CRUD operations on node tags.
* Add REST API for node tag-list filtering support.
* python-ironicclient additions and modifications.


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

Ironic API and python-ironicclient will need to be updated to accompany
this change.


References
==========

https://blueprints.launchpad.net/nova/+spec/tag-instances
