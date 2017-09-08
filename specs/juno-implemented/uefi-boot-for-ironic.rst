..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

======================================
UEFI support for Ironic deploy drivers
======================================

https://blueprints.launchpad.net/ironic/+spec/uefi-boot-for-ironic

This spec proposes to add support for UEFI based deployments on baremetal
nodes.

Problem description
===================
Most of the new hardware comes with UEFI boot mode, which has several technical
advantages over the traditional BIOS system.  The new servers  also have a
compatibility support module(CSM), which provides BIOS compatibility.

Currently there is no provision in Ironic to let a user select and deploy a
baremetal node having capability to boot in UEFI boot mode.

Proposed change
===============

Preparing the environment
-------------------------
1. The operator sets the baremetal node to boot in the desired mode - bios or
   uefi.

2. The operator can inform the boot mode to ironic using the ``capabilities``
   property of the node.  The operator may add a new capability
   ``boot_mode=uefi`` or ``boot_mode=bios`` in ``capabilities`` within
   ``properties`` of the node.

Preparing flavor for boot mode selection
----------------------------------------
The ``extra_specs`` field in the nova flavor may be used for selection of a
machine with the desired boot mode.  The operator may create a flavor with
``boot_mode=bios`` or ``boot_mode=uefi`` to select a baremetal node set to
exactly same ``boot_mode``.

If ``boot_mode`` is not present in ``extra_specs`` of nova flavor, then nova
scheduler may give a baremetal node configured in any boot mode.


Pxe deploy driver changes
-------------------------
Changes required in PXE deploy driver to perform UEFI boot mode deploy:

* Add new pxe config options:

  - ``uefi_pxe_bootfile_name``: specify the efi bootloader to be used.
  - ``uefi_pxe_config_template``: specify the respective efi bootloader config
    template.

* Prepare pxe config for UEFI, by reading ``uefi_pxe_bootfile_name`` and its
  corresponding ``uefi_pxe_config_template``.

  - As of now I will use elilo.efi boot loader.
  - elilo.efi bootloader requires the configuration to be named after
    the ip-address assigned by the DHCP server. It does not recognize
    mac-address named config files.

* Update neutron port DHCP extra opts with correct boot file for UEFI boot:

  - ``bootfile-name``: value should be fetched from ``uefi_pxe_bootfile_name``


Other deploy driver changes
---------------------------
Other deploy drivers may handle the uefi boot option in their deploy driver
code to support UEFI boot mode.

Some deploy drivers (like iLO driver which uses proliantutils library) will be
able to change the boot mode itself, rather than relying on admin to change
the boot mode.  Such deploy drivers may add functionality to change the boot
mode dynamically on a request.  Admin will just need to document the
``boot_mode`` that the machine is supposed to be used (Admin need not do
#1 in the section "Preparing the environment" above).

Overall flow
------------
1. Ironic virt driver picks up ``boot_mode`` (if available) from the
   ``capabilities`` field of the Ironic node and registers it as a capability
   of the hypervisor.  (*NOTE*: The functionality to do this is already
   available in the proposed nova-ironic virt driver).
2. User may select a flavor having ``boot_mode`` specified in its
   ``extra_specs``.
3. ``ComputeCapabilities`` filter of nova scheduler matches the ``boot_mode``
   (if available) against the ``boot_mode`` of the node.
4. The deploy driver reads the ``boot_mode`` from the ``capabilities`` property
   of the node and then makes appropriate changes to deploy process to deploy
   and boot the baremetal node in the required ``boot_mode``.

Alternatives
------------

* Pxe driver can support different efiboot loaders: syslinux.efi, grub, etc.

  - Different bootloaders will have different ways of preparing their
    configuration files.
  - Though pxelinux and syslinx.efi have same configuration changes, but
    syslinux.efi is not yet available on ubuntu 12/13/14. syslinux.efi is
    scheduled for ubuntu utopic release.
  - We will support only elilo.efi at the moment. We can later add support
    to other efi bootloader.

* There could be other vendor specific boot modes, or other boot options
  with-in BIOS/UEFI boot modes. We can support them incrementally on top of
  these standard boot modes.

* UEFI with local HDD boot:

  - As of now there is no support for local HDD boot with pxe driver.
  - When the deploy driver add support for local HDD boot with BIOS mode,
    they have to consider adding support for UEFI as well, if the driver
    support UEFI boot mode.

* Selecting a partition vs whole-disk image for deploy:

  - A partition image can be installed using both bios and UEFI boot mode,
    where as a whole-disk image may ask for a specific boot_mode for deploy.
  - With a partition image we need not specify the required boot_mode.
  - As of now pxe driver supports only partition images, when we add support
    for deploy with whole-disk image, we need to specify the required boot
    mode for that image and pass it on to deploy driver.

* Using IronicBootModeFilter to schedule both uefi and bios boot mode requests:

  - with "ComputeCapabilities" filter we can schedule predefined boot_mode
    on a node, which is capable of both uefi and bios boot modes. For example,
    if we set boot_mode:uefi in "capabilities" node property, on a node which
    is capable of both uefi and bios boot modes, then scheduler will not
    pick this node if user has specified "bios" in nova flavor.
  - With IronicBootMode filter, we can schedule both uefi and bios boot mode
    request on the same node which is capable of both boot_modes.


Data model impact
-----------------
None.

REST API impact
---------------
None.

Driver API impact
-----------------
None.

Nova driver impact
------------------
None.

Security impact
---------------
This feature will enable a later enhancement to support uefi secure boot.

Other end user impact
---------------------

* User can trigger a UEFI boot mode deploy by selecting a flavor with
  ``boot_mode`` in the ``extra_specs`` field.
* Ironic nodes should have additional properties to support UEFI based deploy.

Scalability impact
------------------
None.

Performance Impact
------------------
None.

Other deployer impact
---------------------

* Operator may to set the boot mode of baremetal node to the desired one
  manually.
* Operator may set a new capability ``boot_mode`` in ``capabilities`` within
  ``properties`` of the ironic node.  For example, the user may add
  ``capabilities:boot_mode=uefi`` for a baremetal node which is configured for
  uefi boot mode.
* Copy UEFI bootloader (elilo.efi) under tftp root directory.
* Set pxe configuration parameters: ``uefi_pxe_bootfile_name`` and
  ``uefi_pxe_config_template``

Developer impact
----------------
Other deploy drivers may handle the uefi boot option in their deploy driver
code to support UEFI boot mode.

Implementation
==============

Assignee(s)
-----------
Faizan Barmawer.

Work Items
----------
1. Implement the code changes for supporting uefi boot mode in pxe driver.
2. Other drivers can implement changes required to support UEFI mechanism.

Dependencies
============
None.

Testing
=======
Unit tests will be added for the code.

Documentation Impact
====================
Documentation should be modified to instruct admin to place efi bootloader in
tftp root and ironic node property updation.

References
==========
http://sourceforge.net/projects/elilo/
http://webapp5.rrz.uni-hamburg.de/SuSe-Dokumentation/packages/elilo/netbooting.txt
