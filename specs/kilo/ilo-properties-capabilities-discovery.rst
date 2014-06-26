..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=========================================================
Discover node properties and capabilities for iLO drivers
=========================================================

Blueprint URL:
https://blueprints.launchpad.net/ironic/+spec/ilo-properties-capabilities-discovery

This proposal adds the ability to introspect/update hardware properties
and auto-create ports for HP ProLiant servers via iLO using iLO client
python library i.e. proliantutils library as given in reference section.

Problem description
===================

The iLO driver is proposed to be used to discover node properties irrespective
of whether OS is deployed on baremetal node or not.

Proposed change
===============
Following mandatory properties will be discovered and updated to
node.properties as discussed in
https://github.com/openstack/ironic-specs/blob/master/specs/kilo/ironic-node-properties-discovery.rst

* memory size

* CPUs

* CPU architecture

* NIC(s) MAC address

* disks

The following additional properties are of interest to iLO drivers
and will be discovered and updated to node.properties as
capabilities:

* Supported Boot Modes

  capability name : supported_boot_mode
  possible values : bios, uefi, secure_boot

* iLO Firmware version

  capability name : ilo_firmware_version
  possible values : it can vary hardware to hardware.

* ROM Firmware version

  capability name : rom_firmware_version
  possible values : it can vary hardware to hardware.

* Server Name/Model

  capability name : server_model
  possible values : it can vary hardware to hardware.

* RAID level

  capability name : max_raid_level
  possible values : 0,1,2,3,4,5,6,10

* secure boot capability

  capability name : support_secure_boot
  possible values : True, False

* PCI (GPU) devices

  capability name : pci_gpu_devices
  possible values : count of such devices.

* SR-IOV capabilities

  capability name : sr_iov_devices
  possible values : count of such devices.

* NIC Capacity

  capability name : nic_capacity
  possible values : value with unit.

The properties which are already set will be overridden at
reinvocation of inspect_hardware(). If a property is not
applicable to the hardware or cannot be retrieved from the
hardware, the property will not be added/updated in
node.properties as capabilities. Even if the property cannot
be retrieved from the hardware due to some unknown reasons, the
introspection will not return failure as it is same as property
not applicable to the hardware.

iLO specific module changes:
----------------------------

* Implement the InspectInterface method inspect_hardware().

Alternatives
------------

These properties can be discovered manually outside the ironic and
node.properties updated accordingly with the discovered properties.

Data model impact
-----------------

None.

Ironic CLI impact
-----------------

None.

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
  agarwalnisha1980

Other Contributors:
  wan-yen-hsu

Work Items
----------

* Implementation of the InspectInterface class and
  its methods inspect_hardware(), validate() and get_properties().

Dependencies
============
* This feature is targeted for HP ProLiant servers with iLO4 and above.
  This module might work with older version of iLO (like iLO3), but this
  will not be officially tested by the iLO driver team.

* Depends on proliantutils library.

* Depends on following also:
  https://github.com/openstack/ironic-specs/blob/master/specs/kilo/ironic-node-properties-discovery.rst

Testing
=======

Unit tests will be added conforming to ironic testing requirements,
mocking proliantutils. It will get tested on real hardware by
iLO team with the hardware available to the team.

Upgrades and Backwards Compatibility
====================================

No impact.

Documentation Impact
====================

None.

References
==========

1. proliantUtils library.
(https://github.com/hpproliant/proliantutils)
(https://pypi.python.org/pypi/proliantutils)

2. Introspect spec.
https://github.com/openstack/ironic-specs/blob/master/specs/kilo/ironic-node-properties-discovery.rst
