..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

====================
Cisco IMC PXE Driver
====================

https://blueprints.launchpad.net/ironic/+spec/cisco-imc-pxe-driver

This spec proposes adding a new driver which provides out-of-band non-ipmi
based control of UCS C-Series servers through CIMC.

Problem description
===================

Current drivers only allow for control of UCS servers via either IPMI or UCSM,
the Cisco UCS C-Series operating in standalone mode can also be controlled via
CIMC using its http/s XML API. This provides finer control over the server than
IPMI can, and doesn't require the extra infrastructure that UCSM needs.

Proposed change
===============

Power and Management interfaces will be created that understand how to talk to
CIMC, and these will be used in conjunction with the PXE boot interface,
ISCSI deploy interface and Agent deploy interface to create pxe_cimc and
agent_cimc drivers.

The CIMC Power interface will inherit the base PowerInterface and implement:

  * get_power_state
  * set_power_state
  * reboot
  * get_properties
  * validate

The CIMC Management interface will inherit the base ManagementInterface and
implement:

  * get_properties
  * validate
  * get_supported_boot_devices
  * get_boot_device
  * set_boot_device
  * get_sensors_data - This will raise NotImplemented

Alternatives
------------

The alternatives are to use the pxe_ipmi or agent_ipmi driver to control the
UCS C-Series via IPMI, or install the infrastructure to manage these servers
with UCSM and use the pxe_ucs or agent_ucs driver.

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

When enrolling a node into ironic a user must provide:
  * cimc_address - CIMC IP Address
  * cimc_username - CIMC Username
  * cimc_password - CIMC Password

Additional properties added to ironic.conf in a [cimc] section are:

  * max_retry: maximum times to retry any power operation, default: 6
  * action_interval: the time to wait in-between power operation retries

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  sambetts

Other contributors:
  None

Work Items
----------

* Write CIMC Power Interface and respective unit tests
* Write CIMC Management Interface and respective unit tests
* Create drivers from new and existing interfaces
* Create configuration documentation for pxe_cimc and agent_cimc

Dependencies
============

This driver requires this installation of the ImcSDK on the node where the
ironic conductor will be running.

Testing
=======

Unit tests for the Power and Management interfaces will be provided.
Functional testing will be added in the future.

Upgrades and Backwards Compatibility
====================================

There should be no compatibility issues introduced by this change.

Documentation Impact
====================

* Writing configuration documentation.
* Updating Ironic documentation section _`Enabling Drivers`:
  http://docs.openstack.org/developer/ironic/deploy/drivers.html with pxe_cimc
  and agent_cimc driver related instructions.

References
==========

_`Cisco Imc Python SDK v0.7.1`: https://communities.cisco.com/docs/DOC-37174
