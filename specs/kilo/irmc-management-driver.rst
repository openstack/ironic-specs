..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=================================
iRMC Management Driver for Ironic
=================================

https://blueprints.launchpad.net/ironic/+spec/irmc-management-driver

The proposal presents the work required to add support for management
standard interface for FUJITSU PRIMERGY iRMC, integrated Remote
Management Controller, Drivers in Ironic.


Problem description
===================
FUJITSU PRIMERGY iRMC allows IPMI to get/set boot mode either legacy
BIOS or UEFI, and SCCI to get sensor data.
However the current Ironic standard Management Module,
ipmitool.IPMIManagement, cannot make use of the iRMC's capabilities.


Proposed change
===============
This module inherits ipmitool.IPMIManagement and overrides the
following two functions for iRMC Drivers, namely pxe_irmc, iscsi_irmc,
and agent_irmc [*]_, in order to make use of iRMC IPMI boot mode
get/set capability and SCCI get sensor data.

This module will be re-factored, when Ironic set/get boot mode I/F
is standardized in Ironic Management Interface.

* set_boot_device() - If 'boot_mode:uefi' is specified in
  capabilities parameter within properties field of an Ironic node,
  this function issues IPMI Set System Boot Options Command with
  setting on the bit 5 of data1, BIOS Boot Type to UEFI, in the
  parameter selector 5 to iRMC.
  Otherwise this function just calls the parent class function,
  ipmitool.IPMIManagement.set_boot_device() as default.

* get_sensors_data() - If optional parameter 'sensor_method=scci' is
  specified in [irmc] section of the ironic configuration file, this
  function gets sensors data via iRMC SCCI which returns not only
  standard but also vendor specific sensor data.
  iRMC SCCI uses `python-scciclient package <https://pypi.python.org/pypi/python-scciclient>`_.
  Otherwise, if the optional parameter is the default value
  'sensor_method=ipmitool', this function just calls the parent class
  function, ipmitool.IPMIManagement.get_sensors_data() as default.

.. [*] Driver consists of five elements.
       In the initial implementation, iRMC driver supports three
       combinations out of all combinations.

       ==========  =====  ====  ======  ==========  =======
       driver      power  boot  deploy  management  console
       ==========  =====  ====  ======  ==========  =======
       pxe_irmc    irmc   pxe   iscsi   irmc        ipmi
       iscsi_irmc  irmc   irmc  iscsi   irmc        ipmi
       agent_irmc  irmc   irmc  agent   irmc        ipmi
       ==========  =====  ====  ======  ==========  =======

       Other combinations are considered in the next development cycle
       based on customer's feedback.

Alternatives
------------
There is no alternative if bare metal node is necessary for booting in
UEFI mode automatically.

IPMI management module can be used only if deployer sets boot mode of
a bare metal node manually into UEFI.

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
Admin credentials will be stored unencrypted in the DB and they will
be visible in the driver_info field of the node when a node-show is
issued. But only the ironic admin user will have access to the Ironic
DB and node details.

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
* In order to use iRMC driver, iRMC S4 and beyond is required.
  Deployer is notified by error message if the iRMC version is not
  valid.

* The driver_info fields and the [irmc] section parameters in the
  ironic configuration file are necessary which are specified in
  `iRMC Power Driver for Ironic <http://specs.openstack.org/openstack/ironic-specs/specs/kilo/irmc-power-driver.html>`_.

* Boot mode maybe set to BIOS or UEFI following command described in
  `Bare Metal Service Installation Guide: Boot mode support <http://docs.openstack.org/developer/ironic/deploy/install-guide.html#boot-mode-support>`_
  or `iLO drivers: Boot mode support <http://docs.openstack.org/developer/ironic/drivers/ilo.html#boot-mode-support>`_.

 * To configure a node in BIOS mode::

    ironic node-update <node-uuid> add properties/capabilities='boot_mode:bios'

 * To configure a node in UEFI mode::

    ironic node-update <node-uuid> add properties/capabilities='boot_mode:uefi'

Developer impact
----------------
None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Naohiro Tamura (naohirot)

Other contributors:
  None

Work Items
----------
* Implement iRMC Management Module for the iRMC Drivers (pxe_irmc,
  iscsi_irmc, agent_irmc) by inheriting ipmitool.IPMIManagement and
  overrides set_boot_device() and get_sensors_data().

Dependencies
============
* This feature requires iRMC S4 and beyond that is at least BX S4 or
  RX S8 generation of FUJITSU PRIMERGY servers.

* This feature requires 'ipmitool' command and
  `python-scciclient package <https://pypi.python.org/pypi/python-scciclient>`_.

* This feature implemented based on the iRMC Drivers (pxe_irmc,
  iscsi_irmc, agent_irmc) which are defined in
  `iRMC Power Driver for Ironic <http://specs.openstack.org/openstack/ironic-specs/specs/kilo/irmc-power-driver.html>`_
  and `iRMC Virtual Media Deploy Driver for Ironic <http://specs.openstack.org/openstack/ironic-specs/specs/liberty/irmc-virtualmedia-deploy-driver.html>`_.

Testing
=======
* Unit Tests

* Fujitsu plans Third-party CI Tests

Upgrades and Backwards Compatibility
====================================
The default behavior of this driver remains compatible with
ipmitool.IPMIManagement.

Documentation Impact
====================
The required driver_info fields and [irmc] section parameters in the
ironic configuration file need be included in the documentation to
instruct operators how to use Ironic with iRMC.

References
==========
* `FUJITSU Software ServerView Suite, Remote Management, iRMC S4 -   integrated Remote Management Controller <http://manuals.ts.fujitsu.com/file/11470/irmc-s4-ug-en.pdf>`_

* `iRMC Power Driver for Ironic <http://specs.openstack.org/openstack/ironic-specs/specs/kilo/irmc-power-driver.html>`_

* `iRMC Virtual Media Deploy Driver for Ironic <http://specs.openstack.org/openstack/ironic-specs/specs/liberty/irmc-virtualmedia-deploy-driver.html>`_

* `python-scciclient package <https://pypi.python.org/pypi/python-scciclient>`_

* `New driver ManagementInterface <http://specs.openstack.org/openstack/ironic-specs/specs/juno/new-management-interface.html>`_

* `DRAC Management driver for Ironic <http://specs.openstack.org/openstack/ironic-specs/specs/juno/drac-management-driver.html>`_

* `iLO Management Interface <http://specs.openstack.org/openstack/ironic-specs/specs/kilo/ilo-management-interface.html>`_

* `iLO drivers: Boot mode support <http://docs.openstack.org/developer/ironic/drivers/ilo.html#boot-mode-support>`_

* `Bare Metal Service Installation Guide: Boot mode support <http://docs.openstack.org/developer/ironic/deploy/install-guide.html#boot-mode-support>`_
