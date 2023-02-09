..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

======================================================
Out-of-band RAID configuration using Cisco UCS drivers
======================================================

https://bugs.launchpad.net/ironic/+bug/1526362

This blueprint proposes to implement out-of-band RAID configuration interface
for Cisco UCS drivers. This implementation supports configuration of Cisco
UCS Manager (UCSM) managed B/C/M-series servers.

.. NOTE::
   This specification has been retired as the vendor specific UCS driers are
   no longer available in Ironic. This was a result of the Open Source
   UcsSdk library no longer being maintained. Users may wish to explore use
   of the ``redfish`` driver, but it is unknown to the community if the UCS
   Redfish support has been extended to RAID support.

Problem description
===================

Currently pxe_ucs and agent_ucs drivers don't support RAID configuration on
UCSM managed servers.

Proposed change
===============

It proposes implementing the RAID interface as described by the parent spec
[1]_ for UCS drivers.

List of changes required:

* ucs.raid.RAIDInterface for RAID configuration operations

  The following methods will be implemented:

    * validate
    * create_configuration
    * delete_configuration

    validate() method validates the required UCS parameters for OOB RAID
    configuration. Also calls validate() of the super class to validate json
    schema.
    create_configuration and delete_configuration operations are implemented
    as asynchronous RAID configuration deployment operations by UCS drivers.
    UcsSdk/UCS-API asynchronously deploys the RAID configuration on the target
    node. UCS driver(s) sends the RAID configuration simultaneously to the
    target node when the operation is invoked, but UCS Manager would not deploy
    the configuration simultaneously on the target node. UCS Manager accepts
    the RAID configuration and deploys it as part of UCS Manager FSM deploy
    state. Hence there will be delay between, when the operation is invoked
    and when the RAID configuration is deployed. To know the deploy status,
    we need to query the FSM status using UcsSdk API. These methods return
    states.CLEANWAIT.
    New driver periodic task will be added to fetch the UCSM FSM status of
    these operations. This periodic task is enabled only if pxe_ucs, agent_ucs
    drivers are enabled in the conductor.

* RAID management changes:

  Controlling the RAID configuration is creating storage-profile ManagedObject
  and associating with the Server object in UCS Manager 2.4. Earlier version
  of UCSM requires to configure LocalDiskConfigPolicy and associate with
  respective service-profile ManagedObject. The service-profile information is
  captured as part of node driver_info properties.
  UcsSdk provides RAIDHelper interface, which actually creates the required
  policies specified above. UCS driver uses this interface and makes
  appropriate calls to create_config and delete_config operations.

Alternatives
------------
Operator can change the RAID configuration manually whenever required after
putting the node to MANAGEABLE state. But this has to be done for each node.

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
None

Developer impact
----------------
None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
saripurigopi

Work Items
----------

* Add UcsRAIDManagement inheriting from base.RAIDInterface for ucs drivers.
* Writing and unit-test cases for RAID interface of ucs drivers.
* Writing configuration documents.

Dependencies
============
* UcsSdk to support RAID configuration utility

Testing
=======
Unit-tests will be implemented for RAID interface of ucs driver.

Upgrades and Backwards Compatibility
====================================
Adding RAID interface support for ucs drivers will not break any
compatibility with either REST API or RPC APIs.

Documentation Impact
====================
* Writing configuration documents.

References
==========
.. [1] New driver interface for RAID configuration: https://review.opendev.org/173214
