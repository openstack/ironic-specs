..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

========================================
Power driver for SNMP-enabled smart PDUs
========================================

Launchpad blueprint:

https://blueprints.launchpad.net/ironic/+spec/ironic-snmp-power-driver

This blueprint proposes a mechanism for remote control of node power by
enabling or disabling sockets on a rack power strip. The result will
be a much wider generalisation of the hardware that can be controlled
by Ironic.


Problem description
===================

Currently Ironic's physical hardware support is restricted to servers
implementing power control with embedded management hardware, for
example a BMC or other system that implements IPMI. This blueprint
proposes widening Ironic's capabilities by adding support for a class
of power devices that are controllable by SNMP, including smart PDUs
with network connectivity.

Implementing an interface to smart PDUs would provide the ability to control
bare metal compute nodes built from commodity hardware that does not include
a BMC. A cost-conscious user may want to use bare metal compute without the
additional expense of server equipment that supports integrated power
management.


Proposed change
===============

The proposed design would introduce a new driver to Ironic, snmp.py.
A driver class would provide the SNMP manager entity which can convey
power management operations over SNMP all the way to the SNMP agent
running at the PDU. Classes would derive from this base driver to add
specific Object Identifiers (OIDs) and methods for interfacing with
different vendor equipment.

The proposed design would use the
`PySNMP package <https://pypi.python.org/pypi/pysnmp/>`_ which implements
many aspects of the SNMP technology. The PySNMP package supports all
SNMP versions e.g. v1, v2c and v3. Smart PDUs from APC appear to support
SNMP v1 and v3. The ability to specify a protocol version for each managed
PDU would be desirable. By default, version 3 should be used due to its
superior security.

Note that this blueprint only proposes power management for baremetal
compute node instances.

Note that this blueprint only proposes support for bare metal compute
nodes powered by a single outlet. It is assumed that servers with
redundant PSUs will also include embedded management such as a BMC.

There does not appear to be a standard MIB for PDU control. Each vendor
publishes its own enterprise MIB for power management and monitoring.
Conventionally the same enterprise MIB is implemented by all products
from a vendor. Addition of a new derived class to support a new vendor
MIB requires defining a function to convert outlet number into an SNMP OID,
and defining the values to write to turn the outlet on and off. The design
should enable the creation more complex interactions if a vendor MIB
was defined in a way that required it.

Market research reports indicate the PDU market segmentation is between the
following companies (in descending order of market share):

* APC Corp.
* CyberPower Systems Inc.
* Eaton Corp.
* Emerson Network Power
* Raritan Inc.
* Server Technology Inc.
* AFCO Systems
* Enlogic Systems LLC
* Geist Ltd.
* Hewlett-Packard Co.
* Racktivity NV.

In its first implementation the SNMP power driver will support at least the 3
most dominant vendors - APC, CyberPower and Eaton/Pulizzi.

Alternatives
------------

There is no clear alternative mechanism for interfacing with smart PDUs.
Screen-scraping of human-formatted data from CLI terminals or web interfaces
sounds like a bad idea.

The advantages of an SNMP-based approach are:

* MIBs tend to be a common interface implemented by all products from a vendor.
  A MIB interface is not susceptible to variations between products.
* Once published a MIB interface is not changed in a backward-incompatible
  way. A MIB interface is not susceptible to variations between firmware
  versions.
* Conventionally vendor MIBs are published and freely available.

Options exist for turning symbolic representation of MIB objects into a
MIB-independent OID form.

* The Net-SNMP package comes with the ``snmptranslate`` command-line tool
  which can turn any MIB object into OID.
* libsmi includes a tool called smidump can be used to convert MIB definitions
  into Python dictionaries with some hierarchical structure.
* The `PySMI <https://pypi.python.org/pypi/pysmi>`_ pure-Python package is
  able to parse MIB files into either JSON document or a Python module which
  PySNMP can readily consume. The PySMI package comes with the ``mibdump.py``
  tool which can be used at the command line for MIB conversion similar
  to what ``snmptranslate`` does.
* Current PySNMP has PySMI as a dependency so PySNMP would invoke PySMI
  automatically to parse a MIB whenever needed.

Note that these approaches are heavyweight solutions. For example,
parsing just the APC vendor MIB involves the creation of a hierarchical
structure of 2671 dictionaries to represent the OIDs. Only one OID is
actually required.

The proposed solution is to manually extract only the required OID
definition from the autogenerated output. This works, because a
symbolic representation for the OID is produced. The manual transfer is
done once: published MIBs are immutable, and the address and semantics of an
OID can never change. The result is lightweight, without loss of
functionality.

Data model impact
-----------------

