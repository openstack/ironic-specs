..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

======================
Shard Key Introduction
======================

https://storyboard.openstack.org/#!/story/2010378

After much discussion and attempts to remedy the scalability issues with
``nova-compute`` and its connection to Ironic in large scale deployments,
and upon newly discovered indicators of ``networking-baremetal`` having a
similar scaling issue, the community has started to reach an agreement on
a path forward. Specifically, to introduce a sharding model which would
allow API consumers to map and lock on to specific sets of baremetal nodes,
regardless of if the relationship is semi-permanant or entirely situational.
Only the consumer of the information performing processing can make that
determination, and it is up to Ironic to try and provide the substrate
capabilities to efficiently operate against its API.

Problem description
===================

The reality is Ironic can be used at some absurd scales in the hundreds of
of thousands of baremetal nodes, and while *most* operators of Ironic either
run multiple smaller distinct Ironic deployments with less than 500 physical
machines, some need a single deployment with thousands or tens of thousands
of physical nodes. At increased scales, external operations polling ironic,
generally struggle to scale at these levels. It is also easy for
misconfigurations to be made where performance can become degraded,
which is because the scaling model and limits are difficult to understand.

This is observable with the operation of Nova's Compute process when running
the ``nova.virt.ironic`` driver. It is operationally easy to get into
situations where one is attempting to support thousands of baremetal nodes,
with too few ``nova-compute`` processes. This specific situation leads to
the process attempting to take on more work than it was designed to handle.

Recently we discovered a case, while rooted in misconfiguration, where the
same basic scaling issue exists with ``networking-baremetal`` where it is
responsible for polling and updating physical network mappings in Neutron.
The same basic case, a huge amount of work, and multiple processes.
In this specific case, multiple (3) Neutron services were stressing the Ironic
API retrieving all of the nodes, and attempting to update all of the related
physical network mapping records in neutron, resulting in the same record
being updated 3 times, once from each service.

The root issue is the software consuming Ironic's data needs to be able to
self-delineate the overall node set and determine the local separation points
for sharding the nodes. The delineation is required because the processes
executed are far more processor intensive, which can introduce latency and
lag which can lead towards race conditions.

The challenge, from what has been done previously, is the previous model
required downloading the entire data set to build a hash ring from.

Where things are also complicated, is Ironic has an operational model of
a ``conductor_group``, which is intended to help model a physical grouping
or operational constraint. The challenge here is that conductor groups are
not automatic in any way, shape, or form. As a result, conductor groups
is not the solution we need here.

Proposed change
===============

Overall the idea, is to introduce a ``shard`` field on the node object,
which an API user (Service), can utilize to retrieve a subset of nodes.

This new field on the node object would be inline with existing API
field behavior constraints and can be set via the API.

We *can* provide a means to pre-set the shard, but ultimately it is
still optional for Ironic, and the shard *exists* for the API
consumer's benefit.

In order to facilitate the usage by an API client, ``/v1/nodes`` and
``/v1/ports`` would be updated to accept a ``shard`` parameter
(i.e. GET /v1/nodes?shard=foo, GET /v1/ports?shard=foo,
GET /v1/portgroups?shard=foo) in the query to allow for API consumers
to automatically scope limit their data set and self determine how to
reduce the workset. For example, ``networking-baremetal`` may not care
about assignment, it just needs to reduce the localized workset.
Whereas, ``nova-compute`` needs the shard field to remain static, that is
unless ``nova-compute`` or some other API consumer were to request the
``shard`` to be updated on a node.

.. NOTE::
   The overall process consumers use today is to retrieve everything and
   then limit the scope of work based upon contents of the result set.
   This results in a large overhead of work and increased looping latency
   which also can encourage race conditions. Both ``nova-compute``
   and the ``networking-baremetal`` ML2 plugin operate in this way with
   different patterns of use. The advantage of the the proposed solution
   is to enable the scope limiting/grouping into manageable chunks.

In terms of access controls, we would also add a new RBAC policy to
restrict changes such that the system itself or a appropriately scoped
(i.e. administrative) user can change the field.

In this model, conductors do not care about the shard key. It is only
a data storage field on the node. Lookups for contents of the overall
shard composition/layout, for GET /v1/shards, is to be performed
directly against the nodes table using a SQL query.

Alternatives
------------

This is a complex solution to allow simplified yet delineated usage,
and there are numerous other options for specific details.

Ultimately, each item should be discussed, and considered.

