..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================
Physical Network Awareness
==========================

https://bugs.launchpad.net/ironic/+bug/1666009

Ironic ports and portgroups correspond to the physical NICs that are available
on baremetal nodes.  Neutron ports are logical ports attached to tenant and
provider networks.  When booting baremetal nodes in a system with multiple
physical networks, the mapping between logical and physical ports must account
for the physical network connectivity of the system.

This feature aims to make ironic aware of the ``physical_network`` attribute of
neutron networks and network segments.

Problem description
===================

Physical Networks
-----------------

A neutron port on a provider network or network segment is associated with a
physical network.  The physical network concept is used to specify the physical
connectivity of networks and network segments in the system.

There are many reasons why an operator might use multiple physical networks,
including:

- routed provider networks [1]_
- security, through physical segregation of traffic
- redundancy, through independence of multiple networks
- traffic isolation (e.g. storage vs. application)
- different characteristics (bandwidth, latency, reliability)
- different technologies (Ethernet, Infiniband, Omnipath, etc.)

It is possible that some or all nodes may be connected to more than one
physical network.  OpenStack adoption is growing rapidly in the scientific
computing community, an area in which the use of nodes connected to multiple
physical networks is prevalent.

For context, we provide some examples of how the physical network attribute is
used in other OpenStack components.  The neutron ML2 Open vSwitch agent is made
physical network-aware via the ``[OVS] bridge_mappings`` configuration option.
This option maps physical network names to Open vSwitch bridges that have a
physical network interface as a port. This option is used for flat and VLAN
network types, and is taken into consideration when binding ports to network
segments in the neutron server ML2 driver.  This acts both to ensure that
physical connectivity allows for the requested logical topology, and also
supports hosts being connected to multiple physical networks.

A similar mapping exists in nova for pass-through of PCI physical devices or
SR-IOV virtual functions via the ``[DEFAULT] pci_passthrough_whitelist``
configuration option.

Physical Networks in Ironic
---------------------------

An ironic port is connected to a physical network.  As portgroups are a layer-2
construct, all ports in a portgroup should be in the same physical network.  If
a neutron port is mapped to a port or portgroup and is attached to a neutron
network or network segment on a different physical network, there will be no
connectivity between the bare metal node's NIC and other neutron ports on the
network.  This is perhaps most obvious when it results in a failure to acquire
a DHCP lease for the interface.

The mapping between logical ports in neutron and physical ports and portgroups
in ironic has always been somewhat unpredictable [2]_.  The ironic-neutron
integration work added support for local link information for ports [3]_.  In
the interface attach/detach API work [4]_ ironic moved the responsibility for
attaching virtual interfaces from nova to ironic.  In both of these features
physical network-awareness was seen as out of scope.

Currently when a virtual interface is attached to a node, the procedure used to
map it to an ironic port or portgroup is roughly as follows:

- if there is a free portgroup, select one
- else if there is a free port with PXE enabled, select one
- else if there is a free port with PXE disabled, select one
- else fail

This algorithm takes no account of the physical network to which the ports and
portgroups are connected, and consequently can result in invalid mappings.
Further, there is currently no standard way in ironic to specify the physical
network to which a port or portgroup is connected.

Provisioning and Cleaning Networks
----------------------------------

The ironic pluggable network provider [5]_ work added support for attaching
nodes to dedicated provisioning and cleaning networks during provisioning and
cleaning operations respectively.  Currently, all ironic ports and portgroups
with PXE enabled are attached to the provisioning or cleaning network.  While
this ensures that the node has a port on the provisioning or cleaning
physical network, it may result in unnecessary neutron ports being created if
some of the ironic ports or portgroups are connected to a different physical
network.  In practice this can be avoided by disabling PXE on ports where it is
not required.

Scheduling
----------

