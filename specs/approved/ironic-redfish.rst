..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=========================
Redfish driver interfaces
=========================

https://bugs.launchpad.net/ironic/+bug/1526477

This specification proposes the addition of a new driver in order to support
Ironic deployment on Redfish compliant servers.

Problem description
===================

The Distributed Management Task Force (DMTF) has published a new specification
called Redfish (refer to http://www.dmtf.org/standards/redfish) to provide a
RESTful based API to manage servers in a standard way. This specification aims
at adding support to Ironic for controlling Redfish compliant servers.

Proposed change
===============

Power and management interfaces will be extended with Redfish support.
The new Redfish module can use either the python-redfish (when it is mature
enough) or the sushy library for communicating with a Redfish system.
(refer to https://github.com/openstack/python-redfish and
https://github.com/openstack/sushy)

The goal is to provide power management similarly to what is done
in the pre-existing in-tree drivers.

Note that no OEM specific extension will be supported.

Alternatives
------------
No real alternative exists currently

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

Client (CLI) impact
-------------------
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
The following driver_info fields are required while enrolling nodes into Ironic:
    * redfish_uri URI of the System to interact with
      (e.g.: http://x.y.z.t/redfish/v1/Systems/1 or
      https://redfishmgr/redfish/v1/Systems/CX34R87)
    * redfish_username: User account with admin/server-profile access privilege
    * redfish_password: User account password
    * redfish_verify_ca: this property contains either a boolean value,
                         a path to a CA_BUNDLE file or directory with
                         certificates of trusted CAs. If set to True
                         the driver will verify the host certificates;
                         if False the driver will ignore verifying the
                         SSL certificate; If it's a path the driver will
                         use the specified certificate or one of the
                         certificates in the directory. Defaults to True.

The following new configuration variables are proposed (and their default
values) to be added to the conductor variable group:

* [redfish]/connection_attempts = 5

  Maximum number of attempts to try to connect to Redfish

* [redfish]/connection_retry_interval = 2

  Number of seconds to wait between attempts to connect to Redfish

Developer impact
----------------
None

Implementation
==============

Assignee(s)
-----------

Primary assignee:

* bcornec
* lucasagomes

Other contributors:

* ribaudr

Work Items
----------

* Add a new ``redfish`` hardware type, power and management interfaces.
* Write unit-tests for the new code.
* Modify the Ironic DevStack module to setup a virtual environment that
  is able to test nodes using the new Redfish driver.
* Write documentation.

Dependencies
============
This driver requires either that python-redfish or sushy installed on the
conductor node.

Testing
=======
Unit-tests will be implemented for Redfish support.

DevStack will be updated to setup the nodes with the redfish driver and
the libvirt mockup that is shipped with Sushy allowing it to be tests
in gate against virtual machines.

Upgrades and Backwards Compatibility
====================================
This driver will not break any compatibility with either the REST API or
the RPC API.

Documentation Impact
====================
* Updating Ironic documentation section _`Enabling Drivers`:
  http://docs.openstack.org/developer/ironic/deploy/drivers.html with Redfish
  related instructions.
* Updating Ironic install-guide documentation section
  _`Setup the drivers for the Bare Metal service`:
  http://docs.openstack.org/project-install-guide/baremetal/draft/setup-drivers.html

References
==========

_`Redfish DMTF`: http://www.dmtf.org/standards/redfish
_`python-redfish`: https://github.com/openstack/python-redfish
_`sushy`: https://github.com/openstack/sushy
