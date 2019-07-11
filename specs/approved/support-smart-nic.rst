..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

====================
Smart NIC Networking
====================

https://storyboard.openstack.org/#!/story/2003346

This spec describes proposed changes to Ironic to enable a generic,
vendor-agnostic, baremetal networking service running on smart NICs,
enabling baremetal networking with feature parity to the virtualization
use-case.

Problem description
===================

While Ironic today supports Neutron provisioned network connectivity for
baremetal servers through an ML2 mechanism driver, the existing support
is based largely on configuration of TORs through vendor-specific mechanism
drivers, with limited capabilities.

Proposed change
===============

There is a wide range of smart/intelligent NICs emerging on the market.
These NICs generally incorporate one or more general purpose CPU cores along
with data-plane packet processing acceleration, and can efficiently run
virtual switches such as OVS, while maintaining the existing interfaces to the
SDN layer.

The proposal is to extend Ironic to enable use of smart NICs to implement
generic networking services for Bare Metal servers. The goal is to enable
running the standard Neutron Open vSwitch L2 agent, providing a generic,
vendor-agnostic bare metal networking service with feature parity compared
to the virtualization use-case. The Neutron Open vSwitch L2 agent manages the
OVS bridges on the smart NIC.

In this proposal, we address two use-cases:

#. Neutron OVS L2 agent runs locally on the smart NIC.

   This use case requires a smart NIC capable or running openstack control
   services such as the Neutron OVS L2 agent. This use case strives to view
   the smart NIC as an isolated hypervisor for the baremetal node, with the
   smart NIC providing the services to the bare metal image running on the host
   (as a hypervisor would provide services to a VM). While this spec initially
   targets Neutron OVS L2 agent, the same implementation would naturally and
   easily be extended to any other ML2 plugin as well as to additional
   agents/services (for example exposing emulated NVMe storage devices
   back-ended by a storage initiator on the smart NIC).

#. Neutron OVS L2 agent(s) run remotely and manages
   the OVS bridges for all the baremetal smart NICs.


The enhancements for Neutron OVS L2 agent captured in [1]_, [2]_ and [3]_.

* Set the smart NIC configuration

  smart NIC configuration includes the following:

  #. extend the ironic port with is_smartnic field. (default to False)
  #. smart NIC hostname - the hostname of server/smart NIC where the Neutron
     OVS agent is running. (required)
  #. smart NIC port id - the port name that needs to be plugged to the
     integration bridge. B in the diagram below (required)
  #. smart NIC SSH public key - ssh public key of the smart NIC
     (required only for remote)
  #. smart NIC OVSDB SSL certificate - OVSDB SSL of the OVS in smart NIC
     (required only for remote)

  The OVS ML2 mechanism driver will determine if the Neutron OVS Agent runs
  locally or remotely based on smart NIC configuration passed from ironic.
  The config attribute will be stored in the local_link_information of the
  baremetal port.

  In the scope of this spec the smart NIC config will be set manually by
  the admin.

* Deployment Interfaces

  Extending the ramdisk, direct, iscsi and ansible to support the smart nic
  use-cases.

  The Deployment Interfaces call network interface methods such as:
  add_provisioning_network, remove_provisioning_network,
  configure_tenant_networks, unconfigure_tenant_networks, add_cleaning_network
  and remove_cleaning_network.

  These network methods are currently ordinarily called when the baremetal is
  powered down, ensuring proper network configuration on the TOR before booting
  the bare metal.

  smart NICs share the power state with the baremetal, requiring the baremetal
  to be powered up before configuring the network. This leads to a potential
  race where the baremetal boots and access the network prior to the network
  being properly configured on the OVS within the smart NIC.

  To ensure proper network configuration prior to baremetal boot, the
  deployment interfaces will intermittently boot the baremetal into the BIOS
  shell, providing a state where the ovs on the smart NIC may be configured
  properly before rebooting the bare metal into the actual guest image or
  ramdisk. The ovs on the smart NIC will get programmed after we verify that
  the neutron ovs agent is alive.


  The following code for configure/unconfigure network:

  .. code-block:: python

      if task.driver.network.need_power_on(task):
          old_power_state = task.driver.power.get_power_state(task)
          if old_power_state == states.POWER_OFF:
              # set next boot to BIOS to halt the baremetal boot
              manager_utils.node_set_boot_device(task, boot_devices.BIOS,
                                                 persistent=False)
              manager_utils.node_power_action(task, states.POWER_ON)

      # ...
      # call task.driver.network method(s)
      # ...

      if task.driver.network.need_power_on(task):
          manager_utils.node_power_action(task, old_power_state)

  The following methods in the deployment interface are calling to one or
  more configure/unconfigure networks and should be updated with the logic
  above.

  * iscsi Deploy Interface

    - iscsi_deploy::prepare
    - iscsi_deploy::deploy
    - iscsi_deploy::tear_down

  * ansible Deploy Interface

    - ansible/deploy::reboot_and_finish_deploy
    - ansible/deploy::prepare
    - ansible/deploy::tear_down
    - ansible/deploy::prepare_cleaning
    - ansible/deploy::tear_down_cleaning

  * direct Interface

    - agent::prepare
    - agent::tear_down
    - agent::deploy
    - agent::rescue
    - agent::unrescue
    - agent_base_vendor::reboot_and_finish_deploy
    - agent_base_vendor::_finalize_rescue

  * RAM Disk Interface

    - pxe::deploy

  * Common cleaning methods

    - deploy_utils::prepare_inband_cleaning
    - deploy_utils::tear_down_inband_clean

