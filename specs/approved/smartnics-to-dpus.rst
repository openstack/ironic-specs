..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=======================================
The evolution of the Smart NICs to DPUs
=======================================

https://bugs.launchpad.net/ironic/+bug/2019043

The ideas behind "Smart NICs" have evolved as time has progressed.

And honestly it feels like we in the Ironic community helped drive some
of that improvement in better, more secure directions. Hey! We said we
we're changing the world!

What started out as highly advanced network cards which infrastructure
operators desired to offload some traffic, have morphed into a more generic
workload, yet still in oriented in the direction of offload. Except now these
newer generations of cards have their own BMC modules, and a limited subset of
hardware management can occur.

But the access model and use/interaction also means that a server can have a
primary BMC, and then N number of subset BMCs, some of which may, or may not
be able to communicate with the overall BMC and operating system.

And in order to really support this, and the varying workflows, we need to
consider some major changes to the overall model of interaction and support.
This is not because the device is just a subset, but a generalized computer
inside of a computer with it's own unique needs for management protocols,
boot capabilities/devices, architecture, and has it's own console, internal
state, credentials, et cetra.

Problem description
===================

Context Required
----------------

In order to navigate this topic, we need to ensure we have context of various
terms in use and as they relate.

Smart NIC
~~~~~~~~~

These are best viewed as a "first generation" of DPU cards where an offload
workload is able to be executed on a card, such as a Neutron agent connected
to the message bus in order to bind ports to the physical machine.

Some initial community and vendor discussions also centered around further
potential use cases of providing storage attachments through, similar to the
behavior of a Fibre Channel HBA.

Composible Hardware
~~~~~~~~~~~~~~~~~~~

The phrase "Composible Hardware" is unfortunately overloaded. This is best
described as use of a centralized service to "compose" hardware for use by
a workload. A good way to view this, at least in a classical sense is through
an API or application constructing a cohesive functioning computer resource
with user definable CPU, Memory, Storage, and Networking. Essentially to
virtualize the hardware interaction/modeling like we have with Virtual
Machines.

Aside from some limited hardware offerings from specific vendors, Composible
Hardware largely hasn't been realized as initially pitched by the hardware
manufacters.

DPUs
~~~~

A DPU or Data Processing Unit is best viewed as a more generalized,
"second generation" of the Smart NIC which is designed to run more
generalized workloads, however this is not exclusively a network
or adapter to network attached resources. For example, one may want to
operate a BGP daemon inside of the card, which is entirely out of scope
ironic to operate with and manage, but they could run the service there
in order to offload the need to run it on the main CPUs of the system.
A popular, further idea, is to utilize the card as a "root of trust"

A similarity between DPU's and Composible hardware in modeling is the
concept of providing potentially remote resources to the running operating
system.

Given the overall general purpose capabilities of DPUs and increased
focus of specific computing workload offloads, we need to be careful
to specifically delineate which use cases we're attempting to support,
and also not try to assume one implies the other. In other words, DPUs do
offer some interesting capabilities towards Composible Hardware, however
it is inherently not full configuration as the underlying host is still
a static entity.

.. NOTE::
   DPUs are also sometimes expressed as xPUs, because classical graphics
   cards are Graphics Processing Units. While there does not appear to be
   any explicit movement into supporting that specific offload, some vendors
   are working on highly specific processing cards such those as performing
   protocol/signal translation. They may, or may not be able to have
   an operating system or provisioned application.

The problem
-----------

Today, In Ironic, we have a concept of a baremetal node. Inside of that
baremetal node, there may be various hardware which can be centrally managed,
and interacted with. It has a single BMC which controls basically all aspects.

We also have a concept of a "smart nic" in the form of ``is_smartnic`` on
port objects. However this only impacts Ironic's power and boot mode
management.

Except, not all of these cards are "network" cards, or at least "network"
cards in any traditional computing model. Think Radios!

And the intertwined challenge is this nested access model.

For the purpose of this example, I'm going to refer to Nvidia Bluefield2 cards
with a BMC. It should be noted we have support in Antelope IPA to update
the BMC firmware of these cards. At least, that is our understanding
of the feature.

But to do so:

1) From the host, the access restrictions need to be dropped by
   requesting the BMC on the card to permit the overall host OS to
   Access the card's BMC. This is achievable with an IPMI raw command, but
   against the card's BMC.
2) Then you would apply BMC firmware updates, to the card's BMC
   Today this would boot IPA, and perform it from the host OS, which also
   means that we're going to need to interact with the overall host BMC,
   and boot the baremetal machine overall.
3) Then you would naturally want to drop these rights, which requires calling
   out to the card's BMC to change the access permissions.
