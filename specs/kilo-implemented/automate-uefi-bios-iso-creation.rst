..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
automate-uefi-bios-iso-creation
==========================================

https://blueprints.launchpad.net/ironic/+spec/automate-uefi-bios-iso-creation

This spec proposes to add support creation of dual(bios+uefi)
boot ISO automatically.

Problem description
===================
Today, a dual-mode boot ISO has to be created manually, uploaded to Glance,
and associated with the instance image in Glance by setting its "boot_iso"
image property. The deploy image can be modified using GRUB on runtime.
This is required by the iscsi_ilo driver to enable UEFI boot mode.

Proposed change
===============

This spec proposes to use GRUB to create the dual-mode boot ISO on the
fly in ironic/common/images.py. This image will be uploaded to swift and
associated with the node for which it was created, and will not be shared
between instances, even when using the same instance image. When the instance
is deleted, the boot_iso file is deleted from swift.
The steps would be as follows:

1. Create isolinux config file.

2. Create the grub config files.

3. Create the bootx64.efi.

4. create vfat image efiboot.img

5. Create ISO using mkisofs with the following options
   added "-eltorito-alt-boot -e isolinux/efiboot.img" to existing syntax.

6. The boot iso is created by the driver and uploaded at the swift container.

when node is torn down, the boot iso is deleted by the driver.

Alternatives
------------

To boot up in UEFI mode, the deployer can create the ISO manually using
disk-image-builder utility disk-image-create and upload on glance.

Data model impact
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

The boot iso can be created and uploaded to the swift on the fly
when deploy is invoked for iscsi_ilo driver i.e. current manual step
for updating the deploy image with the boot iso will not be required
after the enhancement.

Developer impact
----------------

None.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  agarwalnisha1980

Work Items
----------

In /opt/stack/ironic/ironic/common/images.py file,

* To create the conf file for UEFI

* To enhance the function create_isolinux_image() for creating UEFI
  capable ISO.

* To remove the check in /opt/stack/ironic/ironic/drivers/modules/ilo/deploy.py
  for erroring out when the deploy image doesn't has the boot_iso uuid updated.

Dependencies
============

None.

Testing
=======

The unit tests will be added/updated as required for the code.

Upgrades and Backwards Compatibility
====================================

The iscsi_ilo driver will support both the manual and automated
boot iso methods. By default, if the image already has the "boot_iso"
property populated, the driver will consume the boot_iso from it.

Documentation Impact
====================

None.

References
==========

None.
