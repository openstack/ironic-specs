..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=============
VXLAN Support
=============

https://bugs.launchpad.net/ironic/+bug/2106460

Network operators often have a number of requirements, which sometimes bring
the operational need to tunnel networks inside of other networks to facilitate
connectivity. This is in part due to economies of scale for data centers and
the balancing of complexity to meet an operational need.

The most common pattern emerging in large-scale networks is to utilize VXLAN
on top of routed cross-device links. This works in a similar fashion to a
routed spine-leaf architecture.

Each physical switch is acting as a translator where packets to and from
the physical interfaces are attached to a VLAN and then the VLAN internally
gets translated to a VXLAN.

This is contrary to the operational model of the OpenStack Networking platform
where a model of building a virtualized overlay network fabric is utilized.

A key benefit of the VXLAN flow is you can directly map and have
traffic flow as routed traffic at the spine, or the "mesh" of the network.
This is contrary to the underlying traffic flow of VLAN networks, where
mechanisms like Spanning-Tree are really the only available tools for
traffic flow management on that level. For example, it makes no sense to
forward packets to a root bridge switch and then back out when there is a
more direct path the traffic can take.

Ultimately, when overlay networks are utilized for hypervisors, they receive
the same benefits that make this approach popular with physical network
operators.

Where the primary discrepancy and disconnect occurs, and what this
specification seeks to bridge is the physical baremetal host networking
so a tenant network can be bridged to the environment's native VXLAN
networking.

Terminology
===========

* Virtual eXtensible LAN (VXLAN) - The protocol model this specification seeks
  to standardize support in Ironic.
* VXLAN Tunnel Endpoint (VTEP) - Tunnel endpoints, such as switches or hosts
  which terminate the VXLAN tunnel and attach it to a physical or virtual
  interface. This may be attached to intermediate interfaces which may also
  be shared by multiple "devices".
* Generic Network Virtualization Encapsulation (GENEVE) - This is an IETF
  effort to unify VXLAN and a competing technology Network Virtualization
  using Generic Routing Encapsulation (NVGRE).
* VXLAN Network Identifier (VNI) - A 24-bit field which defines the "number"
  of the network. In OVN's variation of this protocol, it is restricted to
  12 bits.
* Border Gateway Protocol (BGP) - The routing protocol which powers the
  Internet through a variety of configurations.
* BGP EVPN - BGP Powered Ethernet VPN - A concept of using BGP to facilitate
  Layer2 networking between members in a BGP network fabric. This is due to
  the design of BGP which makes it useful to share other routes and additional
  structural information to the network members while also spreading context
  updates quickly in the event of a change to the network.
* OVS - Short for OpenVSwitch. A toolkit to provide a virtual overlay network.
* OVN - Open Virtual Network - An evolution of OVS to support virtual network
  abstractions on top of OVS along with additional SDN capabilities.
* NGS - Networking-Generic-Switch, the Ironic sub-project which houses an
  ML2 plugin to facilitate VLAN attachment for baremetal nodes.

Overall, a basic primer for this subject can be found as change
`965415 <https://review.opendev.org/c/openstack/neutron/+/965415>`_
if you are curious about additional background context.

Problem description
===================

The base challenge for physical baremetal data centers is the number of
networks which need to be supported, while also moving packets efficiently
between any two points in the environment.

Today's challenge with provisioning and management of baremetal nodes
is that operators seek to efficiently manage their physical machines and
network connectivity to the network fabric.

Where disconnects begin to exist is that the networking services used for
existing virtual machine and workload overlay networking tools expect a model
of shared configuration and purpose. For example, the OVN/OVS model consists
of consistency across participants running software, whereas physical switch
vendors utilize tools like BGP EVPN to facilitate the necessary context
sharing across participants.

Confusion increases further with tools like ``ovn-controller-vtep`` which
could be usable if the switch OS is natively running OVS and OVN, yet this is
not operational reality in most cases. Furthermore, limited VXLAN support
exists in these platforms because they are focused on establishing overlay
"mesh" networks for virtual machine and/or container workloads. See the
`OVN General FAQ <https://docs.ovn.org/en/latest/faq/general.html>`_
and `OVS VXLAN FAQ <https://docs.openvswitch.org/en/latest/faq/vxlan/>`_
for a better picture describing the top line constraints. Despite
utilizing VXLAN-based technologies, the overlay implementations focus
primarily on encapsulation of packets, and not the end-to-end flow of
traffic.

