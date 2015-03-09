..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=======================================
Support for non-glance image references
=======================================

https://blueprints.launchpad.net/ironic/+spec/non-glance-image-refs

Add the ability to provide non-Glance references for images that are used by
Ironic.

Problem description
===================

Currently, kernels and ramdisks, image_source images are downloaded from
Glance, provided their UUID. This requires Glance to be up and running,
and does not allow providing images from specific URL or from local disk.

Proposed change
===============

The proposal is to create new image service base class for downloading images
provided URL for them; also to add some common protocol support, i.e.
downloading from remote HTTP servers and using images available in local file
system.

Depending on the URL, different image service will be used:

* If URL starts with 'glance://' or is just an image UUID (for backwards
  compatibility), Glance image service is used.

* If it starts with 'http://' or 'https://' then it will be downloaded by
  HTTP image service.

* If it starts with 'file://' then it is referencing some file system
  available locally, either hard link will be created for an image if it's in
  the same file system as folder with node's images, or image will be copied
  to that folder by image service for current conductor's local files.

Alternatives
------------

Continue having a hard-dependency on Glance.

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

Operators should download images from trusted sources.

Other end user impact
---------------------

None

Scalability impact
------------------

Depending on the protocol used to download image, network usage can be either
reduced (using local files) or remains the same.

Performance Impact
------------------

None

Other deployer impact
---------------------

Since Ironic may be used without Glance, developers can't make the assumption
that Glance image metadata is the only source for such information. Deployers
must be capable of supplying Ironic with all required metadata
programmatically, and such requirements must be documented.

For example, because of kernel and ramdisk UUIDs are currently got from
image_source image properties returned by Glance, links for those should be
put into instance_info dictionary if Glance is not used. Another example is
whole disk instance images that need to have is_whole_disk flag in
instance_info in order to not to fetch kernel and ramdisk.

Developer impact
----------------

Developers can easily add their own image services to download images using
specific protocols that are needed.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  vdrok

Other contributors:
  None

Work Items
----------

* Implement base image service class for downloading images from URL.

* Implement image service classes for downloading from HTTP server and from
  local file system.

* Implement a class that will return image service based on protocol defined
  in URL.


Dependencies
============

None


Testing
=======

Tests for downloading images using different protocols will be added to
Tempest.


Upgrades and Backwards Compatibility
====================================

For backwards compatibility it is allowed for image URL to contain only Glance
image UUID.


Documentation Impact
====================

Possibility of specifying URLs for images and protocols supported should be
added to documentation.

If a driver uses some image metadata provided by Glance, it should be added
to documentation, so that operators that decide not to run Glance can know
which additional metadata they should provide manually.


References
==========

https://etherpad.openstack.org/p/kilo-ironic-making-it-simple
