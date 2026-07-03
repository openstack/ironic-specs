..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===================================
Standalone Networking Configuration
===================================

https://bugs.launchpad.net/ironic/+bug/2113769

This document proposes a mechanism for configuring switch port attributes
during the management of baremetal nodes. The aim is to enable Ironic to
support this functionality without delegating networking tasks to Neutron.
This new mechanism, initiated by the existing network driver interface in the
Conductor, would delegate actual switch port configuration to a standalone
service. This service could be co-located with existing Ironic services or
managed independently, on a separate server, by an operator group dedicated
to network equipment.

Problem description
===================

Operators seek to automate network configuration to enable node deployment
without manual pre-configuration of switch ports. Nodes connect to
switches via one or more network interfaces, each requiring specific
neighboring switch configurations for their intended use. These interfaces
may require access port or trunk port configurations. Additionally, link
aggregation might be required to enhance a node's networking capacity or
redundancy.  Normally, the configuration operations must be completed manually
before the nodes can be deployed by Ironic.

Managing nodes and networking equipment often falls to separate organizational
groups. This division of responsibility introduces security concerns regarding
who can modify switch configurations and to what extent. Since fine-grained
authorization varies across switch vendors, this service should offer basic
controls to address operator security concerns; thereby limiting what
operations could be attempted by Ironic.

Proposed change
===============

The implementation proposed is to introduce a new standalone service to execute
the interactions with the network switch equipment.  This new service includes
a JSON RPC front end API to be accessed by a network driver running within the
context of the Conductor.  During the normal management lifecycle of baremetal
nodes, any ports defined on a node will be processed by the network driver as
is already the case in the current implementation.

It is the responsibility of the driver to ensure that related switch
configurations are updated according to the ``switchport`` and
``portchannel`` information contained within the ``extra`` property of the
port.  Existing network drivers can interface with the Neutron subsystem to
manage switch configurations, but the solution proposed in this design
eliminates the need to include other OpenStack components and instead provides
an end-to-end Ironic only solution.

.. note:: The usage of the ``extra`` property is an interim approach to enable the new
  functionality.  The long term goal is to replace these properties with a new
  set of API models and endpoints that are specific to the new functionality.
  The intent is to explore the use of this new functionality using the
  ``extra`` property as a means to validate the new functionality.  Once the
  usecases are validated and better understood we can promote the new contents
  of the ``extra`` property to a new set of API models and endpoints.

.. note:: The standalone service may need to consider the implications of
  issuing commands concurrently to the same switch.  This could lead to
  unexpected results under certain circumstances.  The standalone service
  should be designed to handle this scenario gracefully.

.. code-block::

  ┌──────────────────────┐
  │                      │
  │    Ironic API        │
  │                      │
  └──────────┬───────────┘
             │
             │                 ┌────────────────────────┐
  ┌──────────▼───────────┐     │                        │
  │                      │     │   Ironic Standalone    │
  │   Ironic Conductor   │     │   Networking Service   │     ┌───────────────┐
  │          ┌───────────┤     │           ┌────────────┤     │               │
  │          │  Network  ┼─────►           │  Switch    ┼─────►  TOR Switch   │
  │          │  Driver   │     │           │  Driver    │     │               │
  └──────────└───────────┘     └───────────└────────────┘     └───────────────┘


Alternatives
------------
If we could assume that all network switches implemented some form of fine
grained access controls that could be applied to specific user credentials then
we could forgo building an access control mechanism and instead rely on the
access rights granted to the user credentials assigned to the Ironic service.
This would eliminate the need to implement this mechanism as a standalone
service and instead we could simply embed the functionality directly into the
Conductor by way of a custom network driver that could directly interact with
the network switches.

.. code-block::

   ┌──────────────────────┐
   │                      │
   │    Ironic API        │
   │                      │
   └──────────┬───────────┘
              │
              │
   ┌──────────▼───────────┐
   │                      │
   │   Ironic Conductor   │        ┌───────────────────┐
   │          ┌───────────┤        │                   │
   │          │   Network ┼────────►─  TOR Switch      │
   │          │   Driver  │        │                   │
   └──────────└───────────┘        └───────────────────┘