Where additional confusion arises is that OpenStack is a project where you
can assemble the many pieces in different ways to meet operational needs. This
does not mean any particular style or pattern is wrong, it just introduces an
area where the developer and operator context differ and this specification's
goal is to bring a cross-cutting understanding to the area of VXLAN
networking.

Assuming all hierarchical port binding issues are resolved,
this leaves two areas which need to be addressed to facilitate the attachment
of baremetal nodes, which is similar to this `networking example`_.

Proposed Changes
================

At minimum, two fundamental areas are required.

* Connectivity - An established connection between an OpenStack Cloud and the
  physical switch infrastructure.

* Network and Port Configuration - Regardless of the means of connectivity
  to the switch fabric, in the context of VXLAN networking, we need to
  both "create" the VNI, and attach that VNI to a VLAN and ultimately
  the physical machine.

The "how" in terms of connectivity can take several different distinct paths
and have various trade-offs. Ultimately these trade-offs drive both decisions
and performance expectations/impact. Given the Network and Port Configuration
has much more clarity, we must focus on that first, and then dive into
connectivity.

Network and Port Configuration
------------------------------

In order to complete the process of binding one or more physical ports which
a baremetal node is attached to, it is necessary for the end switch device
to receive some specific configuration to facilitate that attachment.

In most switches, the intermediate object to facilitate this configuration
is a VLAN inside of the switch.

* Configuration of a VLAN which is used inside of the switch(s) themselves
  for VXLAN attachment.
* Attachment/detachment of the required VXLAN VNI to the VLAN
* Attachment/detachment of the VLAN to the physical port(s) which
  are necessary.

Regardless of the base connectivity of the cloud, the following basic changes
will be needed, which will facilitate the creation of the network inside of a
network fabric and the establishment of the port attachment.

1) Update update_port_postcommit method to evaluate the top level
   binding segment to identify vxlan networking, extract necessary
   details from the top binding segment and the bottom binding segment,
   and call the underlying switch method to create a VNI.

   .. NOTE::
      Some discussion has yielded consensus that we should translate across
      for both VXLAN and Geneve type networks. In essence, attach and
      translate across both because the underlying binding mechanisms should
      be the same.

2) This should call a new network creation method, for example
   plug_switch_to_network, which then creates the VNI on the remote switch
   and attaches that VNI to a VLAN.

   In the NGS case, for example with Cisco NX-OS:

   - evpn
   - vni ${segmentation_id} l2
   - rd auto
   - route-target both auto
   - exit (exit evpn)
   - vlan ${bottom_segment_segmentation_id}
   - vn-segment ${segmentation_id}
   - exit (exit vlan configuration)
   - exit (configuration in general)

.. NOTE:: As an aside, it may be reasonable for other ML2 plugins to take
   a similar, but vendor-specific configuration approach. The commands above
   are just for illustrative purposes.

.. NOTE::
   In the command example, it should be understood that the network operator
   would have had to previously made the configuration such that vlan is
   setup and enabled on the switch. Different configuration models may exist
   as well as preferred by the vendor. An EVPN style model or a multicast
   style model of VXLAN usage. That is outside the scope of this specification
   but does generally need to be accounted when it comes to implementing
   support in an ML2 plugin, and as such is scoped as an ML2 plugin problem.

3) For cases when port is being unbound, the presence of the VNI and VLAN
   should be removed from the switch when there are no additional port
   binding. This naturally allows VXLAN VNIs to be removed completely as
   ports are removed from the switches. As a result, this happens during
   the ``delete_port_postcommit`` and ``update_port_postcommit``.
   In both cases, the top binding segment is included in the call to
   allow for the VNI to be identified, and removed.

.. NOTE::
   A benefit to NGS usage is that the underlying changes can enable
   Ironic's standalone network updates to eventually have sufficient logic
   to handle port binding for pre-declared VXLAN networks, which should
   result in the overall integration becoming straightforward integration
   logic when that time comes.

Connectivity
------------

Ultimately the connectivity is the harder aspect to meet, but this is where
operator requirements become significant.