One key aspect, which has been recognized thus far, is that existing
mechanisms can be inefficiently leveraged to achieve this. An example
of this is that ``conductor_group``, ``owner``, ``lessee`` all allow for
filtering of the node result set. A ``conductor_group`` being an explicit
aspect an API client can request, where as ``owner`` and ``lessee`` are
access control based filters tied to the API client's submitted Project
ID used for Authentication. More information on why ``conductor_group``
is problematic is further on in this document.

Consensus in discussion with the Nova teams seems to be that usage of
the other fields, while in part may be useful, and possibly even preferred
in some limited and specific cases, doesn't solve the general need
to be able to allow clients to self delineate *without* first downloading
the *entire* node list first. Which in itself, the act of retrieving
a complete list of nodes is a known scaling challenge, and creates increased
processing latency.

In the ``conductor_group`` case, there is no current way to discover
the conductor groups. Where as for ``owner`` and ``lessee``, these are
specific project ID value fields.

Why not Conductor Group?
~~~~~~~~~~~~~~~~~~~~~~~~

It is important to stress similarity wise, this *is* similar to conductor
groups, however conductor groups were primarily purposed to model the physical
constraints and structure of the baremetal infrastructure.

For example, if you have a set of conductors in Europe, and a set of
conductors in New York, you don't want to try and run a deploy for servers
in New York, from Europe. Part of the attractiveness for this to be exposed
or used in Nova, was *also* to align the physical structure. The immediately
recognized bonus to operators was the list of nodes was limited to the running
``nova-compute`` process, if so configured. It is known to the Ironic community
that some infrastructure operators *have* utilized this setting and field to
facilitate scaling of their ``nova-compute`` infrastructure, however these
operators have also encountered issues with this use pattern as well that
we hope to avoid with a shard key implementation.

Where the needs are different with this effort and the pre-existing
conductor groups, is that conductor groups are part of the hash ring modeling
behavior where as in the shards model conductors will operate without
consideration of the shard key value. We need disjointed modeling to support
API consumer centric usage so they can operate in logical units with distinct
selections of work.
Consumers *may* also care about the ``conductor_group`` in addition to the
shard because needing to geographically delineate is separate from needing
smaller "chunks" of work, or in this case "groups of baremetal nodes" for
which a running process is responsible for.

In this specific case, ``conductor_group`` is entirely a manually managed
aspect, which nova has a separate setting name due to name perception reasons,
and our hope ultimately is something that is both simple and smart.

.. NOTE::
   The Nova project has agreed during Project Teams Gathering meetings to
   deprecate the ``peer_list`` parameter they forced use of previously to
   support conductor groups with the hash ring logic.

On top of this, Today's ``conductor_group`` functionality is reliant upon
the hash ring model of use, which is something the Nova team wants to see
removed from the Nova codebase in the next several development cycles.
Where as, Ironic will continue to use the hash ring functionality
for managing our conductor's operating state as it is also modeled for
conductors to manage thousands of nodes. These thousands of nodes just
does not scale well into ``nova-compute`` services.

Why not owner or lessee?
~~~~~~~~~~~~~~~~~~~~~~~~

With the RBAC model improvements which have taken place over the last few
years, it *is* entirely possible to manage separate projects and credentials
for a ``nova-compute`` to exist and operate within. The challenge here is
management of additional credentials and the mappings/interactions.

It might be "feasible" to do the same for scaling ``networking-baremetal``
interactions with Ironic's API, but the overhead and self management of
node groupings seems onerous and error prone.

Also, if this was a path taken, it would also be administratively prohibitive
for nova-computes nodes, and they would be locked to the manual settings.

What if we just let the API consumer figure it out?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This could be an option, but it would lead to worse performance and the
user experience being worse.

The base conundrum is to orderly and efficiently enumerate through, and then
acting upon each and every node API client is responsible for interacting
with.

Today, Nova's Compute service enumerates through every node, using a list
generated upon one query, and it gets *most* of the data it needs to
track/interact with a node, keeping the more costly single node requests to a
minimum. If that client had to track things, it would still have to pull
a full list, and then it would have to reconcile, track, and map individual
nodes. We've already seen this as not working using a Hashring today.

Similarly, ``networking-baremetal`` lists all ports. That is all it needs,
but it has no concept of smaller chunking, blocks, or even enough information
*to* really make a hashring which would represent existing models. To just
expect the client to "figure it out" and to "deal with that complexity",
also means logic far away from a database. And for performance, the closer
we can keep logic and decisions to an indexed column, the better and more
performant, which is why the proposed solution has come forth.

