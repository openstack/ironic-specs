..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================
Ironic L3 based deployment
==========================

https://storyboard.openstack.org/#!/story/1749193

Ironic relies on L2 network for IP configuration (and optionally PXE booting)
during provisioning baremetal nodes. This imposes limitations on Multi-rack
deployments and remote site deployments like Edge Cloud etc. Besides that,
lossy provisioning network may slow down or fail some deployments.

This specification proposes relying upon Virtual Media boot capability of
modern BMCs to deliver boot image, static network configuration, node
identification information and more to the node of choice reliably and
securely.

Proposed way of booting the node should fully eliminate the need for DHCP and
PXE thus enabling deployment over purely L3 network.

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

  Example: Edge cloud servers or Distributed VNF Flexi Zone Controllers [1]_.

* Lossy, overloaded provisioning network may cause DHCP or TFTP packet drop
  slowing down or failing the entire node deployment.

Most of the hardware offerings on the market support booting off virtual media
device. While Ironic can boot the nodes over virtual media, its present
workflow still relies on DHCP for booted OS to obtain IP stack configuration.
This dependency on DHCP can be eliminated if proposed change is implemented.

Proposed change
===============

Deploying a node without DHCP involves solving three crucial problems:

1. Securely delivering boot image to the right node
2. Gathering node configuration information from cloud or site-specific
   infrastructure
3. Provisioning node configuration (as well as authentication, identification
   etc) information to the ramdisk operating system running on the node

Virtual media capability of contemporary BMCs coupled with virtual media boot
support implemented in some ironic hardware types (e.g.
``redfish-virtual-media``) fully solves problem (1). The rest of this spec is
dedicated to pondering items (2) and (3).

Gathering node configuration
----------------------------

Typical ironic node deployment workflow involves booting Ironic Python Agent
(known as IPA or ramdisk) has to be booted to prepare the node. Once set up by
IPA, the tenant (AKA instance) operating system is brought up.

In the context of OpenStack, existing cloud infrastructure is capable to
manage tenant network configuration (e.g. Neutron), to deliver network
configuration to the tenant (e.g. config-drive [2]_) and even simplify the
application of node configuration (e.g. cloud-init [3]_, os-net-config [4]_
or Ignition [11]_).
All these capabilities together largely solve problems (2) and (3) for
the tenants.

However, our software infrastructure does not presently offer much in part of
configuring ironic ramdisk networking without DHCP. This spec proposes:

* Allowing the operator to manually associate static node network configuration
  with ironic node object. The assumption is that the operator would use some
  other mechanism for IP address management.

* Enable ironic to leverage Neutron for building static network configuration
  for the node being deployed out of Neutron information.

Provisioning node configuration
-------------------------------

This spec proposes burning the contents of ``config-drive`` containing Nova
metadata into the ISO image the node has been booted from in provisioning
and state. If no ``config-drive`` information is supplied to Ironic by
the operator, ironic will create one.

To facilitate network configuration processing and application, this spec
proposes reusing ``network-data.json`` [8]_ Nova metadata format, for
Ironic-managed node network configuration.

Example ``network-data.json`` file:

