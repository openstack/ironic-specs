..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=================
OpenBMC Driver
=================

https://bugs.launchpad.net/ironic/+bug/1634635

This proposal covers the addition of power and management interfaces for
OpenBMC and the addition of driver to the IPA and PXE driver classes.

Problem description
===================

Currently IPMI is not fully supported by OpenBMC. Instead, OpenBMC's
power is controlled through a RESTful interface. As well, the boot device can
be retrieved and set through this RESTful interface. While IPMI may be
supported by OpenBMC in the future, the recommended way to interact with it
will continue to be its `REST API <https://github.com/openbmc/docs/blob/master/rest-api.md>`_.

Servers running OpenBMC will require a new interface implementation to control
its power, another to set the boot device, and a hardware type that use
has these interfaces supported.

Proposed change
===============

The addition of an OpenBMCPower() module conforming to base.PowerInterface.
Login credentials will be specified as openbmc_address, openbmc_username, and
openbmc_password in the driver_info property of the node.

The addition of an OpenBMCManagement() module conforming to
base.ManagementInterface which also uses the openbmc_address, openbmc_username,
and openbmc_password as login credentials.

The module will login to the BMC, issue the proper command, then
log out of the BMC.

A hardware type, OpenBMCHardware, will be added. This hardware type will have
OpenBMCPower in it's 'supported_power_interfaces' list. This hardware type
will also have OpenBMCManagement in it's 'supported_management_interfaces'
list.


Alternatives
------------

Wait for IPMI functionality to be fully supported by OpenBMC. This would
allow the pxe_ipmitool and agent_ipmitool drivers to work.

The disadvantage here is that it is not the recommended method of interaction
with the BMC. As well, it is unknown when IPMI will be fully supported.

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

None

Nova driver impact
------------------

None

Ramdisk impact
--------------

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

None

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Michael Turek (mjturek)

Other contributors:
  Mark Hamzy (mark-hamzy)

Work Items
----------

*  Implement a new power interface, OpenBMCPower, conforming
   to base.PowerInterface.
*  Implement a new management interface, OpenBMCManagement, conforming
   to base.ManagementInterface
*  Add hardware type, OpenBMCHardware, that has these interfaces as supported.
*  Add documentation detailing usage of interfaces and driver.


Dependencies
============

This feature will only be usable by target hardware that runs OpenBMC.

Testing
=======

The feature will be tested using the `KVM on POWER OpenStack CI <https://wiki.openstack.org/wiki/PowerKVM>`_ environment.

The job will run the ironic tempest tests, but no new integration tests will be
added. The job will test against real hardware initially.

Unit tests will be added as well.


Upgrades and Backwards Compatibility
====================================

None

Documentation Impact
====================

Documentation will be added describing the new interfaces and how to use them.

References
==========

* `OpenPOWER <https://github.com/openbmc/openbmc>`_
* `OpenBMC REST API Examples <https://github.com/openbmc/docs/blob/master/rest-api.md>`_
* `KVM on POWER OpenStack CI <https://wiki.openstack.org/wiki/PowerKVM>`_
