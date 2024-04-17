..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===============
Project Mercury
===============

https://bugs.launchpad.net/ironic/+bug/2063169

This is a project to create an simplified framework between Ironic and
physical network configuration to facilitate orchustration of networking
in a delineated way from existing OpenStack Neutron service in a model
which would able to operated effectively by another team which is not
a "cloud" team, but a "network" team.

The reasons why are plentiful:

* The number of Operators utilizing Ironic continue to grow, although the
  operators utilizing Ironic in fully integrated configurations is not
  growing at the same rate as operators running in a "standalone" mode.
* Operators needing physical switch management generally need to operate
  in an environment with strong enforcement of separation of duties.
  i.e. The software might not be granted access to the Switch management
  framework, nor can such a service be accessible by any users under any
  circumstances.
* The introduction of DPUs generally means that we now have potential cases
  where switches need to be programmed to provision a DPU, and then the DPU
  needs to be programmed to provision servers.

The goals can be summarized as:

* Provide a mechanism to configure L2 networks on Switches, which may be
  facilitated by a modified networking-generic-switch or similar plugin.
* Provide a mechanism to configure L2 networks to be provided to a host
  from a DPU.
* Provide a mechanism to accomodate highly isolated network management
  interfaces where operators restrict access such that *only* Ironic
  is able to connect to the remote endpoint.
* Provide a tool to apply and clean-up configuration, *not* track
  and then assert configuration. This doesn't preclude a future
  "double check this configuration" mode from existing at some point,
  but the minimal viable functionality is application and removal of
  the network configuration.
* Provide a mechanism of receiving the call to do something, reading in
  networking configuration credentials from local storage, and then doing
  so without the need of a database *OR* shared message bus.

This project is NOT:

* Intended to provide any sort of IPAM functionality.
* Intended to provide management of Routing.
* Intended to provide management of Security Groups or Firewalling.
* Intended to provide a public ReSTful API, nor require a database.

This project MAY:

* Provide a means to help enable and deploy advanced tooling to a DPU under
  Ironic's control.
* Provide a means of offloading some of the layer2 interaction responsibility
  in an environment *with* Neutron and Ironic, espescially.

.. warning::
   This document is not a precise and thus prescriptive design document, but
   an document to record and surface the ideas in a way that can foster
   communication and consensus building. In this case, we are likely to
   leave it to the implementer's progotive with this document being overall
   guard rails.

Problem description
===================

Today, Ironic has only one option to facilitate the automation of switch
level infrastructure, which is to leverage Neutron and the ML2 interface.
Unfortunately, infrastructure operators needing Ironic largely reject this
model because the network is often owned by a separate group.

As a result we need a service to facilitate secure and delienated network
management which can be owned and operated by separate infrastructure team
in an enterprise organization, which brings together, aspects like simple code
patterns and playbooks such that they can trust the interface layer to apply
basic network configuration and enable easier use of Bare Metal. In most cases
where this is needed, just the physical port needs to be set to a specific
network; addressing is often separately managed and not our concern.

Furthermore, the available ecosystem in the DPU spaces wants to model their
devices in a variery of ways and some of those devices have inherent
limitations. For example, some devices are just another computer embedded and
connected to the same PCI device bus. Others present the ability
to load a P4 program to handle specific tasks. Or the available Flash and RAM
of a device is highly limited such that options are very limited and entirely
exclude all "off the shelf" operating systems and their utilities. This nature
makes almost every device and their resulting use case entirely govern their
configuration and use model which means an easy to modify modular interface
would provide the greatest potential impact.

Proposed change
===============

We are proposing an RPC service. Specifically something along the lines of a
JSON-RPC endpoint, which multiple ironic conductors would be able to connect
to in order to request networking changes to be made.

Along side of the RPC service, we would have an appropriately named
``network_interface`` driver to take the information stored inside of Ironic
and perform attachment of interfaces based upon the provided information.

.. note::
   A distinct possibility exists that we may actually start with a hybird
   dual ``network_interface`` driver to help us delineate and handle
   integration in a clear fashion. This is much more of an "implementor's
   progorative" soft of item.

