..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
DRAC Management driver for Ironic
==========================================

https://blueprints.launchpad.net/ironic/+spec/drac-management-driver

The proposal presents the work required to add support for boot management
features for Dell Remote Access Controllers.


Problem description
===================
Dell Remote Access Controller is an interface card from Dell offering remote
system management. This proposal adds the boot management capabilities for
DRAC.

Proposed change
===============
* Create a DracManagement class and implement the following methods interacting
  with the WS-Management API "(WS-Man)" described in the ``DCIM BIOS and Boot
  Management Profile`` using the python binding of the OpenWSMAN library:

    - set_boot_device() - To set the boot device for a node. The ``persistent``
                          flag will be supported to indicate if the change
                          should be applied for the next boot only, or
                          persistently.

    - get_boot_device() - To get the current boot device of a node with the
                          indication whether it's persistent, or not.

    - get_supported_boot_devices() - To get a list of the supported boot
                                     devices of a node. The supported boot
                                     devices will be ``disk`` and ``pxe``.

* Add DracPXEDriver class to the list of the available drivers, which uses the
  PXEDeploy, DracPower, and DracManagement interfaces. (The above change is a
  prerequisite for this one, because PXE requires setting the boot
  device to network).

Alternatives
------------
None

Data model impact
-----------------
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
None

Developer impact
----------------
None


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  ifarkas

Other contributors:
  None

Work Items
----------

* Add methods supporting boot management to the management interface.

* Create the DracPXEDriver class.

Dependencies
============

* This feature depends on the python binding of the OpenWSMAN library which was
  introduced by the power management interface of the DRAC driver.

* This feature requires 11th or 12th generation of Dell PowerEdge servers.

Testing
=======

* Unit tests

* 3rd-party CI: we would like to do it for this driver, but do not have
  sufficient hardware available at this time.

Documentation Impact
====================
None

References
==========

* `Spec for ManagementInterface <https://opendev.org/openstack/ironic-specs/src/branch/master/specs/juno/new-management-interface.rst>`_

* `OpenWSMAN library <http://openwsman.github.io/>`_

* `DCIM BIOS and Boot Management Profile 1.2 <http://en.community.dell.com/techcenter/systems-management/w/wiki/3511.dcim-bios-and-boot-management-profile-1-2.aspx>`_
