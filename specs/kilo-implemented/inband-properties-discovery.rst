..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==============================================================
In-band hardware properties introspection via ironic-discoverd
==============================================================

https://blueprints.launchpad.net/ironic/+spec/inband-properties-discovery

This spec adds support for introspecting hardware properties using
*ironic-discoverd* project for drivers not supporting out-of-band
introspection.

ironic-discoverd [1]_ is a StackForge project for conducting hardware
properties inspection via booting a special discovery ramdisk [2]_ and
interrogating hardware from within it.

.. note::
    Term "hardware discovery" is used through this spec as a synonym to
    "hardware introspection" or "hardware inspection" as opposed to "new
    hardware auto-discovery", which is not covered by this spec.

Problem description
===================

Currently there is no generic way in Ironic to inspect scheduling properties
of a given piece of hardware. While multiple out-of-band methods are proposed,
they are restricted each to a particular vendor (currently HP and DELL). This
proposal will make hardware introspection possible for every driver that can
power on and off the machine.

A couple of future use cases may need in-band discovery even on hardware
supporting out-of-band discovery, namely:

* Auto-discovery of nodes. While out of scope for now, it may be considered
  later, and may require in-band discovery, depending on whether particular
  vendor support it out-of-band.

* Vendor-specific extensions for the introspection, discovering properties
  that are not available via out-of-band means etc.

.. note::
    This spec does not touch any of these use cases directly.

Proposed change
===============

This spec proposes implementing ``InspectInterface`` defined in the
parent spec [3]_ via using *ironic-discoverd*.

.. note::
    *ironic-discoverd* 1.0.0 (to be released in the beginning of February)
    will be a requirement, so e.g. some client functions might be
    missing from the current stable 0.2 release documentation.
    See Dependencies_ for details.

* Add ``[discoverd]`` configuration section:

  * Add configuration option ``service_url`` (string, no default).
    This is a URL of *ironic-discoverd* which will be
    contacted by Ironic for starting the introspection process.
    E.g. ``http://127.0.0.1:5050/v1``.

    .. note::
      Port can be changed via *ironic-discoverd* configuration file.

  * Add configuration option ``enabled`` (boolean, default ``False``),
    that will enable or disable the discoverd introspection specifically.
    By default it will be disabled and ``DiscoverdInspect.inspect_hardware``
    will raise new ``DiscoverdDisabled`` exception with the explanation.

    .. note::
      This option does not affect other inspection implementation.

* Create ``DiscoverdInspect`` class implementing ``InspectInterface``
  in the following way:

  * During driver initialization the constructor (__init__) verifies that
    *inspection_service_url* is provided and ``ironic_discoverd.client``
    module can be imported, otherwise fail.
    It will also check that we have the required version of *ironic-discoverd*
    - see Dependencies_.
    These checks obviously will be skipped, if *ironic-discoverd* support is
    disabled via configuration - see above.

  * ``inspect_hardware`` releases a task manager lock on a node
    (so that *ironic-discoverd* can operate on it) and calls to
    ``ironic_discoverd.client.introspect`` providing node UUID.

    .. note::
        Without releasing lock that was acquired by generic inspection code
        for creating a *task*, *ironic-discoverd* won't be able to manipulate
        a node.

  * *ironic-discoverd* will update scheduling data after successful
    introspection.

  * ``DiscoverdInspect`` will also poll state endpoint [4]_ of
    *ironic-discoverd* via client API ``ironic_discoverd.client.get_status``.
    It will use a driver-specific periodic task as suggested in [5]_.

    On success node will be advanced to the next state.
    On error ``Node.last_error`` will be updated and node will be moved
    to INSPECTFAIL state.

    .. note::
        If we decide not to implement driver-specific periodic tasks for Kilo
        cycle, a LoopingCall at the end of inspect_hardware() method will be
        used instead.

* Add ``DiscoverdInspect`` as ``InspectInterface`` implementation for
  ``pxe_ipmitool``, ``pxe_ipminative`` and ``pxe_ssh`` drivers (the latter for
  easier testing).

High-level schema of how inspection will work:

* ``DiscoverdInspect`` calls to *ironic-discoverd* API

* *ironic-discoverd* communicates with Ironic via regular API for checking
  the current node state.

* *ironic-discoverd* asks Ironic to reboot the machine using the power
  interface.