4) Then if you wanted to update the OS on the card itself, you would rinse
   and repeat the process, with a different set of commands to open the access
   between the OS on the card, and the OS on the BMC.

.. NOTE:: We know the Bluefield2 cards can both be network booted, and updated
   by SSH'ing into the BMC and streaming the new OS image to the installer
   command over SSH. That, itself, would be a separate RFE or feature
   but overall modeling changes would still be needed which this specification
   seeks to resolve.

Hopefully this illustrates the complexity, begins to underscore the need as to
why we need to begin to support a parent/child device model, and permit the
articulation of steps upon a parent node which applies to the one or more
children nodes.

What complicates this further is is ultimately we're just dealing with many
different Linux systems, which have different models of access. For example,
A more recent Dell Server running IPA, with two of these specalized cards,
henceforth referred to as Data Processing Units (DPUs), would have Linux
running on the host BMC, On the host processors, inside the BMCs of each
DPU card, and inside of the processor on the DPU card.

This specification does inherently exclude configuration of the operating
state configuration of the DPU card. There are other projects which are
working on that, and we look forward to integrating with them as they
evolve.

.. NOTE::
   The other project in mind is the OPI project, which is working on quite
   a lot of capabilities in this space, however they explicitly call out
   automated/manual deployment via outsize of zero touch provisioning is out
   of scope for their project. Such is sensible to stand-up a general purpose
   workload, but operating lifecycle and on-going management is an aspect
   where Ironic can help both operators who run a variety of workloads and
   configurations, or need to perform more specific lifecycle operations.

Proposed change
===============

The overall idea with this specification is to introduce the building blocks
to enable the orchusrtration and articulation of actions between parent and
child devices.


* Introduction of ``parent_node`` field on the node object with an API
  version increase.

* Introduction of a sub-node resource view of ``/v1/nodes/<node>/children``
  which allows the enumeration of child nodes.

* Default the /v1/nodes list to only list nodes without a parent, and add a
  query filter to return nodes with parents as well.

* Introduction of a new step field value, ``execute_on_child_nodes`` which
  can be submitted. The default value is False. Steps which return CLEANWAIT,
  i.e. steps which expect asynchronous return will not be permitted under
  normal conditions, however this will be available via a configuration option.

* Introduction of a new step field value, ``limit_child_node_execution``,
  which accepts a list of node UUIDs to allow filtering and constraint
  of steps on some nodes. Specifically, this is largely separate from the
  ``execute_on_child_nodes`` field due to JSON Schema restrictions.

* Introduction of the ability to call a vendor passthrough interface
  as a step. In the case of some smartnics, they need the ability to
  call IPMI raw commands across child nodes.

* Introduction of the ability to call ``set_boot_device`` as a step.
  In this case, we may want to set the DPU cards to PXE boot en-mass
  to allow for software deployment in an IPA ramdisk, or other mechanism.

* Introduction of the ability to call ``power_on``, ``power_off`` management
  interface methods through the conductor set_power_state helpers
  (which includes guarding logic for aspects like fast track).

* Possibly: Consider "physical" network interfaces optional for some classes
  of nodes. We won't know this until we are into the process of
  implementation of the capabilities.

* Possibly: Consider the machine UUID reported by the BMC as an identifier
  to match for agent operations. This has long been passively desired inside
  of the Ironic community as a "nice to have".

* Possibly: We *may* need to continue to represent a parent before child or
  child before parent power management modeling like we did with the Port
  object ``is_smartnic`` field. This is relatively minor, and like other
  possible changes, we won't have a good idea of this until we are further
  along or some community partners are able to provide specific feedback
  based upon their experiences.

With these high level and workflow changes, it will be much easier for an
operator to orchestrate management actions across an single node to extend
further into distinct devices within the whole of the system.

In this model, the same basic rules for child nodes would apply, they may have
their own power supplies and their own power control, and thus have inherent
"on" and "off" states, so deletion of a parent should cause all child nodes
to be deleted. For the purpose of state tracking, the individual cards if
managed with a specific OS via Ironic, may be moved into a deployed state,
however they may just also forever be in a ``manageable`` state independent
of the parent node. This is because of the overall embedded nature, and it
being less of less of a general purpose compute resource compute resource
while *still* being a general computing device. This also sort of reflects
the inherent model of it being more like "firmware" management to update
these devices.

Outstanding Questions
---------------------

* Do we deprecate the port object field ``is_smartnic``? This is documented
  as a field to be used in the wild for changing the power/boot configuration
  flow on first generation smartnics which is still applicable on newer
  generations of cards should the operator have something like Neutron OVS
  agent connected on the message bus to allow termination of VXLAN connections
  to the underlying hardware within the card.