MVP would likely exclude locking, but be modeled as a single worker service
or container which does not maintain state, largely simplfies the problem to
"who is logged into what" to make concurrent changes, which has been the
historical driver for locking.

.. note::
   Teaching networking-baremetal to call this proposed RPC service is
   generally considered out of scope of this work, but entirely within
   reason and possibility to facilitate as this would provide functionally
   a capability for some calls to be proxied through and related to
   actions for a Neutron deployment to ultimately also call this new service.

The overall call model, at a high level could take the following flow.::

 ┌──────────────────────────┐
 │Inbound Request/Connection│
 └───┬──────────────────────┘
     │
 ┌───▼────────────────────────────┐
 │{"type": "attach_port",         │
 │ "payload": {"context": {...}}} │
 └───┬────────────────────────────┘
     │
 ┌───▼──────────────────────────┐
 │Invoke Plugin With Context    │
 └───┬──────────────────────────┘
     │
 ┌───▼────────────────────────────────┐
 │Plugin handles locking, if necessary│
 └───┬────────────────────────────────┘
     │
 ┌───▼───────────────────────────────────────────────────────┐
 │Plugin succeeds (HTTP 200?) or fails and returns HTTP error│
 └───────────────────────────────────────────────────────────┘

While originally envisioned to just be able to load an ML2 plugin directly,
there plugins design model has some challenges in this context of remote
execution, which is likely why a remote RPC model never evolved in Neutron.

Two basic issues:

1) Plugins, upon completing the binding action, update the database state in
   neutron through a pattern of updating the neutron database. This requires
   database access and credentials which are not available in our use case and
   model.

2) Plugins may also invoke methods on the original provided context.
   Context in Neutron, in this case, is not context provided by
   oslo.context, but an entirely separate construct consisting of
   past and future state information for the networking being modified.

So the obvious path forward is to simplify the model and design the RPC model
used for this interaction around the basic actions, and allow for an ML2 user,
the ability for the calls to be made which abstract the actions from the
information/state/configuration updates.

* get_allowed_network_types - Returns a list of supported network types which
  can allow the caller to determine if the action can be supplied.
  Presently, baremetal engaging ML2 plugins largely just hard-code this as
  only supporting a VLAN type, but pushing this as far out as possible to
  a plugin being executed allows for it to be a generic pass-through.

* is_link_valid - Returns True/False depending on if the request has
  sufficient and correct information to be acted upon. Could be used
  for basic pre-action validation.

* is_port_supported - Returns True/False depending if the requested port
  is supported for actions. Generally this is a VNIC type check today,
  but could also be used by the remote service to perform basic
  pre-fliflight validation actions and allow a client to fail-fast.

