..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=============================================
More robust device status checking with fuser
=============================================

https://blueprints.launchpad.net/ironic/+spec/device-status-check-with-fuser

Implement a more robust device status checking with fuser to avoid "device is
busy" issues after partitioning.

Problem description
===================

Right after partitioning, we have a sleep(3) call to avoid the "device is busy"
problem. A less error-prone solution is to check with fuser, whether there is
any process currently using the disk.

Proposed change
===============

Replace the sleep call with a check of the mounted device with fuser. fuser
returns with exit code 0 if at least one access has been found and it lists the
processes. In case there's no access, it returns with exit code 1 with no
output.

Alternatives
------------

* lsof can also be used for checking for open files. There isn't any
  advantage or disadvantage in this use-case.

Data model impact
-----------------

None

REST API impact
---------------

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

The deployment can raise InstanceDeployFailure after partitioning if the device
is not available after a configurable number of retries.


Scalability impact
------------------

None

Performance Impact
------------------

Instead of sleeping every time for 3 seconds, fuser will check the status
immediately after the partitioning is done. This can result in an shorter
deployment time.

Other deployer impact
---------------------

New config options in the ``disk_partitioner`` group:

* check_device_interval: After Ironic has completed creating the partition
                         table, it continues to check for activity on the
                         attached iSCSI device status at this interval prior to
                         copying the image to the node. Default is 1 second.
* check_device_max_retries: Number of retries for checking the device status.
                            Default is 20.

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  ifarkas

Other contributors:
  None

Work Items
----------

* Add config options to ``disk_partitioner`` group.

* Implement the device status check with LoopingCall.


Dependencies
============

* This patch requires fuser to be installed.


Testing
=======

* Unit tests

Documentation Impact
====================

Documentation should include instructions on how to configure the device status
check.

References
==========

None
