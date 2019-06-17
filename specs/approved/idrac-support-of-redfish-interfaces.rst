..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

========================================================
Define idrac Hardware Type Support of Redfish Interfaces
========================================================

https://storyboard.openstack.org/#!/story/2004592

Operators need the ability to configure Ironic to use Redfish_ to manage Dell
EMC bare metal servers, and be assured it:

* offers a means of incrementally increasing the use of Redfish as Ironic's
  support, the standard, and Dell EMC service implementations evolve,
* delivers management protocol choice among those supported by Dell EMC --
  Intelligent Platform Management Interface (IPMI_), Redfish, and Web Services
  Management (WS-Man_),
* provides all the ``idrac`` hardware type functionality they have relied on,
* works and will continue to,
* is supported by the vendor and community, and
* can offer Dell EMC value added.

This specification suggests the ``idrac`` hardware type provides that.


Problem description
===================

Use cases
---------

Expanding on what the introductory paragraph describes above, several use cases
can be envisioned. While this specification enables them, it may turn out only
some will find practical use among operators. That could be driven by many
factors, including an existing versus greenfield deployment, operator comfort
level with Redfish versus WS-Man, maturity of the protocol implementations,
availability of needed functionality across Redfish and WS-Man, requirement for
vendor value added, operational plans and schedules, among others.

Here they are. Note that except for the first two, they can be used in
combination to configure a single Dell EMC bare metal server.

* An Admin User has a Dell EMC bare metal server and uses only WS-Man to manage
  it.

* An Admin User has a Dell EMC bare metal server and uses only Redfish to
  manage it.

* An Admin User has a Dell EMC bare metal server and uses both Redfish and
  WS-Man to manage it. When both offer the needed functionality, either is
  used.

* An Admin User has a Dell EMC bare metal server and uses both Redfish and
  WS-Man to manage it. Ironic's ability to manage the server is maximized.

* An Admin User has a Dell EMC bare metal server and uses both Redfish and
  WS-Man to manage it. Vendor value added, which is available from only one or
  both, is used.

Proposed change
===============

Background
----------

The ``idrac`` hardware type is the Ironic driver intended for use with Dell EMC
bare metal servers equipped with an integrated Dell Remote Access Controller
(iDRAC) baseboard management controller (BMC). To date, all the out-of-band
(OOB) management protocol-dependent interface implementations ``idrac`` has
supported use the WS-Man protocol to interact with the iDRAC. Those implement
the ``inspect``, ``management``, ``power``, ``raid``, and ``vendor`` hardware
interfaces. Like the hardware type, they are named ``idrac``. They rely on
`python-dracclient`_'s WS-Man client.

Operators also have the option to use the generic, vendor-independent
``redfish`` hardware type with Dell EMC bare metal servers that have an iDRAC
that supports the Redfish protocol. ``redfish``'s supported OOB protocol-
dependent interface implementations use the Redfish protocol to interact with
the BMC. Those implement the ``bios``, ``inspect``, ``management``, and
``power`` hardware interfaces. Again, like the hardware type, they are named
``redfish``. They rely on `sushy`_'s Redfish client. Importantly, while some
of those work with the iDRAC, including ``management`` and ``power``, not all
of them do.

The ``redfish`` hardware type enables managing servers compliant with the
Redfish protocol. However, it is relatively new, and the protocol standard has
been evolving, along with its implementations by hardware vendors such as Dell
EMC. As is common among standards, there is a difference between compliance and
interoperability. For example, the Redfish ``bios`` interface implementation
has not worked with the iDRAC because of client and server protocol
implementation incompatibility.

While there is much functional overlap between the interface implementations
supported by the ``idrac`` and ``redfish`` hardware types, it is not complete.
Only ``idrac`` supports a ``raid`` interface implementation and only
``redfish`` supports ``bios``. Also, the optional hardware interface
functionality available in the ``idrac`` and ``redfish`` interface
implementations can differ. For example, while the ``redfish`` implementation
of the ``management`` hardware interface first introduced optional boot mode
functionality, ``idrac`` does not offer that, yet. Therefore, those two
hardware types are not perfect substitutes for one another.

