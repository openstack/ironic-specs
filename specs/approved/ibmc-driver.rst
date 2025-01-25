..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

**********************
Huawei iBMC Driver
**********************

https://storyboard.openstack.org/#!/story/2004635

This specification proposes to add new interfaces that provide Ironic support
to Huawei iBMC 2288H V5, CH121 V5 series servers.

Problem description
===================

Huawei’s Intelligent Baseboard Management System (iBMC) is an embedded server
management system that is used to manage servers throughout their lifecycle.
It provides a series of management tools for hardware status monitoring,
deployment, energy savings, and security protection.

In addition to managing the nodes using IPMI protocol, this specification
proposes to add hardware types and interfaces to manage Huawei servers using
iBMC REST API.

Proposed change
===============
New hardware type named *ibmc* will be added as part of this change.
New power, management and vendor interfaces will be implemented for
the *ibmc* hardware.

The interfaces use iBMC REST API to communicate with iBMC.
The interfaces used are:

    * iBMC.IBMCPower for Power operations
    * iBMC.IBMCManagement for Management operations
    * iBMC.IBMCVendor for Vendorspecific operations

* Power:

  This feature allows the user to turn the node on/off or reboot by using the
  power interface which will in turn call iBMC REST API.

* Management:

  This feature allows the user to get and set the primary boot device of the
  Huawei servers, and to get the supported boot devices.

* Vendor:

  This feature allows the user to perform vendor specific operations.
  For example, query the boot up sequence of the Huawei servers.

.. code-block:: bash

  $ openstack baremetal node passthru call --http-method GET \
    <node id or node name> boot_up_seq
  $ ["Pxe", "Hdd", "Cd", "Others"]


Alternatives
------------
None

Data model impact
-----------------
None

RPC API impact
--------------
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

Ramdisk impact
--------------
None

Other deployer impact
---------------------
The following driver_info fields are required while enrolling node into Ironic:

    * ibmc_address: The URL address to the ibmc controller, example: https://example.com
    * ibmc_username: User account with admin/server-profile access privilege
    * ibmc_password: User account password
    * ibmc_verify_ca(optional): Whether to verify the host certificate or the
      path of a certificate file or directory with trusted certificates

Developer impact
----------------
None

Implementation
==============

Assignee(s)
-----------

Primary assignee:

* QianBiao Ng (iampurse@vip.qq.com)
* Bill Chan (biaocy91@gmail.com)

Other contributors:
    None


Work Items
----------
* Add new iBMC hardware type, and adding new interfaces for Power,
  Management and Vendor.

* Writing appropriate unit tests to provide test coverage for iBMC driver.

* Writing configuration documents.

* Building a third party CI.

Dependencies
============
* Use python-ibmcclient library (not released) to communicate
  with HUAWEI iBMC REST API.

Testing
=======
* Unit tests will be implemented for new iBMC driver.

* Third party CI will be provided.

Upgrades and Backwards Compatibility
====================================
None

Documentation Impact
====================
* Updating Ironic documentation section ``Enabling Drivers``
  with iBMC related instructions.

References
==========
None
