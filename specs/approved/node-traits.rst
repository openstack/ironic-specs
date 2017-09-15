..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===========
Node Traits
===========

https://bugs.launchpad.net/ironic/+bug/1722194

Add more granular Nova placement of ironic nodes by allowing operators to
set a list of traits associated with each node.

Problem description
===================

While the recent addition of Resource Class on every node has helped improve
the way ironic resources are scheduled in Nova, using the new Placement API,
there are many use cases that need more granular control.

An example use case is dedicating a pool of ironic nodes for a specific
project. Another is allowing flavors that best fit to the available hardware,
you might want smaller flavors to build on larger machines if you are out of
smaller machines.

In a similar way, you might have a pool of hardware that are all the same
except for the chosen RAID configuration. Longer term, when you provision the
node via Nova boot it would be good to be able to automatically reconfigure
the hardware with the chosen RAID configuration. For now this is considered
out of scope.

Proposed change
===============

The Placement API has the ability to tag a resource provider with a trait:
http://specs.openstack.org/openstack/nova-specs/specs/pike/approved/resource-provider-traits.html

The nova ironic driver currently ensures a Resource Provider exists for every
Ironic Node. It already populates the inventory with the correct quantitative
resources (i.e the Resource Class).

To get the extra granularity of scheduling we depend on adding traits to the
resource provider, and the implementation of the following Nova specs that
ensure the traits requested in flavors are honored by the scheduling process:

* http://specs.openstack.org/openstack/nova-specs/specs/queens/approved/request-traits-in-nova.html
* http://specs.openstack.org/openstack/nova-specs/specs/queens/approved/add-trait-support-in-allocation-candidates.html

The current proposal is for Ironic to store a list of traits for each node.
That list can then be synced into the appropriate resource provider in the
Placement API by Nova's ironic virt driver, in a similar way to how
the RESOURCE_CLASS of each ironic node is reported today.

Lets talk about the use case of dedicating specific Ironic nodes for use only
by a specific set of projects. The remainder of the hosts are for general use.
If a user has a dedicated pool of resources, they have the ability to pick if
they create an instance in their dedicated pool or in the general pool. Other
users are only able to build in the general pool. One way to bisect the nodes
like this is assigning traits such as `CUSTOM_IRONIC_NODE_PROJECT_B` and
`CUSTOM_IRONIC_NODE_GENERAL_USE` to the appropriate ironic nodes. Then there
is a public flavor to target the general pool of hosts, and a private project
specific flavor that targets their dedicated pool. By taking this approach it
is easy to add additional pools of nodes for other sets of projects. It is
easier because you don't need to modify any of the existing nodes and flavors
when you add an additional pool of nodes.

Note that inspection rules can be used to set the initial value for a
node's Resource Class. It is expected the initial set of traits for a node can
be set in the same way.

.. note::
    There is already a Nova spec proposed discussing the Nova side of how we
    can assign traits to the resource providers, and on Nova boot send the
    chosen traits back to ironic:

    * http://specs.openstack.org/openstack/nova-specs/specs/queens/approved/ironic-driver-traits.html

When provisioning a node, the Ironic virt driver in Nova will now send
additional flavor extra_specs to Ironic. Currently only extra_specs starting
with `capabilities` are set in instance_info. After the above spec, the ironic
virt driver will also include the flavor extra specs that define what traits
have been requested, storing them `instance_info['traits']`.

.. note::
    Note there is no change to how capabilities are used as part of this spec.

Ironic needs to validate that `instance_info['traits']` is consistent with the
list of traits currently associated with Ironic node, i.e. we must check that
`instance_info['traits']` only includes traits that are already in the list
of traits set on the Ironic node. This is particularly useful in preventing
strange behaviour due to races between the update of an Ironic node's trait
list and getting that list copied into the Placement API by the Ironic virt
driver. This validation is probably best integrated as part of
``driver.deploy.validate`` or similar, to ensure it is triggered by a call to
deploy a node and a call to validate a node.

.. note::
    The ironic virt driver in Nova will sync the list of traits reported by
    each Ironic Node into Nova's Placement API, in a similar way to how the
    Resource Class is done today. Should an operator talk directly to Placement
    to adjust the traits, this process will remove all those modifications when
    the next sync occurs. Operators must use the Ironic API to change the list
    of traits on a given node. Ironic is assumed to be the source of truth for
    the list of traits associated with a Resource Provider that is
    representing an Ironic node.

Alternatives
------------

In the future, it is expected that a driver may need to validate some well
known traits to see if they are supported. In addition it may be that some
drivers automatically report some traits. Following on from that, it could
be that drivers read the traits specified in instance_info to reconfigure
the node. This is all out of scope here.