Of course, the access control requirement is only one reason for having a
separate service and we would need to assess whether other requirements would
also push us towards a standalone service (e.g., would it be beneficial to
have the actual switch interactions performed on a separate service for
performance/scalability reasons?  Assuming the driver operations are
synchronous to this other service presumably performance/scalability would
not be improved by having a separate service).

Data model impact
-----------------
There are no planned changes to existing data models.  Switch port
configuration details are to be stored in the ``extra`` property of existing
port objects; therefore, existing port related data model schemas can be used
without modification.

State Machine Impact
--------------------
The mechanism implemented by this feature depends on switch port details being
collected via LLDP discovery.  For this to occur, the switch ports of the node
must be enabled prior to enrollment so that LLDP information can be collected
during the initial inspection operation.  This poses three concerns.

1. The switch ports must be enabled prior to the initial enrollment of the node
and must be configured on a VLAN that is capable of running the initial
inspection for the node.  That is, the VLAN must be routable back to the API
endpoint.

2. To ensure that the enrollment process is repeatable for nodes that are
deprovisioned and later re-enrolled we must ensure that switch ports are
set back to the VLAN described above in (1) whenever not in use.  We refer to
this VLAN as the "idle" VLAN, and we ensure that the standalone experimental
driver always falls back to this VLAN when removing any other network from the
port configuration.

3. Since the "idle" VLAN is potentially different than the final VLAN of the
primary interface of the node, any static network configuration data provided
when enrolling the host may not be valid or appropriate to use on the during
the inspection process.

To address these concerns two changes to the node state machine should be
considered for which two additional configuration options are proposed:

  1. Restoration of Idle Network

  If the "idle" network VLAN is configured then it is restored onto the switch
  port whenever a network is removed from the port.

  This ensures that bare metal hardware can be seamlessly re-enrolled and
  re-provisioned by maintaining the "idle" VLAN configuration on switch
  ports, enabling LLDP information collection during subsequent inspections.

  2. Inspection Network Configuration

  A new configuration option inspector.force_dhcp modifies the inspection
  process behavior:

  - Inspection State: During managed inspection, when enabled, this option
    ensures that static network data is ignored.  The ramdisk will instead
    rely on DHCP on all interfaces to acquire network configuration.
  - Network Discovery: Automatically enables LLDP collection across all
    interfaces to ensure comprehensive network topology discovery

These changes do not introduce new provisioning states but enhance the
existing state transitions to better support standalone networking scenarios
where complete network topology discovery and consistent switch port
configuration are critical for automated bare metal lifecycle management.

REST API impact
---------------
There are no planned changes to existing API schemas or endpoints.  Switch port
configuration details are stored in the ``extra`` property of a port or
portgroup; therefore, existing port and portgroup related API endpoints and
schemas can be used without modification.  The ``extra`` property should be
populated with a dictionary conforming to this schema when related to a port
object.

.. code-block::

    {
      "$schema": "http://json-schema.org/draft-07/schema#",
      "title": "Switchport Configuration",
      "description": "Schema for defining switchport configurations based on
        mode (trunk or access)",
      "type": "object",
      "properties": {
        "switchport": {
          "type": "object",
          "properties": {
            "mode": {
              "type": "string",
              "enum": ["trunk", "access"]
            },
            "native_vlan": {
              "type": "integer",
              "minimum": 1,
              "description": "The native VLAN ID for the switchport.  If not
                supplied then the switch global default VLAN ID is used."
            },
            "allowed_vlans": {
              "type": "array",
              "items": {
                "type": "integer",
                "minimum": 1
              },
              "minItems": 1,
              "description": "List of allowed VLANs for trunk mode.  Only
                applicable, and is mandatory, if mode=trunk."
            }
          },
          "required": [
            "mode",
          ]
        }
      },
      "required": [
        "switchport",
      ],
    }

For example, the following data is stored in the ``extra`` property of a port
to specify that its switch port must be configured as a trunk port having a
specific default VLAN and a set of allowed VLANs.

