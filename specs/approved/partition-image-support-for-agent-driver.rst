..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Partition image support for agent driver
==========================================

https://blueprints.launchpad.net/ironic/+spec/partition-image-support-for-agent-driver

This blueprint suggests to enhance agent driver to support deploy partition
images with subsequent boot to happen over pxe or vmedia as specified by
the driver.

Problem description
===================

As of now agent driver support only whole disk images that can be deployed on
the baremetal. With disk image based deploy, the subsequent boot will happen
from the local hard drive. Ironic does not have control over the subsequent
boots of the provisioned baremetal node.

Proposed change
===============

* Agent driver validate the specified image type is of partition image(raw) by
  looking for kernel_id and ramdisk_id image properties.

* Send partition information(root, swap, etc) to the agent ramdisk through
  image_info.

* Upon receiving the partition information, agent ramdisk will work on the
  given os_install disk and copy the partition image in the root partition.

* Agent ramdisk sends back the root_uuid to the agent driver on the
  controller.

* Post deploy, agent driver prepares the config for subsequent boot, either
  using pxe or vmedia as defined by the driver. Both agent_ipmitool and
  agent_ilo driver should support deploy with partition images.

* Factor out the partitioning code from ironic into a different library
  and use it in both IPA and ironic code base.

Alternatives
------------

We can use iscsi method to write partition image on to the target disk.
We need agent ramdisk to support iscsi, similar to the ironic DIB element.


Data model impact
-----------------

None.

State Machine Impact
--------------------

None.

REST API impact
---------------

None.

Client (CLI) impact
-------------------

None.

RPC API impact
--------------

None.

Driver API impact
-----------------

None.

Nova driver impact
------------------

None.

Ramdisk impact
--------------

N/A

.. NOTE: This section was not present at the time this spec was approved.

Security impact
---------------

None.

Other end user impact
---------------------

Ability to deploy partition images on nodes managed by the agent.

Scalability impact
------------------

None.

Performance Impact
------------------

None.

Other deployer impact
---------------------

None.

Developer impact
----------------

None.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  faizan-barmawer

Other contributors:
  None

Work Items
----------

* Factor out the partitioning code from ironic into a common library
  for both IPA and ironic code base.

  1. Move the disk partition code from ironic/common to an oslo incubator
     project as oslo.libironic

     - ironic/common/disk_partitioner.py

     - Some common disk related functions from
       ironic/drivers/modules/deploy_utils.py

     - Related test cases.

  2. Use oslo.libironic in IPA

* Make necessary changes in agent driver common code, such as validate,
  deploy, etc.

* Make necessary changes in agent_ipmitool driver to generate correct
  pxe config for subsequent reboot.

* Make necessary changes in agent_ilo driver to generate iso for subsequent
  reboot.

* Make changes in IPA (agent ramdisk) to recognize the incoming image
  information and take appropriate action to deploy partition image on the
  disk.

Dependencies
============


Testing
=======

* Unit testing with partition images with agent_ilo and agent_ipmitool drivers.
* Add specific agent driver test cases with partition images in
  tempest/devstack.

Upgrades and Backwards Compatibility
====================================


Documentation Impact
====================

* Make changes to ironic install guide.

References
==========

