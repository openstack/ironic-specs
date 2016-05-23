..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==============================================
In-band RAID configuration using agent ramdisk
==============================================

https://bugs.launchpad.net/ironic/+bug/1526398

This spec proposes to implement a RAID configuration interface using
Ironic Python Agent (IPA). The drivers ``agent_ipmitool``,
``agent_pyghmi``, ``agent_ssh``, ``agent_vbox`` and ``agent_ilo``
drivers will make use of this new implementation of ``RAIDInterface``.

Problem description
===================

Currently there is no way in Ironic to do RAID configuration for servers
using in-band mechanism.

Proposed change
===============

This spec proposes to implement in-band RAID configuration using IPA.
It proposes to implement the ``RAIDInterface`` as mentioned in the parent
spec [1]. The implementation will be named ``AgentRAID``. The main
job of the implementation will be to invoke the corresponding RAID operation
methods on agent ramdisk.  Interested vendors will implement these methods in
Ironic Python Agent using hardware managers.

Following are the changes required:

* The following methods will be implemented as part of ``AgentRAID``:

  + ``create_configuration`` - This will create the RAID configuration on
    the bare metal node. The following are the steps:

    - Uses ``clean.execute_clean_step`` command in Ironic Python Agent ramdisk
      to invoke the ``create_configuration`` step of ``raid`` interface.

  + ``delete_configuration`` - This will delete the RAID configuration on
    the bare metal node. The following are the steps:

    - Uses ``clean.execute_clean_step`` command in Ironic Python Agent ramdisk
      to invoke the ``delete_configuration`` step of ``raid`` interface.

* RAID configuration will be limited to zapping only at first by hardcoding its
  clean step priority to be 0. We'll consider interaction with cleaning
  mechanism later. This allows us to make ``target_raid_config`` mandatory
  for the new clean steps.

* When the agent ramdisk is running an in-band clean step, the conductor gets
  the status of the last in-band clean step on every heartbeat. When an in-band
  clean step completes, the conductor resumes the cleaning and goes on to the
  next clean step if any. A new mechanism - the
  ``agent_base_vendor.post_clean_step_hook`` decorator, will be added. This
  allows a driver implementor to specify a function to be invoked after
  successful completion of an in-band clean step (and before the next clean
  step is started). The decorated function would take two arguments: the task
  and the command status (of the clean step) returned by the agent ramdisk.

  For example::

    @agent_base_vendor.post_clean_step_hook(
        interface='raid', step='create_configuration')
    def _create_configuration_final(task, command):

* A method ``agent._create_configuration_final`` will be added as a post clean
  step hook for ``raid.create_configuration``. This method will call
  ``update_raid_info`` with the actual RAID configuration returned from the
  agent ramdisk.

* A method ``agent._delete_configuration_final`` will be added as a post clean
  step hook for ``raid.delete_configuration``. This will set
  ``node.raid_config`` to ``None``. Note that ``target_raid_config`` will be
  left intact, and will be reused by future zapping calls.

* It is possible to have a hardware manager that does software RAID
  configuration, but it goes beyond the scope of this spec, as it requires
  RAID configuration to be run as a clean step after disk erasure.

Alternatives
------------

Some bare metal servers do not support out-of-band RAID configuration. They
support only in-band raid configuration. I don't see any other alternatives
other than making use of a ramdisk to do this.

We could provide an option to enable RAID as part of cleaning. However, this
will make ``target_raid_config`` mandatory for all nodes managed by a given
conductor. We'll have to reconsider it later.

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

* Implement the mechanism for post clean step hook.
* Implement ``AgentRAID``

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
use of ``AgentRAID`` will need to document it.

References
==========
[1] http://specs.openstack.org/openstack/ironic-specs/specs/approved/ironic-generic-raid-interface.html
