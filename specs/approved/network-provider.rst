..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===========================
Pluggable network providers
===========================

https://bugs.launchpad.net/ironic/+bug/1526401

Today, Ironic provisions servers on the same (flat) network that tenants run
on. Ironic should have the ability to logically separate provisioning and
tenant networks, and switch between them as needed.

Note: where this spec says "network", it generally means "Neutron network",
which may be implemented in different ways.


Problem description
===================

Ironic currently provisions servers on the same (flat) network that tenants
use. It is clear that Ironic should allow operators to separate provisioning
and tenant networks; where deploy ramdisks run on the "provisioning" network,
and instances run on one or more "tenant" networks.

In order to secure the provisioning network, Ironic should be able to switch
between these networks when spawning and destroying instances.

This method should also be extended to other management networks that may or
may not be separated from the provisioning network; for example the operator
may wish to use different management networks for cleaning or rescue tasks.


Proposed change
===============

Ironic should have a pluggable "network provider" that can handle switching
nodes between different networks. This provider should be able to be selected
per Ironic node object. A new ``network_provider`` field will be added to the
node object to define which network provider to use for that node. There should
also be a configuration option for the default network provider, defaulting to
'none' for now. The default value for ``node.network_provider`` will be NULL,
meaning use the configuration option. Both the node field and the configuration
option may be set to 'none' or 'neutron', mapping to the no-op provider and
the Neutron provider, respectively.

This network provider system will not be part of Ironic's driver interface
mixin system; rather it is standalone and is loaded on demand via stevedore.
This is similar to how the DHCP provider code works today.

An initial implementation of a no-op network provider should be written, to
put the logic in place in Ironic while maintaining compatibility with the
existing model.

A second implementation should be written that uses Neutron to attach hardware
to networks as needed, and should work as follows.

The network provider should have a concept of a "provisioning network", where
the control plane can communicate with nodes managed by Ironic in order to
deploy, tear down, or otherwise manage nodes. It should be able to connect
and disconnect nodes from this network.

The network provider should also know how to connect and disconnect nodes from
arbitrary tenant networks. These networks are defined by the Nova user and
Nova. Nova should continue to create Neutron ports (a logical attachment to a
network), but these ports will be left unbound, as they will not have enough
information to be plumbed through. Ironic later should send a port-update call
to Neutron, to pass the necessary information to complete the binding. This
call should happen after deploying the image, between the power off and power
on calls that boot to the instance image. This may have implications for
"boot from volume" workloads. As Ironic does not yet support these workloads,
these are out of scope for the purposes of this spec.

In the case where the Ironic driver is used, Nova should send a null
``host_id`` in the binding profile. This will prevent Neutron from binding
the port immediately, so we can defer this and allow Ironic to tell Neutron
to bind the port when it is ready to do so. Ironic should send the node UUID
as the ``host_id``. Ironic will also delete the Neutron port connecting the
node to the provisioning network at this time. The reverse will happen at tear
down time.

If an older client (e.g. Nova) is in use and does initially send the
``host_id``, Ironic needs to handle this. There are two cases here:

* The node is using the Neutron network provider. In this case, Ironic should
  fetch the ports first, and if the ports are already bound with the correct
  info, do nothing. If binding failed due to missing switchport information,
  Ironic should update the port appropriately and allow it to be bound.

* The node is using the 'none' network provider. In this case, the node
  is expected to be on the provisioning network after deployment (today's
  current model). In this case, the ports should be treated as they are today,
  putting DHCP configs on those ports, etc.

Nova and Ironic should both use the binding:profile dictionary to send data
such as physical switchport information.

Nova currently has a broken assumption that each Ironic port (physical NIC) may
only attach to one network. This assumption will need to be fixed, as hardware
(today) cannot spawn arbitrary NICs like virtual servers can. We may, in the
future, also need a way for Nova users to define which NIC is attached to which
networks. A first version should leave this assumption in place for the sake of
simplicity.

If port groups exist for a node, those should be connected to the networks
rather than the individual port. This allows for an aggregated connection such
as a LAG to connect to the network.

Note that an Ironic environment may be deployed without Nova. In this case,
the user should make the same calls Nova would make.