Data model impact
-----------------

Node: Addition of a ``shard`` column/value string field, indexed,
      with a default value of None. This field is considered to be
      case sensitive, which is inline with the DB storage type.
      API queries would seek exact field value matches.

.. NOTE:: We will need to confer with the Nova team and the nova.virt.ironic
          driver query pattern, to ensure we cover any compound indexes,
          if needed.

To facilitate this, database migrations, and data model sanity checking
will need to be added to ``ironic-status`` as part of the upgrade checks.

State Machine Impact
--------------------

None

REST API impact
---------------

PATCH /v1/nodes/<node>

In order to set a shard value, a user will need to patch the field.
This is canned functionality of the existing nodes controller, and will
be API version and RBAC policy guarded in order to prevent inappropriate
changes to the field once set. Like all other fields, this operation
takes the shape of a JSON Patch.

GET /v1/nodes?shard=VALUE,VALUE2,VALUE3

Returns a subset of nodes limited by shard key. In this specific case
we will also allow a string value of "none", "None" or "null" to
be utilized to retrieve a list of nodes which do *not* have a shard
key set. Logic to handle that would be in the DB API layer.

GET /v1/ports?shard=VALUE,VALUE2,VALUEZ
GET /v1/portgroupss?shard=VALUE,VALUE2,VALUEZ

Returns a subset of ports, limited by the shard key, or list of keys
provided by the caller. Specifically would utilize a joined query
to the database to facilitate it.

GET /v1/shards

Returns a JSON representing the shard keys and counts of nodes
utilizing the shard.

    {{"Name": "Shard-10", "Count": 352},
    {"Name": "Shard-11", "Count": 351},
    {"Name": "Shard-12", "Count": 35},
    {"Name": null, "Count": 921}}

Visibility wise, the new capabilities will be restricted by API
micro-version. Access wise this field would be restricted in use to
``system-reader``, ``project-admin``, and future ``service`` roles
by default. A specific RBAC policy would be added for access to
this endpoint.

.. NOTE::
   The /v1/shards endpoint will be read only.

Client (CLI) impact
-------------------
Typically, but not always, if there are any REST API changes, there are
corresponding changes to python-ironicclient. If so, what does the user
interface look like. If not, describe why there are REST API changes but
no changes to the client.

"openstack baremetal" CLI
~~~~~~~~~~~~~~~~~~~~~~~~~

A ``baremetal shard list`` command would be added.

A ``baremetal node list --shard <shard>`` capability would be
added to list all nodes in a shard.

A ``--shard`` node level parameter for ``baremetal node set``
would also be added.

A ``baremetal port list --shard <shard>`` capability would be
added to limit the related ports to nodes in a shard. Similarly,
the ``baremetal portgroup list --shard <shard>`` would be updated
as well.

"openstacksdk"
~~~~~~~~~~~~~~

A SDK method would be added to get a shard list, and existing list methods
would be checked to ensure we can query by shard.

RPC API impact
--------------

None anticipated at this time.

Driver API impact
-----------------

None

Nova driver impact
------------------

A separate specification document is being proposed for the Nova
project to help identify *and* navigate the overall change.

That being said, no direct negative impact is anticipated.

The overall discussion revolving with Nova is to both facilitate a
minimal impact migration, and not force invasive and breaking changes,
which may not be realistically needed by the operators.

.. NOTE:: An overall migration path is envisioned, but what is
          noted here is only a suggestion and how we perceive the
          overall process.

Anticipated initial Nova migration steps:

Ironic itself will not be providing an explicit process for setting the
shard value on each node, aside from ``baremetal node set``. Below is what
*we, Ironic* anticipate as the migration steps overall to move towards this
model.

1) Complete the Ironic migration. Upon completion, executing the database
   status check (i.e. ``ironic-status upgrade check``) should detect and warn
   *if* a ``shard`` key is present on nodes in the database, but nodes
   exist without a ``shard`` value are present in the database.
2) The nova-compute service being upgraded is shut down.
3) A nova-manage command would be executed to reassign nodes to a user
   supplied ``shard`` value to match.
   Example: nova-manage ironic-reassign <shard-key> <compute-hostname>

   Programmatically, this would retrieve a list of nodes matching the key from
   Ironic, and then change the associated ComputeNode and Instance tables host
   fields to be the supplied compute hostname, to match an existing nova
   compute service.

   .. NOTE:: The command likely needs to match/validate that this is/was a
             compute hostname.

   .. TODO:: As a final step before the nova-manage command exits, ideally it
             would double check the state of records in those tables to
             indicate if there are other nodes the named Compute hostname is
             responsible for. The last compute hostname in the environment
             should not generate any warning, any warning would be indicitive
             of a lost ComputeNode, Instance, or Baremetal node record.

