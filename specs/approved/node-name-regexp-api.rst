..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

============================
Add new node name filter API
============================

https://bugs.launchpad.net/ironic/+bug/1526319

This blueprint proposes adding a way to filter nodes in the API by their
name (regex,wildcard).

 GET /v1/nodes/?name_regex=<regexp_str>
 GET /v1/nodes/?name_wildcard=<wildcard_str>

Problem description
===================

Current there is only api GET /v1/nodes/<node_name> to exactly retrieve the
ironic node via node_name. However for customer, if regular and wildcard
expressions filters are supported to retrieve the nodes via user input, that
should be useful for user to filter nodes by name flexible, especially for
the users who have a lot of baremetal nodes which are managed by ironic.

Possible use case is to support client bulk operations, such as to power off
some nodes which are filtered out by node name regexp or wildcard, with single
command.

Proposed change
===============

Add new API:

 + GET /v1/nodes/?name_regex=<regexp_str>
 + GET /v1/nodes/?name_wildcard=<wildcard_str>

We support both BRE and ERE IEEE POSIX Regular expression standard[1].

And will add db api support, for different databases, there are different
operators for regular expression:

 + postgresql: '~'
 + mysql: 'REGEXP'
 + sqlite: 'REGEXP'

So we will check the current database which ironic is using, and get the
regular expression operator from the above map. If there is no such db in
the above supporting map, will raise api exception to user and tell user the
current database is not supported for this name regex query api.

For wildcard filter, all database can support, because will run with 'LIKE'
SQL operator which is standard SQL.

Alternatives
------------

Use node tags for client bulk operations.

Data model impact
-----------------

None.


State Machine Impact
--------------------

None.

REST API impact
---------------

Add new API 'GET /v1/nodes/?name_regexp=<regexp_str>', and 'GET /v1/nodes/
?name_wildcard=<wildcard_str>', and bump API micro-version.
Please see "Proposed change".

Client (CLI) impact
-------------------

Add new command that executes two new API:

  + ironic node-list --name-regex=<regexp_str>
  + ironic node-list --name-wildcard=<wildcard_str>

Have a similar modification to the OSC plugin.

RPC API impact
--------------

None.

Driver API impact
-----------------

None.

Nova driver impact
------------------

None.

Ramdisk impact
--------------

N/A

.. NOTE: This section was not present at the time this spec was approved.

Security impact
---------------

None

Other end user impact
---------------------

None.

Scalability impact
------------------

None.

Performance Impact
------------------

None.

Other deployer impact
---------------------

None.

Developer impact
----------------

None.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  whaom

Work Items
----------

* Add new API 'GET /v1/nodes/?name_regex=<regexp_str>'
* Add new API 'GET /v1/nodes/?name_wildcard=<wildcard_str>'
* Add new 'name_regex filter' option for ironic node-list command.
* Add new 'name_widcard filter' option for ironic node-list command.
* Add new 'name_regex filter' option for the existing commands which take
  node id as input to support bulk operation.
* Add new 'name_widcard filter' option for the existing commands which
  take node id as input to support bulk operation.

Dependencies
============

None.

Testing
=======

Will add unit test code to cover the new api.

Upgrades and Backwards Compatibility
====================================

None.

Documentation Impact
====================

Update API document adding a new API

References
==========

[1] https://en.wikipedia.org/wiki/Regular_expression#Standards

