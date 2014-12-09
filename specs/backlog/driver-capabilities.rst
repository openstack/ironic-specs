..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Introduce Driver Capabilities
==========================================

This spec introduces inspectable (via Ironic API) capabilities for Ironic
drivers.

https://blueprints.launchpad.net/ironic/+spec/driver-capabilities

Problem description
===================

Capabilities are required for at least these use cases:

* Scheduling on a node with a proper driver.

  E.g. with time we start implementing variants of deployment that are not
  supported by all drivers, including:

  * Whole-disk vs partition deployment [1].
  * Using configdrive for deployment [2].
  * Using ephemeral partitions.

  We need to take all these differences into account when scheduling. Failure
  to do so will lead to errors on the late stage of deployment or even (as with
  whole-disk) to the wrong deployment.

  Ironic should be able to aggregate driver capabilities into node
  capabilities to expose them to the scheduler. (Not addressed by this spec.)

* Examining driver features.

  As we are introducing more vendor-specific things, we need some way to find
  out, if one is supported by a given driver. Driver capabilities would
  enable 3rd-party tools to inspect support of particular feature
  by particular driver.

Proposed change
===============

* Introduce get_capabilities() call to all driver interfaces, return value
  being set of strings.
* Introduce get_capabilities() call to ``BaseDriver``, defaulting to union
  of capabilities of all interfaces.
* Publish capabilities as ``/v1/drivers/{name}/capabilities`` REST endpoint.

With the above changes, a developer could use the Ironic API to go through the
list of drivers and inspect their capabilities.

Alternatives
------------

* Obviously the best solution would be to have all drivers implement the same
  set of capabilities. Unfortunately, it's not realistic. E.g. some drivers
  (like IPMI) are more generic than the other (like ILO and DRAC), but we
  don't want to artificialy limit what more specific drivers can expose.

Data model impact
-----------------

None. For now we expect driver capabilities to be a hardcoded constant.

REST API impact
---------------

* ``/v1/drivers/{name}/capabilities``

  * Get driver capabilities.

  * Method type GET.

  * Normal http response code(s): 200

  * Expected error http response code(s)

    * 404 - driver not found.

  * Parameter: ``name`` - driver name

  * Body: None

  * Response: JSON list of strings.

* A corresponding change in the client library and CLI is necessary, e.g.
  ::

    $ ironic driver-get-capabilities pxe_ipmitool

RPC API impact
--------------

* New synchronous RPC method ``get_driver_capabilities``, taking
  ``driver_name``, returning list of capabilities.

Driver API impact
-----------------

* New method ``get_capabilities`` added to all interfaces, defaulting to
  returning an empty set.

* New method ``get_capabilities`` added to the ``BaseDriver``, defaulting to
  returning a union of ``get_capabilities`` results for all interfaces.

Change is backward-compatible.

Nova driver impact
------------------

None for now. This spec is a starting point to implement hardware capabilities
for nodes [3], which will affect Nova driver.

Security impact
---------------

None

Other end user impact
---------------------

* New CLI command: ``ironic driver-get-capabilities <driver name>``

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

* Driver developers can override ``get_capabilities`` to provide information
  about additional capabilities.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  None

Work Items
----------

* Add ``get_capabilities`` to all interfaces.
* Add ``get_capabilities`` to the ``BaseDriver``.
* Add ``get_driver_capabilities`` to the RPC API.
* Add new REST API.
* Research whether to add capabilities to existing drivers.

Dependencies
============

None

Testing
=======

Unit tests

Upgrades and Backwards Compatibility
====================================

No upgrade impact

Documentation Impact
====================

* New API should be documented.
* Driver documentation should mention the new method.

References
==========

* [1] https://review.openstack.org/97150
* [2] https://review.openstack.org/99235
* [3] https://review.openstack.org/131272
