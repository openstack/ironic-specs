..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

========================
Whole Disk Image Support
========================

https://blueprints.launchpad.net/ironic/+spec/whole-disk-image-support

This spec proposes to add a feature of deploying whole disk images to Ironic.

Problem description
===================

Currently, the Ironic PXE deploy driver and the iLO deploy driver
deploys only partition images making an Image kernel/ramdisk to be mandatory.
The current approach makes it impossible to deploy Images that are not capable
of providing a corresponding kernel/ramdisk. A significantly important use-case
would be to deploy Windows Images on baremetal systems.

Proposed change
===============

Ironic's deploy drivers will infer if they have to deploy a whole disk image
or a partition image based on the presence of a kernel/ramdisk by querying
Glance's properties.

To utilise the scheduler efficiently, Ironic deployments of whole disk images
will only accept a root-only flavor to efficiently utilise the entire disk.
Any other flavor type would be rejected during the validation phase in Ironic.
To help the scheduler fail fast, a new filter will be added to the scheduler
which will compare the image structure with the flavor attributes to check if
it can proceed with scheduling.

For the PXE Deploy driver, once the image structure is inferred and is found
out to be a whole disk image, the image is dumped onto the disk-lun and the
node is restarted with a pxe config file that instructs the server to
boot from the local disk(PXE-localboot).

The agent driver currently only supports deploying whole disk images, however,
the agent driver will adopt the inference pattern stated above to deploy whole
disk images.

The iLO virtual media iscsi deploy driver needs to be validated to deploy whole
disk images which will use the same mechanism the pxe driver uses to write
whole disk images.


Alternatives
------------

Having an optional is_whole_disk_image property explicitly for a Glance image
and using that value to figure out if the deploy driver should deploy a whole
disk image or not.

It was suggested that one could assume image type(i.e part or disk) based on
the image format. So, AMI for Partition images, QCOW2, RAW, etc for Disk
Images. This does not seem appropriate as the other image formats could
also very well be used as a Partition image with a certain Kernel/Ramdisk.

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

A separate Ironic-only Nova filter will be added which will validate flavor
attributes against image structure.

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

For those using disk-image-builder to build images, currently, the ``vm``
element should help in building of whole-disk-images.

Developer impact
----------------

The other deploy drivers need to keep in mind of the pattern being used
currently to infer deployment of whole disk images while writing their own
logic for the same feature.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  sirushtim

Work Items
----------

Modify PXE Deploy Driver to support deploying of whole disk images.

Modify Agent Deploy Driver to use the whole-disk-image inference pattern since
it already supports deploying of whole-disk-images by default.

Modify iLO virtual media Deploy Driver to support deploying of whole disk
images.

Add a Nova filter to validate image structure against flavor attributes.

Dependencies
============

None

Testing
=======

Tempest tests need to be added to validate deployment of Disk Images.

The Cirros whole disk image will be used to test the deployment of whole
disk images in Ironic.

Upgrades and Backwards Compatibility
====================================

None

Documentation Impact
====================

Add user-facing docs to explain how whole disk images should be deployed
via Ironic.

References
==========

https://etherpad.openstack.org/p/icehouse-ironic-windows-support