One caveat here is that nodes will not be able to PXE boot the instance image
if they cannot reach the conductor (for tftp). Local boot will need to be used
for any node deployed outside of the provisioning network. Any deploys outside
of the provisioning network that do not use local boot should error.

Deploy drivers should call to this interface at proper times to switch between
networks. For example, a driver completing a deploy should power off the node,
switch to the instance networks, and power on the node. This will ensure that
the deploy ramdisk never runs on the instance network, and the instance image
never runs on the provisioning network.

Alternatives
------------

Alternatively, Ironic could continue to prescribe that operators run Ironic
on a single flat network shared between tenants and the control plane. This
is clearly not viable for many real-world use cases.

Data model impact
-----------------

A ``network_provider`` field will be added to the Node object.

State Machine Impact
--------------------

None.

REST API impact
---------------

Update the REST API for the node object to allow reading and modifying the
new network_provider field. This will likely need a version bump.

Client (CLI) impact
-------------------

Will need to update the CLI to print the new Node.network_provider field,
when available.

RPC API impact
--------------

None.

Driver API impact
-----------------

This adds a new interface, ``NetworkProvider``. This interface is *not* a part
of Ironic's driver composition system, to be clear. This interface will define
the following methods::

    def add_provisioning_network(self, task):
    """Add the provisioning network to a node."""

    def remove_provisioning_network(self, task):
    """Remove the provisioning network from a node."""

    def add_cleaning_network(self, task):
    """Add the cleaning network to a node."""

    def remove_cleaning_network(self, task):
    """Remove the cleaning network from a node."""

    def configure_tenant_networks(self, task):
    """Configure tenant networks (added by Nova/user) for a node."""

    def unconfigure_tenant_networks(self, task):
    """Unconfigure tenant networks (to be removed by Nova/user) for a node."""

Nova driver impact
------------------

The Nova driver should not be directly impacted here; however, this does depend
on changes to the Neutron network driver in Nova as described above.

Ramdisk impact
--------------

N/A

.. NOTE: This section was not present at the time this spec was approved.

Security impact
---------------

This potentially improves security by restricting tenant access to the
control plane.

Other end user impact
---------------------

To use this feature, end users will need to:

* Set nodes to use the Neutron provider.

* Use local boot for nodes using the Neutron provider.

Scalability impact
------------------

When configured to use the Neutron plugin, this will result in additional
API calls to Neutron to manage a node. However, impact on scalability should
be negligible.

Performance Impact
------------------

None.

Other deployer impact
---------------------

Two new configuration options will be added:

* ``CONF.provisioning_network`` specifies the ID of the provisioning network.

* ``CONF.default_network_provider`` specifies the default network provider to
  use for nodes with ``node.network_provider`` set to NULL.

A new database column (Node.network_provider) is also added, and so deploying
this change will require a database migration to be ran.

Deployers will need to deploy a version of Nova that supports this feature,
if using Nova.

Deployers will need to deploy an ML2 mechanism driver that supports connecting
baremetal resources to Neutron networks.

Developer impact
----------------

Driver authors should support this feature by calling the methods provided.


Implementation
==============

Assignee(s)
-----------

jroll <jim@jimrollenhagen.com>

And hopefully many others! :)

Work Items
----------

* Add the Node.network_provider field and the default_network_provider
  configuration option..

* Implement the base interface.

* Implement the no-op provider.

* Instrument each deploy driver with calls to this interface.

* Implement the Neutron plugin provider.

* Modify Nova to send the extra flag discussed above, when creating ports for
  a machine using the Ironic virt driver.


Dependencies
============

None.


Testing
=======

The no-op provider will be tested in the gate by default.

Neutron will provide an ML2 mechanism that simulates connecting real hardware
to real switches. When that mechanism is available, we can test the Neutron
provider in the gate.


Upgrades and Backwards Compatibility
====================================

Default behavior is the current behavior, so this change should be fully
backwards compatible.


Documentation Impact
====================

This feature will be fully documented.


References
==========

Discussions on the topic include:

* https://etherpad.openstack.org/p/YVR-neutron-ironic

* https://etherpad.openstack.org/p/liberty-ironic-network-isolation

* Logs from https://wiki.openstack.org/wiki/Meetings/Ironic-neutron

* The spec for the rest of the API and data model changes, and ML2 integration
  in general: https://review.opendev.org/#/c/188528