* The machine is PXE-booted using PXE server (usually *dnsmasq*) installed
  along with *ironic-discoverd*.

  .. note::
    It was suggested that *ironic-discoverd* use out-of-band boot methods like
    virtual media, if supported by the driver. While an interesting feature to
    consider, it's not in the near-term plans for *ironic-discoverd* and thus
    is not covered by this spec.

  .. note::
    *ironic-discoverd* does not use Neutron, as Neutron does not provide means
    apply specific DHCP options to all **unknown** machines
    (i.e. with MAC's that do not have ports). If one day it does provide such
    functionality, *ironic-discoverd* will switch to it and stop managing
    *dnsmasq* directly. Please refer to the README [1]_ for details.

  .. note::
    *ironic-discoverd* avoids conflicts with Neutron by managing firewall
    access to PXE port. Only MAC's that are not known to Ironic are allowed to
    PXE-boot via *dnsmasq* instance managed by *ironic-discoverd*.

* The ramdisk calls back to *ironic-discoverd*.

* *ironic-discoverd* communication with Ironic via regular API to update node
  state and powers off the node

Alternatives
------------

* We could stay with out-of-band discovery only. As stated above, it's not
  covering all hardware.

* In-band discovery could be implemented within Ironic itself, without 3rd
  party service. This is believed to be a unnecessary complication to Ironic
  code base.

Data model impact
-----------------

No direct impact expected. *ironic-discoverd* will set scheduling
properties in ``Node.properties`` field.

REST API impact
---------------

No direct REST API impact.

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

The code within Ironic has no security impact.
Presence of *ironic-discoverd* itself has one security issue:

* Endpoint receiving data from the ramdisk is not authenticated. For this
  reason *ironic-discoverd* will verify that node is in it's internal cache
  before updating it.

  Due to this, the current policy is to never overwrite existing properties,
  only set the missing ones. It will be possible to alter the behavior via
  *ironic-discoverd* configuration file. Please refer to the parent spec [3]_
  for discussion.

Other end user impact
---------------------

Operators will be able to gather properties from hardware which does not
support out-of-band introspection via vendor-specific drivers.

Scalability impact
------------------

* *ironic-discoverd* currently requires one PXE boot server and one TFTP
  server to serve all the requests to boot discovery ramdisk.
  This is the only thing that seriously limits the scalability
  of *ironic-discoverd*.

  In the future we'll be looking into how to make *ironic-discoverd* work in
  the redundant setup, but currently it's not supported.

* *ironic-discoverd* also may require more network calls than out-of-band
  inspection.

I believe that these concerns are not critical, if discovery happens not too
often and in reasonable bulks of nodes.

Performance Impact
------------------

Call to *ironic-discoverd* is mostly async, only basic sanity checks are done
in a sync fashion, before returning control back to the conductor.

Other deployer impact
---------------------

* New option ``discoverd.enabled`` (boolean, default ``False``) -
  whether to enable inspection via *ironic-discoverd*

* New option: ``discoverd.service_url`` (string, no default) with
  the URL of *ironic-discoverd*

* *ironic-discoverd* and required services (like dnsmasq and TFTP server)
  should be deployed and managed separately, see the README [1]_ for details.

  *ironic-discoverd* will ensure that these services won't interfere with
  existing Neutron installation managing DHCP for the nodes.

  A special ramdisk [2]_ should be built (e.g. using *diskimage-builder*)
  and located in TFTP root directory - again see README [1]_.

* *ironic-discoverd* support will be optional and disabled by default, thus no
  impact on fresh or upgraded installations.

Developer impact
----------------

Driver developers may use ``DiscoverdInspect`` to provide in-band
hardware discovery for their drivers.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Dmitry Tantsur, LP: divius, IRC: dtantsur

Work Items
----------

* Add new configuration options.

* Implement ``DiscoverdInspect`` interface.

Dependencies
============

* Generic bits for the discovery [3]_

* *ironic-discoverd* package should be installed from PyPI or RDO to enable
  this feature. Version 1.0.0 [6]_ (to be released in the beginning of
  February) will be a requirement for the new interface.
  Drivers using it will refuse to load without it, if ``discoverd.enabled`` is
  set to true.

* Driver-specific periodic task as specified in [5]_ is suggested for use.
  If that spec is not accepted, we'll fall back to using a looping call
  instead.

Testing
=======

* Unit testing with mocking ``ironic_discoverd.client`` for now

* As a follow-up I hope to add support for *ironic-discoverd* to devstack and
  then have a functional test. This however will consume much time and depends
  on the functional testing discussions going on.

  As stated above, *ironic-discoverd* will be disabled by default.

Upgrades and Backwards Compatibility
====================================

None

Documentation Impact
====================

It should be documented how to enable in-band inspection within Ironic.
The documentation should point to *ironic-discoverd* README for the
installation instruction.

References
==========

.. [1] *ironic-discoverd*: https://pypi.python.org/pypi/ironic-discoverd

.. [2] Reference ramdisk: http://bit.ly/1yD9nnq

.. [3] Parent spec: https://review.openstack.org/#/c/100951/

.. [4] *ironic-discoverd* status API blueprint:
        https://blueprints.launchpad.net/ironic-discoverd/+spec/get-status-api

.. [5] Driver-specific periodic tasks spec:
       https://review.openstack.org/#/c/135589

.. [6] *ironic-discoverd* 1.0.0 release status:
       https://bugs.launchpad.net/ironic-discoverd/+milestone/1.0.0
