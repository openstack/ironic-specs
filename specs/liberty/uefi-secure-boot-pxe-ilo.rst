..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==================================================
UEFI Secure Boot support for pxe_iLO driver
==================================================

Include the URL of your launchpad blueprint:

https://blueprints.launchpad.net/ironic/+spec/uefi-secure-boot-pxe-ilo

As part of Kilo release UEFI secure boot support was enabled for all the iLO
drivers except pxe_ilo. It is important to have this feature supported for
pxe_ilo driver so that security sensitive users of pxe_ilo driver could deploy
more securely using Secure Boot feature of the UEFI. This spec proposes UEFI
Secure Boot support in baremetal provisioning for pxe_ilo driver.

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

This feature has been enabled for iscsi_ilo and agent_ilo driver during Kilo
release. It needs to be enabled for pxe_ilo driver. This needs pxe_ilo driver
should support signed UEFI bootloader for the nodes to boot in the UEFI secure
boot environment.

Proposed change
===============

This spec proposes to support UEFI secure boot for pxe_ilo driver and grub2 as
an alternate bootloader for UEFI deploy for PXE drivers.

Preparing the environment
-------------------------

* The operator informs the Ironic using the ``capabilities`` property of the
  node. The operator may add a new capability ``secure_boot=true`` in
  ``capabilities`` within ``properties`` of that node. This is an optional
  property that can be used if node needs to be provisioned for secure boot.
  By default the behavior would be as if this property is set to 'false'. The
  inspection feature in iLO drivers can auto discover secure boot capability
  of the node and create node capability into that node object.

* If the user has ``secure_boot`` capability set in the flavor, pxe_ilo has
  ability to change the boot mode to UEFI and prepare the node for the secure
  boot on the fly using proliantutils library calls.

* Even if the ``secure_boot`` capability is set to ``true`` in the node's
  ``properties/capabilities``, node can be used for normal non-secure boot
  deployments. Driver would use the ``secure_boot`` capability information from
  the node's ``instance_info`` field to provision node for UEFI secure boot.

Preparing flavor for secure boot
--------------------------------

* The ``extra_specs`` field in the nova flavor should be used to indicate
  secure boot. User will need to create a flavor by adding
  "capabilities:secure_boot="true" to it.

* iLO driver will not do secure boot if "secure_boot" capability flavor is
  not present or set to "False". Nova scheduler will use secure_boot
  capability as one of the node selection criteria if "secure_boot" is
  present in extra_spec. If "secure_boot" is not present in extra_spec then
  Nova scheduler will not consider "secure_boot" capability as a node
  selection criteria.

* Ironic virt Driver will pass the flavor capability information to the driver
  as part of 'instance_info'. Having capability information as part of
  'instance_info' would help driver in preparing and decommissioning the node
  appropriately. With respect to secure boot feature, this information would be
  used by pxe_ilo driver for:-

  * During provisioning, driver can turn on the secure boot capability to
    validate signatures of bootloaders and kernel.

  * During teardown, secure boot mode would be disabled on the node.

Preparing bootloader and deploy images
--------------------------------------

To support UEFI secure boot for pxe_ilo driver, pxe driver for Ironic should
support signed UEFI bootloader. Currently 'elilo' is the default UEFI
bootloader for all pxe drivers. Not all major linux distros ship signed 'elilo'
bootloader. They ship signed 'grub2' bootloader.

Enabling grub2 bootloader requires steps similar to elilo. Steps are:-

* Copy signed shim and grub2 bootloader files into tftproot directory as
  bootx64.efi and grubx64.efi respectively .

* Create a master grub.cfg file under /tftpboot/grub

* Contents of master grub.cfg would look something like this.
  set default=master
  set timeout=5
  set hidden_timeout_quiet=false

  menuentry "master" {
  configfile /tftpboot/$net_default_ip.conf
  }

  This master grub.cfg gets loaded first during PXE boot. It tells grub to
  refer to the node specific config file in tftproot directory configured for
  PXE. The name of config file is coined using DHCP IP address that would be
  allocated to the node. This is to ensure that multiple grub.cfg files could
  be created for parallel deploys. The contents of $net_default_ip.conf is
  dynamically filled by PXE driver using grub template file.

Ironic needs to support 'grub2' as an alternate UEFI bootloader for following
reasons:-

* No active development happening on 'elilo'

* All major linux distributions are supporting 'grub2' as a default UEFI
  bootloader.

* All major linux distributions provide signed 'grub2' bootloader which could
  be used in UEFI secure boot deploy with distro supplied cloud images.
  Otherwise users would need to build their own signed images for secure boot
  deploy.

* signed grub2 can be used for normal UEFI deploys as well.

All major linux distros ship their self signed 'grub2' and also provide
Microsoft UEFI CA signed shim bootloader. The shim bootloader contains the UEFI
signature of respective distros.

When node boots up using pxe, it loads Microsoft signed 'shim' boot loader
which in turn loads the distro signed 'grub2'. Distro signed 'grub2' can
validate and load the distro kernel.
Shim bootloader is required as it is signed using Microsoft UEFI CA signature
and recognizes corresponding linux vendors certificate as a valid certificate.
Secure boot enabled HP Proliant UEFI systems are pre-loaded with Microsoft UEFI
CA signatures.
User signed images can be supported but user need to manually configure
their keys to HP Proliant system ROM database using Proliant tools.

User can configure 'grub2' as a bootloader by changing the following existing
variables in /etc/ironic/ironic.conf under pxe section:
uefi_pxe_config_template
uefi_pxe_bootfile_name

Alternatives
------------

Add support for signed 'grub2' as a default UEFI bootloader in Ironic. But such
a change would have backward compatibility impact.

Data model impact
-----------------

None

State Machine Impact
--------------------

None

REST API impact
---------------

None

RPC API impact
--------------

None

Client (CLI) impact
-------------------
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
Currently pxe_ilo driver would support deploy and boot images having 'shim' and
'grub2' signed by Linux OS vendors.
If user wants to use custom signed images, then he would need to manually
configure their keys to UEFI using HP Proliant tools.
If user were to use an unsigned image for deploy with flavor requesting
UEFI secure boot, then deploy process would go through successfully, but
final boot into instance image would fail. The signature validation of
unsigned components would fail resulting in the failure of boot process. The
appropriate boot failure message would get displayed on Node's console.

Scalability impact
------------------

None

Performance Impact
------------------

There is no performance impact due to signature validation in secure boot.

Other deployer impact
---------------------

User can deploy only signed images with UEFI secure boot enabled.

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Shivanand Tendulker (stendulker@gmail.com)

Work Items
----------

1. Add support for grub2/shim as a alternate UEFI bootloaders for Ironic pxe
   driver.

2. Implement secure boot for pxe_ilo driver.

Dependencies
============

Signed user images.
The necessary DiskImageBuilder changes has been done to
build signed Ubuntu and Fedora images.

Testing
=======

Unit tests would be added for all newly added code.

Upgrades and Backwards Compatibility
====================================

None. grub2 would be alternate bootloader, which user can use only if it needs
UEFI secure boot functionality.

Documentation Impact
====================

Newly added functionality would be appropriately documented.

References
==========

1. UEFI specification http://www.uefi.org
2. Proliantutils module - https://pypi.python.org/pypi/proliantutils
3. HP UEFI System Utilities User Guide - http://www.hp.com/ctg/Manual/c04398276.pdf
4. Secure Boot for Linux on HP Proliant servers http://h20195.www2.hp.com/V2/getpdf.aspx/4AA5-4496ENW.pdf

