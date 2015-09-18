..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=====================================
iLO Virtual Media iSCSI Deploy Driver
=====================================

https://blueprints.launchpad.net/ironic/+spec/ironic-ilo-virtualmedia-driver

Add ability to provision proliant baremetal nodes (having iLO4 and beyond)
by booting the baremetal node with virtual media and using iscsi from conductor
node to deploy the image (reusing existing deploy mechanism).

Problem description
===================

- Today Ironic's PXE reference driver uses pxe protocol to boot the machine.
  Some customer's don't prefer PXE protocol in their environment because of
  it unreliability and security issues.
- Today Ironic's PXE reference driver passes the keystone authentication token
  in clear text over tftp on the data network to the baremetal node.

Proposed change
===============

The proposed change for Ironic deploy will happen in two stages:

* Refactor the iSCSI deploy code in current pxe deploy driver into a new module
  ironic/drivers/modules/iscsi_deploy.py so that it can be reused in a new
  deploy driver.

* Add two new methods ``create_vfat_image`` and ``create_iso_image``  in
  ironic/common/images.py for creating vfat images and iso images respectively.
  The vfat images will be used for passing the token and parameters to the
  ramdisk when it is booted over virtual media.  The ISO image will be used for
  booting up the kernel/ramdisk on the baremetal machine.

* Add a new module ironic/common/swift.py to manage objects in swift.

* Add two generic methods ``setup_virtual_media_boot`` and
  ``cleanup_virtual_media__boot`` which helps in setting up and cleanup up
  virtual media for booting respectively.

* Create a new deploy module named ``IloVirtualMediaIscsiDeploy`` in
  ironic/drivers/modules/ilo/deploy.py which adheres to
  ``base.DeployInterface``.

* Create a new class ``VendorPassthru`` which adheres to
  ``base.VendorInterface`` in ironic/drivers/modules/ilo/deploy.py.
  Implement a vendor passthru method ``pass_deploy_info`` in it.

* The reboot() method in ``IloPower`` module will be changed.


Changes in Detail
-----------------

Virtual media for booting
-------------------------
This class exposes the following methods:

setup_virtual_media_boot()
^^^^^^^^^^^^^^^^^^^^^^^^^^

- Validate that the node's iLO has virtual media feature enabled using
  proliantutils module.  If the node doesn't have virtual media feature, it
  comes out with error.
- If ``boot_parameters`` is not empty:

  - Create a virtual floppy image containing the user token and a config
    file, which contains ``boot_parameters``.
  - Upload the virtual floppy image to swift.  Set ``X-Delete-After`` for swift
    to delete the image after ``deploy_helper_images_ttl`` minutes. The default
    value will be 10 minutes. Upload to container ``swift_ilo_container`` whose
    default value will be "ironic_ilo_container".
  - Generate the swift temp url for virtual floppy image. Let it be named as
    floppy_image_temp_url. The timeout of tmpurl will be
    ``deploy_helper_images_ttl`` minutes.
  - Attach floppy_image_temp_url as virtual media floppy in the iLO.  Set the
    timeout to ``deploy_helper_images_ttl``
- Generate tmpurl for ``boot_iso`` and attach it as virtual media cdrom. The
  timeout of tmpurl will be ``deploy_helper_images_ttl`` minutes.
- Set the baremetal node to boot from virtual media cdrom for the next boot
  using proliantutils module with BOOT_ONCE option.

cleanup_virtual_media_boot()
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Remove the virtual media floppy image uploaded to swift for the node. The
  object name in swift will be "image-<node uuid>"

ironic/common/swift.py
----------------------
This module will provide a class SwiftAPI which will handle the creation
and managing swift objects.  This SwiftAPI module by default will use admin
credentials for talking to swift. The user of this module may also choose to
pass ``user``, ``tenant_name``, ``key``, ``authurl`` to create the swiftAPI
object.

- *upload_object* - Creates the container if required and requested, and
  then creates the new object in swift using swiftclient.  Returns the swift
  object id.
- *delete_object* - Deletes the object from the mentioned swift container.
- *get_tmp_url* - This will call the ``swift_utils.generate_temp_url()`` which
  is available in python-swiftclient.


ironic/common/images.py
-----------------------
Add a new method ``create_vfat_image`` which helps in creating
virtual floppy images. This method takes the files and parameters to be
included in the floppy image as input, and then creates a vfat floppy image.

Add a new method ``create_iso_image`` which helpsin creating ISO images.
This method takes the files and parameters to be included in the ISO as input,
and then creates the ISO image.

The common components between the two methods above will be reused.

ironic/drivers/modules/iscsi_deploy.py
--------------------------------------
This module will refactor every method belonging to the iscsi deploy mechanism
from the pxe driver.  The following methods will be moved to the new module:

- parse_instance_info()
- _cache_instance_image
- InstanceImageCache
- _check_image_size
- _destroy_images()
- _get_deploy_info
- _continue_deploy()

Minor changes will be required in the refactoring to remove the "pxe" portions
out of the above methods.

IloVirtualMediaIscsiDeploy
--------------------------
This class will implement the following:

- *validate()* - Validates that node has ports added, parses deploy_info(),
  checks that conductor api url is available, and validates that ``deploy_iso``
  property exists in driver_info of node. Most of the functions from
  refactored iscsi_deploy is used.
- *deploy()* - Caches instance image, uses virtual media boot helper method
  ``setup_virtual_media_boot`` to setup the machine for booting with
  driver_info['deploy_iso'].
- *tear_down()* - Powers down the node.
- *clean_up()* - Destroys the images, calls ``cleanup_virtual_media_boot``
  method  to clean the temporary floppy images.  Decrements the ``usage_count``
  for ``boot_iso`` in swift and destroys the boot ISO image if the
  ``usage_count`` meta-property becomes 0 (if ``boot_iso`` was created by
  ironic).

