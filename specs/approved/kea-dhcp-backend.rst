..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

================
Kea DHCP backend
================

https://bugs.launchpad.net/ironic/+bug/2081847


Problem description
===================

DHCP is a critical service for assigning IP addresses to instances in
OpenStack deployments. Both Ironic and Neutron rely on dnsmasq to provide
DHCP services. However, dnsmasq has become increasingly unreliable,
with intermittent DHCP failures, frequent restarts and crashes of dnsmasq
processes, etc.

Refer to the bug on dnsmasq here:
https://bugs.launchpad.net/ironic/+bug/2026757.


Proposed change
===============

Add a new Kea DHCP backend for Ironic and Neutron as an alternative DHCP
provider. This will provide a more reliable DHCP option that's easily
extensible while maintaining compatibility with existing systems.

* Create a new DHCP provider class extending the BaseDHCP interface.
* Add configuration options to enable and configure Kea DHCP.
* Add methods to manage DHCP options, leases, and port updates using Kea APIs.
* Ensure DevStack support for Kea
* Update documentation to cover the addition of Kea DHCP, setup and usage.

Ironic will interact with the Kea DHCP server via HTTP-based APIs [1]_.

* ``config-get``, ``config-set``: Manage Kea configuration
* ``reservation-get``: Retrieve host reservations that will be handled
  externally via a host-reservation database shared between Kea and
  Ironic/Neutron query to retrieve reservation data. Dynamic reservation
  updates (``reservation-add`` and ``reservation-del``) require a premium ISC
  subscription and are not supported in this implementation [3]_.
* ``lease4-get``, ``lease6-get``: Retrieve lease information
* ``subnet4-add``, ``subnet6-add``: Add new subnets
* ``statistic-get``: Monitor DHCP server statistics

The Kea DHCP backend can be added with or without an agent layer. Both
approaches will use Kea's HTTP-based APIs, but differ in their architecture
and how Ironic interacts with the Kea DHCP server.

An agent approach has more moving parts and complexity, but better scalability
for large deployments, local management of Kea instances and reduced network
traffic to central Ironic service.

* Flow: Ironic → Driver → Agents → Kea Servers
* Kea DHCP Agent is deployed on each DHCP server node and manages local Kea
  config and handles communication between Ironic and Kea.
* Ironic DHCP Driver implements Ironic DHCP interface and communicates with
  the Kea DHCP Agent.
* Ironic sends DHCP configuration to Ironic DHCP Driver which in turn
  distributes it to Kea agents to apply config to local Kea servers.
* For lease management, agents monitor local Kea lease changes report changes
  back to Ironic DHCP Driver.

The agentless approach will have a much simpler architecture, probably easier
to implement and maintain with direct control from Ironic, but may not scale
as well, increased network traffic to Kea servers and even a potential
performance impact on Ironic for large-scale operations.

* Flow: Ironic driver translates configs to Kea API calls and applies changes
        directly to Kea servers.
* Ironic manages all Kea servers, through direct Kea API no agent layer.
* The Ironic driver translates configs to Kea API calls and applies changes
  directly to Kea servers.
* For lease management, maybe a periodic polling of Kea servers for lease
  updates, or, a webhook mechanism.

Alternatives
------------

* Find a way to improve existing Dnsmasq implementations. It's worth noting
  that dnsmasq has inherent limitations as it's really intended for small
  computer networks even though Ironic has been using it for the longest, so
  addressing these problems may require significant re-engineering. It's also
  single maintainer OSS project, as of the time of this specification.
  The fact it is a single maintainer project results in long spans of
  inactivity, which increases consumer risk for a project like OpenStack.
* Use a different DHCP provider than Kea that is also actively maintained,
  provides the reliability, flexibility, and integration Kea offers or better.
* Develop a completely new, custom DHCP server which will be quite an
  undertaking and additional long-term technical debt.

Data model impact
-----------------

No changes to Ironic's data model are required.

State Machine Impact
--------------------

No changes to the state machine are required.

REST API impact
---------------

No changes to the REST API are required.


Client (CLI) impact
-------------------

No changes to python-ironicclient are required.

RPC API impact
--------------

No changes to the RPC API are required.

Driver API impact
-----------------

A new DHCP provider class will be added, but this should not impact existing
drivers.

Nova driver impact
------------------

None

Ramdisk impact
--------------

No changes to the ironic-python-agent or ramdisk are required.

Security impact
---------------

There's no expected security trade-offs with the addition of a Kea DHCP
backend. The increase in options for operators limits overall risk by
providing additional options, which should be a net security gain.

In the event of such occurrences in the future, its active development will
likely ensure timely security updates.

Other end user impact
---------------------

None

Scalability impact
------------------

Kea DHCP is designed for better scalability than dnsmasq, which could improve
performance, especially for large deployments.

Performance Impact
------------------

Kea DHCP will likely offer performance improvements over dnsmasq, especially
for large deployments with thousands of machines.

Other deployer impact
---------------------

Deployers will need to install and configure the Kea DHCP server
alongside Ironic, likely in the same manner as dnsmasq, but with Kea-specific
configurables such as network interfaces, IP address ranges, and lease times.

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Afonne-CID (cid).

Other contributors:
  Jay Faulkner (JayF).

Work Items
----------

* Write a Kea DHCP backend extending the BaseDHCP interface.
* Add unit tests and DevStack support for running with Kea.
* Configure at least one CI job to use Kea DHCP.
* Add Bifrost support for the new Kea DHCP backend.
* Implement unmanaged inspection support for Kea DHCP.
* Update documentation.


Dependencies
============

* Kea DHCP server [2]_.


Testing
=======

Add tests to verify full DevStack support, new Tempest tests specific to
Kea DHCP functionality, and new unit tests for:
* Retrieving lease information via Kea APIs.
* Ensuring Kea correctly reads from the host-reservation database.

Upgrades and Backwards Compatibility
====================================

Existing dnsmasq support will remain unchanged.


Documentation Impact
====================

* Full documentation on Kea’s capabilities and how it's different from dnsmasq
  with cross-references to external Kea resources.
* Document configuration options and steps on switching from dnsmasq to Kea,
  including configuring Kea to use a read-only host-reservation database and
  how to set up Ironic/Neutron to manage this database.
* Installation, configuration, and architecture documentations should present
  Kea as a configurable option, with clear instructions on how users can choose
  between Kea and dnsmasq.
* API documentation will need to be updated to reflect any changes to existing
  methods and how they now interact with Kea compared to dnsmasq.
* Sections of the current documentation that might have referenced dnsmasq as
  the default or only DHCP provider will need to be updated to reflect that
  Kea is now also a supported backend.


References
==========

.. [1] https://kea.readthedocs.io/en/latest/api.html
.. [2] https://www.isc.org/kea/
.. [3] https://kea.readthedocs.io/en/latest/arm/hooks.html
