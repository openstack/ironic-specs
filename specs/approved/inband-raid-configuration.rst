..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==============================================
In-band RAID configuration using agent ramdisk
==============================================

https://blueprints.launchpad.net/ironic/+spec/inband-raid-configuration

This spec proposes to implement a RAID configuration interface using
Ironic Python Agent (IPA). The first driver to make use of this interface
will be the ``agent_ilo`` driver.

Problem description
===================

Currently there is no way in Ironic to do RAID configuration for servers
using in-band mechanism.

Proposed change
===============

This spec proposes to implement in-band RAID configuration using IPA.
It proposes to implement the ``RAIDInterface`` as mentioned in the parent
spec [1]. The implementation will be named ``AgentRAIDManagement``. The main
job of the implementation will be to invoke the corresponding RAID operation
methods on agent ramdisk.  Interested vendors will implement these methods in
Ironic Python Agent using hardware managers.

Following are the changes required:

* The following methods will be implemented as part of ``AgentRAIDManagement``:

  + ``create_configuration`` - This will create the RAID configuration on
    the bare metal node. The following are the steps:

    - Calls ``clean.create_raid_configuration`` on the agent ramdisk passing
      the details of ``raid_config``.

  + ``delete_configuration`` - This will delete the RAID configuration on
    the bare metal node. The following are the steps:

    - Calls ``clean.delete_raid_configuration`` on the agent ramdisk.

* The results for both of the above commands will be polled on subsequent
  heartbeats from the ramdisk and then ``update_raid_info`` will be called once
  the RAID operation is done.

* Agent ramdisk will be enhanced to add two new methods
  ``clean.create_raid_configuration`` and ``clean.delete_raid_configuration``.
  These methods will route the call to hardware manager, so that different
  hardware vendors can implement their own methods of managing RAID
  on their hardware.  ``clean.create_raid_configuration`` will accept
  ``raid_config`` as argument (RAID configuration dictionary as mentioned in
  `New driver interface for RAID configuration`_.
  ``clean.delete_raid_configuration`` will not accept any arguments.

.. _`New driver interface for RAID configuration`: http://specs.openstack.org/openstack/ironic-specs/specs/liberty/ironic-generic-raid-interface.html


* It is possible to have a hardware manager that does software RAID
  configuration.  When software RAID configuration is done, agent based
  ``raid.create_config`` should be used as a clean step so that software RAID
  is configured everytime after a secure disk erase (which wipes out the
  previous software RAID configuration if it exists).

Alternatives
------------

Some bare metal servers do not support out-of-band RAID configuration.  They
support only in-band raid configuration.  I don't see any other alternative
other than making use of a ramdisk to do this.

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

Security impact
---------------

None.

Other end user impact
---------------------

None.


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

Other hardware vendors developing drivers for OpenStack can use Ironic
Python Agent for in-band RAID configuration. They can add their own hardware
manager implementing the method and get the RAID configuration done.


Implementation
==============

Assignee(s)
-----------

rameshg87

Work Items
----------

* Implement ``AgentRAIDManagement``
* Make changes in Ironic Python Agent to add methods
  ``clean.create_raid_configuration`` and ``clean.delete_raid_configuration``
  which route calls to respective hardware manager.


Dependencies
============

* Implement Zapping States - https://review.openstack.org/140826


Testing
=======

Unit tests will be added.


Upgrades and Backwards Compatibility
====================================

None.

Documentation Impact
====================

None.  Most of the RAID configuration details in Ironic are covered in the
parent spec.  If anything is required in addition, respective vendors making
use of ``AgentRAIDManagement`` will need to document it.

References
==========

None.