.. list-table:: Connectivity Options
   :widths: 20 80 50 50 10
   :header-rows: 1

   * - Basic Option
     - Description
     - Positives
     - Negatives
     - Unknowns
   * - Option 1: `Hierarchical port binding attachment for network nodes`_
     - Uses port binding such that we attach the VXLAN network inside of a "network node" and pass it on an assigned VLAN to the directly attached switch, which internally in the switch is mapping the VLAN to a VNI.
     - Downstream Operators have done this themselves. Relies upon switch ASICs to maximize performance.
     - Limits each "network node" connection to the physical fabric to the physical number of permissible VLANs for use on the physical fabric.
     - A plugin will be required to facilitate the physical attachment, on every networker node to create a "trunk" port for egress traffic. A complete understanding of the Compute/Networker node networking attachments needs to be better understood, however this is not blocking initial progress.
   * - Option 2: Neutron EVPN with Type2 routes (Under Development)
     - The Neutron community is currently working on developing support for Type2 routes as it relates to EVPN. The basic model of interaction here is that connectivity is facilitated between the cloud and the remote endpoint and a VNI can be passed across natively.
     - Better possible horizontal scalability inside the cloud to distribute the encapsulation and decapsulation workload across the cloud.
     - Individual stream and connectivity performance is unlikely to be as performant compared to the usage of switch ASICs.
     - None known at this time.

.. NOTE:: Previously a concept existed of building a "virtual cross-connect"
   for Ironic to facilitate some of this connectivity.
   This idea would have utilized Linux kernel networking packet handling code
   to bridge and re-encapsulate the packet payloads, while leveraging internal
   OVS/OVN data to determine the attachment points. This idea would have been
   a bit more expansive than just the concepts presented in Option 1 and
   Option 2, and ultimately would have found itself in the middle ground
   performance wise from the two different usage profiles we anticipate.
   Given the reality that it would have been substantially more work, we
   believe any ideas for improvement should instead focus on
   `Hierarchical port binding attachment for network nodes`_.


Hierarchical port binding attachment for network nodes
------------------------------------------------------

In this model of use, the attachment of the tenant networking takes place by
using the br-ex interface, combined with hierarchical port binding to
allocate, and trigger port binding attachments to have the necessary
attachment details.

In essence, the end state which results looks something like this:

[Networker Node]-[br-ex.tag]-[local-switch-port]-[vxlan]-[remote-switch-port]

In this scenario, an ML2 plugin would configure both the local-switch-port and
the remote-switch-port by binding the port to a VLAN, the VLAN to a VNI. Both
switches in that case operate as VTEPs allowing the traffic to be
appropriately tunneled through the wider network fabric.

This model of use is already proposed upstream:

The mechanism driver proposed as
`change 973889 <https://review.opendev.org/c/openstack/networking-baremetal/+/973889>`_
is required regardless of the deployment model as an intermediary
VLAN is needed on the switch side. The beneficial aspect around binding
is that the real difference of use patterns between both options is rooted
in port binding and configuration of the network node itself. The mechanism
driver handles some of that, in that it is also able to register ``localnet``
port definitions which will allow the ports to be bound to the local physical
networks.

A potential improvement to this model is to make it aware of the
`HA Chassis Group`_ and `OVN External Ports`_ data, coupled with some
additional configuration which would need to be present in any mech
driver to facilitate the end-to-end attachment and configuration.

The following limitations and background context for this design should not
be ignored:

- A limited number of networks may be passed through each network node
  servicing the traffic. This depends on the physically attached switch and
  the available range of VLANs which are permitted.
  For example, a switch may not permit use of VLANs beyond 3850, and that
  will require matching appropriate configuration and guard rails as well.
  These guard rails will likely need to take place as part of both checks
  in the Mechanism driver which identifies and creates the attachment
  information, along with some checks in Networking-Generic-Switch as we
  become better aware of the cases. This is in large part because the bottom
  binding segments are allocated, tracked, and controlled by Neutron itself.
  As such, there is a need of the Ironic project to ensure we thoroughly
  document all known limitations and constraints, such that operators have a
  better chance to understand and correct issues when port binding and thus
  deployments fail due to VLAN resource exhaustion in their configuration,
  as lower binding segment creation will fail in their environments
  when that occurs.
- This design trades network nodes for throughput by focusing on ASICs to
  perform the heavy lifting of mapping and translating packets to their
  remote destination. This approach leverages what switches are designed to
  do: switch vendors design these devices to approach wireline speeds of
  hundreds of gigabits per second.
