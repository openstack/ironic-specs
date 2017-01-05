..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=====================
Implement Rescue Mode
=====================

https://bugs.launchpad.net/ironic/+bug/1526449

Implement Nova rescue/unrescue in Ironic. Also implement an extension in IPA
that carries out rescue-related tasks. After rescuing a node, it will be left
running a rescue ramdisk, configured with the rescue_password, and listening
with ssh on the specified network interfaces.

Problem description
===================

Ironic does not currently implement the Nova rescue/unrescue interface.
Therefore, end users are left with few options for troubleshooting or fixing
anomalous and misconfigured nodes.

Proposed change
===============
* Implement rescue(), and unrescue() in the Ironic virt driver (no spec req'd):
  https://blueprints.launchpad.net/nova/+spec/ironic-rescue-mode
* Add InstanceRescueFailure, and InstanceUnRescueFailure exceptions to Nova
* Add methods to Nova driver to poll Ironic to wait for nodes to rescue and
  unrescue, as appropriate.
* Store plaintext password in Ironic node instance_info for use on the rescued
  node.
* Add method for injecting password into OS.
* Modify Ironic state machine as described in the state machine impact section
* Add AgentRescue driver (implements base.RescueInterface). This driver will
  be mixed into the agent_ipmitool and agent_pyghmi drivers.
* Add periodic task _check_rescue_timeouts to fail the rescue process if
  it takes longer than rescue_callback_timeout seconds for the rescue ramdisk
  to come online.
* Add Conductor methods: do_node_rescue, and do_node_unrescue
* Add Conductor RPC calls: do_node_rescue, and do_node_unrescue (and
  increment API version)
* Add conductor.rescue_callback_timeout config option
* Add rescue-related functionality to Ironic Python Agent including ability
  to set rescue password and kick off any needed network configuration
  automation
* Documentation of good practices for building rescue ramdisk in multitenant
  environments
* Add rescue_network configuration, which contains the UUID of the network the
  rescue agent should be booted onto. For security reasons, this should be
  separate from the networks used for provisioning and cleaning in multi-tenant
  environments.

An outline of the standard (non-error) rescue and unrescue processes follows:

Standard rescue process:

1. User calls Nova rescue() on a node.
2. Nova ComputeManager calls the virt driver's rescue() method, passing in
   rescue_password as a parameter.
3. Virt driver calls node.set_provision_state(RESCUE), with the rescue_password
   as a parameter.
4. Virt driver loops while waiting for provision_state to change, and updates
   Nova state as appropriate.
5. Ironic API receives set_provision_state call, and performs do_node_rescue
   RPC call (ACTIVE -> RESCUING).
6. Ironic conductor sets rescue password in instance_info and hands off call to
   appropriate driver.
7. Driver boots rescue ramdisk (RESCUING -> RESCUEWAIT), using the configured
   boot driver. As part of this process, Ironic will put the node onto the
   rescue_network, as configured in ironic.conf.
8. Agent ramdisk boots, performs a lookup (/v1/lookup in ironic-api), gets node
   info back, and begins heartbeating (/v1/heartbeat in ironic-api).
9. Upon receiving heartbeat, the conductor calls finalize_rescue (/v1/commands)
   with config drive and rescue password (RESCUEWAIT -> RESCUING), and removes
   the rescue password from the instance_info, as it's no longer needed.
10. Agent sets password, configures network from information in config drive,
    and stops agent service.
11. The conductor flips network ports putting the node back on the tenant
    network, and the state is set to RESCUE.

Standard Unrescue process:

1. User calls Nova unrescue() on a node.
2. Nova calls Ironic unrescue() virt driver.
3. Virt driver calls node.set_provision_state(ACTIVE).
4. Virt driver loops while waiting for provision_state to change, and updates
   Nova state as appropriate.
5. Ironic API receives set_provision_state call, and performs
   do_node_unrescue RPC call.
6. Ironic conductor hands off call to appropriate driver.
7. Driver performs actions required to boot node normally, and sets provision
   state to ACTIVE.

Rescue/Unrescue with standalone Ironic:

1. Call Ironic provision state API with verb "rescue", with the rescue password
   as an argument.
2. When finished with rescuing the instance, call Ironic provision state API
   with "unrescue" verb


Alternatives
------------
* Continue to not support rescue and unrescue.
* Use console access to get rescue-like access into the OS, although this may
  not help in cases of lost password.

Data model impact
-----------------
Essentially none.  We will use instance_info to store, and subsequently
retrieve, the rescue_password while rescuing a node.

State Machine Impact
--------------------
* Add states to the Ironic state machine: RESCUING, RESCUEWAIT, RESCUE,
  RESCUEFAIL, UNRESCUING, UNRESCUEFAIL.
* Add transitions to the Ironic state machine:

  * ACTIVE -> RESCUING (initiate rescue)
  * RESCUING -> RESCUE (rescue succeeds)
  * RESCUING -> RESCUEWAIT (optionally, wait on external callback)
  * RESCUING -> RESCUEFAIL (rescue fails)
  * RESCUEWAIT -> RESCUING (callback succeeds)
  * RESCUEWAIT -> RESCUEFAIL (callback fails)
  * RESCUEWAIT -> DELETING (delete without waiting)
  * RESCUE -> RESCUING (re-rescue node)
  * RESCUE -> DELETING (delete rescued node)
  * RESCUE -> UNRESCUING (unrescue node)
  * UNRESCUING -> UNRESCUEFAIL (unrescue fails)
  * UNRESCUING -> ACTIVE (unrescue succeeds)
  * UNRESCUEFAIL -> RESCUING (re-rescue node after failed unrescue)
  * UNRESCUEFAIL -> UNRESCUING (re-unrescue node after failed unrescue)
  * UNRESCUEFAIL -> DELETING (delete instance that failed unrescuing)
  * RESCUEFAIL -> RESCUING (re-rescue after rescue failed)
  * RESCUEFAIL -> UNRESCUING (unrescue after failed rescue)
  * RESCUEFAIL -> DELETING (delete after failed rescue)

* Add state machine verbs:

  * RESCUE
  * UNRESCUE

REST API impact
---------------
Modify provision state API to support the states and transitions described in
this spec.  Also increment the API microversion. Nodes in states introduced by
this spec (and related, future microversion) would be unable to be modified by
clients using an earlier microversion.

Client (CLI) impact
-------------------
Support for the new verbs "rescue" and "unrescue" must be added to the client.

RPC API impact
--------------
Add do_node_rescue and do_node_unrescue to the Conductor RPC API.

Driver API impact
-----------------
None, because we defined the RescueInterface a long time ago.

Nova driver impact
------------------
Implement rescue() and unrescue() in the Nova driver.  Add supporting methods
including _wait_for_rescue() and _wait_for_unrescue().

Ramdisk impact
--------------
An agent that wishes to support rescue should:
  * Read and understand ipa-api-url kernel parameter for configuring API
    endpoint
  * Implement a client for ironic's lookup API call
     * The rescue_password will be in instance_info in the node object
       returned by Ironic on lookup. This can be placed in a linux-style
       /etc/shadow entry to enable a new user account.
  * Implement heartbeating to the appropriate API endpoint in Ironic
      * After one heartbeat, the agent should then kickoff any action needed
        to reconfigure networking, such as re-DHCPing, as the Ironic conductor
        will complete all actions to finish rescue - including moving the
        node off a network with access to Ironic API, if relevant.
      * Once network is reconfigured, the agent process should shutdown. Rescue
        is complete.

IPA will have a rescue extension added, implementing the above functionality.

Security impact
---------------
The rescue_password must be sent from Nova to Ironic, and thereafter to the
rescued node.  If, at any step in this process, this password is intercepted
or changed, an attacker can gain root access to the rescued node.

Additionally, the lookup endpoint will be required to return the rescue
password as a response to the first lookup once rescue is initiated. That
means a properly executed timing attack could recover the password, but since
this would also cause the rescue to fail (despite the node changing states),
it's at worst a denial of service.

Security vulnerabilities involving the rescue ramdisk is another source of
attacks. This is different from existing ramdisk issues, as once the rescue
is complete, the tenant would have access to the ramdisk. This means deployers
may need to ensure no secret information (such as custom cleaning steps or
firmwares) are not present in the rescue ramdisk.

IPA is entirely unauthenticated.  If IPA endpoints continue to be available
after a node is rescued, then attackers with access to the tenant network
would be able to leverage IPA's REST API to gain privileged access to the
host. As such, IPA itself should be shut down, or the network should be
sufficiently isolated during rescue operations.

Other end user impact
---------------------
We will add rescue and unrescue commands to python-ironicclient.

Scalability impact
------------------
None.

Performance Impact
------------------
None.

Other deployer impact
---------------------
Add conductor.rescue_callback_timeout config option.

Multi-tenant deployers will most likely need to support two ram disks--one
running IPA for use with normal node-provisioning tasks, and another running
IPA for rescue mode (with non-rescue endpoints disabled). This is to ensure
the full suite of tooling and authentication needed for secure cleaning is not
given to a tenant.

Additionally, in some environments, operators may not want to use the full
Ironic Python Agent inside the rescue ramdisk, due to it's requirement for
python or linux-centric nature. They may use statically compiled software
such as onmetal-rescue-agent [0]_ to perform the lookup and heartbeat needed
to finalize cleaning.

Developer impact
----------------
None.

Implementation
==============

Assignee(s)
-----------
Primary assignee:
  JayF

Other contributors:
  Help Wanted!

Work Items
----------
See proposed changes.

Dependencies
============
* Updating the Ironic virt driver in Nova to support this.

Testing
=======
Unit tests and Tempest tests must be added.

Upgrades and Backwards Compatibility
====================================
Clients that are unaware of rescue-related states may not function correctly
with nodes that are in these states.

Documentation Impact
====================
Write documentation.

References
==========
.. [0] https://github.com/rackerlabs/onmetal-rescue-agent