.. code-block::

    {'switchport':
      {'mode': 'trunk',
       'native_vlan': 1,
       'allowed_vlans': [2, 3, 4]
      }
    }

The following data is stored in the ``extra`` property of a port to specify
that its switch port must be configured as an access port having a specific
default VLAN.

.. code-block::

    {'switchport':
      {'mode': 'access',
       'native_vlan': 1,
      }
    }

If related to a portgroup object then a similar schema is supported but with
differences applicable to switch port channels only.

.. code-block::

    {
      "$schema": "http://json-schema.org/draft-07/schema#",
      "title": "Switchport Configuration",
      "description": "Schema for defining switch port channel configurations
        based on mode (e.g., trunk or access) and aggregation mode (e.g., LACP
        or static)",
      "type": "object",
      "properties": {
        "portchannel": {
          "type": "object",
          "properties": {
            "mode": {
              "type": "string",
              "enum": ["trunk", "access"]
            },
            "native_vlan": {
              "type": "integer",
              "minimum": 1,
              "description": "The native VLAN ID for the switchport.  If not
                supplied then the switch global default VLAN ID is used."
            },
            "allowed_vlans": {
              "type": "array",
              "items": {
                "type": "integer",
                "minimum": 1
              },
              "minItems": 1,
              "description": "List of allowed VLANs for trunk mode.  Only
                applicable, and is mandatory, if mode=trunk."
            },
            "aggregation_mode": {
              "type": "string",
              "enum": ["lacp", "static"],
            },
          },
          "required": [
            "mode",
            "aggregation_mode",
          ]
        }
      },
      "required": [
        "portchannel",
      ],
    }

For example, the following data is stored in the ``extra`` property of a
portgroup to specify that a corresponding portchannel must be created and
managed on the switch.  The portchannel should be configured as a trunk port
having a specific default VLAN and a set of allowed VLANs, and operate in the
LACP link aggregation mode.

.. code-block::

    {'portchannel':
      {'mode': 'trunk',
       'native_vlan': 1,
       'allowed_vlans': [2, 3, 4],
       'aggregation_mode': 'lacp'
      }
    }

The following data is stored in the ``extra`` property of a portgroup to
specify that a corresponding portchannel must be created and managed on the
switch.  The portchannel must be configured as an access port having a specific
default VLAN, and operation in the static link aggregation mode.

.. code-block::

    {'portchannel':
      {'mode': 'access',
       'native_vlan': 1,
       'aggregation_mode': 'static'
      }
    }


Client (CLI) impact
-------------------
None

"openstack baremetal" CLI
~~~~~~~~~~~~~~~~~~~~~~~~~
None

"openstacksdk"
~~~~~~~~~~~~~~
None

RPC API impact
--------------

1. Conductor RPC API:
   None

2. Standalone Service API:
   The RPC API used between the driver and the standalone networking service
   can be defined as follows

+------------------------------+---------------------------------------------+
| Method                       | Signature                                   |
+==============================+=============================================+
| update_port                  | .. code-block::                             |
|                              |                                             |
|                              |   {"switch_id": "xx:xx:xx:xx:xx:xx",        |
|                              |    "port_name": "xxx",                      |
|                              |    "description": "xxx",                    |
|                              |    "mode": "[access|trunk]",                |
|                              |    "native_vlan": n,                        |
|                              |    "allowed_vlans": [x, y, z],              |
|                              |    "portchannel_name": "xxx"}               |
+------------------------------+---------------------------------------------+
| reset_port                   | .. code-block::                             |
|                              |                                             |
|                              |   {"switch_id": "xx:xx:xx:xx:xx:xx",        |
|                              |    "port_name": "xxx",                      |
|                              |    "native_vlan": n,                        |
|                              |    "allowed_vlans": [x, y, z],              |
|                              |    "default_vlan": n}                       |
|                              |                                             |
+------------------------------+---------------------------------------------+
| disable_port                 | .. code-block::                             |
|                              |                                             |
|                              |   {"switch_id": "xx:xx:xx:xx:xx:xx",        |
|                              |    "port_name": "xxx"}                      |
|                              |                                             |
+------------------------------+---------------------------------------------+
| create_portchannel           | .. code-block::                             |
|                              |                                             |
|                              |   {"switch_ids": ["xx:xx:xx:xx:xx:xx",...]  |
|                              |    "portchannel_name": "xxx",               |
|                              |    "description": "xxx",                    |
|                              |    "mode": "[access|trunk]",                |
|                              |    "default_vlan": {1 to 4094},             |
|                              |    "allowed_vlans": [x, y, z],              |
|                              |    "aggregation_mode": "[lacp|static]"}     |
|                              |                                             |
+------------------------------+---------------------------------------------+
| delete_portchannel           | .. code-block::                             |
|                              |                                             |
|                              |   {"switch_ids": ["xx:xx:xx:xx:xx:xx",...], |
|                              |    "port_name": "xxx"}                      |
|                              |                                             |
+------------------------------+---------------------------------------------+


