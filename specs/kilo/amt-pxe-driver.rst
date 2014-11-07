..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
AMT PXE Driver
==========================================

https://blueprints.launchpad.net/ironic/+spec/amt-pxe-driver

This blueprint implements a new driver -- "PXEAndAMTToolDriver" which
supports deployment for AMT/vPro system on Desktops.

Problem description
===================

Currently there is no support with Ironic to do deployment for Desktops
within AMT/vPro system. This BP will extend Ironic to Desktop area.

Proposed change
===============
Implement a new driver -- "PXEAndAMTToolDriver" -- that uses
amttool to control the power of nodes with AMT System and uses
pxe to deliver the image to nodes. Following are details,

* Add new class PXEAndAMTToolDriver inherited from base.BaseDriver
  in ironic/drivers/pxe.py

* Add new class AMTPower inherited from base.PowerInterface
  in ironic/drivers/modules/amttool.py
  - ``validate()`` - Validate the node driver info

  - ``get_power_state()`` - Get the power state from the node

  - ``set_power_state()`` - Set the power state of the node,
    such as power on/off

  - ``reboot()`` - reboot the node

* Add new class AMTMangement inherited from base.ManagementInterface
  in ironic/drivers/modules/amttool.py
  - ``set_boot_device()`` - Set the boot device of the node

  - ``get_boot_device()`` - Get the boot device of the node

Alternatives
------------
None

Data model impact
-----------------
None

REST API impact
---------------
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
Additionally two fields need to be provided with driver_info
  * ``amt_address`` - node's IP address to connect to.
  * ``amt_password`` - node's password.

Developer impact
----------------
None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  tan-lin-good

Work Items
----------
Implement ``PXEAndAMTToolDriver`` class inherited from
``base.BaseDriver``.

Implement ``AMTPower`` class inherited from ``base.PowerInterface``

Implement ``AMTManagement`` class inherited from
``base.managementInterface``


Dependencies
============
amttool
It can be installed with package amtterm.

Testing
=======
Will add Unit Testing.

Upgrades and Backwards Compatibility
====================================
None

Documentation Impact
====================
Will document the usage of this driver.

References
==========
None