- This design may not be optimal for environments with a large number of
  hypervisors with workloads which are not bandwidth intensive but need to
  communicate with physical baremetal nodes. In such scenarios, focusing on
  Neutron native EVPN Type2 route handling may make more sense. This allows
  encapsulation and decapsulation to be distributed across the environment
  as a whole, though individual VM workloads may only see a fraction of
  wireline performance.

The way the physical attachment works is inherently through the mapping of
OVN node to the physical network through the external bridge mapping.

The resulting way to facilitate the physical attachment of the networker
node (or compute node) networking to the appropriate physical network VNI
is through the same exact process of port binding as we perform with the
end baremetal node.

It is with this in mind, that we propose to use the ironic-neutron-agent to
identify and reconcile some of the binding information, and issue port binding
attachments as needed.

1) Ironic-neutron-agent would make Trunk (as in 802.1q) ports are pre-baked
   and mapped for *each* OVN agent host in the cloud for every
   physical_network they have defined. This is available in the representitive
   data objects. It would do this by using a mix of possible local link
   port data housed in Ironic, in a local configuration file. This is because
   local link connection information is **critical** for the base port to
   be created. If all else fails, It would log error messages. This aligns
   with the current mission of ensuring physical network mappings are
   present and up to date.

2) Any user would then create a network. This network, under default
   configuration, would have a DHCP port. This port creation will
   result in the creation of the bottom_binding_segment, just like
   ports for baremetal hosts.

3) The mechanism driver, or ironic-neutron-agent, then creates the
   additional port bindings. This may be best managed by ironic-neutron-agent
   because it could work to ensure they are always present and reconcile the
   networking as-needed. The goal is to identify the port and then trigger a
   trunk sub-port to be created.

   IF we do this in a network mech driver, we could consider possibly
   doing some of these additional checks and updates after the ML2 Mech
   driver methods after networks are created, but the use of the agent
   seems like a more resillient model.

4) The trunk subport is requested to be bound to the same segmentation ID
   as the lower binding segment, then triggers the VLAN segmentation ID
   on the physical network be able to pass traffic over the interface.
   This attachment *also* attaches the VNI to the physical switch which
   is directly attached, enabling other switches to be aware of that VNI
   in advance of additional ports being bound on the network fabric as a
   whole. These ports are created as VNIC_BAREMETAL type as well,
   so normal teardown and deletion logic also removes these port and
   their related attachment records as well.

Whenever these ports are unbound, the subports and ports would be unwound.
The greatest risk in this architecture is if an admin deletes the trunk port
for the agent which represents the trunk port which br-ex is attached to,
but in this model the trunk port would be reconfigured and sub-port re-bound.

Going back to `HA Chassis Group`_ and `OVN External Ports`_, a possibility
exists that we may want the ironic-neutron-agent to explicitly ensure the
segmentation ID is bound and active for each node in the Chassis Group as it
relates, such that should a failover or reconfiguration need to occur, then
the physical switch side configuration is already done. The exact algorithm
to be used may require some iteration because we will need to work and source
several different data sources together, especially when multiple physical
net bridge mappings may exist on a networker node or compute node.

.. NOTE::
   In this model, this functionally results in a limitation of 4096 (or subset
   number of physically available VLANs) by physical network mappings,
   but should be relatively appropriate scale wise given it is a base
   constraint of the existing model, and the remedy is to just add
   additional physical networks to isolate the behavior.
   The VXLAN traffic can attach and route across that without the same
   limitation.

.. WARNING::
   As far as we are aware, neutron advocates for a model of trunk ports for
   physical network bridges, i.e. br-ex or other named interfaces, to allow
   all VLANs to be used and passed. In this model, we are not advocating for
   this model... in part because we need the port binding to occur.

.. TODO::
   We might need to double check that update_port_postcommit in
   Networking-Generic-Switch does properly unwind subports. If
   it does not, that is a bug.

Alternatives
------------

Alternatives to building a virtual cross-connect with OVN
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This section exists because we've received questions and feedback which
demonstrate a lack of understanding of the actual use case. It is
straightforward to think of all inter-host and inter-device communication as
IP traffic, but when we extend to baremetal switch ports, this premise begins
to break down. Furthermore, OVS's VXLAN support is noted to be limited to
encapsulation and decapsulation on the appropriate unicast tunnel.