* attach_port - Performs the actual action of "attaching"
  (Adding vlans or ultimately VNI's to a port).

* detach_port - Performs the actual action of "detaching"
  (removing network access from a port).

* update_port - Peroforms an attempt to update a port for "attachment",
  such as if port-channels/bonding properties have changed.

* add_network - Adds a network to the remote device.

* delete_network - Deletes the network from the remote device.

In a sense, this changes the idea of "just load an ml2 plugin" to
"load either a hybridized ml2 plugin interface, OR just define
our own plugin model which can be supported", and as such is an
outstanding question this specification seeks to bring an answer to.

For the remote RPC service, it is anticipated that logging will need to
be verbose enough that Operators can understand the questions they may raise
when investigating issues. For example: When, Who, What, Why, and How.
Plugin code in Ironic should **also** log verbosely when invoked to ensure
operators can match requests and resulting changes should an issue arise.

While beyond an initial MVP of basic functionality, to solve the DPU case,
the overall pattern model would likely take the shape of one where Ironic
would enumerate through the "child nodes", attach the child nodes to the
requested physical network, and then engage on some level of programming
which may need to be vendor or deployment specific based upon the overall
use model. Details which at present time cannot be determined without the
foundational layer needing to be constructed before being built upon.

From a user's standpoint, the following sequence depicts their basic
interaction and the overall resulting sequence.::

 ┌──────────────────────────────┐
 │ Existing node chosen by user │
 └───┬──────────────────────────┘
     │
 ┌───▼───────────────────────────────────────────────┐
 │ User posts to /v1/nodes/<ident>/vifs with payload │
 │ containing an id of a vlan ID.                    │
 └───┬───────────────────────────────────────────────┘
     │
 ┌───▼──────────────────────────────────────────────┐
 │ User requests the node to deploy via the         │
 │ /v1/nodes/<ident>/states/provision API interface │
 └───┬──────────────────────────────────────────────┘
     │
 ┌───▼──────────────────────────────────────────────┐
 │ Ironic follows existing flow, triggering the new │
 │ network_interface module which calls this new    │
 │ service to perform the attach/detach operations  │
 │ in accordance with the existing model and node   │
 │ lifecycle state.                                 │
 │ Initial network in a deploy is the provisioning  │
 │ network.                                         │
 └───┬──────────────────────────────────────────────┘
     │
 ┌───▼──────────────────────────────────────────────┐
 │ Node deployment proceeds with resources already  │
 │ connected to the desired network.                │
 └───┬──────────────────────────────────────────────┘
     │
 ┌───▼──────────────────────────────────────────────┐
 │ Once deployment has been completed, the network  │
 │ interface module calls the new service to change │
 │ the attachment to the requested vlan ID. In the  │
 │ event of a failure, the physical switch port     │
 │ is detached.                                     │
 └──────────────────────────────────────────────────┘

Alternatives
------------

The closest alternative would be a ``standalone Neutron`` coupled with some
sort of extended/proxy RPC model, which is fine, but that really does not
address the underlying challenge of the attach/detach functionality
being needed by Infrastructure Operators. It also introduces modeling which
might not be suitable for bulk infrastucture operators as they would need
to think and operate a cloud model, as opposed to the physical infrasructure
model. Plus operating Neutron would require a database to be managed,
increasing operational complexity, and state would also need to still
be navigated which increases the configuration and code complexity based upon
different Neutron use models.

Another possibility would be to directly embed the network attach/detach
loading and logic into Ironic itself, however that would present difficulties
with maintenance where we largely want to unlock capability.

Data model impact
-----------------

At this time, we are largely modeling the idea to leverage existing port data
stored inside of Ironic which is utilized for attachment operations.

A distinct possibility exists we may look at storing some additional physical
and logical networking detail inside of Ironic's database to be included in
requests, which could possibly be synchronized, but this would be beyond the
scope of the minimum viable product as in the initial phase we intend to use
the VIF attach/detach model to represent the logical network to be attached.

State Machine Impact
--------------------

None

REST API impact
---------------

With a MVP, we do not anticipate any REST API changes to Ironic itself
with the very minor exception of the loosing of a Regular Expression
around what Ironic accepts for VIF attachment requests. This was agreed
upon by the Ironic community quite some time ago and just never performed.

Existing fields on a node and port will continue to be used just as they
have before with an MVP.

Post-MVP may include some sort of /v1/physical_network endpoint to be
designed, but that is anticipated to be designed once we know more.

Client (CLI) impact
-------------------

"openstack baremetal" CLI
~~~~~~~~~~~~~~~~~~~~~~~~~

None

"openstacksdk"
~~~~~~~~~~~~~~

None

RPC API impact
--------------

This change proposes a service which would be accessed by Ironic utilizing
an RPC model of interaction. This means there would be some shared meaning
for call interactions in the form of a library.

In all likelihood, this may be as simple as "attach" and "detach", but given
the overall needs of an MVP and a use model we're focusing upon trying to
leverage existing tooling as well, the exact details are best discovered
through the development process which likely covers what was noted above in
the Proposed Change section.

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

Impact for Ironic itself is minimal, although it will require credentials to
be set for the remote service to signal interface attachment/detachments.

The security risk largely revolves around the new service we're looking at
creating with this effort. The shared library utilized to connect to the
remote service, likely needs to also contain the necessary client
wrapper code, as an MVP service is likely going to start only with support
for HTTP Digest Authentication, which can then move towards certificate
authentication as it evolves.

In large part because that service will need to load and combine a set of
credentials and access information. As such, this new service will **not**
be a user facing service.

Today, individual ports are attached through a combination of network
identifier and a binding profile which is utilized to map a port to a switch.
In this model, there would be no substantial difference. A network_id would
be a user supplied detail, and the local_link_information would contain
sufficient information for the plugin executing to identify which device.
The new service would retrieve the details to access the remote device from
local configuration, and combine the rest of the binding profile and target
network identifier to facilitate the attachment of the port to the device.

.. note::
   This security impact does not denote the likely situation of DPU credential
   management. We are presently defferring the possibility as a challenge we
   would focus on after an initial minimum viable product state is reached.

.. note::
   This security risk does not include any future mechanisms to do perform
   aspects such as software deployment on a DPU to facilitate a fully
   integrated with Neutron case, which is something we would want to
   identify and determine as we iterate along the path to support such
   a capability.

Other end user impact
---------------------

None

Scalability impact
------------------

Please see the Performance Impact section below.

Performance Impact
------------------

This proposal is intentionally designed to be limited and isolated
to minimze risk and reduce deployment complexity. It is also intentionally
modeled as a tool to "do something", and that "something" happens to be
configuration in area where device locking is necessary. This realistically
means that the only content written to disk is going to be lock files.

Furthermore, the possibility exists that the Ironic driver code utilized
*could* wait for a response, where today Neutron port attachment/detachment
calls are asynchronous. This would pose an overall improvement for end users
of Ironic. This is solved today as a 15 second sleep by default, and
might not be necessary in this design overall improving Ironic performance.

Other deployer impact
---------------------

To utilize this functionality, deployers would need to deploy a new service.

This would be opt-in, and would not impact existing users.

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  <Volunteer #1>

Other contributors:
  <Volunteer #2>

Work Items
----------

Broadly speaking, the work items would include:

1) Prototyping this new service.
2) Wire up an ML2 driver such that we have interfaces we can load and
   call. This is anticipated to be neworking-generic-switch.
