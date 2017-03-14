..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

====================================
Redfish hardware type and interfaces
====================================

https://bugs.launchpad.net/ironic/+bug/1526477

This specification proposes the addition of a new ``redfish`` hardware
type, power and management interfaces in order to support ironic
deployment on Redfish compliant servers.

Problem description
===================

The Distributed Management Task Force (DMTF) has published a new specification
called Redfish (refer to http://www.dmtf.org/standards/redfish) to provide a
RESTful based API to manage servers in a standard way. This specification aims
at adding support to ironic for controlling Redfish compliant servers.

Proposed change
===============

This spec proposes adding a new ``redfish`` hardware type, power and
management interfaces. None of which will be enabled by default.

The new interfaces will use the `sushy`_ library in order to handle the
communication between the driver and the Redfish controller.

This library may be switched to `python-redfish`_ in the future after
re-evaluation by the ironic community. The switch to `python-redfish`_
is outside the scope of this specification, but it should not cause
any public interface to be changed. It would most likely involve code
changes and new configuration options.

Note that no OEM specific extension will be supported.

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
The following driver_info fields are required while enrolling nodes
into ironic:

    * ``redfish_address``: The URL address to the Redfish controller. It
      should include scheme and authority portion of the URL. For example:
      https://mgmt.vendor.com

    * ``redfish_system_id``: The canonical path to the ComputerSystem
      resource that the driver will interact with. It should include the
      root service, version and the unique resource path to a ComputerSystem
      within the same authority as the redfish_address property. For
      example: /redfish/v1/Systems/1

    * ``redfish_username``: User account with admin/server-profile
      access privilege. Although this property is not mandatory it's highly
      recommended to set a username. Optional

    * ``redfish_password``: User account password. Although this property
      is not mandatory it's highly recommended to set a password. Optional

    * ``redfish_verify_ca``: This property contains either a boolean
      value, a path to a CA_BUNDLE file or directory with certificates
      of trusted CAs. If set to True the driver will verify the host
      certificates; if False the driver will ignore verifying the SSL
      certificate; If it's a path the driver will use the specified
      certificate or one of the certificates in the directory. Defaults
      to True. Optional

For more information about the expected syntax of the
``redfish_system_id`` property check the `Resource identifier property
<http://redfish.dmtf.org/schemas/DSP0266_1.1.html#resource-identifier-property>`_
section of the DMTF specification.

The following new configuration variables are proposed (and their default
values) to be added to the conductor variable group:

* [redfish]/``connection_attempts``

  Maximum number of attempts to try to connect to Redfish.

* [redfish]/``connection_retry_interval``

  Number of seconds to wait between attempts to connect to Redfish.

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
* Modify the ironic DevStack module to setup a virtual environment that
  is able to test nodes using the new Redfish driver.
* Write documentation.

Dependencies
============
The new ``redfish`` power and management interfaces will require the
`sushy`_ library to be installed on the conductor node.

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
* Updating ironic documentation section `Enabling Drivers
  <http://docs.openstack.org/developer/ironic/deploy/drivers.html>`_
  with Redfish related instructions.

* Updating ironic install-guide documentation section
  `Setup the drivers for the Bare Metal service
  <http://docs.openstack.org/project-install-guide/baremetal/draft/setup-drivers.html>`_.

References
==========
* Redfish DMTF: http://www.dmtf.org/standards/redfish
* Sushy library: https://github.com/openstack/sushy
* python-redfish library: https://github.com/openstack/python-redfish

.. _`sushy`: https://github.com/openstack/sushy
.. _`python-redfish`: https://github.com/openstack/python-redfish
