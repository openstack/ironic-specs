..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Local boot support with partition images
==========================================

https://blueprints.launchpad.net/ironic/+spec/local-boot-support-with-partition-images

This blueprint proposes to accept the boot option specified by Nova
flavor and make the subsequent reboot of the baremetal from local hard
disk drive instead of pxe or vmedia, depending on the boot option selected
by the user.


Problem description
===================

At present Ironic drivers that deploy partition images require
Ironic-conductor for subsequent reboots of the node.  The subsequent
reboot of the node will happen either through pxe or using virtual
media. Also there is no way a Nova user can specify the boot option,
local/netboot for deploy using partition image.

Proposed change
===============

* Nova Ironic driver should read the specified boot option
  ``capabilities:boot_option`` flavor key which should be passed
  through ``node.instance_info`` field by Nova Ironic driver.

* Ironic will then pass this information to the deploy ramdisk via kernel
  cmdline in the PXE template, set the boot device to HDD persistently and
  clean up the PXE configuration files after the deployment is completed.

* The deploy ramdisk to check the parameter in the kernel cmdline and
  handle the bootloader installation.

.. note::
   For setting the local boot the images being deployed should have
   grub2 installed.

   Windows images won't be supported as part of this spec.

   Creating an EFI boot partition, including the EFI modules and managing
   the bootloader variables via efibootmgr won't be supported as part
   of this spec.

Alternatives
------------

* Use "localboot" element from Disk image builder:

  While generating the partition images using disk-image-builder, we can
  use "localboot" element, which is available in tripleo-image-elements
  project.  The downside of using this is that the local boot will be
  enabled during the first boot after node deploy. So it requires two
  resets of the server to enable localboot. Also the Ironic-conductor
  is not aware of this change and continue to provide the pxe or vmedia
  boot for the reboot operation done from conductor.

* Use whole disk image to achieve local boot:

  The other way to achieve a local boot is to use whole disk image
  for deploy.  Right now, this can be achieved by using agent driver only.

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

Nova Ironic driver need to pass down the ``capabilities:boot_option`` from
Nova flavor to Ironic ``node.instance_info`` field.

Security impact
---------------

Local boot is a double-edged problem. On one hand, in case of a
electricity outage the customer nodes that are configured to local boot
could potentially boot up before the control plane. On the other hand
if electricity outage causes the control plane to not boot after is also
a problem. So, this spec makes local boot and net boot configurable per
instance, deployers should be aware of that when deploying their clouds.

Other end user impact
---------------------

* Deployer can specify the boot option request in Nova
  flavor as capability.  ``capabilities:boot_option=local`` or
  ``capabilities:boot_option=netboot`` (default).

* Set ``boot_option``:``local`` or ``netboot`` as capability in
  node.properties.

Scalability impact
------------------

This can improve scalability by the fact that there will be less network
traffic not having to transfer a kernel and ramdisk over the network to
boot a node.

Performance Impact
------------------

None.

Other deployer impact
---------------------

* The image being deployed should have grub2 installed.

Developer impact
----------------

None.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  lucasagomes

Other contributors:
  faizan-barmawer

Work Items
----------

* Implement the code in Ironic that will check for the ``boot_option``
  parameter in the ``node.instance_info`` field. If set to "local" we have to:

  - Pass the information down to the deploy ramdisk via the kernel
    cmdline in the PXE configuration file.

  - Delete the PXE configuration files for that node after the deployment
    is completed.

  - Set the boot device to HDD persistently before the final reboot.

* Implement the code in the deploy ramdisk that will look at the parameter
  passed via the kernel cmdline and install the bootloader on the disk as
  part of the deployment.

Dependencies
============

* Require this Nova virt Ironic driver fix to pass down the capabilities from
  Nova flavor to Ironic node's instance info field.
  See https://review.openstack.org/141012

Testing
=======

* Unit testing.

Upgrades and Backwards Compatibility
====================================

None.

Documentation Impact
====================

* Make changes to Ironic install guide.

References
==========

* PoC patches:

  - Nova: https://review.openstack.org/146619

  - Ironic: https://review.openstack.org/146189

  - DIB: https://review.openstack.org/146097
