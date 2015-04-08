..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

====================
Cisco UCS PXE driver
====================

https://blueprints.launchpad.net/ironic/+spec/cisco-ucs-pxe-driver

This blueprint proposes adding new driver that supports deployment of Cisco
UCS Manager (UCSM) managed B/C/M-series servers.

In this blueprint servers, nodes are used interchangeably that denotes Cisco
UCS B/C/M-series servers.

Problem description
===================

Current Ironic drivers require IPMI protocol to be enabled on all Cisco UCS
B/C/M-series servers in order to manage power operations. For security reasons
from UCS Manager version 2.2.2 IPMI protocol is disabled by default on all
servers.

Instead of using IPMI protocol, this blueprint proposes new driver to manage
Cisco UCS B/C/M-series servers using Cisco UCS PySDK.

Proposed change
===============

New power and management interfaces will be added as part of pxe_ucs driver.
This driver uses the Cisco UCS PySDK for communicating with UCSM.

This driver uses
    * pxe.PXEDeploy for PXE deployment operations
    * ucs.power.Power for power operations
    * ucs.management.UcsManagement for management interface operations

UCS Manager provides python SDK with which user can perform various operations,
like controlling the power of nodes, enabling the ports, associating the
servers etc. Physical and Logical entities in UCSM are represented as
ManagedObject.

* Power management:

  Controlling the power is similar to modifying the property of the
  corresponding ManagedObject. LsPower is the ManagedObject that represents the
  Power of service-profile. As part of managing the power, this provider
  modifies 'state' property of LsPower ManagedObject. UCSM takes care of the
  rest.

* Management Interface:

  This interface allows the user to get and set the boot-order on UCS B/C/M
  servers. LsbootDef is the ManagedObject that represents the boot-order of
  service-profile. This interface reads and updates LsbootDef ManagedObject
  appropriately for get and set boot-device operations.
  get_sensor_data() implementation is not in scope of this spec. A separate
  spec will be submitted.

Alternatives
------------
The IPMI Pxe driver could be used with Cisco UCS B/C/M-series servers, if IPMI
protocol is explicitly enabled overriding the default settings in UCS Manager.

Data model impact
-----------------
None

RPC API impact
--------------
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
None

Scalability impact
------------------
None


Performance Impact
------------------
None


Other deployer impact
---------------------
The following driver_info fields are required while enrolling node into ironic:
    * ucs_hostname: UCS Manager hostname/ip-address
    * ucs_username: User account with admin/server-profile access privilege
    * ucs_password: User account password
    * ucs_service_profile: service_profile DN (DistinguishedName) being used
      for this node.

The following parameters are added in to the newly created [ucs] section
in the ironic configuration file which is typically located at
/etc/ironic/ironic.conf.

    * max_retry: maximum number of retries, default value is set to 5.
    * action_timeout: seconds to wait for power action to be completed
      default value is 30 seconds, there is no explicit maximum limit.


Developer impact
----------------
None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
saripurigopi

Other contributors:
vinbs


Work Items
----------

* Add new pxe_ucs driver, extending power and management interface APIs.
* Writing and unit-test cases for pxe_ucs driver.
* Writing configuration documents.

Dependencies
============
This driver requires Cisco UCS Python SDK installed on the conductor node.

Testing
=======
Unit-tests will be implemented for new pxe_ucs driver.
tempest test suite will be updated to cover the pxe_ucs driver.
Continuous integration (CI) support will be added for Cisco UCS B/C/M series
servers.

Upgrades and Backwards Compatibility
====================================
This driver will not break any compatibility with either on REST API or RPC
APIs.

Documentation Impact
====================
* Writing configuration documents.
* Updating Ironic documentation section _`Enabling Drivers`:
  http://docs.openstack.org/developer/ironic/deploy/drivers.html with pxe_ucs
  driver related instructions.

References
==========

_`Cisco UCS PySdk`:https://github.com/CiscoUcs/UcsPythonSDK
