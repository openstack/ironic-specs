..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

========================================
Override PXE options via Glance property
========================================

https://bugs.launchpad.net/ironic/+bug/1526409

The proposal presents the work required to allow PXE boot an image using
a specific kernel command line for that image.

Problem description
===================

Some images requires having specific kernel command line to boot
correctly. Currently, Ironic tries to determine things like the root
filesystem the image is on ("root=" kernel command line) by getting the
UUID of the image filesystem and setting as the root= parameter. This is
not correct for all images because some may need to boot from a different
root filesystem, e.g:

 * The device path of its LVM volume [root=/dev/mapper/vg-lv_root]
 * From one squashfs filesystem [root=live:<path>]
 * A btrfs subvolume [root=/dev/disk/by-uuid/<UUID of btrfs-root>]

As a real example, the Fedora Atomic uses ``lvm`` and ``ostree``. It
requires a kernel command line as the example below to boot properly::

  nofb nomodeset vga=normal console=tty1 no_timer_check
  rd.lvm.lv=atomicos/root root=/dev/mapper/atomicos-root
  ostree=/ostree/boot.0/fedora-atomic/a002a2c2e44240db614e09e82c/0

Proposed change
===============

In the same way Ironic look at the Glance image properties to find out the
Glance UUID for the image's kernel and ramdisk (kernel_id and ramdisk_id)
and populate the node's ``instance_info`` field with the ``kernel`` and
``ramdisk`` keys.

This spec propose having a new image's property field called
``kernel_cmdline`` that Ironic will look at, and if present, it will
populate the node's ``instance_info`` field with a ``kernel_cmdline``
key.

If the ``instance_info.kernel_cmdline`` is populate Ironic will skip
getting the root partition filesystem UUID and will use the command
line from the ``instance_info`` field instead of the default one in
the template. It's important to note that the values present at the
``pxe_append_params`` configuration option will still be appended at
the end of the image's custom kernel command line by Ironic.

Setting the keys in the ``instance_info`` field is important because
it also allows Ironic to operate in standalone mode without Glance.

Alternatives
------------
Always use whole disk images when deploying images that requires a
specific kernel command line

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

N/A

.. NOTE: This section was not present at the time this spec was approved.

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

Deployers that wants to deploy an image with a specific kernel command
line should know and set it in Glance image's property prior to trying
to boot the image.

Developer impact
----------------
None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  lucasagomes <lucasagomes@gmail.com>

Other contributors:
  None

Work Items
----------

* Make Ironic look at the ``kernel_cmdline`` image property in Glance
  and if present set it to the node's ``instance_info`` field

* When preparing to boot the user's image, make Ironic check if the
  node's ``instance_info`` field contains a key called ``kernel_cmdline``
  (along with ``kernel_id`` and ``ramdisk_id``) and if so, use that kernel
  command line to boot the image.

Dependencies
============
None

Testing
=======

* Unit Tests

Upgrades and Backwards Compatibility
====================================
None

Documentation Impact
====================

The Ironic deploy documentation will be updated to reflect the changes
made by this spec.

References
==========

* `Kernel parameters <https://www.kernel.org/doc/Documentation/kernel-parameters.txt>`_

* `Project atomic <http://www.projectatomic.io>`_