* Network Interface

  Extend the base `network_interface` with need_power_on -
  return true if any ironic port attached to the node is a smart nic

  Extend the ironic.common.neutron add_ports_to_network/
  remove_ports_from_network methods for the smart NIC case:

  * on add_ports_to_network and has smartNIC do the following:

    - check neutron agent alive - verify that neutron agent is alive
    - create neutron port
    - check neutron port active - verify that neutron port is in active state

  * on remove_ports_from_network and has smartNIC do the following:

    - check neutron agent alive - verify that neutron agent is alive
    - delete neutron port
    - check neutron port is removed


* Neutron ml2 OVS changes:

  - Introduce a new vnic_type for ``smart-nic``.
  - Update the Neutron ml2 OVS to bind smart-nic vnic_type with
    `binding:profile` smart NIC config.

* Neutron OVS agent changes:

Example of smart NIC model::

  +---------------------+
  |      baremetal      |
  | +-----------------+ |
  | |  OS Server    | | |
  | |               | | |
  | |      +A       | | |
  | +------|--------+ | |
  |        |          | |
  | +------|--------+ | |
  | |  OS SmartNIC  | | |
  | |    +-+B-+     | | |
  | |    |OVS |     | | |
  | |    +-+C-+     | | |
  | +------|--------+ | |
  +--------|------------+
           |

  A - port on the baremetal host.
  B - port that represents the baremetal port in the smart NIC.
  C - port that represents to the physical port in the smart NIC.

  Add/Remove Port B to the OVS br-int with external-ids

  In our case we will use the neutron OVS agent to plug the port on update
  port event with the following external-ids: iface-id,iface-status, attached-mac
  and node-uuid


Alternatives
------------

* Delay the Neutron port binding (port binding means setting all the
  OVSDB/Openflows config on the SmartNIC) to be performed by Neutron
  later (once the bare metal is powered up). The problem with this
  approach is that we have no guarantee of if/when the rules will be
  programmed, and thus may inadvertently boot the baremetal while
  the smart NIC is still programmed on the old network.

Data model impact
-----------------

A new ``is_smartnic``  boolean field will be added to Port object.


State Machine Impact
--------------------

None

REST API impact
---------------

The port REST API will be modified to support the new ``is_smartnic``
field.  The field will be readable by users with the baremetal observer role
and writable by users with the baremetal admin role.

Updates to the is_smartnic field of ports will be restricted in the
same way as for other connectivity related fields (link local connection, etc.)
- they will be restricted to nodes in the ``enroll``, ``inspecting`` and
``manageable`` states.

Client (CLI) impact
-------------------


"ironic" CLI
~~~~~~~~~~~~

None

"openstack baremetal" CLI
~~~~~~~~~~~~~~~~~~~~~~~~~

The openstack baremetal CLI will be updated to support getting and setting the
``is_smartnic`` field on ports.

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

* Smart NIC Isolation

Both use cases run infrastructure functionality on the smart NIC, with
the first use case also running control plane functionality.

This requires proper isolation between the untrusted bare metal host and the
smart NIC, preventing any/all direct or indirect access, both through the
network interface exposed to the host and through side channels such as the
platform BMC.

Such isolation is implemented by the smart NIC device and/or the hardware
platform vendor. There are multiple approaches for such isolation,
ranging from completely physical disconnection of the smart NIC from the
platform BMC to a platform with a trusted BMC wherein the BMC considers
the baremetal host an untrusted entity and restricts its capabilities/access
to the platform.

In the absence of such isolation, the untrusted baremetal tenant
may be able to gain access to the provisioning network, and in the second
may be able to compromise the control plane.

Proper isolation is dependent on the platform hardware/firmware, and cannot
be directly enforced/guaranteed by ironic. Users of smart NIC use case should
be made well aware of this via explicit documentation, and should be guided
to verify the proper isolation exists on their platform when enabling such
use cases.

* Security Groups

This will allow to use Neutron OVS agent pipeline. One of the features in the
pipeline is security groups which will enhance the security model when using
baremetal in a cloud.

* Security credentials

The node running the Neutron OVS agent (smart NIC or remote, according to use
case) should be configured with the message bus credentials for the Neutron
server.

In addition, for the second use case, the SSH public key and OVSDB SSL
certificate should be configured for the smart NIC port.


Other end user impact
---------------------

* Baremetal admin needs to update the SmartNIC config manually.

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
  hamdyk  - hamdy@mellanox.com

Work Items
----------

* Update the Neutron network interface to populate the Smart NIC config from
  the ironic port to the Neutron port `binding:profile` attribute.
* Update the network_interface and common.neutron as described above
* Update deployment interfaces as described above
* Documentation updates.


Dependencies
============

None, but the Neutron specs [1]_, [2]_ and [3]_ depend on this spec.

Testing
=======

* Mellanox CI Jobs testing with Bluefield SmartNIC

Upgrades and Backwards Compatibility
====================================

None


Documentation Impact
====================

* Update the multitenancy.rst with setting the SmartNIC config
* Document the security implications/guidelines under admin/security.rst

References
==========

.. [1] https://review.opendev.org/#/c/619920/

.. [2] https://review.opendev.org/#/c/595402/

.. [3] https://review.opendev.org/#/c/595512/
