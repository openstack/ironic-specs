..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=======================================================================
Out-of-band RAID configuration for Gen10 and above HPE Proliant Servers
=======================================================================

https://bugs.launchpad.net/ironic/+bug/1716329

This specification proposes implementation of out-of-band RAID configuration
for ILO managed HPE Proliant servers.

Problem description
===================

Ilo5 based HPE Proliant Gen10 servers provide support to perform out-of-band
RAID configuration which was not there in Gen9 and below servers.

Proposed change
===============

This spec proposes to implement out-of-band RAID configuration as described
by the parent spec [1]. This will require the implementation of a new hardware
type ``Ilo5Hardware`` and a new raid interface for ilo as ``IloRAID``.

List of changes required:

* The following would be the composition of ``Ilo5Hardware``:

  + This hardware type would be supported on ilo5 based HPE Proliant servers.

  + Ilo5Hardware will inherit all interfaces of parent class IloHardware.

  + Ilo5Hardware will support the new interface ``IloRAID``.

* The following would be the composition of ``IloRAID``:

  + IloRAID will inherit RAIDInterface of base class.

  + ``create_configuration`` - This will create the RAID configuration on
    the bare metal node.

    - It will create an IloClient object from proliantutils library to do
      operations on the iLO. This will make call to create_raid_configuration
      of proliantutils library to create the logical drives on the system.

  + ``delete_configuration`` - This will delete the RAID configuration on
    the bare metal node.

    - It will create an IloClient object from proliantutils library to do
      operations on the iLO. This will make call to delete_raid_configuration
      of proliantutils library to delete the logical drives on the system.

  + ``_create_configuration_final`` - This will be called after the clean
    step ``IloRAID.create_configuration`` is completed. This method will call
    ``update_raid_info`` with the actual RAID configuration returned by ilo
    object.

  + ``_delete_configuration_final`` - This will be called after
    ``IloRAID.delete_configuration`` is completed. This will set
    ``node.raid_config`` to ``None``.

Alternatives
------------

One can perform in-band raid configuration to achieve the same result.
However, The ramdisk to be used in such case should have proliant-tools
element as part of the image.

Data model impact
-----------------
None

State Machine Impact
--------------------
None

REST API impact
---------------
None

Client (CLI) impact
-------------------
None

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
None

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

User need to configure below two things to make use of OOB RAID configuration
on HPE Proliant Gen10 servers.

* Configure the new hardware type ``ilo5`` to ([DEFAULT]
  ``enabled_hardware_types``).

* Configure the new raid interface ``ilo5`` to ([DEFAULT]
  ``enabled_raid_interfaces``).


Developer impact
----------------
None


Implementation
==============

Assignee(s)
-----------

Primary assignee:
theanshuljain

Work Items
----------

* Add a new hardware type for ilo ``Ilo5Hardware`` which inherits IloHardware.
* Add a new hardware interface ``IloRAID`` which inherits base.RAIDInterface.
* Writing unit-test cases for the new OOB RAID interface.


Dependencies
============

The current proliantutils version 2.4.1 does not support OOB Raid. It is under
development and will be supported in the coming release.


Testing
=======

Unit test cases will be added. Will be tested in 3rd party CI setup.

Upgrades and Backwards Compatibility
====================================

None


Documentation Impact
====================

Need to update iLO driver documentation for new hardware type and RAID
interface.


References
==========

[1] Ironic generic raid spec: https://review.openstack.org/173214