Driver API impact
-----------------
No changes to the existing driver interfaces.  It is expected that this
functionality can be implemented within the existing definition of the
Networking Driver API.  This means that the existing Conductor workflow does
need to be modified.  The new networking driver must implement the defined
abstract interfaces of the base network interface in a way that ensures that
switch port configurations are updated correctly as the baremetal node
transitions through the full management life cycle state machine.

Proper operation of the driver depends on the port being populated with LLDP
information in the form of the ``link_local_connection`` property.  This
ensures that the driver can associate the configuration to the correct port on
the switch.

+------------------------------+---------------------------------------------+
| Interface                    | Actions                                     |
+==============================+=============================================+
| port_changed                 | Update switch port configuration to match   |
|                              | if necessary.                               |
+------------------------------+---------------------------------------------+
| portgroup_changed            | Update switch port configuration to match   |
|                              | if necessary.                               |
+------------------------------+---------------------------------------------+
| vif_attach                   | N/A.  VIF attachments not expected or       |
|                              | supported by this driver.                   |
+------------------------------+---------------------------------------------+
| vif_detach                   | N/A.  VIF attachments not expected or       |
|                              | supported by this driver.                   |
+------------------------------+---------------------------------------------+
| vif_list                     | N/A.  VIF attachments not expected or       |
|                              | supported by this driver.                   |
+------------------------------+---------------------------------------------+
| get_current_vif              | N/A.  VIF attachments not expected or       |
|                              | supported by this driver.                   |
+------------------------------+---------------------------------------------+
| add_provisioning_network     | Configure each ports according to the       |
|                              | provisioning network configured in the      |
|                              | config file; otherwise, configure according |
|                              | to its defined switchport ``extra``         |
|                              | property.                                   |
+------------------------------+---------------------------------------------+
| remove_provisioning_network  | Reset port back to switch port defaults, or |
|                              | set back to "idle" network if configured.   |
+------------------------------+---------------------------------------------+
| configure_tenant_networks    | Configure each ports according to the       |
|                              | ``switchport`` configuration defined in its |
|                              | ``extra`` property.                         |
+------------------------------+---------------------------------------------+
| unconfigure_tenant_networks  | Reset port back to switch port defaults, or |
|                              | set back to "idle" network if configured.   |
+------------------------------+---------------------------------------------+
| add_cleaning_network         | Configure each ports according to the       |
|                              | cleaning network configured in the          |
|                              | config file; otherwise, configure according |
|                              | to its defined switchport ``extra``         |
|                              | property.                                   |
+------------------------------+---------------------------------------------+
| remove_cleaning_network      | Reset port back to switch port defaults, or |
|                              | set back to "idle" network if configured.   |
+------------------------------+---------------------------------------------+
| validate_rescue              | N/A                                         |
+------------------------------+---------------------------------------------+
| add_rescuing_network         | Configure each ports according to the       |
|                              | rescuing network configured in the          |
|                              | config file; otherwise, configure according |
|                              | to its defined switchport ``extra``         |
|                              | property.                                   |
+------------------------------+---------------------------------------------+
| remove_rescuing_network      | Reset port back to switch port defaults, or |
|                              | set back to "idle" network if configured.   |
+------------------------------+---------------------------------------------+
| validate_inspection          |  N/A                                        |
+------------------------------+---------------------------------------------+
| add_inspection_network       | Configure each ports according to the       |
|                              | inspection network configured in the        |
|                              | config file; otherwise, configure according |
|                              | to its defined switchport ``extra``         |
|                              | property.                                   |
+------------------------------+---------------------------------------------+
| remove_inspection_network    | Reset port back to switch port defaults, or |
|                              | set back to "idle" network if configured.   |
+------------------------------+---------------------------------------------+
| need_power_on                | False                                       |
+------------------------------+---------------------------------------------+
| get_node_network_data        | Build network data from configured ports    |
+------------------------------+---------------------------------------------+
| add_servicing_network        | Configure each ports according to the       |
|                              | servicing network configured in the         |
|                              | config file; otherwise, configure according |
|                              | to its defined switchport ``extra``         |
|                              | property.                                   |
+------------------------------+---------------------------------------------+
| remove_servicing_network     | Reset port back to switch port defaults, or |
|                              | set back to "idle" network if configured.   |
+------------------------------+---------------------------------------------+