.. code-block:: json

    {
        "links": [
            {
                "id": "interface0",
                "type": "phy",
                "ethernet_mac_address": "a0:36:9f:2c:e8:80",
                "mtu": 1500
            },
            {
                "id": "interface1",
                "type": "phy",
                "ethernet_mac_address": "a0:36:9f:2c:e8:81",
                "mtu": 1500
            }
        ],
        "networks": [
            {
                "id": "provisioning IPv4",
                "type": "ipv4",
                "link": "interface0",
                "ip_address": "10.184.0.244",
                "netmask": "255.255.240.0",
                "routes": [
                    {
                        "network": "10.0.0.0",
                        "netmask": "255.0.0.0",
                        "gateway": "11.0.0.1"
                    },
                    {
                        "network": "0.0.0.0",
                        "netmask": "0.0.0.0",
                        "gateway": "23.253.157.1"
                    }
                ],
                "network_id": "da5bb487-5193-4a65-a3df-4a0055a8c0d7"
            },
            {
                "id": "provisioning IPv6",
                "type": "ipv6",
                "link": "interface1",
                "ip_address": "2001:cdba::3257:9652/24",
                "routes": [
                    {
                        "network": "::",
                        "netmask": "::",
                        "gateway": "fd00::1"
                    },
                    {
                        "network": "::",
                        "netmask": "ffff:ffff:ffff::",
                        "gateway": "fd00::1:1"
                    },
                ],
                "network_id": "da5bb487-5193-4a65-a3df-4a0055a8c0d8"
            }
        ],
        "services": [
            {
                "type": "dns",
                "address": "10.0.0.1"
            }
        ]
    }

This spec anticipates associating the content of ``network_data.json``
document with ironic node object by introducing a new ``network_data`` field
to the node object to contain ``network_data.json`` information for ironic
ramdisk booting.

On the ramdisk side, this spec proposes using Glean [12]_ for consuming
and applying network configuration to the operating system running ironic
ramdisk. The main consideration here is that, unlike ``cloud-init``, ``Glean``
is lean, and readily supports a subset of ``cloud-init`` features.

Alternative ramdisk implementations can choose other ways of bootstrapping
OS networking based on ``network_data.json`` information.

To summarize - in the area of provisioning node network configuration this spec
proposes:

* Reusing Nova metadata representation for provisioning network configuration
  via ramdisk image.

* Adding a new field to ironic node object: ``network_data`` to use for ramdisk
  bootstrapping.

  The contents of this field should be validated by ironic conductor API
  against ``Glean`` JSON schema and some ad-hoc checks the implementers deem
  reasonable.

  Having ``Glean`` schema effectively hardwired into ironic conductor API will
  not allow for an easy extension or addition of other network configuration
  formats.

* Creating a new ``config-drive`` to have it including ``network-data.json``
  file.

* Writing the contents of ``config-drive`` image into the root of the ISO file
  system (along with ramdisk and kernel blobs), then making a bootable ISO
  image.

* Including ``Glean`` dependency to ramdisk image for managed OS bootstrapping.

However, Ironic rescue operation, at least in its current implementation, will
only work if user and provisioning networks are the same network.

That's because rescue ramdisk will try to renumber NICs of ramdisk by
restarting DHCP client. Working around this limitation is out of scope
of this spec.

Deployment workflow
+++++++++++++++++++

To make it easier to grasp, let's reiterate on the entire Ironic deploy work
flow focusing on how network configuration is built and used. We will consider
two scenarios - stand-alone ironic and ironic within OpenStack cloud. In each
scenario we will only consider deploy ramdisk and omit instance booting phases.

Stand-alone ironic
~~~~~~~~~~~~~~~~~~

1. Operator supplies deploy ramdisk network configuration, in form of
   ``network-data.json`` contents, via ``network_data`` field of ironic
   node being deployed. The contents of ``network_data.json`` must comply to
   the JSON schema of ``network_data.json`` that ``Glean`` can consume.

2. Ironic conductor validates supplied ``network-data.json`` against ``Glean``
   schema (that is supplied to ironic API program via configuration) and
   fails early if validation fails. ``Glean`` schema will not allow any
   properties of ``network_data.json`` that can't be applied to the OS by
   ``Glean`` even if these properties are valid as Nova metadata.

3. Ironic builds a new ``config-drive`` image and places ``network-data.json``
   file, with contents taken from ``network_data`` field, at a conventional
   location within ``config-drive`` image.

4. To boot deploy ramdisk, ironic builds bootable ISO out of ``deploy_kernel``
   and ``deploy_ramdisk`` also writing ``config-drive`` contents into the root
   of boot ISO image.

   ``Glean`` running inside ramdisk will try to mount virtual CD drive(s), in
   search for a filesystem labeled ``config-2``, read ``network_data.json`` and
   apply network configuration to the OS.

