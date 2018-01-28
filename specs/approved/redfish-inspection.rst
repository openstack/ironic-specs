..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

============================================================
Out of Band Inspection support for ``redfish`` hardware type
============================================================

https://bugs.launchpad.net/ironic/+bug/1668487

This proposal adds the ability to inspect/update hardware properties and
auto-create ports in OOB manner for `Redfish hardware type`_.


Problem description
===================

Node inspection automatically collects and updates node properties. These
properties can be used to seggregate bare metal nodes into appropriate
resource classes that could be used in nova scheduling. Node inspection
also creates ironic ports for all discovered NIC(s). The ``redfish``
hardware type has support for inband inspection using
``inspector`` (`Ironic Inspector`_). The `DMTF standard Redfish schemas`_
supports OOB interfaces to fetch most of the inspection properties supported
by ironic. By adding support for OOB inspection, the overall time needed to
introspect a bare metal can be reduced.

Proposed change
===============

This spec proposes add OOB inspection support for ``redfish`` hardware type.
It would discover ironic supported node properties and capabilities for Redfish
compliant servers. This will be done by enhancing `Sushy library`_ to fetch the
required properties from Redfish controller running on the bare metal BMC.

The following mandatory properties will be discovered and updated in
``node.properties`` for ``redfish`` hardware type, as discussed in
`Introspect spec`_

* memory size

* CPUs

* CPU architecture

* NIC(s) MAC address

* disks

It would also implement the additional capabilities discussed in
`Common Ironic Capabilities spec`_ and available using
`DMTF standard Redfish schemas`_  for ``redfish`` hardware type.

The properties which are already set will be overridden upon invocation of
``inspect_hardware()`` except for ironic ports. If a ironic port already
exists, it will not create a new port for that MAC address. It will take
care of adding as well as deleting of the ports for NIC changes as
discussed in `Introspect spec`_.
Not all the capabilities supported by ironic are available in all Redfish
compliant servers. If a property is not available in the hardware, the
property will not be added/updated in node.properties as capabilities.

Inspection would return failure in the following cases:

* Failed to get basic properties.
* Failed to get capabilities, due to service configuration errors.
* Communication errors with Redfish manager.

Sushy changes
-------------
Implement ``InspectInterface`` method ``inspect_hardware`` in Sushy library.

Alternatives
------------

One can continue to discover these properties using inband mechanism of
``inspector`` supported by  ``redfish`` hardware type.

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

With OOB inspection, time required for hardware introspection would be reduced.

Scalability impact
------------------

None

Performance Impact
------------------

None

Other deployer impact
---------------------

With OOB inspection, time required for hardware introspection would be reduced.

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  stendulker

Other contributors:
  agarwalnisha1980

Work Items
----------

* Implementation of the ``InspectInterface`` class and
  its methods ``inspect_hardware()``, ``validate()`` and ``get_properties()``.
* Enhance Sushy library to discover required hardware properties.

Dependencies
============

* Depends on Sushy library

Testing
=======

* Unit tests will be added conforming to ironic testing requirements.
* CI support will be added for inspection server using virtual CI based
  on sushy-tools.

Upgrades and Backwards Compatibility
====================================

None

Documentation Impact
====================

`Redfish hardware type`_ document would be updated for OOB inspection feature.

References
==========

* `Introspect spec`_
* `Common Ironic Capabilities spec`_
* `Sushy library`_
* `Redfish hardware type`_

.. _`Introspect spec`: https://github.com/openstack/ironic-specs/blob/master/specs/kilo/ironic-node-properties-discovery.rst
.. _`Common Ironic Capabilities spec`: https://specs.openstack.org/openstack/ironic-specs/specs/not-implemented/add-new-oob-properties-to-ilo-drivers.html
.. _`DMTF standard Redfish schemas`: https://www.dmtf.org/standards/redfish
.. _`Sushy library`: https://pypi.python.org/pypi/sushy
.. _`Ironic Inspector`: https://docs.openstack.org/ironic-inspector/latest/
.. _`Redfish hardware type`: https://docs.openstack.org/ironic/latest/admin/drivers/redfish.html