Out of Scope, for this Specification
------------------------------------

Ideally, we do eventually want to have DPU specific hardware types, but the
idea of this specification is to build the substrate needed to build upon to
enable DPU specific hardware types and enable advanced infrastructure
operators to do the needful.

Alternatives
------------

Three alternatives exist. Technically four.

Do nothing
~~~~~~~~~~

The first option is to do nothing, and force administrators to manage their
nested hardware in a piecemeal fashion. This will create a barrier to Ironic
usage, and we already know from some hardware vendors who are utilizing these
cards along side Ironic, that the existing friction is a problem point
in relation to just power management. Which really means, this is not a viable
option for Ironic's use in more complex environments.

Limit scope and articulate specific workflows
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A second option is to potentially limit the "scope of support" to just power
or boot operations. However, we have had similar discussions, in relation to
supporting xPU's in servers with external power supplies in the past, and have
largely been unable to navigate a workable model, in large part because this
model would generally require a single task.node to be able to execute with
levels of interfaces with specific parameters. For example, to the system BMC
for base line power management, and then to a SNMP PDU for the auxiliary power.
This model also doesn't necessarily work because then we would inherently
have blocked ourselves from more general managmeent capabilities and access
to on DPU card features such as "serial consoles" through it's own embedded
BMC without substantial refactoring and re-doing the data model.

There is also the possibility that nesting access controls/modeling may not
be appropriate. You don't necessarily want to offer an baremetal tenant in a
BMaaS who has lessee access to Ironic, the ability to get to a serial console
which kind of points us to the proposed solution in order to provide
capabilities to handle the inherently complex nature of modeling which can
result. Or eat least provide organic capabilities based upon existing code.

Use Chassis
~~~~~~~~~~~

The third possibility is to use the existing Chassis resource. The idea
of a parent/child relationship *does* sound similar to the modeling of
Chasssis and a Node.

Chassis was originally intended to allow the articulation of entire Racks
or Blade Chassis in Ironic's data model, in part to allow relationship and
resource tracking more in lines with a Configuration Management Data Base
(CMDB) or Asset Inventory. However, Chassis never gained much traction because
those systems are often required and decoupled in enterprise environments.

Chassis has been proposed to be removed several times in Ironic, and does
allow the creation of a one to many relationship which cannot
presently be updated after it is set. Which inherently is problematic
and creates a maintenanance burden should a card need to be moved or a
chassis replaced but the DPU is just moved to the new chassis.

But the inherent one to many modeling which can exist with DPUs ultimately
means that the modeling is in reverse from what is implemented for usage.
Nodes would need to be Chassises, but then how do users schedule/deploy
"instances", much less perform targeted lifecycle operations against part
of the machine which is independent, and can be moved to another chassis.

Overall, this could result in an area where we may make less progress
because we would essentially need to re-model the entire API, which might
be an interesting challenge, but that ultimately means the work required
is substantially larger, and we would potentially be attempting to remodel
interactions and change the user experience, which means the new model would
also be harder to adopt with inherently more risk if we do not attempt to
carry the entire feature set to a DPU as well. If we look at solving the
overall problem from a "reuse" standpoint, the proposed of this specification
document solution seems like a lighter weight solution which also leaves the
door open to leverage the existing capabilities and provide a solid foundation
for future capabilities.

Realistically, The ideal use case for chassiss is fully composible hardware
where some sort of periodic works to pre-populate "available" nodes to be
scheduled upon by services like Nova from a pool of physical resources,
as well as works to reconcile overall differences. The blocker though to that
is ultimately availability of the hardware and related documentation to
make a realistic Chassis driver happen in Open Source.

Create a new interface or hardware type
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We could create a new interface on a node, or a new hardware type.

We do eventually want some DPU specific items to better facilitate and enable
end operators, however there is an underling issue of multiple devices, a
one to many relationship. Further complicated by a single machine may have
a number of different types of cards or devices, which kind of points us
back to the original idea proposed.

Data model impact
-----------------

A ``parent_node`` field will be added, and the field will be indexed.
A possibility exists that the DB index added may be a multi-field
compound index as well, but that is considered an implementation detail.

State Machine Impact
--------------------

No State Machine impact is expected.

REST API impact
---------------

GET /v1/nodes/?include_children=True

Returns a list of base nodes with all child nodes child nodes, useful for
a big picture view of all things Ironic is responsible for.

GET /v1/nodes/

The view will by default return only nodes where the ``parent_node`` field
is null. Older API clients will still receive this default behavior change.

GET /v1/nodes/<node_ident>/children

