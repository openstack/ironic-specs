..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=============================================
Implement Cleaning Operations for iLO drivers
=============================================

https://blueprints.launchpad.net/ironic/+spec/ilo-cleaning-support

This spec proposes to support certain functionalities to be invoked as part of
Cleaning process through iLO drivers to manage HP Proliant nodes.

Problem description
===================

The spec 'Implement Cleaning States' [1] provides a framework to invoke certain
actions as part of cleaning process. Some of these operations could be hardware
dependent and could be supported out-of-band via iLO.

So, iLO Drivers should be able to support Proliant specific cleaning
operations.

Proposed change
===============

* Add the following functions to IloManagement Interface and decorate the same
  using @clean_step(priority)

  - ilo_reset()
        Reset iLO.
  - apply_base_firmware_settings()
        To apply base firmware settings.
  - reset_ilo_credential()
        reset bmc password to the new one.
        This can be useful for the environments, where operator wants to
        refresh the password for the new workload.
  - reset_secure_boot_keys()
        To reset the secure boot keys to manufacturer's defaults.
        (Applicable if secure boot feature is supported for ironic drivers)
  - clear_secure_boot_keys()
        To clear secure boot keys
        (Applicable if secure boot feature is supported for ironic drivers)


* The suggested default ordering would be -
        reset_ilo_credential()          9
        reset_secure_boot_keys()        8
        apply_base_firmware_settings()  7
        ilo_reset()                     6

* The priority of clear_secure_boot_keys() by default would be zero, operator
  would have option to choose either reset_secure_boot_keys or
  clear_secure_boot_keys(to reset to manufacturer's defaults or clear all keys)

* ``proliantutils`` [2] library will be used for performing out-of-band
  operations like reset_bmc_credential, ilo_reset,
  apply_base_firmware_settings, reset_secure_boot_keys, clear_secure_boot_keys.

* New CONF variable 'CONF.ilo.base_firmware_settings' would be added, which
  takes the default settings to be applied on cleanup of every node.

* secure_disk_erase, update_firmware will be implemented via in-band mechanism.
  Tools like hdparm, shred are being explored for disk erase and hpsum ,
  smart component executables are being explored for the firmware update.

* Parameters required for cleaning operations need to be passed via driver_info
  with appropriate keys.

  eg: Following are the mandatory parameter keys required by the clean steps -
      1. ``upgrade_firmware`` - ``ilo_firmware_location_url`` key,
         which can accept the http location url or swift url for the tar/gz
         file of all the firmwares to be updated.

      2. ``reset_ilo_credential`` - ``ilo_change_password``, which accepts the
         default iLO password to be changed during cleaning.

* If the keys are missing and if the respective clean step is enabled, warning
  message will be logged and the step will be no-op and continue with other
  clean steps.

Alternatives
------------
None

Data model impact
-----------------
None

REST API impact
---------------
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

Security impact
---------------
Security is enhanced by performing some of the cleaning tasks like secure
disk erase, iLO password reset etc.

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
* Deployer might need to build the IPA ramdisk with HP specific tools.
* DIB element will be enhanced to add ProLiant specific cleaning tools for
  deploy ramdisk. Deployer can use the enhanced DIB element to build the
  ramdisk.

Developer impact
----------------
None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
   ramineni

Work Items
----------
Implement the functions that can be invoked during cleaning.

Dependencies
============
Depends on https://review.openstack.org/#/c/102685/ for the framework to
perform cleaning.

Testing
=======
Unit tests will be added mocking proliantutils library.

Upgrades and Backwards Compatibility
====================================
None

Documentation Impact
====================
* Supported firmware settings will be documented.
* Parameter keys required for certain clean operations will be documented.
* Creating deploy ramdisk with HP Specific tools will be documented.

References
==========
[1] Implement cleaning states - https://review.openstack.org/#/c/102685/

[2] proliantutils - https://github.com/hpproliant/proliantutils
