..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

============
Agent Driver
============

https://blueprints.launchpad.net/ironic/+spec/agent-driver

Ironic needs a deploy driver to interact with
`Ironic Python Agent <https://wiki.openstack.org/wiki/Ironic-python-agent>`_.

Problem description
===================

Today, Ironic is limited in the tasks that may be performed on a bare metal
node. Actions like 'update firmware' and 'secure erase disks' are not possible.
This is not due to any flaw in Ironic itself, but rather a limitation of the
deploy ramdisk used by Ironic's PXE driver.

Ironic Python Agent (IPA) is a project to provide a deploy agent for use by
Ironic. This agent is designed to run in a ramdisk and perform maintenance
on bare metal nodes, including hardware configuration and management,
provisioning, and decommissioning of servers. This agent exposes a REST API
that Ironic could call in order to perform various tasks.

Potential use cases:

* It is usually advantageous for a server to be running the latest BIOS
  firmware. Updating firmware is a critical feature in Ironic.

* End users often prefer that their data is erased when a server is released.
  The ability to run secure erase on a bare metal node's disks is another
  critical feature for Ironic.

* End users may have varying workloads they wish to deploy to a bare metal
  node. Some users may wish to run an application on bare metal, where others
  may wish to run a hypervisor. These different workloads may require
  different BIOS configurations, such as switching the VT bit on or off. This
  utility ramdisk enables Ironic to manage these configurations.

* Some users may desire faster boot times for a single bare metal node. The
  utility ramdisk may be used to accomplish this by leaving the node running
  the ramdisk, ready for deployment. This removes one POST cycle from the
  deployment process, compared to the PXE driver. Additionally, the ramdisk
  could write popular images to the boot device before deployment time, to
  remove the time spent writing the image.

* End users may wish to use cloud-init with a configdrive to load data such
  as SSH keys or network configurations. The ramdisk can write a partition
  containing the configdrive to be used by the end user and their image.

Ironic needs a deploy driver that interacts with the agent, rather than the
existing deploy ramdisk.

Proposed change
===============

A full deploy driver that interacts with the agent should be implemented.

The driver will:

* Allow the agent to look up the UUID stored by Ironic for the node that the
  agent is running on.

* Allow the agent to periodically heartbeat. The driver should use this
  heartbeat to verify that the agent is online.

* Leverage the periodic heartbeat as a callback mechanism.

* Make calls to the agent's REST API to instruct the agent to do
  deploy-related tasks, such as writing an image.

* Make calls to the agent's REST API to perform decommissioning tasks.

* Behave similarly to the existing PXE driver, with an explicit goal of
  eventually merging the two (not a hard requirement, if this turns out to
  be impossible, this goal may be dropped).

Alternatives
------------

The only alternative to building this driver would be to continue work on the
existing PXE deploy driver, to deliver the functionality identified in this
spec. Today, this driver has a very different model to the proposed agent
driver. It seems best, from discussion with Ironic's leadership, to start the
work diverged and work from both ends to converge on a single driver.

Data model impact
-----------------

* Two fields will exist on the `driver_info` field: "agent_url" and
  "agent_last_heartbeat".

REST API impact
---------------

Two vendor_passthru methods will be added:

Node lookup method:

* Description: The agent will post a JSON blob containing detailed hardware
  information to this endpoint at startup.  Ironic will use this
  information to determine which node the agent is running on (first iteration
  will look for matching MAC addresses), and pass the node's UUID back, along
  with an integer (in seconds) defining the timeout for receiving another
  heartbeat from the agent.

* Method type: POST

* Normal response code: 200

* Expected errors:

  * 400: Invalid hardware data structure version sent.
  * 404: A node with the provided hardware information could not be found.

* URL: /{api_version}/drivers/{driver}/vendor_passthru/lookup

* Parameters: none.

* Body JSON schema::

    {
      "version": 2
      "inventory": {
        "interfaces": [{...}, ...],
        "cpu": {...},
        "disks": [{...}, ...],
        "memory": {...}
      }
    }

* Response JSON schema::

    {
      "heartbeat_timeout": 300,
      "node": {
        "uuid": "some-uuid"
      }
    }

Heartbeat method:

