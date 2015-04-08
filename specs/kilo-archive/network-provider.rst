..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===========================
Pluggable network providers
===========================

https://blueprints.launchpad.net/ironic/+spec/network-provider

Today, Ironic provisions servers on the same (flat) network that tenants run
on. Ironic should have the ability to logically separate provisioning and
tenant networks, and switch between them as needed.

Note: where this spec says "network", it generally means "Neutron network",
which is generally a VLAN in Ironic's case.


Problem description
===================

Ironic currently provisions servers on the same (flat) network that tenants
use. It is clear that Ironic should allow operators to separate provisioning
and tenant networks; where deploy ramdisks run on the "provisioning" network,
and instances run on one or more "tenant" networks.

In order to secure the provisioning network, Ironic should be able to switch
between these networks when spawning and destroying instances.


Proposed change
===============

Ironic should have a pluggable "network provider" that can handle switching
nodes between different networks.

The network provider should have a concept of a "provisioning network", where
the control plane can communicate with nodes managed by Ironic in order to
deploy, tear down, or otherwise manage nodes. It should be able to connect
and disconnect nodes from this network.

The network provider should also know how to connect and disconnect nodes from
arbitrary tenant networks. These networks are defined by the user and Nova,
and the Nova virt driver puts the network ID on the Port object in
Port.extra['vif_port_id']. This currently assumes one network per Port. This
spec will carry this assumption, but later work should be done to allow an
arbitrary number of networks to be attached to the node (this may require
re-thinking Ironic's concept of a Port).

One caveat here is that nodes will not be able to PXE boot the instance image
if they cannot reach the conductor (for tftp). Local boot will need to be used
for any node deployed outside of the provisioning network.

A pluggable interface for doing these tasks should be implemented. A "none"
provider that no-ops each task should be implemented for compatibility.

A second provider that talks to Rackspace's Neutron plugin for Ironic[0]
should be implemented. This plugin is the only known Neutron plugin that
can configure real switches.

Deploy drivers should call to this interface at proper times to switch between
networks. For example, a driver completing a deploy should power off the node,
switch to the instance networks, and power on the node. This will ensure that
the deploy ramdisk never runs on the instance network, and the instance image
never runs on the provisioning network.

This interface will define the following methods::
    def add_provisioning_network(self, task):
    """Add the provisioning network to a node."""

    def remove_provisioning_network(self, task):
    """Remove the provisioning network from a node."""

    def configure_tenant_networks(self, task):
    """Configure tenant networks (added by Nova) for a node."""

    def unconfigure_tenant_networks(self, task):
    """Unconfigure tenant networks (to be removed by Nova) for a node."""

Alternatives
------------

Alternatively, Ironic could continue to prescribe that operators run Ironic
on a single flat network shared between tenants and the control plane.

Data model impact
-----------------

Switch port mappings (switch hostname and port ID) will need to be stored in
order to interact with the Neutron plugin. This spec proposes that this data
should be stored in a new ``driver_info`` field for the Port object
representing the connected NIC.

REST API impact
---------------

None.

RPC API impact
--------------

None.

Driver API impact
-----------------

None.

Nova driver impact
------------------

None.

Security impact
---------------

This potentially improves security by restricting tenant access to the
control plane.

Other end user impact
---------------------

To use this feature, end users will need to:

* Deploy the Neutron plugin.

* Configure the plugin by setting ``CONF.provisioning_network``.

* Use local boot for instances using this feature.

Scalability impact
------------------

When configured to use the Neutron plugin, this will result in additional
API calls to Neutron to manage a node. However, impact on scalability should
be minor or negligible.

Performance Impact
------------------

None.

Other deployer impact
---------------------

Two new configuration options will be added:

* ``CONF.network_provider`` specifies the network provider to be used.

* ``CONF.provisioning_network`` specifies the ID of the provisioning network.

A new database column (Port.driver_info) is also added, and so deploying this
change will require a migration to be ran.

Deployers will need to move to using local boot in order to use this feature.

Developer impact
----------------

Driver authors should support this feature by calling the methods provided.


Implementation
==============

Assignee(s)
-----------

jroll <jim@jimrollenhagen.com>

Work Items
----------

* Add the Port.driver_info field.

* Implement the base interface.

* Implement the no-op provider.

* Implement the Neutron plugin provider.

* Instrument each deploy driver with calls to this interface.


Dependencies
============

None.


Testing
=======

The no-op provider will be tested in the gate by default. The Neutron plugin
would be difficult to test in the gate, as it configures real switches.
Perhaps in the future, an OVS plugin could be added to the Neutron plugin,
or a third network provider could be added that talks to stock Neutron and
configures OVS.


Upgrades and Backwards Compatibility
====================================

Default behavior is the current behavior, so this change should be fully
backwards compatible.


Documentation Impact
====================

This feature will be fully documented.


References
==========

[0] Neutron plugin: https://github.com/rackerlabs/ironic-neutron-plugin
