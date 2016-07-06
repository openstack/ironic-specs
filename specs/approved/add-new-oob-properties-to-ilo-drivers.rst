..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Add more capabilities to ironic inspection
==========================================

https://bugs.launchpad.net/ironic/+bug/1599425

This spec adds a few more capabilities to ironic drivers.
The capabilities can be implemented in-band or out-of-band
as per driver maintainer's technical decision.

Problem description
===================

The operator may be interested to schedule and select the hardware
based on many other hardware properties like cpu_vt, trusted_boot,
etc.

Proposed change
===============

Following properties will be discovered::

    capability name: trusted_boot
    possible values: true|false
    explanation    : The hardware supports trusted boot or not.

    capability name: iscsi_boot
    possible values: true|false
    explanation    : The hardware supports iscsi boot or not.

    capability name : boot_mode_uefi
    possible values : true|false
    explanation     : The hardware supports uefi boot or not.
                      It is not the current boot mode. This
                      may not be discovered through inband
                      inspection.

    capability name : boot_mode_bios
    possible values : true|false
    explanation     : The hardware supports bios boot or not.
                      It is not the current boot mode.

    capability name : sriov_enabled
    possible values : true|false

    capability_name : has_ssd
    possible values : true|false

    capability_name : has_rotational
    possible_values : true|false

    capability name : rotational_drive_<rpm_value>_rpm
    possible values : true|false
    explanation     : The capabilities will turn out to be
                      rotational_drive_4800_rpm,
                      rotational_drive_5400_rpm,
                      rotational_drive_7200_rpm,
                      rotational_drive_10000_rpm, and
                      rotational_drive_15000_rpm. These
                      looks to be the only and standard values
                      for rotational drive rpms.

    capability name : logical_raid_level_<num>
    possible values : true|false
    explanation     : The capabilities ``logical_raid_level_<num>``
                      will have "num" as the dynamic number and
                      will have names as ``logical_raid_level_1``,
                      ``logical_raid_level_2``, and so on. There can
                      be multiple RAIDs configured on a hardware. This
                      gives flexibility to the operator to choose a
                      hardware which has the desired raid configured.
                      So if RAID level 1 is configured, the
                      variable becomes ``logical_raid_level_1`` set
                      to ``true``. if RAID level 5 is configured,
                      the variable becomes ``logical_raid_level_5``
                      set to ``true``. These capabilities would be
                      used only for scheduling, and ironic is
                      not supposed to create RAID level as per these
                      capabilities.
                      These capabilities should be added via RAID
                      interfaces also. These are added via inspection
                      as there can be baremetals added to ironic which
                      have RAID pre-configured.

    capability name : cpu_vt
    possible values : true|false

    capability name : hardware_supports_raid
    possible values : true|false

    capability name : boot_mode
    possible values : bios, uefi
    explanation     : This represents the deploy boot mode of
                      the system.

    capability name : has_nvme_ssd
    possible values : true|false

    capability name : persistent_memory
    possible values : true|false

    capability name : nvdimm_n
    possible values : true|false

    capability name : logical_nvdimm_n
    possible values : true|false

The other drivers/vendors may require the below list of capabilities.
These are already implemented by iLO drivers::

    capability name : <driver>_firmware_version
    possible values : varies from hardware to hardware
    explanation     : Here driver means ilo or irmc or any other
                      vendor. Hence the capability becomes
                      ilo_firmware_version or irmc_firmware_version.

    capability name : server_model
    possible values : varies from hardware to hardware.

    capability name : secure_boot
    possible values : true|false

    capability name : pci_gpu_devices
    possible values : count of total GPU devices.

    capability name : nic_capacity
    possible values : Maximum NIC capacity value with unit.

    capability name : rom_firmware_version
    possible values : vary from hardware to hardware.

Few which are already implemented by ironic-inspector::

    capability name : cpu_aes
    possible values : true|false

    capability name : cpu_txt

    capability name : cpu_hugepages

    capability name : cpu_hugepages_1g

These may not be part of capabilities specifically, but required to
be inspected. The ironic-inspector already inspects these properties::

    property name   : switch_id
    explanation     : Identifies a switch and can be a MAC address
                      or an OpenFlow-based ``datapath_id``

    property_name   : port_id
    explanation     : Port ID on the switch, for example, Gig0/1

    property_name   : switch_info
    explanation     : Used to distinguish different switch models
                      or other vendor-specific identifier.

``has_ssd`` and ``has_rotational`` are two different properties
as the hardware can have both kind of drives attached.

The capabilities ``boot_mode_*`` are added as a hardware could be
supporting both bios and uefi and the current capability ``boot_mode``
can accept only one value. The drivers would need to adjust the
deploy behaviour when the new capabilities ``boot_mode_bios`` or
``boot_mode_uefi`` are given in nova flavor. The changes required
in drivers for ``boot_mode_*`` capabilities is out of scope of
this spec.


Alternatives
-------------

Operator may need to manually configure the node with above properties for
nova scheduler to be able to select the desired node for deploy.

Data model impact
-----------------

None.

State Machine Impact
--------------------

None.

REST API impact
---------------

None.

Client (CLI) impact
-------------------

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

Ramdisk impact
--------------

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
  Nisha Agarwal <agarwalnisha1980>

Work Items
----------

* To add the above capabilities to the inspection.

Dependencies
============

None.

Testing
=======

* Test the drivers to return above properties after inspection is done.

Upgrades and Backwards Compatibility
====================================

None.

Documentation Impact
====================

Following will be documented:

- The new properties which would be added as part of this spec.

- The nova flavor samples how these properties can be used in creation
  of required nova flavors.

References
==========

None.