Unfortunately, that doesn't really align with the dynamic environments which
data center operators exist in. It would be ideal if we could tell OVS and
OVN "extend the L2 traffic to the attached physical VXLAN fabric", but there
also appear to be technical design decisions which were made as part of OVN
which don't align well to the basic model.
Referencing the `OVN installation manual for Neutron
<https://docs.openstack.org/neutron/latest/install/ovn/manual_install.html>`_,
you can see the Segmentation ID has been reduced to 12 bits to enable
OVN to pass additional information. `RFC 7348 <https://datatracker.ietf.org/doc/html/rfc7348#section-4>`_
explicitly notes a VXLAN Network Identifier (VNI) is 24 bits long.
To further translate this and draw a conclusion, OVN VXLAN support was only
intended to operate with remote nodes speaking OVN. Later work for EVPN
support does natively extend the VXLAN VNI header value to be the appropriate
24-bit length which makes native EVPN approach a viable option in some use
cases once Type2 routes are supported in OVN. That being said, an eventual
future state model has a different performance approach, and that is perfectly
okay. For baremetal heavy environments, the model we propose will enable
larger streams, whereas an environment with some baremetal hosts which is
virtualization heavy would likely be better suited to leverage the OVN EVPN
model due to the distributed nature and focus on VM centric traffic flows.

As for existing plugins, tools, and services, they all appear to be built
upon the concept of routing to the remote network. While that may be suitable
for some use cases, end users as it relates to Ironic demand their physical
machines, virtual machines, and containers to all be present on the same
logical network. Essentially, their expectations were set by VLAN
functionality, and they are not wrong to make that demand given the need to
"share nothing" in multi-tenant environments, even remote routers.

In essence, because we're not routing, and because we can't make a machine
appear with IP addresses without some sort of networking substrate, we
functionally need an L2VNI with related routes to be distributed. L3VNIs
can't transport Layer2 protocols like DHCP. Furthermore, because we need to
handle the L2VNIs, we are not routing traffic for inside the tunnel in remote
devices. The L2VNIs are just a carrier and the packets may be routed within the
network fabric itself to reach the end terminating device (i.e. the VTEP),
and that is okay.

Why don't you just install OVS/OVN on the baremetal node?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A tenet of baremetal deployment is you don't inject credentials or
configuration outside of the basic contract of deployment. This creates
a boundary layer because functionally we don't know if the user who has been
assigned the baremetal node is trustworthy. Thus, we cannot expose
credentials or provide elevated networking context to the user to
participate in the overlay network.

Alternatives to Switch Attachment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Ultimately, there are no real alternatives here to support the attachment
or use of VXLAN. For the most part, it appears that physical switches all
have the same basic model: attach a VXLAN to a VLAN, and attach the VLAN
to a port.

This has been confirmed to be the case with the following switch operating
systems:

* Cisco NX-OS
* SONiC
* Dell OS10
* Arista EOS
* Juniper Junos
* HPE Aruba
* Cumulus NVUE

Obviously, if a specific switch doesn't need an intermediary VLAN ID, as long
as the VXLAN VNI is passed through, then the driver logic in NGS should be able
to complete the binding request.

.. NOTE:: Overall, the model appears to be uniform, even Nvidia DPUs
   internally maintain a mapping where VLANs are translated to VNIs.

.. NOTE::
   While the overall mapping model applies to Dell OS10 switches, they may not
   end up being supported switch devices. Some further configuration
   investigation leading into this specification document has revealed the
   need to articulate an independently numbered mapping utilizing a 16-bit
   integer (1-65536), which cannot be easily extrapolated from a VNI or VNI
   range.

Data model impact
-----------------

None

State Machine Impact
--------------------

None. The existing state machine flow already covers the basic network binding
cases and actions. The only focus of the work on this effort is in the
networking-generic-switch sub-project to provide a visible "way" to support
this, and a mechanism driver which handles the bottom binding segment
allocation.

REST API impact
---------------

None

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

None

Driver API impact
-----------------

No network interface changes are anticipated with this functionality, in large
part because this is proposing what will likely be a service which is able
to bridge the gap between the logical networks defined and the physical
network. This is outside of the core structure of Ironic.