In a system with multiple physical networks where not all nodes are connected
to every physical network, it becomes possible for a user to request a logical
network topology that cannot be realised.  Without awareness of the physical
networks that each ironic node is connected to, nova cannot reliably schedule
instances to ironic nodes.  This problem is considered beyond the scope of this
spec.

Proposed change
===============

There are four parts to the proposed solution to this problem.

1. It must be possible to specify the physical network to which an ironic port
   is connected.
2. The ironic network interfaces must account for the physical network of an
   ironic node's ports and portgroups when attaching tenant virtual interfaces.
3. When attaching a node to a provisioning or cleaning network, neutron ports
   should be created only for ironic ports and portgroups on the same physical
   network as the provisioning or cleaning network.
4. The binding profiles of attached neutron ports should be updated with the
   physical network of the ironic port or portgroup to which the port was
   mapped.

Tagging Ports
-------------

There are a few options for how ports might be tagged with a physical network:

1. a new attribute of the ``local_link_connection`` field
2. a new attribute of the ``extra`` field
3. a new first class field

Reusing an existing field would certainly be easier to implement than adding a
new one, but OpenStack history has frequently shown that buried fields often
end up needing to become first class citizens.  A relevant example here is the
``provider:physical_network`` extension field on neutron networks, which later
became a first class field on network segments [1]_.  Further, if ironic
intends to support physical network-aware scheduling in future, the ability to
efficiently filter ports by their physical network may be advantageous.  This
spec therefore proposes to add a new first class ``physical_network`` field to
ironic's ``Port`` object.  For backwards compatibility, this field will be
optional.

The process of mapping physical networks to ironic ports is out of scope for
ironic.  This could be done either through a manual procedure or through an
automated process using information gathered during a hardware introspection
process.  For example, if using ironic inspector to perform introspection it
would be possible to create an introspection plugin [6] that maps switch IDs
discovered via LLDP to physical networks.

Portgroups
----------

The physical network of a portgroup will be determined through the physical
network of its constituent ports.  All ports in the portgroup must have the
same physical network, and this will be enforced in the ironic API when
creating and updating ports.

This has the unfortunate consequence of making it rather unwieldy to update the
physical network of the ports in a portgroup, since the ports must be removed
from the portgroup while their physical network is updated.  This may be
improved upon in future through the use of a virtual physical network field in
the portgroups API that allows simultaneous update of the physical network
field of all the ports in the group.

Mapping Logical Ports to Physical Ports
---------------------------------------

In order to account for physical network connectivity, the virtual
interface attachment algorithm must determine the physical networks that the
neutron port being attached can be bound to.  This information is available via
the neutron API as the ``physical_network`` field on network segments in the
port's network or as ``provider:physical_network`` on the port's network.

The virtual interface attachment mapping algorithm will be modified to the
use the following set of criteria listed in order of descending priority:

1. reject ports and portgroups with a non-null physical network that is
   different than all of the network's physical networks
2. prefer ports and portgroups with a non-null physical network to ports with a
   null physical network
3. prefer portgroups to ports
4. prefer ports with PXE enabled to ports with PXE disabled

This algorithm provides backwards compatibility for environments in which the
port(s) and/or portgroup(s) associated with the ironic node do not have a
``physical_network`` property configured.

Provisioning and Cleaning Networks
----------------------------------

In ironic network drivers that support network flipping for provisioning and
cleaning operations, we will create neutron ports only for those ironic ports
and portgroups that have PXE enabled and are on the same physical network as
the provisioning or cleaning network in question, or do not have a physical
network specified.

Neutron Port Binding Profiles
-----------------------------

When attaching virtual interfaces to physical or virtual functions of PCI
network devices, nova sets a ``physical_network`` attribute in the
``binding:profile`` field of the neutron port.  Further research is required
to determine what effect it would have if ironic were to do the same.

Alternatives
------------

We could continue to use an unpredictable mapping between logical ports and
physical ports.  This limits the use of ironic to environments in which there
is only one physical network.