Looking at what is in scope, there are alternative approaches:

* Make operators (and ironic-inspector) talk directly to the Placement API to
  set the node traits. This would be very odd given the Nova sync of the
  Resource Providers using the ComputeNode uuid as the uuid for the Resource
  Provider. You can't set the traits until that sync has completed. Right now
  placement is largely an internal API with few policy controls, so that would
  all need to change to allow the above. It all seems very messy.

* Keep traits APIs in Ironic, but make it a pass-through proxy to Placement.
  This is would make Ironic hard depend on placement, which would be a strange
  requirement for things like Bifrost, and would complicate upgrades.

The current approach keeps Ironic from needing to depend on placement in any
way, which works well.

The REST API described below allows fine grained control of setting traits,
following the patterns from the API-WG and existing placement APIs. We could
instead have just extended the existing ironic node PATCH interface.

The suggested CLI approach below follows the new API, but as an alternative
we could have extended the existing CLI interface around the PATCH API call.
It would have looked something more like:

* openstack baremetal node set --trait CUSTOM_FOO <node-uuid>
* openstack baremetal node unset --trait CUSTOM_FOO <node-uuid>

Data model impact
-----------------

Following a similar pattern to the existing table for tags, we will need to add
this new table to store the traits associated with a node::

    CREATE TABLE node_traits (
        node_id INT(11) NOT NULL,
        trait VARCHAR(255) CHARACTER SET utf8 NOT NULL,
        PRIMARY KEY (node_id, trait),
        KEY (trait),
        FOREIGN KEY (node_id)
          REFERENCES nodes(id)
          ON DELETE CASCADE,
    )

A new ``ironic.objects.traits.NodeTraitList`` object will be added to the
object model. The ironic.objects.traits.NodeTraitList field in the python
object model will be populated on-demand (i.e. not eager-loaded).

A trait should be defined in a way that matches the placement API definition,
as a Unicode string no longer than 255 characters.

State Machine Impact
--------------------

No impact.

REST API impact
---------------

The placement API defines a set of standard traits in the `os-traits` library.
Any traits that are not defined in that library must start with the prefix of
`CUSTOM_`. Any trait set in Ironic must follow these rules, else the ironic
Nova virt driver will be unable to add the traits in Placement. For similar
reasons there is a limit of 50 traits on any node, to match the limit in
Placement. A request to add a badly formatted trait should get a response with
the status code 400.

Note at no point does Ironic talk to the Placement API. The above validation
depends only on access to the python library `os-traits`. As such, this
validation poses little restriction on how traits can be used in standalone
Ironic to assign arbitrary traits on particular Ironic nodes. Any non-standard
traits simply need to have a prefix of ``CUSTOM_`` added. For more details on
`os-traits` please see: https://docs.openstack.org/os-traits/latest

For convenience, it will be possible to get the full list of nodes and the
traits associated with each node by extending the existing API in the following
way (when requesting a high enough microversion that includes these details)::

    GET /v1/nodes/detail

    {
      "nodes": [
        {
          ...
          "traits": ['CUSTOM_FOO', 'CUSTOM_BAR', 'CUSTOM_BAZ'],
          ...
        }
      ]
    }

In a similar way to other fields, we will also support a request to get just
this field (in part to make the Nova virt driver polling more efficient)::

    GET /v1/nodes/?fields=uuid,traits

    {
      "nodes": [
        {
          "uuid": "uuid-1",
          "traits": ['CUSTOM_FOO', 'CUSTOM_BAR', 'CUSTOM_BAZ']
        },
        ...
      ]
    }


The manipulation of node traits will follow the patterns established by both
the placement API and API WG tags spec:

* https://developer.openstack.org/api-ref/placement/#resource-provider-traits
* http://specs.openstack.org/openstack/api-wg/guidelines/tags.html

To start with there will be a new traits resource that follows the above
patterns.

Example request for all node traits::

    GET /nodes/{node_ident}/traits

Response::

    {
        "traits": ['CUSTOM_FOO', 'CUSTOM_BAR', 'CUSTOM_BAZ']
    }

Example request to set all node traits to given list::

    PUT /nodes/{node_ident}/traits
    {
        "traits": ['CUSTOM_FOO', 'CUSTOM_BAR', 'CUSTOM_BAZ']
    }

Response::

    {
        "traits": ['CUSTOM_FOO', 'CUSTOM_BAR', 'CUSTOM_BAZ']
    }

The response on success is status code 200. On failure to validate (using the
os-traits library) we return the status code 400 (Bad Request), matching
the HTTP Guidelines from the API-WG.

