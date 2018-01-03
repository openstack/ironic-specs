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

In the current scenario where RAID configuration on HPE Proliant servers is
done only via inband cleaning, Ilo5 based HPE Proliant Gen10 servers provide
support to perform out-of-band RAID configuration which was not there in Gen9
and below servers. However, the raid creation or deletion will take into effect
only when the system reaches POST stage. Hence, creation or deletion of RAID
needs to be accompanied by a reboot.

Proposed change
===============

This spec proposes to implement out-of-band RAID configuration as described
by the parent spec [1]. This will require the implementation of a new hardware
type ``Ilo5Hardware`` and a new raid interface for ilo as ``IloRAID``.

OOB RAID configuration will be a four step process.
1. delete_configuration - delete the current raid config from the system.
2. read_configuration - get the updated raid config from system and update
the node properties accordingly.
3. create_configuration - create the raid config which set by the user in
target_raid_config of node properties.
4. read_configuration - get the updated raid config from system and update
the node properties accordingly.

List of changes required:

* The following would be the composition of ``Ilo5Hardware``:

  + This hardware type would be supported on ilo5 based HPE Proliant servers.

  + Ilo5Hardware will inherit all interfaces of parent class IloHardware.

  + Ilo5Hardware will support the new RAID interface ``IloRAID``.

* The following would be the composition of ``IloRAID``:

  + IloRAID will inherit RAIDInterface of base class.

  + ``delete_configuration`` - This will delete the RAID configuration on
    the bare metal node.

    - Since a reboot is required for changes to get reflected, this function
      will be decorated with additional argument `reboot_required` with
      value set to `True`.

    - It will create an IloClient object from proliantutils library to do
      operations on the iLO. This will make call to delete_raid_configuration
      of proliantutils library to delete the logical drives on the system.

  + ``create_configuration`` - This will create the RAID configuration on
    the bare metal node.

    - Since a reboot is required for changes to get reflected, this function
      will be decorated with additional argument `reboot_required` with
      value set to `True`.

    - It will create an IloClient object from proliantutils library to do
      operations on the iLO. This will make call to create_raid_configuration
      of proliantutils library to place a request to firmware to create the
      logical drives on the system.

  + ``read_configuration`` - This will read the RAID configuration on
    the bare metal node.

    - It will create an IloClient object from proliantutils library to do
      operations on the iLO. This will make call to read_raid_configuration
      of proliantutils library to get the logical drives on the system.
      Hence, it will update the node properties with the actual RAID
      configuration when called after ``create_configuration`` and to ``None``
      when called after ``delete_configuration``.

* The following would be the updates required in cleaning architecture in
  ironic to support post reboot operation if required any clean step.

  + Addition a new boolean positional argument ``reboot_required`` to
    clean_step function of  BaseInterface. Default is set to ``False`` for
    this parameter.
    NOTE: The same approach is being used in inband cleaning for steps
    that require reboot.

  + Update ironic/conductor/manager.py:_do_next_clean_step() for each
    step to call prepare_cleaning() if reboot_required is set to True
    and result of the last command interface.execute_clean-step() is
    not ``clean wait``.

Alternatives
------------

One can perform in-band raid configuration to achieve the same result.
However, The ramdisk to be used in such case should have proliant-tools
element that bundles 'ssacli' utility required for RAID operations as
part of the image.

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

Support for OOB RAID in proliantutils is under development and is yet to be
released.


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
