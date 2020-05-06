..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=====================================================
Allow a ramdisk deploy user to specify their boot ISO
=====================================================

https://storyboard.openstack.org/#!/story/2007633

With support for virtual media, there are cases where an operator may
wish to boot a machine with a specific virutal media image to facilitate
the deployment of a machine or even just the completion of an action like
firmware upgrades.

Providing an interface to signal "boot to this" iso, seems logical.

Problem description
===================

A detailed description of the problem:

* The ``ramdisk`` deployment interface allows a user to define a kernel
  and ramdisk to be utilized to boot a ramdisk instance which after the
  initial deployment the instance is considered a deployed machine in
  active state.
* At present, because of the ``ramdisk`` deployment interface constraints,
  users are unable to specify ISOs for virtual media. They must supply a
  kernel/ramdisk and in the virtual media case it must be rebuilt.

Proposed change
===============

* Allow a ``instance_info/boot_iso`` parameter to be leveraged to be
  the medium utilized for booting from an explicit ISO image which the
  conductor would support downloading, caching, and providing to the
  baremetal machine.

* Teach the code related to the pass-through to provide the same basic
  capability to append parameters to the command line through decomposition
  of the ISO, appending to ``grub2`` and ``isolinux`` configurations with
  the supplied values, and repackaging of the ISO file for deployment.

* Optionally: Enable the glance image ``image_source`` code to support this
  path for iso booting. This could potentially allow the OpenStack Nova
  virt driver for ironic to enable booting of instances from ISO mediums,
  however this is out of scope.

Alternatives
------------

* Use an external provisioning tool, and ``adopt`` the node into Ironic,
  if applicable.

* Pre-mastered machine specific configurations into ISO images which would
  ultimately result in pushing the preparation and execution workload to the
  API user.

Data model impact
-----------------

None, this leverages the existing data model.

State Machine Impact
--------------------

None

REST API impact
---------------

None, this change leverages existing JSON data fields with-in Ironic's data
model.

Client (CLI) impact
-------------------

"openstack baremetal" CLI
~~~~~~~~~~~~~~~~~~~~~~~~~

None

"openstacksdk"
~~~~~~~~~~~~~~

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

The distinct possibiliy exists, if a user requests multiple concurrent
deployments, that configuration injection could consume a large amount
of disk space.

Also, we may wish to enable some sort of logic to prevent mass consumption
of disk space as part of the conductor, for the reasons of cleanup, however
the conductor has no real way to understand if this is a forever usage, or
not. Ideally operator documentation would be updated to help scale planning
for this condition. Alternatively we may wish to introduce a "one-shot"
indicator flag so we don't attempt to persist ISOs after takeover on active
machines.

Performance Impact
------------------

A large number of concurrent deployments may slow the conductor due to overall
system performance constraints, depending on the exact options and settings
leveraged.

Other deployer impact
---------------------

None

Developer impact
----------------

None is anticipated, however we would likely focus on implementing this in the
redfish virtual media code path, and should likely try to ensure that we do
not make such changes redfish interface specific as other drivers are present
in Ironic which support Virtual Media.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Julia Kreger <juliaashleykreger@gmail.com>


Work Items
----------

* Implement support to pass an explicit boot ISO into the ramdisk interface.
* Implement support to inject configuration into the boot ISO.
* Document this functionality for the ramdisk interface.

Dependencies
============

* None

Testing
=======

Unit tests should be sufficent for ensuring this functionality is not broken.

A tempest test may also be viable, but we may wish to partner with the Metal3
community on integration testing, as ultimately this is essentially just an
item of integration testing when virtual media AND ramdisk interfaces are
leveraged.

Upgrades and Backwards Compatibility
====================================

N/A

Documentation Impact
====================

We will want to update the documentation on the ramdisk deployment interface to
detail this capability.

References
==========

None