On creation of an Ironic bare metal node, additional attributes would be
attached to the node object:

* snmp_driver - The class of power driver to interface with. This will
  identify a vendor-specific MIB interface to use.
* snmp_protocol - The SNMP protocol version to use: v1, v2c, or v3
* snmp_address - The hostname or IP address of the SNMP agent running
  at the PDU.
* snmp_community - The write SNMP community name shared between SNMP manager
  (e.g. Ironic SNMP driver) and SNMP agent (at PDU).
* snmp_outlet - The power outlet number on the power device.

These attributes would be passed through with other instance data to the
Ironic SNMP driver and used to generate the SNMP management operations to
achieve the required power action.

For full SNMPv3 support additional attributes might need to be added
to the node object.

REST API impact
---------------

None.

Driver API impact
-----------------

This driver would implement a complete interface for a power driver.
The power driver functionality is orthogonal to the deployment or boot
device management, and these interfaces would not be implemented. A new
Ironic driver class, derived from base.BaseDriver, will be implemented
to couple the existing PXE boot device configuration and deployment
driver with the new SNMP power driver.

Nova driver impact
------------------

None.

Security impact
---------------

Providing access to power management has obvious implications, but these
are not substantially different between one mechanism and another. An
argument could be made that the PDU outlets provide access to more devices
than might otherwise be reachable from Ironic.

If a user was able to effect a change in the attributes associated with
her nodes, it could be possible to affect the power of other devices in the
system. This is no different from other power mechanisms.

Using SNMP protocol version 3 increases security through use of encryption.
SNMP v3 also adds the potential to increase security through options for
authentication. This would provide security above the level of other power
drivers, but would require management of authentication credentials by Ironic.
Support for power driver authentication is not proposed as part of this
initial spec.

Other end user impact
---------------------

Providing remote control of the outlets on a smart PDU creates a dependency
on the connection of the power leads attached to the smart PDU. To use the
outlets for power control, the mapping between bare metal node and power
outlet must be accurately maintained. However, this is no different from
any other scenario in which smart PDUs are deployed.

Scalability impact
------------------

The scalability load is no different from other mechanisms using a network
protocol for power control.

Performance Impact
------------------

None.

Other deployer impact
---------------------

This driver would not be enabled in a default configuration.

To enable this driver in a deployment, driver-specific data would need to
be supplied as bare metal node properties. The mapping of power outlets
to bare metal nodes would also need to be determined.

Developer impact
----------------

There should be no impact on other Ironic development activity.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  <stigtelfer>

Assistance from other contributors would be welcome.

Work Items
----------

* Develop the framework and base class SNMP power driver.
* Add derived classes for interfacing with various PDU vendor MIBs.
* Investigate the feasibility of implementing third party CI for PDU hardware.
* Investigate the feasibility of implementing a virtualized PDU for Tempest.


Dependencies
============

This project would have a dependency on the PySNMP module. The dependency
could be relaxed to a dynamic runtime dependency that only applied if the
configuration was enabled. This would also enable unit testing without
importing PySNMP.


Testing
=======

The standard driver unit tests can easily be ported to apply to the new
SNMP driver.

The SNMP driver module is used in production by the driver's implementers.
If the driver is accepted into the project then this team proposes to support
and maintain it in future Ironic development cycles.

The module will be tested and used in production with all available PDU
equipment used on-site (APC, Teltronix). The feasibility of implementing a
third party CI infrastructure for PDU testing will be investigated and
created if possible.

Other collaborators at different sites with PDUs from different vendors would
make a valuable contribution to increasing test coverage and qualifying other
PDU hardware.

Theoretically, a Tempest suite could be created in which a virtualized PDU was
implemented, in the same manner as the fake ssh driver. This approach to test
depends on the ability to create an SNMP agent on the test hypervisor and to
associate virtual power outlets with VMs. Reviewer's thoughts on achieving this
concept are welcome.


Documentation Impact
====================

A detailed description of the driver parameters would be needed.
A list of tested and qualified PDU hardware would also be helpful.
Additionally, any brief notes (in wiki form) on how to configure PDUs
from various vendors would be valuable.


References
==========

* PySNMP package on PyPI: https://pypi.python.org/pypi/pysnmp/
* APC PowerNet MIB download (registration may be required): http://www.apc.com/resource/include/techspec_index.cfm?base_sku=SFPMIB403&tab=software
* CyberPower MIB: http://www.cyberpowersystems.com/software/CPSMIB2011.mib
* Eaton Power MIB: http://powerquality.eaton.com/Support/Software-Drivers/Downloads/ePDU/EATON-EPDU-MIB.zip
* Public MIB files repository: http://mibs.snmplabs.com/asn1/