* Description: The agent will periodically send a heartbeat to Ironic to
  signal that it is still running, as well as immediately after completing a
  command from Ironic. The agent driver will leverage this heartbeat as a
  callback mechanism. If a node is powered on, not provisioned, and a
  heartbeat is not received within a configurable timeout period, then Ironic
  will take action on this node; perhaps attempt a reboot or put the node into
  maintenance mode. As part of the heartbeat request, the agent provides its
  endpoint URL, where Ironic can issue requests to the agent. Ironic stores the
  time of the heartbeat and the agent's URL in `Node.driver_info`.

* Method type: POST

* Normal response code: 202

* Expected errors:
  * 404: The specified node could not be found.

* URL: /{api_version}/nodes/{node_uuid}/vendor_passthru/heartbeat

* Parameters: The node's UUID is part of the URL.

* Body JSON schema::

    {
      "agent_url": "http://1.2.3.4:9999/"
    }

* Response JSON schema: none

Driver API impact
-----------------

There is no impact on the driver API.

Nova driver impact
------------------

There is no impact on the Nova driver.

Security impact
---------------

Some authentication method will need to be implemented. Today, Ironic's PXE
driver sends a token through PXE configs when booting the deploy ramdisk, and
the agent driver could do something similar. More preferable would be to send
a secret through some out of band mechanism, and use that secret to
authenticate the agent ramdisk to Ironic.

This is TBD and will likely not be implemented in the first iteration of
this spec.

Other end user impact
---------------------

An end user will not interact directly with features provided by this driver.

Scalability impact
------------------

This change will involve communication between the agent and Ironic, which
may have some impact on performance. However, as the agent is able to
directly download and write images, Ironic will no longer have image traffic
going through it, and so overall network traffic by Ironic may be less.

Additionally, this driver may allow more nodes to be managed by a single
conductor, as the conductor only makes API calls to the agent, rather than
writing image data.

Ironic's API servers may end up doing more work if the agent is used in a
long-running model, as agents will be heartbeating periodically via the API.

The database is updated on each heartbeat, and so may also see extra load in
this scenario. However, this update call should be fairly fast, fairly
infrequent, and is done in the background in the conductor, so this should
cause only a small impact. This can be mitigated easily by scaling the
conductor cluster.

Performance Impact
------------------

This driver will not change the performance characteristics of any existing
code.

The driver does lock nodes sometimes - however, only during deploy and
tear_down will the lock be held for a significant amount of time.

The driver should behave similarly to the PXE driver when the hash ring
is rebalanced.

Other deployer impact
---------------------

To use this driver, deployers need to:

* Explicitly enable the driver in the configuration.

* Register nodes with the driver.

* Build an agent image using the tools available in the ironic-python-agent
  project.

A single configuration option will be added:

* agent.heartbeat_timeout: how long to wait before deciding that an agent
  is no longer running. Defaults to 300 seconds.

The driver classes added include:

* agent_ssh (AgentDeploy + SSHPower)

* agent_ipmitool (AgentDeploy + IPMIPower)

* agent_pyghmi (AgentDeploy + NativeIPMIPower)

* fake_agent (AgentDeploy + FakePower)

The agent will rely on access to the following services:

* Glance and/or Swift

* Neutron for DHCP

The references section below includes a diagram of an example architecture
for running Ironic with the agent driver.

Developer impact
----------------

This change should not impact other Ironic developers.


Implementation
==============

Assignee(s)
-----------

Primary assignee: JoshNang

Other contributors:

* jroll
* russell_h
* JayF
* dwalleck

Work Items
----------

* Implement the driver.

* Add a diskimage-builder element for IPA.

* Add devstack support for running Ironic with the IPA and PXE drivers
  *concurrently*. This is crucial for testing.

* Write Tempest tests for Ironic running with the agent driver.


Dependencies
============

None.


Testing
=======

The plan is to use the existing tempest tests, but with this driver specified.
This will require changes to tempest and devstack.

It is critical that deployers can use the PXE and IPA drivers in the same
environment. Tempest tests should explicitly test for this support.


Documentation Impact
====================

There will need to be clear documentation on how to run Ironic with the
agent driver.


References
==========

* `Ironic Python Agent wiki <https://wiki.openstack.org/wiki/Ironic-python-agent>`_

* `Ironic Python Agent repo <https://github.com/openstack/ironic-python-agent>`_

* `Example agent Architecture <https://8c9281d7b726ce93a4bd-63b3a98a421b1a8eb26177fc7852e719.ssl.cf5.rackcdn.com/teeth-architecture.png>`_
