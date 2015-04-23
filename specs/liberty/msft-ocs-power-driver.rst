..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==================================================
Open CloudServer (OCS) power driver
==================================================

https://blueprints.launchpad.net/ironic/+spec/msft-ocs-power-driver

This blueprint adds support for the Open CloudServer (OCS) v2.0 power interface
in Ironic. The OCS design and specs have been contributed by Microsoft to the
Open Compute project.

Problem description
===================

The OCS chassis system includes a chassis manager server which exposes a REST
API to manage the individual blades, replacing traditional protocols like
IPMI. The REST API service itself is open source (Apache 2 license).

In order to be able to execute power and management actions on OCS blades, the
corresponding interfaces need to be implemented.

Furthermore, the OCS REST API supports also a serial console interface for
individual blades that can be supported in Ironic.

Proposed change
===============

The proposed implementation consists in a driver implementation. A client will
be provided to abstract the OCS service REST API calls, which in turn can be
referenced by the power, management and console interfaces.

Both UEFI and legacy BIOS boot modes are supported and can be specified by
the user as part of the properties/capabilities.

Driver properties that can be specified by the user:

**msftocs_base_url**

Base url of the OCS chassis manager REST API, e.g.: http://10.0.0.1:8000.
Required.

**msftocs_blade_id**

Blade id, must be a number between 1 and the maximum number of blades available
in the chassis. In the current configuration OCS chassis have a maximum of 24
or 48 blades. Required.

**msftocs_username**

Username to access the chassis manager REST API. Required.

**msftocs_password**

Password to access the chassis manager REST API. Required.

Alternatives
------------

No alternatives are available for the OCS case.

Data model impact
-----------------

None

State Machine Impact
--------------------

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

The interaction between Ironic and the OCS chassis manager involves REST API
calls, using HTTP basic authentication and potentially NTLM authentication in
the future.

The HTTP credentials are provided by the user as part of the driver properties
and  need to be passed to the REST API service. It is highly recommended to
employ HTTPS for transport encryption in any production environment.

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
  <alexpilotti>

Other contributors:
  <atuvenie>

Work Items
----------

* Power and management interfaces
* Console interface

Dependencies
============

None

Testing
=======

Potential continuous integration system integrated with Gerrit / Zuul. The
challenge is that a non trivial amount of OCS resources is required for
this purpose.

Upgrades and Backwards Compatibility
====================================

None

Documentation Impact
====================

The driver should be documented in a way similar to other Ironic drivers under
http://docs.openstack.org/developer/ironic/index.html

References
==========

* OCS design and specs: http://www.opencompute.org/wiki/Server/SpecsAndDesigns
* Chassis Manager sources: https://github.com/MSOpenTech/ChassisManager
