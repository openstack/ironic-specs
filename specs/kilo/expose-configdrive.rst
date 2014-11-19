..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===============================
Expose configdrive to instances
===============================

https://blueprints.launchpad.net/ironic/+spec/expose-configdrive

This blueprint adds support for exposing a configdrive image[1] to instances
deployed by Ironic.


Problem description
===================

Instances deployed by Ironic should be able to use cloud-init (or similar
software) to put an end user's data on an instance. This is possible today with
Ironic by including cloud-init with the image, and pointing it at a Nova
metadata service.

There are two issues with this approach:

* Some deployers do not run a metadata service in their environment.

* If a deployer provisions Ironic machines using static IP address assignment,
  the instance will not have network access until cloud-init puts the network
  configuration into place. If the metadata service is the only way to get
  the network configuration, the instance is deadlocked on getting network
  access.

To solve these problems, a configdrive image can take the place of the metadata
service. In the VM world, this is typically handled by the hypervisor exposing
a configdrive image to the VM as a volume.

In Ironic's case, there is no hypervisor, so this image needs to be exposed to
the instance in some other fashion. This could be accomplished by writing the
image to a partition on the node, exposing the image via the out-of-band
mechanism (e.g. a virtual floppy in HP's iLO), or configuring the node to mount
the image from a SAN. In any case, this needs to be handled by Ironic, rather
than Nova. However, Nova has the data that belongs in the configdrive, as well
as the code to generate the image. So, it makes sense for Nova to generate an
image and pass it to Ironic.

This blueprint outlines how Ironic will handle the configdrive image that Nova
provides and expose it to an instance.


Proposed change
===============

Nova's Ironic virt driver will generate a configdrive image and pass a
reference to it to Ironic via a "configdrive" field in node.instance_info.
This should be a URI for the image. This is discussed in more detail in
this nova spec.[0]

The reference implementation for the storage service to hold the configdrive
will be via Swift.

Drivers will be responsible for exposing the configdrive to the instance, as
well as removing the configdrive from the instance upon deletion. This cannot
be coordinated by code outside of the driver, as only the driver can know
when and how to take these actions.

Some mechanisms a driver may use to expose a configdrive include:

* Write the image to the instance's disk as a partition.

* Use an OOB mechanism to mount the image as a virtual disk.

* Use an OOB mechanism to configure the instance to mount the image from a SAN.

Alternatives
------------

There are no clear alternatives here.

Data model impact
-----------------

A "configdrive" key will be added to node.instance_info.

REST API impact
---------------

None.

RPC API impact
---------------

None.

Driver API impact
-----------------

None.

Nova driver impact
------------------

The nova driver will need to implement the functionality to generate the
configdrive image and get it to Ironic.

This is discussed in the corresponding nova spec.[0]

Security impact
---------------

This proposal involves storing end user data as an image in Swift. This may
be a security concern, as this data is not encrypted at rest.

There are methods for securing this data that are out of the scope of this
initial work.

Other end user impact
---------------------

None.

Scalability impact
------------------

Use of the configdrive would require a call to Swift (or some other object
store), which will have some impact on the system, but is probably
negligible.

Performance Impact
------------------

None.

Other deployer impact
---------------------

This feature will require deploying some object store service (Swift for
the reference implementation).

Developer impact
----------------

Developers writing drivers should implement this functionality, but it is not
required, as it may not be possible for some drivers.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  jroll

Work Items
----------

* Implement the Nova side of this feature.

* Implement functionality for various deploy drivers.

* Add support to IPA to fetch a configdrive by URL. It currently only supports
  being passed a blob in the prepare_image command.

* Add tempest tests (in conjuction with the Nova driver).


Dependencies
============

This change depends on the corresponding Nova spec.[0]


Testing
=======

A tempest test should be added that deploys a bare metal instance with a
configdrive, and verifies that the configdrive is properly written to the
instance.


Upgrades and Backwards Compatibility
====================================

The Ironic code will need to be deployed before enabling configdrive support
in Nova.

This feature is completely optional, so it is backward compatible.


Documentation Impact
====================

Documentation may need to be updated to indicate that a configdrive may
be used with instances deployed by Ironic.


References
==========

[0] https://blueprints.launchpad.net/nova/+spec/use-configdrive-with-ironic

[1] http://cloudinit.readthedocs.org/en/latest/topics/datasources.html#config-drive
