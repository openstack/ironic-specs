..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=================
Root device hints
=================

https://blueprints.launchpad.net/ironic/+spec/root-device-hints

Allow operators to pass some hints to Ironic to decide which device
should be selected for the deployment.

Problem description
===================

When the deploy ramdisk boots Ironic picks the first disk it finds to
be the root device (the device where the image will be put on). If the
server has more than one SATA, SCSI or IDE disk controller, the order
in which their corresponding device nodes are added is arbitrary [`1`_]
[`2`_]. This may result in devices like /dev/sda and /dev/sdb switching
around on each boot and Ironic picking different disk every time the
machine is being deployed.

As an operator, if my server has multiple disks I would like to choose
which one Ironic should deploy the image onto. Or in case I have created
a RAID device to be my root device, I'd like to tell Ironic to always
use that.

Another problem, in case for the full disk image deployment, if we
deploy a server twice and on each deployment Ironic picks a different
disk we could end up with 2 disks containing a valid bootloader.

.. _`1`: https://wiki.archlinux.org/index.php/persistent_block_device_naming
.. _`2`: https://access.redhat.com/documentation/en-US/Red_Hat_Enterprise_Linux/5/html/Online_Storage_Reconfiguration_Guide/persistent_naming.html

Proposed change
===============

The change proposed by this blueprint is to give operators a means via
the Ironic API to pass some hints about what disk should be picked in
deploy time. That way Ironic can always pick the right disk to write
the image on.

Also, with the addition of Ironic being able to create RAID arrays,
it would be nice to be able to tell Ironic to use the device that was
just created to be the root device for the deployment.

This spec is proposing having a limited number of hints that could be
passed as part of the initial work, but could be extended later on. The
initial proposed hint list is:

* model (STRING): device identifier
* vendor (STRING): device vendor
* serial (STRING): disk serial number
* wwn (STRING): unique storage identifier
* hctl (STRING): Host:Channel:Target:Lun for SCSI
* size (INT): size of the device in GB

The hints should live in the `properties` attribute of the Node resource,
the key would be `root_device` and the value a dictionary so operators
could combine one or more hints. For example::

 node.properties['root_device'] = {'wwn': '0x4000cca77fc4dba1'}

The logic about which disk will be picked will follow:

#. If the hints are not specified Ironic will continue to pick the
   first disk it finds.

#. If hints are specified and only one disk is found Ironic will pick it.

#. If hints are specified and multiple disks are found Ironic will pick
   the first disk that matches the all the criteria.

#. If hints are specified and no disks are found the deployment is aborted.

The default deploy ramdisk and `IPA`_ needs to be changed to support
filtering the disks based on the hints, if specified.

Alternatives
------------

We could recommend operators to avoid having multiple storage devices
on the machines being managed by Ironic.

Data model impact
-----------------

None

REST API impact
---------------

As we want to use a dictionary as a value on the `properties` attribute
the `bug 1398350`_ needs to be fixed.

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

Deployers will have a finer granularity in selecting the disk device
to be used for the deployment.

.. note::
    When specifying device size as a hint operator needs to make sure that
    the value doesn't conflict with the local_gb properties of the node.
    This is going to be documented as part of this spec.

Developer impact
----------------

None


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  lucasagomes

Other contributors:
  None

Work Items
----------

* Make Ironic check for hints in the node.properties

* Pass the hint information to the deploy ramdisk and `IPA`_

* Add tests and documentation

* Modify the default deploy ramdisk in `diskimage-builder`_ to consider
  the hints when picking the disk device

* Modify `IPA`_ to consider the hints when picking the disk device

Dependencies
============

* `bug 1398350`_ needs to be fixed.

Testing
=======

* Unit tests will be added

Upgrades and Backwards Compatibility
====================================

The change is backwards compatible since if hints are not specified
Ironic will continue to do what it does today (pick the first disk it
found for the deployment).


Documentation Impact
====================

A document explaining how hints works and what are the options and values
supported is going to be added.

References
==========

None

.. _`bug 1398350`: https://bugs.launchpad.net/ironic/+bug/1398350
.. _`diskimage-builder`: https://github.com/openstack/diskimage-builder/tree/master/elements/deploy-ironic
.. _`IPA`: https://github.com/openstack/ironic-python-agent
