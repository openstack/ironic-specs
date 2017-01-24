..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=======================================
Promote iPXE to separate boot interface
=======================================

https://bugs.launchpad.net/ironic/+bug/1628069

The iPXE boot should be promoted to a separate boot driver interface.
This will simplify the code base and allow to not force global PXE *vs* iPXE
conductor setting.


Problem description
===================

Currently setting PXE or iPXE is enforced per-conductor, and taking
into account the possibility of node take-over, this choice is effectively
global for the whole Ironic installation.

Due to this the current code of ``PXEBoot`` interface is riddled
with constructs of:

.. code-block:: python

   if CONF.pxe.ixpe_enabled ...

Recently added or proposed changes (like ``CONF.pxe.ipxe_use_swift`` option)
make the logic there even more complicated.

Proposed change
===============

It is proposed to implement a separate iPXE boot interface,
which will use the new way of serving iPXE boot scripts and boot config files
directly from Ironic API as outlined in `dynamic iPXE configuration`_ spec.

The new interface will get a separate ``[ipxe]`` config section,
where all ``[pxe]ipxe_*`` options should be moved following proper deprecation
policy for config options.
Current iPXE-related behavior of ``PXEBoot`` interface should
be deprecated and eventually removed.

Alternatives
------------

Continue mixing PXE and iPXE in single driver interface
and setting iPXE *vs* PXE globally.

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

None

Scalability impact
------------------

None

Performance Impact
------------------

None

Other deployer impact
---------------------

* A new config section ``[ipxe]`` will be added, with most of the
  ipxe_* options copied from current ``[pxe]`` section (with ``ipxe_`` removed
  from option names).
  By the virtue of ``oslo_config`` library, the new options will be backward
  compatible with old, deprecated ones, using their values when not set
  explicitly.

* This change has no immediate effect. Enabling it is a conscious choice of
  the operator:

  + a driver utilizing this new ``iPXEBoot`` boot interface must be composed
  + such driver must be assigned to the node


Developer impact
----------------

None


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  pshchelo (Pavlo Shchelokovskyy)

Work Items
----------

* create a new ``iPXEBoot`` boot interface

  - identify and refactor code that is common for ``PXEBoot`` and
    ``iPXEBoot`` interfaces

* register this driver as entry point for ``ironic.hardware.interfaces.boot``

  - add it to list of boot interfaces enabled by default in ironic config
    (``[DEFAULT]enabled_boot_interfaces`` config option)

* add appropriate documentation

Dependencies
============

* `Dynamic iPXE configuration`_
* `Driver composition reform`_

Testing
=======

No specific coverage seems to be needed apart from enabling a driver that
uses this new proposed boot interface at least on one gate job.

Upgrades and Backwards Compatibility
====================================

The feature has no immediate effect on existing installation as it must
be manually enabled first by enabling the interface and composing an
appropriate driver with this boot interface.

Existing drivers do not depend on this feature in any way.

It is also proposed to deprecate and eventually remove iPXE capabilities
from the PXEBoot interface.

Chain-loading an iPXE-capable boot-loader will still be supported by
iPXEBoot driver to support older/dumber/buggy hardware.

Documentation Impact
====================

Document new driver interface and its usage.

References
==========

.. _dynamic iPXE configuration: http://specs.openstack.org/openstack/ironic-specs/specs/not-implemented/ipxe-dynamic-config.html
.. _Driver composition reform: http://specs.openstack.org/openstack/ironic-specs/specs/not-implemented/driver-composition-reform.html
