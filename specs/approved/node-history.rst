..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

====================
Support node history
====================

https://storyboard.openstack.org/#!/story/2002980

This spec proposes node history support for nodes, which is useful for
identifying issues.


Problem description
===================

Currently ironic uses one last_error field to record error information when
an operation failed, this field is easily overwritten, to traceback the root
cause we have to search logs on the conductor host located somewhere in the
cloud. To make bare metal management easier, it would be handy to have a
history, especially, errors and state transitions of a node.

The proposal is to introduce a new table to store those events and provide
API support to retrieve them.


Proposed change
===============

Introduces a new table named ``node_history`` and a db object ``NodeHistory``,
see `Data model impact`_ for the schema definition.

Implements API layer to support node history query. The node history is
supposed to be query only.

Only two kinds of events will be logged in this proposal:

* State transitions
* Everything goes to last_error, this also covers node maintenance state
  change.

The range could be extended according to requirements in the future, but not
included in this spec.

Introduces a periodic task to remove node history entries which exceed
specified maximum of number, the number will be configurable by configuration
options.

Adds a ``history`` module to provide history interface abstraction and provides
two implementation with ``none`` and ``database``.


Alternatives
------------

Other solutions exist, like using LOG collector and aggregator, but they need
more integrations and not directly supported from ironic.

Data model impact
-----------------

A new database table will be added with following schema::

    op.create_table('node_history',
                    sa.Column('created_at', sa.DateTime(), nullable=True),
                    sa.Column('updated_at', sa.DateTime(), nullable=True),
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('uuid', sa.String(length=36), nullable=False),
                    sa.Column('conductor', sa.String(length=255), nullable=True),
                    sa.Column('event', sa.Text(), nullable=True),
                    sa.Column('node_id', sa.Integer(), nullable=True),
                    sa.Column('user'), sa.String(length=32), nullable=True),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('uuid', name='uniq_history0uuid'),
                    sa.ForeignKeyConstraint(['node_id'], ['nodes.id'], ),
                                            mysql_ENGINE='InnoDB',
                                            mysql_DEFAULT_CHARSET='UTF8')
                    sa.Index('node_id', 'node_id')

``event`` is the string conveys what happened to the node, the content will
be truncated to 1000 characters.

``conductor`` is the hostname of the conductor who recorded the entry.

``user`` is the requester for the operation from the context, for the Identify
service it's a string with fixed length.


State Machine Impact
--------------------

None

REST API impact
---------------

Following endpoints will be added to support querying node history,
microversioned. Clients with earlier microversion will receive 404.

* GET /v1/{node_ident}/history

  * Retrieve the list of events logged for this node. By default ``uuid``,
    ``event`` and ``created_at`` are returned. The ``event`` will be
    truncated to 255 to give a brief information. Detailed history entry
    will be returned if ``detail`` is set to True in the query string.
  * For a normal request, 200 is returned.

* GET /v1/{node_ident}/history/{history_uuid}

  * Get detailed information of an event.
  * For a normal request, 200 is returned.

Client (CLI) impact
-------------------

"openstack baremetal" CLI
~~~~~~~~~~~~~~~~~~~~~~~~~

OSC will be enhanced to support following operations:

* ``openstack baremetal node history list``: list all events kept for this node
* ``openstack baremetal node history show <uuid>``: show a specific node event

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

Node events could occupy considerable amount of data in the database
when this feature is enabled, depending on the scale of bare metals and
activities. In such case the configuration options of this feature should be
evaluated.

Performance Impact
------------------

The new periodic task and database access will use some resource, but should
be trivial.

Other deployer impact
---------------------

Adds following configuration options to change the behavior of this feature:

* ``[conductor]node_history_backend``: can be ``none`` and ``database``.
  ``none`` does nothing and effectively disable this feature, this is the
  default.
* ``[conductor]node_history_max_entries``: how many events ironic should keep.
  Oldest events will be removed when reached max entries. The default is 300,
  the minimum value is 1.
* ``[conductor]node_history_cleanup_interval``: the interval in seconds, the
  clean up periodic task should be scheduled. One day by default. Set to 0
  will disable periodic clean up.
* ``[conductor]node_history_cleanup_batch_num``: the maximum number of entries
  will be removed during one clean up operation.

Developer impact
----------------

Other events could be added once this spec is implemented.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  <kaifeng, kaifeng.w@gmail.com>

Other contributors:
  <None>

Work Items
----------

Implements proposed work:

* Database support
* The history module and two backends namely none and database
* Log history at proper code path
* API support
* CLI support
* Documentation

Dependencies
============

None

Testing
=======

The feature will be covered by unit test.


Upgrades and Backwards Compatibility
====================================

This feature is disabled by default.

Documentation Impact
====================

Documentation will be updated.

References
==========

None