Note that unlike with Resource Class, we are allowing the trait to be updated
at any time. This is mostly because placement allows such updates and because
although the Resource Class and Ironic node are used in the allocations in
placement, traits are not used in allocations.

In a similar way the following API removes all the traits::

    DELETE /nodes/{node_ident}/traits

The response on success is status code 204, with an empty body.

To add or remove an individual trait use::

    PUT /nodes/{node_ident}/traits/CUSTOM_FOO
    <no body>

    DELETE /nodes/{node_ident}/traits/CUSTOM_FOO

Filtering the node list by traits should work as expected::

    GET /nodes?traits=CUSTOM_RED,CUSTOM_BLUE
    GET /nodes?not-traits=CUSTOM_RED,CUSTOM_BLUE&traits=CUSTOM_FOO
    GET /nodes?traits-any=CUSTOM_RED,CUSTOM_BLUE
    GET /nodes?not-traits-any=CUSTOM_RED,CUSTOM_BLUE

As mentioned above, the final change that is made is to ensure
``instance_info/traits`` is a subset of the traits set on the Ironic node.
This should be part of the existing ``driver.deploy.validate()`` call (or
similar) such that the traits will be checked both before a deploy starts and
on an explicit node validate call.

Client (CLI) impact
-------------------

"ironic" CLI
~~~~~~~~~~~~

No changes, it is deprecated.

"openstack baremetal" CLI
~~~~~~~~~~~~~~~~~~~~~~~~~

You can list the traits on a node:

* openstack baremetal node list --fields uuid name traits
* openstack baremetal node show <node-ident> --fields uuid name traits
* openstack baremetal node trait list <node-ident>

You can update the list of traits on a node:

* openstack baremetal node add trait <node-ident> CUSTOM_FOO CUSTOM_BAR
* openstack baremetal node remove trait <node-ident> CUSTOM_FOO CUSTOM_BAR
* openstack baremetal node remove trait --all <node-ident>

This is roughly copying the command syntax of consistency groups:
https://docs.openstack.org/python-openstackclient/latest/cli/command-objects/consistency-group.html#consistency-group-add-volume

It is common to use set and unset for key value pairs, but add and remove seems
a better fit for in-place modifications of a list. It stops any ambiguity of
set meaning either an addition of a list of traits or replacing the whole list
of traits. Another alternative is to add trait operations into the existing
``openstack baremetal node set`` operation, but we are instead following the
structure of the API.

You can query the list of nodes using traits:

* openstack baremetal node list --trait CUSTOM_RED --not-trait CUSTOM_BLUE
* openstack baremetal node list --trait-any CUSTOM_RED CUSTOM_BLUE
* openstack baremetal node list --not-trait-any CUSTOM_RED CUSTOM_BLUE

RPC API impact
--------------

No impact.

Driver API impact
-----------------

No impact.

Nova driver impact
------------------

Need to ensure the correct flavor extra specs are passed back when starting
a node.

Ramdisk impact
--------------

None

Security impact
---------------

There will be a hard coded limit of 50 traits for any Node to prevent misuse
of the API. This prevents denial of service attack where the database is filled
up by a rogue user setting lots of traits. Really the limit is in place to
match the limit applied in the placement API.

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
  John Garbutt (johnthetubaguy)

Other contributors:
  Dmitry Tantsur (dtantsur)
  Mark Goddard

Work Items
----------

* Add table to store traits for nodes
* Add object to expose the table
* Add new traits API
* Add openstack cli support for the new API
* Follow up with Nova driver work

Dependencies
============

The following nova spec depends on this spec:

* http://specs.openstack.org/openstack/nova-specs/specs/queens/approved/ironic-driver-traits.html

Testing
=======

Nova functional tests are planning on covering the scheduling aspects of the
integration. As part of this spec we will focus on ensuring the API works
correctly to persist the traits for given nodes, and query resources using
traits.

Upgrades and Backwards Compatibility
====================================

Longer term, capabilities and other APIs may be phased out. We are not
considering that as part of this spec. There is much more work needed before
we have feature parity between the old and new scheduling mechanisms.

Documentation Impact
====================

Need to update the API-REF and the admin doc to cover how to use the new API.

References
==========

* http://specs.openstack.org/openstack/nova-specs/specs/pike/approved/resource-provider-traits.html
* http://specs.openstack.org/openstack/nova-specs/specs/queens/approved/ironic-driver-traits.html
* http://specs.openstack.org/openstack/nova-specs/specs/queens/approved/request-traits-in-nova.html
* http://specs.openstack.org/openstack/nova-specs/specs/queens/approved/add-trait-support-in-allocation-candidates.html
