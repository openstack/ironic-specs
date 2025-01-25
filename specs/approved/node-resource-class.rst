..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=============================
Add node resource_class field
=============================

https://bugs.launchpad.net/ironic/+bug/1604916

Nova has a plan for scheduling ironic resources the same way as other nova
resources, that involves making each ironic node a "resource provider",
which has a "resource class". That resource class is referenced by the
nova flavor, in short saying that the flavor requires exactly one thing
from that resource class. When running the resource tracker, nova must
be able to associate each ironic node with a resource class, which operators
must be able to specify (because operators are the people creating the flavors
and need to know how to associate the flavor). To allow for this, we add a new
"resource_class" field to ironic's node object.

Problem description
===================

Currently, nova tracks ironic resources with a (host, node) tuple. This
causes a number of problems within nova's internals, and the nova team is
trying to get away from this. At the same time, nova wants to schedule
ironic instances the same way as other instances are scheduled. This
allows ironic to follow along in the ongoing scheduler changes, which
will help reduce (or eventually eliminate) scheduling races, and benefit
from other scheduler optimizations coming down the road (like making
qualitative decisions more performant).

Proposed change
===============

The current proposal in nova is to make each ironic node a "resource provider",
which is associated with a "resource class".[0] A nova flavor may declare that
it requires some amount of a given resource class; in ironic's case it would
require one and only one. The resource provider record for an ironic node
will declare that it provides exactly 1 (or 0, if it is in maintenance or
similar) of the resource class for that provider record.

This proposal still allows nodes to be scheduled to based on qualitative
properties, such as capabilities or affinity rules. The resource class is
simply the first "filter" in this case (though it isn't a traditional
scheduler filter).

To do so, nova needs to know which resource class the resource provider record
needs to be associated with. As operators manage the flavors that will be
linked to these classes, we need a way for the operator to specify what
class each node is in, so that the flavor is linked correctly. As such,
we add a "resource_class" field to the node record in ironic, which nova
will use when creating the resource provider record.

As an example, imagine an ironic deployment has the following nodes::

    - node-1:
      resource_class: ironic-gold
      properties:
        cpus: 4
        memory_mb: 16384
        capabilities:
          boot_mode: uefi,bios
    - node-2:
      resource_class: ironic-silver
      properties:
        cpus: 2
        memory_mb: 8192

The operator might define the flavors as such::

    - baremetal-gold
      resources:
        ironic-gold: 1
      extra_specs:
        capabilities: boot_mode:bios
    - baremetal-gold-uefi
      resources:
        ironic-gold: 1
      extra_specs:
        capabilities: boot_mode:uefi
    - baremetal-silver
      resources:
        ironic-silver: 1

Note that the flavor definition is a strawman and may not be the actual keys
used when this is implemented.

A nova user booting an instance with either the baremetal-gold or
baremetal-gold-uefi flavor would land on node-1, because capabilities can
still be passed down to ironic, and the resource_class on the node matches
what is required by flavor. The baremetal-silver flavor would match node-2.

Alternatives
------------

Keep doing the (host, node) thing long enough such that the nova team
decides they want to remove our driver from nova, and subsequently remove
the (host, node) tuple and break our driver horribly.

Data model impact
-----------------

Adds a "resource_class" field to the nodes table. This will be a VARCHAR(80)
because that matches nova's table structure. There will be data migrations
provided for this change. The objects API will also take this change, with
a corresponding version bump. This will default to NULL.

State Machine Impact
--------------------

None.

REST API impact
---------------

The new "resource_class" field will be exposed in the API, just like any
other string field, with the same semantics.

Default policy for this field should be the same as driver,
network_interface, etc.

Filtering and sorting on this field will be added.

There will be a microversion bump, as usual.

Client (CLI) impact
-------------------

The client will be updated to add the field.

"ironic" CLI
~~~~~~~~~~~~

The CLI will be updated to add the field.

"openstack baremetal" CLI
~~~~~~~~~~~~~~~~~~~~~~~~~

The CLI will be updated to add the field.

RPC API impact
--------------

Only the objects changes mentioned above.

Driver API impact
-----------------

None.

Nova driver impact
------------------

Immediately, we'll pass the ``resource_class`` field back up to the resource
tracker, so that nova can put these resources in the placement database in
Newton. There will be a small patch that bumps the API version we're using
and passes the field back in the resource_dict. This will need a release
note dictating the ironicclient version and available API version needed
to run this code.

During Ocata, work will be done on the scheduler to use this for scheduling,
however that is outside of the ironic driver.

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

After the deployment of the Newton version of nova, deployers will
need to populate the resource_class field in ironic, and associate the
flavors, before deploying the Ocata version of nova.

Developer impact
----------------

None.

Implementation
==============

Assignee(s)
-----------

jroll

Work Items
----------

* Add the field to the DB.

* Add the field to the objects model.

* Add the field to the API, with filtering and sorting.

* Doc updates for install guide and such.


Dependencies
============

None.


Testing
=======

Unit tests should suffice here.


Upgrades and Backwards Compatibility
====================================

No direct impact, but it's important to note that scheduling in the Ocata
version of nova will still fall back to the old method, if resource_class is
set to NULL for any node. Operators should have up until the P version of nova
to populate this data.

Documentation Impact
====================

Add the new field to the API reference.

We'll also need to update the install guide and any other docs that talk
about setting up nova with ironic, to make sure that deployers are setting
this field when adding nodes. This will also need to be communicated
extremely hard via release notes (and probably ops list emails).


References
==========

[0] https://review.opendev.org/#/c/312696
