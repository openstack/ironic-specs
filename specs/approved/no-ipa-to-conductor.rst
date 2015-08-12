..
   This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=================================
No IPA to conductor communication
=================================

https://storyboard.openstack.org/#!/story/1526486

This spec intends to make agent->ironic communication optional, instead
using polling to make all communication inbound to the agent.

Problem description
===================

As part of the boot process IPA must call the ironic API to query its node
ID, and notify ironic when it's completed the boot process.

This implies that a target node has network access to the ironic API, which
means that a malicious party could in theory attack the control plane from an
instance. If the same control plane holds Keystone, Neutron, or other such
services, the attacker can now DoS or compromise those. This grants them
significant control over the infrastructure.

A deployer could mitigate this security flaw by using two networks for hosts:

* A provisioning network, which has access to the ironic API, but no ability
  to communicate with other nodes in the datacenter.

* A tenant network, which can communicate with the outside world, and other
  hosts, but cannot contact the ironic API.

However, this doesn't scale with medium to mega scale deployers who leverage
layer 3 network topologies. In L3 networks a subnet is constrained to a single
rack. This means that to leverage two networks to image hosts one would need
to provision a second subnet for every single rack.

Compounding the issue further, different networks with different fundamental
security policies implies that these disparate policies must be enforced.
Thus, for each of your provisioning networks that require access to the ironic
API, there must be access controls configured and enforced in the firewall.

In the context of hundreds, or thousands of racks, this does not scale.

An example of the (potential) security problem:

* Bob boots a host with ironic, this host is publicly routable to the
  internet. Mallory finds and compromises this host. She then attacks the
  ironic API from this host. Once she compromises the ironic API, she then
  starts booting other hosts in the datacenter with a compromised disk image.
  If Bob uses ironic to manage every host in the datacenter, then Mallory
  has now effectively owned an entire datacenter.

To remediate this, we need to reduce the attack surface of the control plane
by removing the need for the data plane to be able to send traffic to the
API host. To do this, we need to be able to tell the agent that it should not
call ironic, and make ironic poll the agent instead.

If the deployer runs DHCPD and serves PXE/iPXE from the control plane, then
there is still logical network access between the target node and the control
plane. However, this is easily fixed by running those services on dedicated
intermediary hosts which do not have network access to the rest of the
control plane.

In this context the network flow is::

  +-----------+     +-----------+     +-------------+
  |           |     |           +---> |             |
  | Conductor +---> | iPXE host |     | Target node |
  |           |     |           | <---+             |
  +-----------+     +-----------+     +-------------+
  |                                     ^
  +-------------------------------------+


And a simple example of the provisioning process would be:

1. Conductor receives call to boot node.
2. Conductor creates boot data, without the ipa-api-url parameter.
3. Conductor sends OOB call to power target node on.
4. Target node boots, uses DHCP to get IP.
5. Target node runs PXE/iPXE, pulls data from ipxe host.
6. Target boots and runs IPA.
7. Conductor polls for IPA until it is alive.
8. Conductor calls IPA's ``get_hardware_info`` command to get information
   about the node's hardware. This is used to validate the MAC addresses
   to ensure this is the node we are expecting.
9. Conductor calls IPA's ``node_info`` command to give it the data it needs
   to do its job, including the config data returned by the lookup API.
10. Conductor calls IPA commands on target node to walk it through the
    provisioning process.
11. Conductor polls instance at a configurable interval to check on state,
    gather information, etc.
12. Target is complete. Conductor reboots target node.
13. Conductor cleans up boot data.
14. Complete.

An example of this as a fix to the security problem:

* Bob boots a host with ironic, this host is publicly routable to the
  internet. Mallory finds and compromises this host. She attempts to attack
  the ironic API. The connection times out. She gives up and attacks the iPXE
  host. She succeeds and compromises the iPXE host. She then attempts to
  attack the ironic API. The connection fails. Mallory, disappointed, gives
  up and puts her life of crime behind her.

In this case, even though Mallory has compromised the target node, there is no
intrinsic network access between the target node and the control plane. Thus
her only route of attack against the provisioning infrastructure would be DoS,
or to impact hosts which are in the process of booting. But she has no ability
to attack the queue, conductor, api, db, etc. She cannot gain control over the
infrastructure, and her attack has been limited.

Proposed change
===============

We will add two options to the [agent] category:

* ``poll_only``: BoolOpt to enable passive mode. Defaults to False.
* ``poll_interval``: IntOpt, poll interval in seconds. Defaults to the
  current ``[api]/ramdisk_heartbeat_timeout`` setting.

And one option to the [api] category:

* ``disable_agent_api``: BoolOpt which disables the agent lookup and heartbeat
  APIs. Defaults to False.