Ironic within OpenStack
~~~~~~~~~~~~~~~~~~~~~~~

1. Prior to booting ramdisk, unless operator-supplied network configuration
   already exists in ``network_data`` ironic node field, ironic gathers network
   configuration for each ironic port/portgroup, associated with the node
   being deployed, by talking with Neutron. Then ironic builds network
   configuration for ramdisk operating system in form of a
   ``network-data.json`` file.

2. Ironic builds a new ``config-drive`` image and places ``network-data.json``
   file, as build at step (1), at a pre-defined location within
   ``config-drive`` image.

3. To boot deploy ramdisk, ironic builds bootable ISO out of ``deploy_kernel``
   and ``deploy_ramdisk`` also writing ``config-drive`` contents into the root
   of boot ISO image.

   ``Glean`` running inside ramdisk will try to mount virtual CD drive(s), in
   search for a filesystem labeled ``config-2``, read ``network_data.json`` and
   apply network configuration to the ramdisk operating system.

Alternatives
------------

Alternatively to associating the entire and consistent ``network_data.json``
JSON document with ironic node object, ``network_data.json`` can be
tied to ironic port object. However, experimental implementation revealed
certain difficulties stemming from port-centric design, so consensus
has been reached to bind ``network_data.json`` to ironic node object.

Alternatively to make ironic gathering and building ``network-data.json`` [8]_,
ironic could just directly request Nova metadata service [10]_ to produce
necessary file by instance ID. However, this will not work for non-deploy
operations (such as node cleaning) because Nova is not involved.

Alternatively to relying on Nova metadata and ``Glean`` as its consumer in
ramdisk, we could leverage ``os-net-config``'s feature of taking its compressed
configuration from kernel parameters. On the flip side, the size of kernel
cmdline is severely limited (256+ bytes). Also, ``os-net-config`` feels like
a TripleO-specific tool in comparison with ``cloud-init``, which, besides
being a mainstream way of bootstrapping instances in the cloud, understands
OpenStack network configuration metadata.

Alternatively to having operator supplying ramdisk network configuration
as a ``network_data.json`` file, Ironic can also accept the entire
``config-drive``. That would make it looking similar to instance booting (e.g.
Ironic provision state API) and would allow for passing more files to ramdisk
in the future.

Alternatively to wiring ``Glean`` schema validation into Ironic conductor,
operator can be asked to validate their ``network_data.json`` data with some
external tool prior to submitting it to Ironic. This would relax ironic
conductor dependency on ``Glean`` input requirements changes and ease
``network_data.json`` reuse for bootstrapping both ramdisk and instance.

Data model impact
-----------------

Add a new, user manageable, field ``network_data`` to ironic node object
conveying ramdisk network configuration information to ironic. If set,
the contents of this new field should be a well-formed ``network-data.json``
document describing network configuration of the node running ramdisk.

State Machine Impact
--------------------

None.

REST API impact
---------------

* Update ``GET /v1/nodes/detail``, ``GET /v1/nodes/{node_id}``,
  ``PATCH /v1/nodes/{node_id}`` to add new request/response fields

* ``network_data`` JSON object conveying network configuration.

Client (CLI) impact
-------------------

"ironic" CLI
++++++++++++

None

"openstack baremetal" CLI
+++++++++++++++++++++++++

* Update ``openstack baremetal node create`` and
  ``openstack baremetal node set`` commands to accept new argument
  ``--network-config <JSON>`` with help text describing JSON structure
  of the network configuration.

* Extend the output of the ``openstack baremetal node show``
  command with ``network_data`` column.

RPC API impact
--------------

None

Driver API impact
-----------------

* Extend ironic base NetworkInterface with ``get_node_network_config`` API
  call providing network configuration for the node being managed. Ironic will
  burn the output of this API call to the boot image served over virtual media.