Nova driver impact
------------------
None

Ramdisk impact
--------------
None

Security impact
---------------
* RPC API Authentication/Authorization: The intent of this design is to create
  a standalone service that exists as part of the Ironic subsystem but that
  could be run and managed separately by a group dedicated to managing
  networking equipment.  In this capacity the process must have sufficient
  security controls such that only authorized users have access to its
  configuration file and RPC API.  A discussion is needed to settle on the
  approach to be used.

* Access control over switch resources: Ideally, an ACL mechanism native to the
  switch operating system would be used to restrict access to switch resources
  for the user entity assigned to the standalone networking service, but since
  an objective of this design is to not assume that all switch vendors support
  fine grained control over access to resources it may be beneficial to add
  the ability to control access to resources directly from configuration data
  stored in the configuration file for the standalone service.

  Resources to be controlled could include:

  1. Allowed/Denied VLAN IDs
  2. Allowed/Denied port list
  3. Allowed port channel management

Other end user impact
---------------------
As described in the "State Machine Impact" section.  New nodes must have their
switch ports configured on the inspection VLAN prior to enrollment.

Scalability impact
------------------
Needing to perform switch operations as part of the management of baremetal
nodes will no doubt increase the time required to complete node operations.
Exactly how much additional time will depend entirely on the responsiveness of
the management software running on the networking switch.  Having switch ports
configured before booting the node is a definite requirement; therefore, it is
likely not feasible to decouple the Conductor process from the configuration
of the switch by making it an asynchronous operation.

This will have to be evaluated as the implementation progresses.

Performance Impact
------------------
See "Scalability impact" above.

Other deployer impact
---------------------
To define the switch port configuration details to be used for provider
networks the following config file attributes must be used.  For each of the
network classes if no value is provided in the config file then the port's
``extra.switchport`` or ``extra.portchannel`` property will be used, if the
port or portgroup does not contain any such attribute then it will be ignored
by the driver.  The following attributes can be added to the main
``ironic.conf`` file.

.. code-block::

    [networking]
    idle_network = <[access|trunk]/vlan-id{1 to 4094}>
    provisioning_network = <[access|trunk]/vlan-id={1 to 4094}>
    cleaning_network = <[access|trunk]/vlan-id={1 to 4094}>
    servicing_network = <[access|trunk]/vlan-id={1 to 4094}>
    # Optionally, for inspection if a separate network is used
    # inspection_network = <[access|trunk]/vlan-id={1 to 4094}>

Example:

.. code-block::

    [networking]
    idle_network = <[access|trunk]/vlan-id=9
    provisioning_network = access/vlan-id=10
    cleaning_network = access/vlan-id=11
    servicing_network = trunk/vlan-id=12
    # Optionally, for inspection if a separate network is used
    # inspection_network = access/vlan-id=13

