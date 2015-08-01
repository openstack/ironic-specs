..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

============================================
UEFI Secure Boot support for iLO drivers
============================================

https://blueprints.launchpad.net/ironic/+spec/uefi-secure-boot

Some of the Ironic deploy drivers support UEFI boot. It would be useful to
security sensitive users to deploy more securely using Secure Boot feature
of the UEFI. This spec proposes alternatives to support Secure Boot in
baremetal provisioning for iLO drivers.

Problem description
===================

Secure Boot is part of the UEFI specification (http://www.uefi.org). It helps
to make sure that node boots using only software that is trusted by Admin/End
user.

Secure Boot is different from TPM (Trusted Platform Module). TPM is a standard
for a secure cryptoprocessor, which is dedicated microprocessor designed to
secure hardware by integrating cryptographic keys into devices. Secure Boot is
part of UEFI specification, which can secure the boot process by preventing
the loading of drivers or OS loaders that are not signed with an acceptable
digital signature.

When the node starts with secure boot enabled, system firmware checks the
signature of each piece of boot software, including firmware drivers (Option
ROMs), boot loaders and the operating system. If the signatures are good,
the node boots, and the firmware gives control to the operating system.

The Admin and End users having security sensitivity with respect to baremetal
provisioning owing to the workloads they intend to run on the provisioned
nodes would be interested in using secure boot provided by UEFI.

Once secure boot is enabled for a node, it cannot boot using unsigned boot
images. Hence it is important to use signed bootloaders and kernel if node
were to be booted using secure boot.

Proposed change
===============

Preparing the environment
-------------------------

* The operator informs the Ironic using the ``capabilities`` property of the
  node. The operator may add a new capability ``secure_boot=True`` in
  ``capabilities`` within ``properties`` of that node. This is an optional
  property that can be used if node needs to be provisioned for secure boot.
  By default the behavior would be as if this property is set to False. The
  iLO hardware discovery feature (proposed) could auto discover the secure
  boot capability of the node and create node capability into that node object
  in future.

* If the user has ``secure_boot`` capability set in the flavor, iLO drivers
  have ability to change the boot mode to UEFI and prepare the node for the
  secure boot on the fly using proliantutil library calls.

Preparing flavor for secure boot
--------------------------------

* The ``extra_specs`` field in the nova flavor should be used to indicate
  secure boot. User will need to create a flavor by adding
  "capabilities:secure_boot="True" to it.

* iLO driver will not do secure boot if "secure_boot" capability flavor is
  not present or set to "False". Nova scheduler will use secure_boot
  capability as one of the node selection criteria if "secure_boot" is
  present in extra_spec. If "secure_boot" is not present in extra_spec then
  Nova scheduler will not consider "secure_boot" capability as a node
  selection criteria.

* Ironic virt Driver needs to pass the flavor capability information to the
  driver as part of instance info. Having capability information as part of
  instance info would help driver in preparing and decommissioning the node
  appropriately. With respect to secure boot feature, instance info should
  contain the capability info related to ``secure_boot``. This information
  would be used by iLO driver for :-

  * During provisioning, driver can turn on the secure boot capability to
     validate signatures of bootloaders and kernel.

  * During cleaning stage of teardown, clean_step could be added to initiate
    steps to clear the signatures, if any stored onto the node signature
    database.

Preparing boot and deploy images
--------------------------------

Disk Image builder changes are required to integrate signed shim and grub
bootloaders. shim bootloader is required as it is signed using Microsoft UEFI
CA signature and recognises corresponding linux vendors certificate as a valid
certificate. Secure boot enabled Proliant UEFI systems are pre-loaded with
Microsoft UEFI CA signatures.
User signed images can be supported but users needs to manually configure
their keys to system ROM database using Proliant tools.

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

This enhances security. Only correctly signed firmware, bootloader and OS can
be booted. It provides users with the opportunity to run the software of their
choice in the most secure manner.

Other end user impact
---------------------

Users need to use properly signed deploy and boot components.
Currently iLO driver would support deploy and boot images having shim and grub
signed by Linux OS vendors.
If user wants to use custom signed images, then he would need to manually
configure their keys to UEFI using Proliant tools.

Scalability impact
------------------

None

Performance Impact
------------------

There is no performance impact due to signature validation in secure boot.

Other deployer impact
---------------------

User can deploy only signed images with secure boot enabled. If the user wants
to use custom unsigned images for decommissioning then he would need to
disable secure boot on the node as part of clean_step during teardown stage
before booting into such custom images.

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

primary author and contact.

Primary assignee:
  Shivanand Tendulker (stendulker@gmail.com)

Work Items
----------

1. Implement code changes for supporting secure boot.

3. Implement secure boot iLO drivers.

4. Changes into Nova Virt Driver to pass capability information in the flavor
   as instance info. It is being proposed as part of following design spec.
   https://review.openstack.org/136104

Dependencies
============

1. DIB changes are required to add signed shim and grub2 to the ubuntu cloud
   image creation using disk-image-create and ramdisk-image-create scripts.

2. Changes in Nova Virt driver to pass capabality information from flavor to
   driver through instance info.

Testing
=======

Unit tests would be added for all newly added code.

Upgrades and Backwards Compatibility
====================================

None

Documentation Impact
====================

Newly added functionality would be appropriately documented.

References
==========

Discover node properties for iLO drivers
https://review.openstack.org/#/c/103007

Ironic Management Interfaces to support UEFI Secure Boot
https://review.openstack.org/#/c/135845