prepare() and take_over() will be empty.

VendorPassthru
--------------
Implement a new vendor passthru method 'pass_deploy_info'. This vendor passthru
method will call continue_deploy() from iscsi_deploy.py.

After deploying over iSCSI, it checks the following in that order to pick up
a boot ISO:

- If user has specified a boot ISO in glance image, then it picks up this.
- Checks if a boot_iso is already available for the mentioned (image, kernel,
  ramdisk) for the image in swift on ``swift_ilo_container`` (by hashing the
  UUIDs of the image, kernel, ramdisk to get a unique name).  If the boot
  iso exists, then the ``usage_count`` swift meta-property for the swift
  object is incremented by 1.
- If we still can't find boot ISO, it creates a bootable ISO image, uploads
  it to swift on ``swift_ilo_container`` with the generated name and
  sets ``usage_count`` to 1.

It then records the information about ``boot_iso`` in node's
``instance_info[boot_iso]``

IloPower reboot()
-----------------
If node has ``boot_iso`` in its instance_info, use ``setup_virtual_media_boot``
to set the machine to boot from ``boot_iso``.

Alternatives
------------
The proliant baremetal machines could be booted with proposed iPXE, but even
that will involve booting the machine with PXE to load the iPXE software. Also
it would not solve the security issues in token handoff to baremetal node.

Data model impact
-----------------
The new deploy driver will use two new parameters:

- driver_info['deploy_iso'] - This will be used to boot up the node before the
  deploy.
- instance_info['boot_iso'] - This is set by the deploy driver once the
  baremetal node deploy completes.

REST API impact
---------------
One vendor_passthru method will be added:

pass_deploy_info:

* Description: The deploy ramdisk built using deploy-ironic element of
  diskimage-builder will call this method on the node.  It will also pass
  the required information for completing the deploy after connecting to the
  baremetal node's local disk using iSCSI.

* Method type: POST

* Normal response code: 200

* Expected errors: 400: Insufficient/Invalid data sent or some data for
  deployment missing.

* URL: /{api_version}/nodes/<node-uuid>/vendor_passthru/pass_deploy_info

* Parameters:

  + ``address`` - Address of the baremetal node.
  + ``key`` - The deployment key generated by ironic.
  + ``iqn`` - The iqn of the target disk on baremetal node where the image has
    to be deployed.
  + ``error`` - The error message if some error was encountered.

* Body JSON schema::

    {
     "address": "10.10.1.150"
     "iqn": "iqn-12345678-1234-1234-1234-1234567890abcxyz"
     "key": "1234567890"
     "error": ""
    }

* Response JSON: None

Driver API impact
-----------------
None.

Nova driver impact
------------------
No changes are required on the nova ironic virt driver.  The new iLO driver
will continue to use the below 5 parameters set by nova ironic virt driver in
the node's instance_info:

- ``image_source``
- ``root_gb``
- ``swap_mb``
- ``ephemeral_gb``
- ``ephemeral_format``

Security impact
---------------
- The PXE driver requires the admin token to be available on tftp
  which can be accessed by anyone in the deploy network (since the filename of
  the token is predicatable, which is token-<node uuid>).  In virtual media
  boot, the user token is sent to the conductor node securely over https
  through OOB channel. Hence, this deploy method can be used for more secure
  deployments.

- The virtual floppy image is uploaded to a swift container with user token
  and is destroyed automatically by swift after the timeout. It is recommended
  to use a separate container to secure the floppy images.

- Glance backed by swift can be configured to store the images such that the
  owner of the image and a defined list of admin accounts will be able to
  access the image.  For more information refer using
  ``swift_store_multi_tenant`` in [1].

Other end user impact
---------------------
None

Scalability impact
------------------
None.

Performance Impact
------------------
None.

Other deployer impact
---------------------
The cloud operator is supposed to do the following as part of configuring the
iLO driver:

- Upload the deploy_iso to glance and mention its UUID in
  driver_info['deploy_iso'].

Also, the user/operator may also optionally specify a ``boot_iso`` from which
the kernel/ramdisk can be booted off for a deploy image.  This may be
specified as a glance meta-property ``boot_iso`` for the image to be deployed.

Utilities will be provided in diskimage-builder for creating the deploy ISO.

This method of deploy doesn't require an extra service (like tftp service
incase of pxe driver) to be running on the conductor node.

Developer impact
----------------
None.

Known Limitation
----------------
- If the user needs to reboot the baremetal node, then the reboot needs to be
  triggered from Ironic (or from Nova).

- If the user needs to issue an inband reboot of the baremetal node (reboot
  from within the baremetal node), then the baremetal node will fail to boot.
  In such a case, the user may just issue a reboot from ironic again to get the
  node booted up.

Implementation
==============

Assignee(s)
-----------
Primary assignee:
  rameshg87

Work Items
----------
The work will be split up into following separate items (or patches):

1. Refactor the iSCSI deploy code in current pxe deploy driver.
2. Implement the changes to ironic/common/images.py module.
3. Implement the ironic/common/swift.py module.
4. Implement the virtual media boot helper methods, add the new deploy driver
   and new vendor passthru module.
5. Implement the changes to reboot() method in IloPower.

Dependencies
============
Depends on hpproliant module:

- https://github.com/hpproliant/proliantutils

Testing
=======
Unit tests will be added for all the code.

Tempest tests for the deploy will be considered later.

Documentation Impact
====================
The procedure for configuring the proliant baremetal node will need to be
documented. This will be documented in rst format in doc/ directory in ironic
source tree.  The contents of this file can be put in ironic wiki as well.

References
==========
1. http://docs.openstack.org/admin-guide-cloud/objectstorage_tenant_specific_image_storage.html