If ``poll_only`` is enabled, we do not pass the ``ipa-api-url`` kernel command
line parameter to IPA, which will disable the node lookup and heartbeat
mechanisms.

If ``poll_only`` is enabled, the conductor will use a periodic task to query
each agent at an interval as defined in 'poll_interval' instead of querying
the agent after a heartbeat is received. This periodic task will only query
nodes in states IPA would normally be heartbeating in: (DEPLOY*, RESCUE*,
CLEAN*).

It is assumed that the deployer should disallow communication between the
target node and the ironic API. However, if an API call does come through
when ``disable_agent_api`` is True, then Ironic should return a 403.

For this mode, we will also need to remove ``ipa-api-url`` being passed as
kernel parameter to the agent.

We will also add a ``node_info`` command to IPA, described below, which the
conductor will use to pass the "lookup data" to a node.

Last, we will add a ``get_hardware_info`` command to IPA, which will return
hardware info we can use to ensure the node is the node we are expecting.

Notes:

* This spec depends on the assumption that ironic can look up the node IP in
  Neutron. Deployments without Neutron are not supported with poll_only=True.
  This may be added in the future.

* ironic-inspector is out of scope for this feature, as it does not use
  Neutron.

* There may be a use case to set ``poll_only`` per node, rather than globally.
  However, this is outside the scope of this spec.

Alternatives
------------

None.

Data model impact
-----------------

None

State Machine Impact
--------------------

None

REST API impact
---------------

The lookup and heartbeat APIs used by agents will now return a 403 when
``disable_agent_api`` is set to True.

Client (CLI) impact
-------------------

None

"ironic" CLI
~~~~~~~~~~~~

None

"openstack baremetal" CLI
~~~~~~~~~~~~~~~~~~~~~~~~~

None

RPC API impact
--------------

None

Driver API impact
-----------------

Deploy drivers will need to ensure that anything reaching into some agent
can also be triggered by a periodic task.

Nova driver impact
------------------

None

Ramdisk impact
--------------

ironic-python-agent mostly supports this already, as it will run just fine
without an API URL.

Some steps may also require other data returned by the lookup endpoint. We'll
add a new synchronous command ``node_info``, which will take this data as a
single ``node_info`` argument and store it in memory for later use. Ironic will
call this command when it first notices that IPA is up.

To validate the node is the node we expect, we'll add another synchronous
command ``get_hardware_info``. This will return the MAC addresses at first,
but could be evolved later to include things like serial numbers, etc.

Security impact
---------------

This change will prevent a malicious actor from using IPA as a vector of attack
against the ironic API.

Note that TLS on the agent API is still important to completely secure the
interactions between IPA and Ironic; however, this is outside the scope of
this spec.

Other end user impact
---------------------

None

Scalability impact
------------------

Polling target nodes for state from the conductor could have scale issues
when managing many thousands of nodes. However, polling will be done in a
thread pool, and so there should be limited impact.

Performance Impact
------------------

Polling in a large parallel fashion will introduce additional CPU load on the
conductor nodes. Deployers may need to scale out their conductor nodes to
handle the additional load.

Other deployer impact
---------------------

Recap of the configuration options added:

[agent]
* poll_only (type=BoolOpt, default=False)
* poll_interval (type=IntOpt, default=<[api]/ramdisk_heartbeat_timeout>)

[api]
* disable_agent_api (type=BoolOpt, default=False)

We should document where each of these needs to be set (API vs conductor
hosts).

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  jroll

Other contributors:
  penick

Work Items
----------

* Enable IPA to skip the lookup process when ironic does not pass the
  ``ipa-api-url`` kernel parameter.

* Create the ``get_hardware_info`` IPA command.

* Create the ``node_info`` IPA command.

* Add the new options to ironic.

* Enable Ironic to use polling for agent actions/status rather than using
  the heartbeat as a trigger.

* Make ironic call the ``node_info`` command after IPA boots, when in polling
  mode.

* Disable heartbeating in the agent in polling mode.

* Test scale and performance impact on periodic tasks.

* Lots of documentation, especially in admin guides. It may also be worth a
  large blurb in the reference architecture guide.


Dependencies
============

None.

Testing
=======

We should configure one of the existing tempest jobs to use this feature.

Upgrades and Backwards Compatibility
====================================

The deployer must update IPA in their images to support passive mode prior to
upgrading Ironic and enabling the feature. If they do not, all imaging
attempts will fail.

Documentation Impact
====================

This feature needs to be documented as a deployment option.

The ironic-inspector docs need to be updated to capture that inspector won't
work with poll_only=True.

Admin docs should be updated to note that firewall rules need to be
implemented to actually close network access between the target node and
the ironic API.

References
==========

None