To propagate switch port configuration details to switches, the new networking
service must be provided with details needed to access and configure the
switches.  This includes user credentials, network address, and any other
attributes required to access the switch.

The following example is a hybrid based on the configuration requirements of
two Neutron ML2 mechanism drivers ([1], [2]) combined with some additional
access control information to limit access to switch resources.  It contains
provisions for eventually allowing different types of driver implementations to
interact with switches.  These attributes can be added to the config file
supplied to the standalone networking service.

.. code-block:: ini

    [DEFAULT]
    enabled_devices = <list of switch names>
    allowed_vlans = <list of allowed vlans, takes precedence over denied_vlans
      if provided>
    denied_vlans = <list of denied vlans, superseded by allowed_vlans if
      provided>
    allowed_ports = <list of allowed port names, takes precedence over
      denied_ports if provided>
    denied_ports = <list of denied port names, superseded by allowed_ports if
      provided>
    portchannels_allowed = [true/false]

    [<switch name>]
    driver = <driver name>
    switch_id = <switch mac address>
    host = <switch management ip address>
    username = <username>
    password = <password, if driver support basic auth>
    key_filename = <ssh private key file absolute path, if driver supports ssh>
    hostkey_verify = <[true|false]>
    allowed_vlans = <list of allowed vlans, takes precedence over denied_vlans
      if provided. Overrides global value if supplied>
    denied_vlans = <list of denied vlans, superseded by allowed_vlans if
      provided. Overrides global value if supplied>
    allowed_ports = <list of allowed port names, takes precedence over
      denied_ports if provided. Overrides global value if supplied>
    denied_ports = <list of denied port names, superseded by allowed_ports if
      provided, Overrides global value if supplied>
    portchannels_allowed = [true/false, Overrides global value if supplied]


Example:

.. code-block:: ini

    [DEFAULT]
    enabled_devices = netconf-based-device.example.net,cli-based-device.example.net
    allowed_vlans = 3,4,5
    denied_vlans = 6,7,8

    [netconf-based-device.example.net]
    driver = netconf-openconfig
    switch_id = <switch mac address>
    host = <switch management ip address>
    username = user
    key_filename = /etc/ironic/ssh_keys/device_a_sshkey
    hostkey_verify = false

    [cli-based-device.example.net]
    driver = netmiko_cisco_ios
    switch_id = <switch mac address>
    host = <switch management ip address>
    username = user
    password = secret

Developer impact
----------------
None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  alegacy

Other contributors:
  n/a

Work Items
----------
* Define RPC API for standalone service

* Split networking-generic-switch into a reusable library without any Neutron
  entanglements.

* Implement standalone service

* Implement network driver to interface with standalone service

* Implement switch driver (using refactored parts of the
  networking-generic-switch package, see above) to interface with networking
  equipment

* Revisit the use of the ``extra`` properties and replace with new API models
  and endpoints.

Dependencies
============
* The network-generic-switch library contains code to implement interactions
  with network switches.  Unfortunately, that code is entangled with Neutron
  API dependencies.  It is desirable to reuse as much of that library as
  possible to implement part of this service, but the Neutron specific aspects
  of its API and implementation must be removed.  A possible path forward is to
  refactor that library so that the Neutron specific parts remain in the actual
  networking-generic-switch library while the switch specific parts get moved
  into a new library that can be referenced from the networking-generic-switch
  project and this new standalone service separately.

Testing
=======
* Unit testing
* Possibly a Devstack setup with a stubbed-out driver to simulate switch
  configurations.

Upgrades and Backwards Compatibility
====================================
None

Documentation Impact
====================
TBD

References
==========
* [0] https://specs.openstack.org/openstack/ironic-specs/specs/not-implemented/mercury.html
* [1] https://etherpad.opendev.org/p/ironic-standalone-networking
* [2] https://docs.openstack.org/networking-baremetal/latest/index.html
* [3] https://docs.openstack.org/networking-generic-switch/latest/index.html