* Implement ``get_node_network_config`` network interface call for non-Neutron
  networks providing ``network_data.json`` from ``network_data`` field of
  ironic object (if present). The operator could then implement their own IPAM
  (e.g. for stand-alone ironic use-case).

* Implement ``get_node_network_config`` network interface call for Neutron
  networks generating ``network_data.json`` based on Neutron port and subnet
  information [9]_.

* Make virtual media boot interfaces in ironic generating config-drive with
  ``network_data.json`` in it if ``network_data.json`` is not already passed
  to ironic with the config-drive.

* Make virtual media boot interfaces in ironic writing config-drive contents
  into root of bootable ISO image it generates on every node boot. Filesystem
  on this bootable ISO should be labeled ``config-2`` if it contains
  config-drive files.

Nova driver impact
------------------

None

Ramdisk impact
--------------

* Diskimage-builder tool should install ``Glean`` into ramdisk and invoke
  on boot.

  On top of that, the ``dhcp-all-interfaces`` DIB element might not be used
  anymore because ``Glean`` will run DHCP on all not explicitly configured
  (via ``config-drive``) interfaces [13]_.

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
    etingof (etingof@gmail.com)

Other contributors:
    None.

Work Items
----------

* Document ``Glean`` requirements, with regards to ``network_data.json``, in
  form of machine-readable JSON schema.

* Update ironic node model to include optional, user-specified
  ``network_data`` fields carrying ramdisk network configuration
  in form of ``network_data.json`` JSON document.

* Update REST API endpoints to support new ``network_data`` field

* Support new ``network_data`` fields in baremetal CLI (``openstack
  baremetal node ...``)

* Extend ironic base NetworkInterface with the ``get_node_network_config`` API
  call providing network configuration for the node being managed.

* Implement ``get_node_network_config`` network interface call for non-Neutron
  networks providing ``network_data.json`` from ``network_data`` field of
  ironic node object (if present).

* Implement ``get_node_network_config`` network interface call for Neutron
  networks generating ``network_data.json`` based on Neutron port and subnet
  information [9]_.

* Make virtual media boot interfaces in ironic generating ``config-drive`` with
  ``network_data.json`` on it.

* Make virtual media boot interfaces in ironic writing config-drive files into
  the root file system of the bootable ISO image it generates on every node
  boot. The file system should be labeled as ``config-2`` for ``Glean``
  to find and use it.

* Update ramdisk bootstrapping code to invoke ``Glean`` on system boot
  making use of ``network-data.json`` file if present on the ``config-drive``.

* Update diskimage-builder tool to control the inclusion and the options of
  the new static network configuration processing features.

* Create documentation on DHCP-less boot setup and work flow.

Dependencies
============

Ramdisk will start depending on ``Glean`` for processing ``network-data.json``
document.

Testing
=======

Tempest test of the ironic node deployment using operator-supplied and
Neutron-originated ``network_data.json``.

Upgrades and Backwards Compatibility
====================================

None.

Documentation Impact
====================

Use of L3 based deployment should be documented as part of this item.

References
==========

.. [1] https://networks.nokia.com/products/flexi-zone
.. [2] https://docs.openstack.org/nova/latest/user/metadata.html#config-drives
.. [3] https://cloudinit.readthedocs.io/en/latest/
.. [4] https://github.com/openstack/os-net-config
.. [8] https://specs.openstack.org/openstack/nova-specs/specs/liberty/implemented/metadata-service-network-info.html
.. [9] https://github.com/openstack/nova/blob/master/nova/virt/netutils.py#L60
.. [10] https://docs.openstack.org/nova/latest/user/metadata-service.html
.. [11] https://github.com/coreos/ignition/blob/master/doc/configuration-v3_0.md
.. [12] https://docs.openstack.org/infra/glean/
.. [13] https://opendev.org/opendev/glean/src/branch/master/glean/cmd.py#L323

