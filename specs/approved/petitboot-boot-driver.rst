..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

======================
Petitboot boot driver
======================

https://bugs.launchpad.net/ironic/+bug/1526265

This adds petitboot boot driver for OpenPOWER servers. The OpenPOWER
Foundation is a collaboration around Power Architecture products initiated by
IBM.

Problem description
===================

OpenPOWER servers use FSP (flexible service processor) to initialize the system
chip and monitor the other hardware components. FSP can be set to OPAL
(Open Power Abstract Layer) mode to handle the IPMI operation. The firmware on
OpenPOWER servers use petitboot as a platform independent bootloader.
Petitboot can load kernel, initrd and device tree files from any Linux
mountable filesystem, plus can load files from the network using the FTP,
SFTP, TFTP, NFS, HTTP and HTTPS protocols.

Petitboot is very similar to the standard pxe behaviour, but a little
difference, like:

    * Petitboot will be loaded every time no matter what the boot device is.
    * Petitboot will check the system configuration like boot device in the
      firmware and will not download any netboot loader, as itself can be
      worked as a netboot loader.
    * If boot device is hard disk, petitboot will scan boot or prep partition
      to load the boot option from the local boot loader, for example grub2,
      then let grub2 load the system.
    * If boot device is network, petitboot will look for PXE configuration
      file (209) option in the dhcp response. If no explicit configuration file
      is given, then petitboot will attempt ``pxelinux-style`` configuration
      auto-discovery, using the machine's MAC address, the IP of the DHCP
      lease, and fall back to a file named default.
    * Petitboot requests images from network according to the path information
      in the configuration file, then use kexec to load the system. So both the
      deploy system and the instance system should support boot from kexec when
      the boot device is network.
    * The format of petitboot configuration file for netboot is different from
      the ``pxelinux.cfg`` and more kernel command parameters about network
      should be passed.

Proposed change
===============

* Add ``iscsi_opc`` and ``agent_opc`` drivers. ``opc`` means OpenPOWER
  controller which use petitboot driver as the boot driver and ipminative
  driver as the hardware control driver. For example, the iscsi_opc driver will
  look like this ::

    class OpenPOWERIscsiAndIPMINativeDriver(base.BaseDriver):
    """Petitboot + Iscsi + IPMINative driver"""
      def __init__(self):
        self.power = ipminative.NativeIPMIPower()
        self.console = ipminative.NativeIPMIShellinaboxConsole()
        self.boot = petitboot.PetitbootBoot()
        self.deploy = iscsi_deploy.ISCSIDeploy()
        self.management = ipminative.NativeIPMIManagement()
        self.vendor = iscsi_deploy.VendorPassthru()
        self.inspect = inspector.Inspector.create_if_enabled(
            'OpenPOWERIscsiAndIPMINativeDriver')

* Add configuration option for petitboot driver in ironic.conf ::

    [petitboot]
    config_template: template path for petitboot configuration.
    protocol: string value for the transfer protocol, only support http and
              tftp in this spec, default http.

* Add Petitboot driver inherits base.BootInterface and implements the following
  functions.

  * ``validate()`` - Check boot option and image type. In this spec, OpenPOWER
    machine only support local boot with whole disk image and netboot with
    partition images.

  * ``get_properties`` - In this spec, return common properties which are as
    same as the properties of pxe driver.

  * ``prepare_ramdisk()`` - Petitboot driver will update the dhcp option, build
    the configuration file for the petitboot netboot loader, then set the boot
    device to network. This procedure is similar to the pxe driver, but a
    little difference.

    - Petitboot do not need NBP file, so petitboot driver will not pass
      ``bootfile-name`` (67) option to dhcp. Petitboot driver will use PXE
      configuration file (209) option and PXE path prefix (210) option to
      locate the configuration file. Petitboot will concatenate these values to
      generate the file transfer request. The value of 209 option is the
      relative file path like ``<node_uuid>/config``. The value of 210 option
      depends on the ``protocol`` configuration in the petitboot section.

      - If it is tftp, the value of 210 option is ``CONF.deploy.tftp_root``
      - If it is http, the value of 210 option is ``CONF.deploy.http_url``.

    - Petitboot driver will manage this configuration file which contains the
      path information for the kernel and ramdisk. The format of the
      configuration file is like ::

        default deploy

        label deploy
        kernel ``{{ [petitboot_url]/<node_uuid>/deploy_kernel }}``
        initrd ``{{ [petitboot_url]/<node_uuid>/deploy_ramdisk }}``
        append ``{{ parameter }}``

  * ``clean_up_ramdisk()`` - Cleans up the environment that was setup for
    booting the deploy system. It unlinks the deploy kernel/ramdisk.

  * ``prepare_instance()`` - This method is very similar to the pxe driver.

    - If boot option is local, just clean up the petitboot configuration file.
    - If boot option is network, update the petitboot configuration file to
      boot the instance image.

  * ``clean_up_instance()`` - Cleans up the environment that was setup for
    booting the instance. It unlinks the instance kernel/ramdisk and removes
    the petitboot config.

Alternatives
------------
None

Data model impact
-----------------
None

RPC API impact
--------------
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

Driver API impact
-----------------
None

Nova driver impact
------------------
None

Ramdisk impact
--------------

A ramdisk capable of running on PPC64 hardware will need to be built, however,
this may be done downstream.

Support should be added to ramdisk build tooling, such as
``disk-image-builder`` and ``coreos-image-builder``, to build such ramdisks.

.. NOTE: This section was not present at the time this spec was approved.


Security impact
---------------
None

Other end user impact
---------------------
To use petitboot driver for the OpenPOWER servers, the ``cpu_arch`` in driver
properties should be ppc64le or ppc64 which depends on the cpu architecture of
instance image. OpenPOWER servers can switch to the appropriate endian format
according to the endian format of kernel image. Both the deploy kernel and the
instance kernel should support boot from kexec when local boot is not enabled.

Scalability impact
------------------
None

Performance Impact
------------------
None

Other deployer impact
---------------------
New config options ::

  [petitboot]
  config_template: template path for petitboot configuration.
  protocol: string value for the transfer protocol, only support http
            and tftp in this spec, default http.

Developer impact
----------------
None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  chenglch <chenglch@cn.ibm.com>

Other contributors:
  baiyuan <bybai@cn.ibm.com>

Work Items
----------

* Implement petitboot boot driver.
* Add ``iscsi_opc`` and ``agent_opc`` drivers to manage the OpenPOWER servers.
* Write unit-test cases.
* Write configuration documents.

Dependencies
============
None

Testing
=======

* Unit Tests
* Third-party CI Tests: We have plan to build 3rd-party CI for this driver,
  but do not have sufficient hardware available at this time.

Upgrades and Backwards Compatibility
====================================
This driver will not break any compatibility with either on REST API or RPC
APIs.

Documentation Impact
====================

Writing documents to instruct operators how to use Ironic with petitboot
driver.


References
==========

* `OpenPOWER <http://openpowerfoundation.org>`_
* `petitboot <https://www.kernel.org/pub/linux/kernel/people/geoff/petitboot/petitboot.html>`_
* `Netbooting with petitboot <http://jk.ozlabs.org/blog/post/158/netbooting-petitboot>`_
