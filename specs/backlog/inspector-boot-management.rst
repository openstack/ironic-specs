..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

======================================
Boot management for in-band inspection
======================================

https://storyboard.openstack.org/#!/story/1528920

This is a cross-project (**ironic** and **ironic-inspector**) spec for making
the **ironic-inspector** inspection interface implementation optionally manage
the boot procedure for the in-band inspection process.

Problem description
===================

This spec targets to add support for virtual media boot to in-band inspection.

Proposed change
===============

Allow **ironic** to dictate which side (**ironic** or **ironic-inspector**)
will manage the boot for each inspection.

Inspector changes
-----------------

.. note:: This proposal was implemented in **ironic-inspector** 8.0.0.

#. Modify **ironic-inspector** inspection API to accept ``manage_boot``
   parameter (boolean, defaults to ``True``). If it's set to ``False``,
   **inspector** won't set boot device or power state
   for this node but will manage the node ports PXE filtering to avoid
   booting collisions.

   .. note:: Even though a ``manage_boot=False`` node won't
             PXE boot, it should still receive IP address
             leases from the DHCP server otherwise node NICs
             won't get configured and the IPA image won't be
             able to post the introspection data to
             **inspector**.

#. Add ``[DEFAULT]can_manage_boot`` option defaulting to
   ``True``.  If it's ``True``, the **ironic-inspector**
   will accept both `manage_boot=True` and `manage_boot=False` in the API.
   If it is ``False``, trying `manage_boot=True` will result in
   an error reported from **ironic-inspector** to **ironic**.
   If `can_manage_boot=False` and `manage_boot=False`, then **inspector**
   won't set boot device or power state for this node but will manage
   the node ports PXE filtering to avoid booting collisions as given above.

   This option is designed for cases when the **ironic-inspector**
   installation does not have a PXE environment configured. Then
   we'd better fail earlier if we're unable to configure boot for
   inspection, otherwise it will time out.

Ironic changes
--------------

#. Modify ``ironic.drivers.modules.inspector.InspectInterface`` to look at
   ``deploy_kernel`` and ``deploy_ramdisk`` or ``deploy_iso``
   fields in ``driver_info``. If they're present,
   use the boot interface to configure booting them on a node,
   set boot device accordingly (PXE for hardware type ``pxe``, but can be
   different for other hardware types).
   These parameters would be validated using ``boot.validate()``. If these
   fields are not there in the ``driver_info``, then the boot would be
   managed by **inspector**.
   This would require the microversion to be added in **inspector** for
   the ``manage_boot`` parameter.

   ``boot.prepare_ramdisk`` will be used for this. We will assume
   the IPA ramdisk, as it's the only ramdisk supported right now.

Unsolved problems
-----------------

This specification has the following problems that must be solved in its final
version:

#. ``PXEboot.validate`` will not pass without instance image parameters.
#. ``PXEBoot.prepare_ramdisk`` tries to configure DHCP, which requires VIFs and
   conflicts with DHCP of **ironic-inspector**.
#. It is not specified how to pass kernel parameters when **ironic-inspector**
   DHCP is not used (e.g. for virtual media).
#. The change will be in effect immediately for many deployments without a way
   to opt-out.

Alternatives
------------

* Continue requiring a full (i)PXE environment for in-band inspection.

* Expose the boot interface in the **ironic** API and make **ironic-inspector**
  use it.

Data model impact
-----------------

None

State Machine Impact
--------------------

None

REST API impact
---------------

No changes in the **ironic** API.

A change in the **ironic-inspector** API:

* Update ``POST /v1/introspection/<UUID>``, add a new URL parameter:

  ``manage_boot`` - boolean, defaults to ``True``. If set to ``False``,
  Ironic Inspector won't set the boot device or update the PXE filter rules
  for this node.

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

This change will allow to use in-band inspection with virtual media, reducing
the potentially unsafe PXE environment to node discovery only.

Other end user impact
---------------------

None

Scalability impact
------------------

Using virtual media for inspection will increase scalability, as PXE
is often a bottleneck for scaling.

Performance Impact
------------------

None

Other deployer impact
---------------------

* The ``pxe_enabled`` flag will not be set for any of the **ironic** ports of
  the **ironic** node when inspector is being run using the boot device as
  virtual media.

* For the discovery feature to work with virtual media, a node would have
  to be manually booted with a custom IPA ISO with the **inspector** IP address
  baked-in.

New configuration option in the ``DEFAULT`` section of the **ironic-inspector**
configuration file:

* ``can_manage_boot`` (boolean, default ``True``) whether
  to *require* the **inspector** inspection implementation to accept
  ``manage_boot`` parameter or not.

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Dmitry Tantsur (lp: divius, irc: dtantsur)

Other contributors:
  Nisha Agarwal (lp:agarwalnisha1980, irc: Nisha_Agarwal)

Work Items
----------

#. Add a new parameter to the Ironic **Inspector** API.

New configuration option in the ``DEFAULT`` section of the **ironic-inspector**
configuration file:

* ``can_manage_boot`` (boolean, default ``True``) whether
  to *require* the **inspector** inspection implementation to accept
  ``manage_boot`` parameter or not.

Dependencies
============

None

Testing
=======

Coverage by unit tests. This would be covered by CI tests as well.

Upgrades and Backwards Compatibility
====================================

Using the new **inspector** API flag will require bumping the
**ironic-inspector** API version used in **ironic**. This will
make **ironic** require the latest version of **ironic-inspector**.
Meaning, **ironic-inspector** will have to be updated first.

The default behaviour will change only if ``can_manage_boot`` is
set to ``True`` in **ironic-inspector** and ``manage_boot`` is
set to ``False`` in which case **ironic** will manage the boot.

Documentation Impact
====================

The **ironic-inspector** documentation should be updated for the API change.

The **ironic** documentation should be updated to explain using boot management
for **ironic-inspector**.

References
==========