Will return the list of nodes, with the pre-existing access list constraints
and modeling of all defined nodes where ``parent_node`` matches
``node_ident``. In alignment with existing node list behavior, if access
rights do not allow the nodes to be viewed, or there are no nodes, an empty
list will be returned to the API client.

Additional parameters may also be appropriate with this field, but at present
they are best left to be implementation details leaning towards the need to
not support additional parameters.

.. NOTE:: We would likely need to validate the submitted node_ident is also
   a UUID, otherwise resolve the name to a node, and then lookup the UUID.

A links field will refer to each node, back to the underlying node which
may require some minor tuning of the logic behind node listing and link
generation.

All of the noted changes should be expected to be merged together with a
microversion increase. The only non-version controlled change, being the
presence/match of the ``parent_node`` field.

Corresponding API client changes will be needed to interact with this area
of the code.

Client (CLI) impact
-------------------

"openstack baremetal" CLI
~~~~~~~~~~~~~~~~~~~~~~~~~

The ``baremetal`` command line interface will need to receive parameters
to query child nodes, and query the child nodes of a specific node.

"openstacksdk"
~~~~~~~~~~~~~~

An SDK change may not be needed, or may be better suited to occur organically
as someone identifies a case where they need cross-service support.

RPC API impact
--------------

No additional RPC API calls are anticipated.

Driver API impact
-----------------

No direct driver API changes are anticipated as part of this aside
from ensureing the management interface ``set_boot_device`` as well as
the IPMI interface ``send_raw`` commands can be called via the steps
framework.

Nova driver impact
------------------

None are anticipated, this is intended to be invisible to Nova.

Ramdisk impact
--------------

The execution of our ramdisk inside of a DPU is presently considered out of
scope at this time.

Some of the existing smartnics might not be advisable to have operations like
"cleaning" as well, for example Bluefield2 cards with more traditional SPI
flash as opposed to NVMe in Bluefield3 cards. Given some of the speciality
in methods of interacting with such hardware, we anticipate we may eventually
want to offer specific deployment or boot interfaces which may bypass some of
the inherent "agent" capabilities.

Security impact
---------------

No additional security impact is anticipated as part of this change.

Other end user impact
---------------------

None

Scalability impact
------------------

This change does propose an overall relationship and ability which may result
far more nodes to be managed in ironic's database. It may also be that for
child devices, a power synchronization loop may *not* be needed, or can be
far less frequent. These are ultimately items we need to discuss further,
and consider some additional controls if we determine the need so operators
may not feel any need nor impact to their deployments due to the increase in
rows int the "nodes" table.

.. NOTE::
   It should be noted that the way the hash ring works in Ironic, is that the
   ring consists of the *conductors*, which are then mapped to based upon
   node properties. It may be that a child node's mapping should be the
   parent node. These are questions to be determined.

Performance Impact
------------------

No direct negative impact is anticipated. The most direct impact will be the
database and some periodics which we have already covered in the preceding
section. Some overall performance may be avoided by also updating some of
the periodics to not possibly match any child node, the logical case is
going to be things like RAID periodics, which would just never apply and
should be never configured for such a device, which may itself make the
need to make such a periodic change moot.

Other deployer impact
---------------------

No negative impact is anticipated, but it might be that operators may
rapidly identify need for a "BMC SSH Command" interface, as the increasing
trend of BMCs being linux powered offers increased capabilities and
possibilities, along with potential needs if logical mappings do not map
out.

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Julia (TheJulia) Kreger <juliaashleykreger@gmail.com>
Other contributors:
  <IRC handle, email address, None>

Work Items
----------

* Addition of ``parent_node`` db field and node object.
* Addition of node query functionality.
* Introduction of the /v1/nodes/<node>/children API resource
  and the resulting API microversion increase.
* Add step support to iterate through step definitions which
  has mixed step commands for parent nodes and child node.
* Introduction of generalized power interface steps:
  * ``power_on``
  * ``power_off``
* Add an IPMI management interface ``raw`` command step method.
* Examples added for new step commands and invocation of child
  node objects.

Dependencies
============

None.

Testing
=======

Basic tempest API contract testing is expected, however a full tempest
scenario test is not expected.

Upgrades and Backwards Compatibility
====================================

No negative impact is anticipated.

Documentation Impact
====================

Documentation and examples are expected as part of the work items.

References
==========

- https://github.com/opiproject/opi-prov-life/blob/main/PROVISIONING.md#additional-provisioning-methods-out-of-opi-scope
- https://docs.nvidia.com/networking/display/BlueFieldBMCSWLatest/NVIDIA+OEM+Commands