3) Prototyping an ironic network_interface driver to utilize this new
   service.
4) Test!

.. note::
   The list below is intended to paint a picture of what we feel are the
   possible steps beyond the initial step of creating an Minimum Viable
   Product. They are included to provide a complete contextual picture
   to help the reader understand our mental model.

Past initial prototyping, the following may apply order:

* Creation of a common library for Ironic and any other program or tool
  to utilize to compose RPC calls to this service.
* Extend support to VXLAN ports, which may require additional details or
  design work to take place and work in any ML2 driver utilized.
* Design an API rest endpoint to facilitate the tracking of physical
  networks to be attached to baremetal nodes.
* Add support to networking-baremetal to try and reconcile these
  physical networks into Ironic, so node port attachment/detachments
  can take place.
* Add support to networking-baremetal for it to proxy the request
  through to this service for port binding requests in Neutron.
* Design a new model, likely superceeding VIFS, but vifs could just also be
  an internal network ID moving forward. This would likely be required for
  formal adoption of the functionality by Metal3, but standalone users could
  move to leverage this immediately once implemented.
* Development of a model and flow where DPU devices could have a service
  deployed to them as part of a step invoked by Ironic. This would involve
  many challenges, but could be used to support the Neutron Integrated
  OVS/OVN agents to operate on the card for cases such as the remote
  card being in a hypervisor node.

Dependencies
============

To be determined.

Testing
=======

An ideal model of testing in upstream CI has not been determined, and
is dependent upon the state upon reaching a minimum viable product
state, and then what the next objectives appear to be.

This may involve duplication of Ironic's existing multinode job in a
standalone form. Ultimately the expectation is we would have one or
more CI jobs dedicated to supporting such functionality being exercised.

Upgrades and Backwards Compatibility
====================================

This functionality is anticipated to be "net new" for Ironic and exposed
to end users through a dedicated ``network_interface`` module which could
be selected by users at a point in the future. As such no upgrade or backwards
compatability issues are anticipated.

Documentation Impact
====================

No impact is anticipated at this time.

References
==========

https://etherpad.opendev.org/p/ironic-ptg-april-2024#L609