Nova driver impact
------------------

None

Ramdisk impact
--------------

None

Security impact
---------------

No negative security impact is anticipated because the resulting service
code should make use of logical segmentation IDs which are allocated through
operator-defined range restrictions as to not conflict with existing networks.

Other end user impact
---------------------

None

Scalability impact
------------------

Fundamentally, this model of Option 1 leverages some of the
scaling design of OVN while keeping an approximate limitation
of 4096 networks per networker node that can be engaged.
An operator who intentionally restricts or constrains their
environment will experience logically constrained performance.

Given environments which are scaling should scale linearly,
this model should not be a significant issue performance wise as it is rooted
in the state and usage of the deployment. Where things may need to
be enhanced is the mechanism driver, wherever it lands, in order
to provide enough feedback and visibility as it relates to the
bottom binding segment of the port binding.

Performance Impact
------------------

Overall, this model does have a risk of hot-spotting based on a
constrained network fabric, but ultimately that should be distributed
amongst many nodes for the number of networks present.

That being said, this won't impact the overall performance of Ironic
itself. Network performance is ultimately going to be the key attribute,
and that is largely outside the scope of Ironic, and up to the union of
how well scaled the environment is, and the hardware choices of the
infrastructure operator.

The act of port binding may be a little slower, and reiterates the need
to complete Neutron callback handling with Ironic, because port binding,
regardless of option 1 or option 2, will take some additional steps to
determine if a VNI to VLAN mapping already exists, or not. Those challenges
are rooted in the execution of the configured ML2 plugin as part of Neutron.

Other deployer impact
---------------------

This model is likely going to cause a little confusion for operators
who are not already co-installing networking-baremetal, and may
require that plugin and code base to be installed on a wider basis
with the service running elsewhere on the network fabric.

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------


Primary assignee:
  Julia "TheJulia" Kreger <juliaashleykreger@gmail.com>

Other contributors:
  Doug "cardoe" Goldstein <cardoe@cardoe.com>

Work Items
----------

1) Reach consensus on where to land the mechanism driver and sort out the
   issues with hierarchical port binding.
2) Augment Networking-Generic-Switch to create and delete VNIs as needed
   while also attaching that VNI to a VLAN.
3) Add support for the VNI attachment configuration for additional switches
   to Networking-Generic-Switch.
4) Determine if a CI job is feasible and attempt to put one in place.
5) Add documentation and guidance for operators to understand the variety of
   options.
6) Stretch: Ironic likely needs to consider a minor RFE or API change to
   enable operators to manually re-trigger port binding as a single action,
   because the bottom binding VLAN segment is treated as a hidden detail
   for the most part which makes hardware failure recovery a bit more
   challenging without additional functionality to help recover in such a
   case. At a minimum, this challenge should be crystallized into a bug or
   RFE before this work is completed.
7) Stretch: Evaluate if we can just enable Geneve network type matching
   in addition to "VXLAN".

Dependencies
============

https://review.opendev.org/c/openstack/ironic/+/964570
https://review.opendev.org/c/openstack/networking-baremetal/+/973889

Testing
=======

This will be difficult to test in CI, and the only real viable option may
be to switch the existing multinode job over to leverage this model utilizing
a specialized version of the Networking-Generic-Switch "OVS" driver which
currently exercises VLAN attachments in CI. In the possible model, we might
configure aspects without actual VXLAN usage, but still have a pattern of
tracking so that we can set/unset values and perform the attachments.

In terms of testing each individual driver proposed, some effort will need to
go into the development to attempt to validate commands, interaction, and
resulting configuration.

Upgrades and Backwards Compatibility
====================================

Not Applicable - This specification is outside of the direct scope of
Ironic's code base.

Documentation Impact
====================

Documentation for ``networking-baremetal`` and ``networking-generic-switch``
will require updates related to these changes along with example
configurations.

References
==========

.. _networking example: https://vincent.bernat.ch/en/blog/2017-vxlan-bgp-evpn
.. _HA Chassis Group: https://www.ovn.org/support/dist-docs/ovn-nbctl.8.html
.. _OVN External Ports: https://docs.openstack.org/neutron/latest/admin/ovn/external_ports.html

* An initial prototype of l2vni plugging for networking-generic-switch: https://review.opendev.org/c/openstack/networking-generic-switch/+/968377