Dell EMC wants to be able to offer its customers vendor value added as
supported by the Redfish standard, like it has done through WS-Man. That
benefits operators by making available features and functionality that has not
yet been standardized. Dell EMC can be more responsive to its customers' needs
and differentiate itself in the market.

Goal
----

With this specification, we are going to achieve the goal of promoting and
accelerating the adoption of Redfish by operators with Dell EMC bare metal
servers.

Non-goals
---------

The following is considered outside the scope of this specification:

* Support a node configuration with a mix of Redfish and WS-Man ``management``
  and ``power`` interface implementations. The legacy ``idrac`` implementations
  of the ``management`` and ``power`` hardware interfaces interact to set the
  boot device. It is not clear there is a compelling need to accommodate that
  in a mixed Redfish and WS-Man configuration.

* The following TripleO command can be used to register and configure nodes for
  their deployment with Ironic::

    openstack overcloud node import instackenv.json

  See the `TripleO register nodes`_ documentation. It sets properties in a
  node's ``driver_info`` field which are required by its driver. Presently,
  when the node's driver is ``idrac``, those are the properties --
  ``drac_address``, ``drac_username``, and ``drac_password`` -- needed by the
  WS-Man interface implementations ``idrac`` has supported. See the
  `iDRAC driver`_ documentation.

  The Redfish interface implementations need similar, but different, properties
  in the ``driver_info`` field, including ``redfish_address``,
  ``redfish_system_id``, ``redfish_username``, and ``redfish_password``. See
  the `Redfish driver`_ documentation.

  Changing that TripleO command to set both the Redfish and WS-Man properties
  in a node's ``driver_info`` field when its ``driver`` is ``idrac`` is beyond
  the scope of this specification. That will be addressed by a TripleO project
  blueprint.

* Define ``idrac`` hardware type support of IPMI interface implementations.
  That could be done as a follow-on to this.

Solution
--------