4) The nova-compute.conf file for the upgraded ``nova-compute`` service is
   restarted with a ``my_shard`` (or other appropriate parameter) which
   signals to the ``nova.virt.ironic`` driver code to not utilize the hash
   ring, and to utilize the blend of what it thinks it is responsible for
   from the database *and* what matches the Ironic baremetal node inventory
   when queried for matching the configured shard key value.
5) As additional compute nodes are migrated to using the new shard key setup,
   existing compute node imbalance should be settled in terms of the
   internal compute-node logic to retrieve what each node it thinks it is
   responsible for, and would eventually match the shard key.

This would facilitate an ability to perform a rolling, yet isolated outage
impact as the new nova-compute configuration is coming online, and also allows
for a flow which should be able to be automated for larger operators.

The manageability, say if one needs to change a ``shard`` or rebalance
shards, is not yet clear. The current discussion in the Nova project is that
rebalance/reassociation will only be permitted *IF* the compute service
has been "forced down" which is an irreversible action

Ramdisk impact
--------------

None

Security impact
---------------

The ``shard`` key would be API user settable, as long as sufficient
API access exists in the RBAC model.

The ``/v/shards`` endpoint would also be restricted based upon the RBAC
model.

No other security impacts are anticipated.

Other end user impact
---------------------

None Anticipated

Scalability impact
------------------

This model is anticipated to allow users of data stored in Ironic to be more
scalable. No impacts to Ironic's scalability are generally anticipated.

Performance Impact
------------------

No realistic impact is anticipated. While another field is being added,
initial prototyping benchmarks have yielded highly performant response
times for large sets (10,000) baremetal nodes.

Other deployer impact
---------------------

It *is* recognized that operators *may* wish to auto-assign or auto-shard
the node set programmatically. The agreed upon limitation amongst Ironic
contributors is that we (Ironic) would not automatically create *new*
shards in the future. Creation of new shards would be driven by the operator
by setting a new shard key on any given node.

This may require a new configuration option to control this logic, but
the logic overall is not viewed as a blocking aspect to the more critical
need of being able to "assign" a node to a shard. This logic may be added
later on, we will just endeveour to have updated documentation to explain
the appropriate usage and options.

Developer impact
----------------

None anticipated

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Jay Faulkner (JayF)

Other contributors:
  Julia Kreger (TheJulia)

Work Items
----------

* Propose nova spec for the use of the keys
  (https://review.opendev.org/c/openstack/nova-specs/+/862833)
* Create database schema/upgrades/models.
* Update Object layer for the ``Node`` and ``Port`` objects in order to
  permit both objects to be queried by ``shard``.
* Add query by shard capability to the Nodes and Ports database tables.
* Expose ``shard`` on the node API, with an incremented microversion
  *and* implement a new RBAC policy which restricts the ability to change
  the ``shard`` value
* Add pre-upgrade status check to warn if there are fields which are
  not consistently populated. i.e. ``shard`` is not populated on
  all nodes. This will provide visibility into the mixed and possibly
  misconfigured operational state for future upgrader.
* Update OpenStack SDK and python-ironicclient

Dependencies
============

This specification is loosely dependent upon Nova accepting
a plan for use of the sharding model of data. At present, it is the
Ironic team's understanding that it is acceptable to Nova, and Ironic
needs to merge this spec and related code to support this feature before
Nova will permit the Nova spec to be merged.

Testing
=======

Unit testing is expected for all the basic components and operations
added to Ironic to support this functionality.

We may be able to add some tempest testing for the API field and access
interactions.

Upgrades and Backwards Compatibility
====================================

To be determined. We anticipate that the standard upgrade process would apply
and that there would not realistically be an explicit downgrade compatibility
process, but this capability and functionality is largely for external
consumption, and details there are yet to be determined.

Documentation Impact
====================

Admin documentation would need to include an document covering sharding,
internal mechanics, and usage.

References
==========

PTG Notes: https://etherpad.opendev.org/p/nova-antelope-ptg
Bug: https://launchpad.net/bugs/1730834
Bug: https://launchpad.net/bugs/1825876
Related Bug: https://launchpad.net/bugs/1853009

