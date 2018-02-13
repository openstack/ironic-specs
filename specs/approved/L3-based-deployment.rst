..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================
Ironic L3 based deployment
==========================

https://storyboard.openstack.org/#!/story/1749193

Ironic relies on L2 network for IP configuration (and optionally PXE booting)
during provisioning baremetal nodes. It puts limitations on Multi-rack
deployments and remote site deployments like Edge Cloud etc. This specification
proposes passing IP network info via virtual media on hardware supporting
virtual media boot, which enables deployment to run on purely routed L3 layers
without any dependency on DHCP.

This specification suggests creating extra option (host_network_info) to
virtual media based boot interfaces for deployment with backward compatibility
to the existing DHCP based booting. This extra option should be selectable with
a flag at boot interface level.

Problem description
===================

It is not always easy to provide Layer-2 connectivity between Ironic conductor
node and target nodes.

Example use cases:

* Multi Rack deployment: Inter-Rack L2 switching beyond ToR is a challenge with
  DHCP-relay, as this adds requirement of either having ToR with DHCP-relay, or
  having a system or VM listening on the remote subnet to relay or proxy DHCP
  requests.

* Remote site targets: It would be a great idea to deploy Servers in different
  remote sites from a central location. With the current setup of L2 dependency
  we need to provide VPN L2 tunnel between Ironic Conductor and remote target
  server.
  example: Edge cloud servers or Distributed VNF Flexi Zone Controllers:[5].

Proposed change
===============

Most of the Hardware offerings in the market support Virtual media connection
and booting. To date even these servers rely on DHCP to get the IP
configuration. This dependency on DHCP can be supported with below proposed
changes.

On the Ironic Conductor side:-
All vendors supporting Virtual media connection, booting and power management
on L3, needs to create a new option that will use IP config data of target
nodes which can be derived as follows:

1. Stand-alone mode:- IP network information can be fed/removed directly by the
   end user to ironic node port or portgroup's field "host_network_info".

2. Integrated Deployment Mode:- Neutron's network info is derivable from ironic
   node port or portgroup -> neutron port -> neutron subnet -> neutron network.
   This info can be cached in ironic node port or portgroup's field
   "host_network_info". This field should be cleared when the baremetal node is
   disassociated with nova node or when the node is unplugged from provisioning
   network.

Ironic virtmedia boot interfaces can use this derived information to construct
os-net-config JSON structure:[2]. This would be added as "host_network_info" in
parameters.txt when running create_vfat_image:[1].

Example:- Content for *host_network_info*

.. code-block:: JSON

   {
       "interface_mapping": {
           "nic1": "aa:bb:cc:d0:e0:f0"
       },
       "network_config": [
           {
               "addresses": [
                   {
                       "ip_netmask": "192.168.1.21/24"
                   }
               ],
               "device": "nic1",
               "mtu": 1500,
               "type": "vlan",
               "use_dhcp": false,
               "vlan_id": 20
           },
           {
               "mtu": 1500,
               "name": "nic1",
               "type": "interface",
               "use_dhcp": false
           }
       ]
   }

.. end

Note:- This JSON structure should be validated by ironic-conductor to avoid
parser errors on ironic-python-agent side.

Passing vfat image to target node:

* Option-1: This vfat image can be attached to the target node's Virtual Floppy
  if it is supported by the hardware.

* Option-2: Some hardware do not support attaching more than one Virtual
  device. In such case the vfat image can be zipped and append to the end of
  IPA boot ISO with an extra 64K block.

On the Ironic-Python-Agent Ramdisk side below changes are needed:

1. A logic should be added to IPA to extract last 64K block of boot iso, check
   if it is a valid zip file, if so unzip and loop mount it. This step is
   needed to extract vfat image in the case of above described [Option-2].

2. Adding logic in IPA to read the virtual media parameters data. Look for
   "host_network_info" JSON structure. If found create a config file
   /etc/os-net-config/config.json.

3. os-net-config tool and its dependencies need to be added to configure
   realtime network in accordence to /etc/os-net-config/config.json, before
   initiating REST APIs towards ironic conductor.

This method can be used by all ironic in-band operations, for avoiding L2
dependency.

Alternatives
------------

glean:[3] can also be used instead of os-net-config:[2]
Ignition:[4] can also be used instead of os-net-config:[2]

Data model impact
-----------------

As described in `Proposed change`_ section, port and portgroup needs a new
database field ``host_network_info`` to store networking information. This will
be a JSON dictionary.

State Machine Impact
--------------------

None

REST API impact
---------------

* Update ``GET /v1/ports/detail``, ``GET /v1/ports/{port_id}``,
  ``PATCH /v1/ports/{port_id}``, ``GET /v1/nodes/{node_ident}/ports/detail``,
  ``GET /v1/portgroups/detail``, ``GET /v1/portgroups/{portgroup_ident}``,
  ``PATCH /v1/portgroups/{portgroup_ident}``,
  ``GET /v1/nodes/{node_ident}/portgroups/detail``,
  ``GET /v1/portgroups/{portgroup_ident}/ports/detail``:

  New request/response field:

  * ``host_network_info`` JSON structure of the host network configuration.

Client (CLI) impact
-------------------

"ironic" CLI
~~~~~~~~~~~~

None

"openstack baremetal" CLI
~~~~~~~~~~~~~~~~~~~~~~~~~

* Update ``openstack baremetal port create``, ``openstack baremetal port set``,
  ``openstack baremetal port group create`` and
  ``openstack baremetal port group set`` commands to accept one more argument
  ``--host-network-info <JSON>``, with help text describing JSON structure of
  the host network configuration.

* Extend the output of the ``openstack baremetal port show`` and
  ``openstack baremetal portgroup show`` commands with ``host_network_info``
  column.

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

* Changes to IPA service, which would check availability of "host_network_info"
  parameter in Virtual Floppy.

* os-net-config package needs to be added to IPA deploy ramdisk.

Security impact
---------------

None.

Other end user impact
---------------------

None.

Scalability impact
------------------

None.

Performance Impact
------------------

None.

Other deployer impact
---------------------

None.

Developer impact
----------------

None.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
    shekar (chandra.s.rangavajjula@nokia.com)

Other contributors:
    None.

Work Items
----------

* Changes to IPA and addition of os-net-config tool in IPA Ramdisk.

* Add support to build os-net-config JSON structure using create_vfat_image:[1]
  on hardware which support virtual media boot.

* Update documentation

Dependencies
============

* os-net-config tool in IPA ramdisk

* Hardware specific APIs to attach detach Virtual Media

Testing
=======

Test the ironic deployment without enabling DHCP and L2 switch connectivity
between ironic-conductor and Target nodes.

Upgrades and Backwards Compatibility
====================================

None.

Documentation Impact
====================

Use of L3 based deployment should be documented as part of this item.

References
==========

.. [1] https://specs.openstack.org/openstack/ironic-specs/specs/juno-implemented/ironic-ilo-virtualmedia-driver.html#proposed-change
.. [2] https://github.com/openstack/os-net-config
.. [3] https://github.com/openstack-infra/glean
.. [4] https://coreos.com/ignition/docs/latest/network-configuration.html
.. [5] https://networks.nokia.com/products/flexi-zone
