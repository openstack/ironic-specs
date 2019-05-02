..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===========================
Support for node retirement
===========================

https://storyboard.openstack.org/#!/story/2005425

This spec proposes to add initial support for retiring nodes from ironic.

Retiring nodes is a natural part of a server's life cycle, for instance
when the end of the warranty is reached and the physical space is needed
for new deliveries to install replacement capacity.

However, depending on the type of the deployment, removing nodes from
service can be a full workflow by itself as it may include steps like moving
applications to other hosts, cleaning sensitive data from disks or the BMC,
or tracking the dismantling of servers from their racks.

In order to help Deployers with these tasks, ironic should provide basic
means to mark nodes as being retired, i.e. mark them as not eligible for
scheduling any longer (while still allowing other operations such as
cleaning), or support a convenient search for and list such nodes.

Extensions of this initial support, such as extending the state machine by
an explicit 'retired' state (which could be used as a starting point for a
dedicated retirement workflow with end-of-life cleaning or other more
elaborate actions, such as 'prepare for donation') are beyond the scope of
this spec.


Problem description
===================

There is currently no explicit support in ironic for node retirement: when
a node needs to be taken out of service, the instance is deleted (which
triggers cleaning) and the node is deleted, either directly from state
'available' or after being moved to 'manageable' (and potential additional
cleaning).

There are at least two issues that this spec tries to fix:

* between the deletion of the instance and the deletion of the node, there
  is a time window in which a new instance could be scheduled to a node on its
  way into retirement (setting maintenance to 'True' does only partially help
  with this scheduling race as -- apart from not being meant to be used in this
  situation -- this will prevent cleaning);
* there is no easy way to mark nodes as 'retired'; this makes identifying and
  listing such nodes (as required by third party tools or the remaining
  retirement workflow) cumbersome.

The retirement use case is different from other use cases, like a
non-functional node which needs to be taken out of service for some time, in
that nodes may be marked for retirement a long time before anything actually
happens on the node. Also, retired nodes are not supposed to enter service
again.

Proposed change
===============

The proposal is to extend the list of node properties by two new fields:

* 'retired' (True/False)
* 'retired_reason' (text)

in analogy to the existing 'protected' and 'protected_reason'.

The 'retired' field shall signal that a node is meant to be retired and that
the node should not be considered for scheduling any longer. The 'retired'
field can be set irrespective of the node's state, in particular when the
node is 'active'.

Active nodes which are cleaned while 'retired' is True, e.g. upon instance
deletion, go to 'manageable' (rather than 'available'). This leaves no window
where a retired node would receive another instance. Otherwise, 'retired' set
to True shall not interfere with cleaning or rebuilding.

Nodes with 'retired' set to True cannot move from manageable to available
(to prevent accidental re-use): the "provide" verb is blocked. In order to
move these nodes to available, the 'retired' field needs to be set to False
first.

The new field shall also be used to get these nodes quickly via a 'list'
command, e.g. by an additional flag '--retired' (in analogy to
'--maintenance').


Alternatives
------------

An alternative to address the lack of support for node retirement would be
to introduce a new state 'retired' in the ironic state diagram. While this
would require additional efforts to implement, there are no obvious benefits
compared to the proposal of this specification.

Using the currently available means in ironic, such as the 'maintenance' state
and 'maintenance_reason', is certainly possible but will cause inconveniences
during node cleaning and when trying to extract the list of nodes to be
removed.


Data model impact
-----------------

The 'nodes' table will get two additional fields:

* 'retired' (tinyint)
* 'retired_reason' (text)

For existing instances, i.e. for data migration, 'retired' will be set to False
and 'retired_reason' will be left empty.


State Machine Impact
--------------------

The 'retired' field can be set on nodes in any state except 'available'.
Nodes in 'available' should be moved to manageable first to ensure
backwards compatibility with tools like metalsmith. This also eliminates
the need for changes in the nova driver.


The 'retired' field can also be set for nodes in transient states,
as long as the node is not locked.

When 'retired' is set to True, a node will not move to 'available' after
cleaning, but to 'manageable'.

When 'retired' is set to True, a node cannot move from 'manageable' to
'available', the corresponding 'provide' verb will return an HTTP 409.


REST API impact
---------------

The REST API will need to be extended with a new version to include
the new 'retired' field, in a similar way as the protected field
was introduced [0][1].

In addition, there should be a filter /v1/nodes?retired=True/False
to easily identify retired nodes.

Client (CLI) impact
-------------------

"ironic" CLI
~~~~~~~~~~~~

None.

"openstack baremetal" CLI
~~~~~~~~~~~~~~~~~~~~~~~~~

The '--retired' and '--retired-reason' options will be added to the 'set'
and 'unset' subcommands:

* openstack baremetal node set --retired --retired-reason <reason> <node>
* openstack baremetal node unset --retired <node>

shall be added to set and unset a node's 'retired' field (and provide a
reason in the case of 'set').

An additional flag '--retired' shall be added to the 'openstack baremetal
node list' command to restrict the returned result to the nodes which have
the retired flag set.


RPC API impact
--------------


Driver API impact
-----------------

None.


Nova driver impact
------------------

None.


Ramdisk impact
--------------

None.


Security impact
---------------

None.


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

Primary assignees:
  Arne Wiebalck (arne_wiebalck)
  Riccardo Pittau (rpittau)

Other contributors: None

Work Items
----------

* Add new database fields
* Adapt state machine if 'retired' is set to True
    * change cleaning --> manageable
    * move available --> manageable
    * block manageable --> available
* Exclude retired nodes from periodic tasks
* Extend API
* Extend cli
* Add new API to openstacksdk
* Add documentation


Dependencies
============

None.


Testing
=======

Needs testing similar to 'maintenance'.


Upgrades and Backwards Compatibility
====================================

Upon upgrades the new fields need to be set as specified in the
'Data model impact' section.


Documentation Impact
====================

The additional 'retired' field and its intended use need to be documented.


References
==========

[0] https://storyboard.openstack.org/#!/story/2003869
[1] https://review.opendev.org/#/c/611662
