..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=========================================================
Discover node properties and capabilities for ucs drivers
=========================================================

https://bugs.launchpad.net/ironic/+bug/1526359

This proposal adds the ability to inspect/update hardware properties and
auto-create ports for Cisco UCS B/C/M-servers managed by Cisco UCS Manager.
It uses out-of-band H/W inspection utility provided by UcsSdk.

Problem description
===================

Node inspection automatically collects node properties. These properties are
required for scheduling or for deploy (ports creation). Today UCS drivers
doesn't support node inspection. Enhance UCS drivers to support node
inspection.

Proposed change
===============
This spec proposes change to enhance UCS drivers to support node inspection
that discovers node properties and capabilities of Cisco UCS B/C/M-series
servers managed by Cisco UCSM. This is done by using out-of-band H/W inspection
interface provided by UcsSdk Python library.

The following mandatory properties will be discovered and updated in
node.properties as discussed in
http://specs.openstack.org/openstack/ironic-specs/specs/kilo/ironic-node-properties-discovery.html

* memory size

* CPUs

* CPU architecture

* NIC(s) MAC address

* disks

The following additional properties are of interest to UCS drivers
and will be discovered and updated to node.properties as
capabilities:

* UCS Host Firmware pack

  capability name : ucs_host_firmware_package
  possible values : it can vary hardware to hardware.

* Server Name/Model

  capability name : server_model
  possible values : it can vary hardware to hardware.

* RAID level

  capability name : max_raid_level
  possible values : 0,1,5,6,10

* secure boot capability

  capability name : secure_boot
  possible values : true, false

* PCI (GPU) devices

  capability name : pci_gpu_devices
  possible values : count of such devices.

* SR-IOV capabilities

  capability name : sr_iov_devices
  possible values : count of such devices.

* NIC Capacity

  capability name : nic_capacity
  possible values : value with unit.

* TPM Support

  capability name : trusted_boot
  possible values : true, false

* Multi LUN support

  capability name : multi_lun
  possible values : true, false

* CDN (Consistent Device Name) Support

  capability name : cdn
  possible values : true, false

* VXLAN Capability

  capability name : vxlan
  possible values : true, false

* NV GRE Capability

  capability name : nv_gre_devices
  possible values : count of such devices

* NET FLOW Capability

  capability name : supports_net_flow
  possible values : true, false

* FlexFlash Capability

  capability name : flex_flash
  possible values : true, false

* UCS service-profile template name

  capability name : ucs_sp_template
  possible values : service profile template name


The properties which are already set will be overridden at reinvocation of
inspect_hardware() except for NICs. If a port already exists, it will not
create a new port for that MAC address. It will take care of adding as well as
deleting of the ports for NIC changes [2].
Not all the capabilities are applicable to all Cisco UCS B/C/M-series server
models. If a property is not applicable to the hardware, the property will not
be added/updated in node.properties as capabilities. Inspection fetches only
those capabilities applicable to the specific server model.

Inspection returns failure in the following cases:
    * Failed to get basic properties.
    * Failed to get capabilities, due to service-profile configuration errors.
    * Communication errors with UCS Manager.

UCS specific module changes:
----------------------------

* Implement the InspectInterface method inspect_hardware().

Alternatives
------------

These properties can be discovered manually outside the ironic and
node.properties updated accordingly with the discovered properties.

Data model impact
-----------------

None.

State Machine Impact
--------------------

None

REST API impact
---------------

None.

Client (CLI) impact
-------------------
None

RPC API impact
--------------

None.

Driver API impact
-----------------

None.

Nova driver impact
------------------

None.

Ramdisk impact
--------------

N/A

.. NOTE: This section was not present at the time this spec was approved.

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
  saripurigopi

Work Items
----------

* Implementation of the InspectInterface class and
  its methods inspect_hardware(), validate() and get_properties().

Dependencies
============
* This feature is targeted for Cisco UCS B/C/M-series servers managed by
  UCS Manager 2.2(4b) or above. All the capabilities listed might not be
  available with older versions of UCS Manager (like 2.2(3b)).

* Depends on UcsSdk library.

Testing
=======

Unit tests will be added conforming to ironic testing requirements, mocking
UcsSdk. It will get tested on real hardware by UCS team with the available
hardware models to the team.

Upgrades and Backwards Compatibility
====================================

No impact.

Documentation Impact
====================

'Hardware Inspection' section will be added and updated accordingly in
doc/source/drivers/ucs.rst.

References
==========

1. UcsSdk library:
* https://github.com/CiscoUCS/UcsSdk
* https://pypi.org/project/UcsSdk

2. Introspect spec:
* https://github.com/openstack/ironic-specs/blob/master/specs/kilo/ironic-node-properties-discovery.rst