This specification proposes to solve the problem it describes by changing the
``idrac`` hardware type. Since the Ironic `Driver composition reform`_, we have
been allowed to have "one vendor driver with options configurable per node
instead of many drivers for every vendor." [#f1]_ The reform's goals include
[#f2]_::

  * Make vendors in charge of defining a set of supported interface
    implementations in priority order

  * Allow vendors to guarantee that unsupported interface implementations will
    not be used with hardware types they define. This is done by having a
    hardware type list all interfaces it supports.

Implementing the solution in the ``idrac`` hardware type contributes toward
making it the one Dell EMC driver for its bare metal servers with iDRACs and
their value added implementations of the IPMI, Redfish, and WS-Man management
protocols. It also aligns with the goals of the reform. That is what operators
have come to expect.

Here are the details of the proposal.

* Define two new groups of interface implementations with entrypoints named
  ``idrac-redfish`` and ``idrac-wsman``. The ``idrac-redfish`` entrypoints
  refer to Redfish interface implementations which are compatible with the
  iDRAC, presently those of the ``management`` and ``power`` hardware
  interfaces. The ``idrac-wsman`` entrypoints are new names for the legacy
  ``idrac`` entrypoints. The legacy ``idrac`` entrypoints are left unchanged.
  For example::

    ironic.hardware.interfaces.management =
        ...
        idrac = ironic.drivers.modules.drac.management:DracManagement
        idrac-redfish = ironic.drivers.modules.drac.management:DracRedfishManagement
        idrac-wsman = ironic.drivers.modules.drac.management:DracWSManManagement
        ...
        redfish = ironic.drivers.modules.redfish.management:RedfishManagement


* Declare ``idrac`` hardware type support for the ``idrac``, ``idrac-redfish``,
  and ``idrac-wsman`` interface implementations. ``idrac`` continues to have
  the highest priority by being first in its
  ``supported_<INTERFACE>_interfaces`` lists. Here ``<INTERFACE>`` is a type of
  hardware interface: ``inspect``, ``management``, ``power``, etc. For
  example::

    class IDRACHardware(generic.GenericHardware):
        ...
        @property
        def supported_management_interfaces(self):
            return [management.DracManagement, management.DracWSManManagement,
                management.DracRedfishManagement]
        ...

.. note::
   The property uses classes, not instances nor entrypoint names. The example
   assumes the required modules are imported.

* New ``idrac-redfish`` entrypoints are defined by new Python classes, because
  using the generic, vendor-independent Redfish classes would make the
  ``redfish`` entrypoints synonyms for ``idrac-redfish`` and supported. A later
  requirement to change the name of an entrypoint's Python class to resolve a
  Dell EMC-specific incompatibility or introduce vendor value added, which
  would eliminate support for ``redfish``, could be a breaking change. The new
  Python classes are derived from the generic, vendor-independent Redfish
  classes.

* New ``idrac-wsman`` entrypoints are defined by new Python classes. Those
  classes are created by renaming the classes for the legacy ``idrac``
  entrypoints from ``Drac<INTERFACE>`` to ``DracWSMan<INTERFACE>``. Here
  ``<INTERFACE>`` refers to a type of hardware interface: ``Inspect``,
  ``Management``, ``Power``, etc.

  The legacy ``Drac<INTERFACE>`` classes are redefined by simply deriving them
  from the new ``DracWSMan<INTERFACE>`` classes. For example::

    class DracManagement(DracWSManManagement):
        pass

  That makes the legacy ``Drac<INTERFACE>`` classes aliases for the new
  ``DracWSMan<INTERFACE>`` classes. Any bug fixes or features added to the
  WS-Man interface implementations are available from both the ``idrac`` and
  ``idrac-wsman`` entrypoints. Having separate classes for the two groups of
  entrypoints makes it possible to subsequently add logic that implements
  deprecation of the legacy ``idrac`` entrypoints by emitting a log message and
  similar.

Alternatives
------------

* We could change the lowest layer of ``python-dracclient`` to support
  Redfish, in addition to WS-Man. However, we expect it would be challenging
  to provide ``python-dracclient`` APIs and workflows which abstract the very
  different Redfish and WS-Man technologies. Redfish's interface is RESTful,
  while WS-Man is a Simple Object Access Protocol (SOAP). APIs and workflows
  would likely need to be changed or newly defined. That would require
  substantial modification of the existing ``idrac`` interface implementations.

* We could maintain the status quo split of the ``idrac`` hardware type for
  WS-Man and ``redfish`` hardware type for Redfish. However, that would not
  promote and accelerate the use of Redfish among operators with Dell EMC
  bare metal servers today, because ``redfish`` does not offer everything
  ``idrac`` does. That also would not support resolving Dell EMC vendor-
  specific incompatibilities with the generic, vendor-independent ``redfish``
  hardware type nor using Redfish to introduce vendor value added.

* We could let the ``redfish`` interface implementations use Redfish OEM
  extensions to address vendor-specific incompatibilities and introduce vendor
  value added. However, that seems inconsistent with the intent that they be
  generic and vendor-independent.

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

* A deployer can add ``idrac-redfish`` to the ``enabled_management_interfaces``
  and ``enabled_power_interfaces`` options to enable those new interface
  implementations.

* A deployer can add ``idrac-wsman`` to the ``enabled_inspect_interfaces``,
  ``enabled_management_interfaces``, ``enabled_power_interfaces``,
  ``enabled_raid_interfaces``, and ``enabled_vendor_interfaces`` to enable
  those new interface implementations.

* A deployer must specify properties in the node's ``driver_info`` field that
  are needed by Redfish interface implementations, including
  ``redfish_address``, ``redfish_system_id``, ``redfish_username``, and
  ``redfish_password``, to use the ``idrac-redfish`` interface implementations.
  That is in addition to the legacy properties the ``idrac`` hardware type has
  needed in ``driver_info`` -- ``drac_address``, ``drac_username``, and
  ``drac_password``.
  ::

    openstack baremetal node create --driver idrac --driver-info \
      drac_address=1.2.3.4 --driver-info drac_username=admin --driver-info \
      drac_password=password --driver_info redfish_address=https://1.2.3.4 \
      --driver-info redfish_system_id=/redfish/v1/Systems/System.Embedded.1 \
      --driver-info redfish_username=admin --driver-info \
      redfish_password=password

  See the `Redfish driver`_ documentation, `iDRAC driver`_
  documentation, and Non-goals_.

* A deployer can specify the new ``idrac-redfish`` and ``idrac-wsman``
  interface implementations on node enrollment::

    openstack baremetal node create --driver idrac ... --management-interface \
      idrac-wsman --power-interface idrac-wsman ...

  They can also be set by the following command::

    openstack baremetal node set <NODE> --management-interface idrac-redfish \
      --power-interface idrac-redfish

  They must be enabled as described above.

Developer impact
----------------

None


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  rpioso

Other contributors:
  None

Work Items
----------

* Define two new groups of interface implementations with entrypoints named
  ``idrac-redfish`` and ``idrac-wsman``.

* Declare ``idrac`` hardware type support for the ``idrac``, ``idrac-redfish``,
  and ``idrac-wsman`` interface implementations.

* Integration test the changes against Dell EMC bare metal servers.

* Modify the Dell EMC Ironic third-party continuous integration (CI) to cover
  supported configurations added by this specification.

* Update the `iDRAC driver`_ documentation.


Dependencies
============

This specification is related to the `Driver composition reform`_.

It specifically targets Dell EMC bare metal servers equipped with an iDRAC and
managed by the ``idrac`` hardware type.


Testing
=======

This is not testable in the gate given current limitations on the availability
of the specific hardware required.

The mitigation plan is to add coverage to the Dell EMC Ironic third-party CI
for supported configurations added by this specification that we expect to be
common.


Upgrades and Backwards Compatibility
====================================

This change is designed to be backwards compatible. The legacy ``idrac``
interface implementation entrypoints will be supported for at least some time.
A separate story will cover their deprecation.

We will recommend switching to the appropriate new ``idrac-redfish`` and
``idrac-wsman`` interface implementation entrypoints as soon as it is possible.


Documentation Impact
====================

The `iDRAC driver`_ documentation is updated to:

* describe switching from the legacy ``idrac`` interface implementation
  entrypoints to the new ``idrac-redfish`` and ``idrac-wsman`` entrypoints,

* reflect the changes to the supported interface implementations, and

* inform that a node configuration with a mix of Redfish and WS-Man
  ``management`` and ``power`` interface implementations is not supported.


References
==========

OpenStack software projects:
  - `ironic`_
  - `python-dracclient`_
  - `sushy`_

Related Ironic specifications:
  - `Driver composition reform`_

Documentation:
  - `iDRAC driver`_
  - `Redfish driver`_
  - `TripleO register nodes`_

Standards:
  - IPMI_
  - Redfish_
  - WS-Man_

.. rubric:: Footnotes

.. [#f1] See the *introduction* paragraph of the Ironic
         `Driver composition reform`_.
.. [#f2] See the *Introduction* subsection in the *Proposed change* section of
         the Ironic `Driver composition reform`_.

.. _Driver composition reform: https://specs.openstack.org/openstack/ironic-specs/specs/7.0/driver-composition-reform.html
.. _iDRAC driver: https://docs.openstack.org/ironic/latest/admin/drivers/idrac.html
.. _IPMI: https://www.intel.com/content/www/us/en/servers/ipmi/ipmi-technical-resources.html
.. _ironic: https://opendev.org/openstack/ironic.git
.. _python-dracclient: https://opendev.org/openstack/python-dracclient.git
.. _Redfish: https://www.dmtf.org/standards/redfish
.. _Redfish driver: https://docs.openstack.org/ironic/latest/admin/drivers/redfish.html
.. _sushy: https://opendev.org/openstack/sushy.git
.. _TripleO register nodes: https://docs.openstack.org/tripleo-docs/latest/install/basic_deployment/basic_deployment_cli.html#register-nodes
.. _WS-Man: https://www.dmtf.org/standards/ws-man