We could continue with the existing mapping algorithm in ironic but provide
neutron with the information required to determine whether a mapping is valid
from the ``local_link_connection`` binding information.  Ironic would then be
modified to retry interface attachment with a different neutron port if neutron
determined the mapping to be invalid.  This method would be inefficient due to
the retries necessary.

We could avoid the need to tag ironic ports with a physical network by
providing a mechanism to map from the information in their
``local_link_connection`` fields to a physical network.  This would require
either an addition to ironic's data model to support Switch objects or a new
neutron API providing a lookup from switch ID to physical network.

Data model impact
-----------------

A new ``physical_network`` field will be added to Port object.  In neutron the
``Segment`` object's ``physical_network`` field is defined as
``sqlalchemy.String(64)``, so the same will be used in ironic.

State Machine Impact
--------------------

None

REST API impact
---------------

The port REST API will be modified to support the new ``physical_network``
field.  The field will be readable by users with the baremetal observer role
and writable by users with the baremetal admin role.  If the port is a member
of a portgroup, the API will enforce that all ports in the portgroup have the
same value in their physical network field.

Updates to the the physical network field of ports will be restricted in the
same way as for other connectivity related fields (link local connection, etc.)
- they will be restricted to nodes in the ``enroll``, ``inspecting`` and
``manageable`` states.

The API microversion will be bumped.

Client (CLI) impact
-------------------

"ironic" CLI
~~~~~~~~~~~~

The ironic CLI will not be updated.

"openstack baremetal" CLI
~~~~~~~~~~~~~~~~~~~~~~~~~

The openstack baremetal CLI will be updated to support getting and setting the
``physical_network`` field on ports.

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

This change should increase the potential security level of an ironic bare
metal cloud by supporting multiple segregated physical networks and honoring
the physical network restrictions assigned by the operator.

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

In order to make use of this feature, deployers must tag ironic ports and
portgroups with the physical network to which they are attached.  This implies
that they must have a mechanism to correctly determine this information.

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

mgoddard

Work Items
----------

- Modify the ironic port model to include a ``physical_network`` field.
- Modify the ironic ports REST API to support the ``physical_network`` field.
- Modify the openstack baremetal CLI to support the ``physical_network`` field.
- Modify the ironic ``VIFPortIDMixin`` plugin with the new port mapping
  algorithm.
- Modify the ironic ``NeutronNetwork`` network driver to be physical network-
  aware when creating neutron ports for cleaning and provisioning.
- Modify the ironic network drivers to add the physical network to neutron
  ports' binding profiles.
- Add support for multiple (virtual) physical networks to DevStack.
- Update the ironic developer documentation to cover the use of physical
  networks.

Dependencies
============

None

Testing
=======

Support will be added to DevStack for ironic environments with multiple
(virtual) physical networks.

Upgrades and Backwards Compatibility
====================================

The proposed data model and algorithm changes are backwards compatible.  A
database migration will be provided to add the ``physical_network`` field to
existing ports with a null value.

Documentation Impact
====================

The ironic developer documentation will be updated to cover the use of this
feature.

References
==========

.. [1] `Neutron routed networks <https://specs.openstack.org/openstack/neutron-specs/specs/newton/routed-networks.html>`_
.. [2] `ports cannot be mapped to networks <https://bugs.launchpad.net/ironic/+bug/1405131>`_
.. [3] `Ironic neutron integration <https://specs.openstack.org/openstack/ironic-specs/specs/not-implemented/ironic-ml2-integration.html>`_
.. [4] `interface attach/detach API <https://specs.openstack.org/openstack/ironic-specs/specs/approved/interface-attach-detach-api.html>`_
.. [5] `pluggable network providers <http://specs.openstack.org/openstack/ironic-specs/specs/6.1/network-provider.html>`_
.. [6] `introspection plugins <https://docs.openstack.org/developer/ironic-inspector/contributing.html#writing-a-plugin>`_
