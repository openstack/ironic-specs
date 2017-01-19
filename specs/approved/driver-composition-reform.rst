..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=========================
Driver composition reform
=========================

https://bugs.launchpad.net/ironic/+bug/1524745

This spec suggests revamping how we name and compose drivers from interfaces.
It will allow having one vendor driver with options configurable per node
instead of many drivers for every vendor.

Problem description
===================

Our driver interface matrix has become increasingly complex. To top it all off
nowadays we have many interfaces that can be used for every driver. To name a
few:

* ``boot``: most drivers support PXE and iPXE, while some also support
  virtual media; support for *petitboot* bootloader is proposed.

* ``deploy``: two deploy approaches are supported: write image via iSCSI or
  write it directly from within the agent.

* ``inspect``: there is generic inspection using ironic-inspector, but some
  drivers also allow out-of-band inspection. This feature is optional, so we
  should provide a way to disable it.

Currently we've ended up with a complex and really confusing naming scheme.
For example:

* ``pxe_ipmitool`` uses PXE or iPXE for boot and iSCSI for deploy.

* ``agent_ipmitool`` actually also uses PXE or iPXE, but it does not use iSCSI.

* To top it all, ``pxe_ipmitool`` is actually using agent!

* To reflect all the possibilities, the names would have to be more like
  ``pxe_iscsi_ipmitool``, ``ipxe_iscsi_ipmitool``, ``pxe_direct_ipmitool``,
  ``ipxe_direct_ipmitool``, etc.

* Now repeat the same with every power driver we have.

Proposed change
===============

Introduction
------------

The following concepts are used in this spec:

**vendor**
    The driving force behind a specific driver. It can be hardware vendors
    or the ironic team itself in case of generic drivers, such as IPMI.
    This also includes out-of-tree drivers.
**hardware interface** (or just **interface**)
    A notion replacing the term "driver interface" - a set of functionality
    dealing with some aspect of bare metal provisioning in a vendor-specific
    way. For example, right now we have ``power``, ``deploy``, ``inspect``,
    ``boot`` and a few more interfaces.
**hardware type**
    A family of hardware supporting the same set of interfaces from the ironic
    standpoint. This can be as wide as all hardware supporting the IPMI
    protocol or as narrow as several hardware models supporting some specific
    interfaces.
**driver**
    A thin object containing links to hardware interfaces. Before this spec
    *driver* meant roughly the same as *hardware type* means in this spec.
**classic driver**
    An ironic driver from before this spec: a class with links to interfaces
    hardcoded in the Python code.
**dynamic driver**
    A *driver* created at run time with links to interfaces generated based on
    information in the node record (including hardware type and interfaces).

With this spec we are going to achieve the following goals:

* Make *vendors* in charge of defining a set of supported interface
  implementations in priority order.

* Allow *vendors* to guarantee that unsupported interface implementations
  will not be used with hardware types they define. This is done by having
  a hardware type list all interfaces it supports.

* Allow 3rd parties to create out-of-tree *hardware types* that allow them to
  maximize their reuse of the in-tree interface implementations.

* Make *hardware type* definition as declarative as possible.

* Allow a user to switch *hardware type* for a node, just as it was possible
  to change a driver before this spec.

* Allow a user to switch between *interface* implementations supported by
  a *hardware type* for a node via the bare metal API.

Configuration
-------------

* A *hardware type* is defined as a Python class - see `Hardware Types`_ for
  details. An entry point is created to provide a simple name for each
  *hardware type*, for example::

    ironic.hardware.types =
        generic-ipmi = ironic.hardware.ipmi:GenericIpmiHardware
        ilo-gen8 = ironic.hardware.ilo:iLOGen8Hardware
        ilo-gen9 = ironic.hardware.ilo:iLOGen9Hardware

* The list of *hardware interfaces* is still hardcoded in the Python code
  and cannot be extended by plugins. The interfaces are implemented
  in the same way as before this spec: by subclassing an appropriate
  abstract class from `ironic.drivers.base
  <http://docs.openstack.org/developer/ironic/api/ironic.drivers.base.html#module-ironic.drivers.base>`_.

* For each *hardware interface*, all implementations get their own entrypoint
  and a unique name, for example::

    ironic.hardware.interfaces.power =
        ipmitool = ironic.drivers.modules.ipmitool:IpmitoolPower

* Compatibility between *hardware types* and *hardware interface*
  implementations is expressed in the Python code - see `Hardware Types`_
  for details.

* Create a new configuration option ``enabled_hardware_types`` with a list of
  enabled *hardware types*. This will not include *classic drivers* which
  are enabled by the existing ``enabled_drivers`` option.

* Create a family of configuration options ``default_<INTERFACE>_interface``
  that allows an operator to explicitly set a default interface for new nodes
  upon creation, if one is not specified in the creation request.

  Here ``<INTERFACE>`` is a type of interface: power, management, etc.

* Create a family of configuration options ``enabled_<INTERFACE>_interfaces``
  with a list of enabled implementations of each *hardware interface* that
  are available for use in the ironic deployment.

  The default value, if provided by the ``default_<INTERFACE>_interface``, must
  be in this list, otherwise a conductor will fail to start.

* If no interface implementation is explicitly requested by a user in a node
  creation request, use the value calculated as follows:

  * If ``default_<INTERFACE>_interface`` is set, use its value. Return an
    error if it is not supported by the *hardware type* of the node.

  * Otherwise choose the first available interface implementation from an
    intersection of the ``enabled_<INTERFACE>_interfaces`` as defined in
    the deployment's configuration and the *hardware_type*'s priority ordered
    list of supported_<INTERFACE>_interfaces. Return an error, if this
    intersection is empty.

  This calculated default will be stored in the database entry for the node
  upon creation.

* Change how we load drivers instead of one singleton instance of a driver,
  we'll have an instance of *dynamic driver* per node, containing links
  to hardware interface implementations (just like today).

  However, interface implementations themselves will stay singletons, and will
  be preloaded during the start up and stored in the conductor.

  Conductor will fail to start if any **enabled** *hardware types* or
  *interface* implementations cannot be loaded (e.g. due to missing
  dependencies).

  .. note::
     While it's technically possible to enable interfaces that are not used in
     any of enabled *hardware types*, they will not get loaded in this case.

  The *classic drivers* will be loaded exactly as before.

* Modify the periodic tasks collection code to also collect periodic tasks
  for enabled interfaces of every enabled *hardware type*.

* Conductor will fail to start if there is a name clash between a *classic
  driver* and a *hardware type*.

Database and Rest API
---------------------

* Allow the node ``driver`` field to accept the *hardware types* as well.
  This will work in all API versions.

  .. note::
     There are two reasons for that:

     * Consistency: we never prevented new drivers to be used with old API
       versions, and *dynamic drivers* will look mostly like new drivers to
       users.

     * Usability: we plan on eventually deprecating the classic drivers.
       When we remove them, all clients will need to specify the *hardware
       types* when enrolling nodes. To allow older clients to continue
       interacting with the API service, even as they use new driver
       names (hardware types), we must continue to use the same field name and
       API semantics.

* For each interface create a new field on the ``node`` table named
  ``<interface_name>_interface``. A migration will be needed each time
  we add a new interface (which hopefully won't happen too often).

  For *hardware types* setting ``<interface_name>_interface`` field to ``None``
  means using the calculated default value as described in Configuration_.

  Trying to set any of these fields to a value other than ``None`` will result
  in an error if the ``driver`` field is set to a *classic driver*. Similarly,
  all these fields are reset to ``None`` if the ``driver`` field is set to
  a *classic driver*.

* Every time ``driver`` and/or any of the interface fields is updated,
  the conductor checks that the *hardware type* supports all the resulting
  interfaces (except when ``driver`` is set to a *classic driver*).

  To change between two incompatible sets of interfaces, all changes should
  come in one API call. E.g. for a node with the ``ilo-gen8`` *hardware type*
  and ``vmedia_ilo`` boot interface the following JSON patch will be allowed::

    [
        {"op": "replace", "path": "/boot_interface", "value": "ipxe"},
        {"op": "replace", "path": "/driver", "value": "generic-ipmi"}
    ]

  but the following patch will fail because of incompatible boot interface::

    [
        {"op": "replace", "path": "/driver", "value": "generic-ipmi"},
    ]

  .. note::
    `RFC 6902 <https://tools.ietf.org/html/rfc6902#section-5>`_ requires
    a JSON patch to be atomic, because an HTTP PATCH operation must be atomic.
    Meaning, it's possible for some operations to end up with an inconsistent
    object as long as the end result is consistent.

  The validation will be conducted on the API service side by checking the new
  ``conductor_hardware_interfaces`` database table.

* If for some reason the existing *interface* becomes invalid for a node (e.g.
  it was disabled after the node was enrolled), it will be signalized via the
  usual node validation API. The validation for this interface won't pass with
  an appropriate error message. On the programming level, the driver attribute
  for this interface (e.g. ``task.driver.deploy``) will be set to ``None``.

* Update ``GET /v1/drivers`` to also list enabled *hardware types*.
  This change is **not** affected by API versioning, because we allow old API
  versions to use *hardware types* with the ``driver`` field.

* Allow ``GET /v1/drivers`` to filter only *hardware types* or only *classic
  drivers*.

  Update ``GET /v1/drivers/<HW TYPE>`` to report the *hardware type*
  information, including the list of enabled *hardware interfaces*.

  This feature is guarded by an API version bump (as usual).

* Allow filtering nodes by ``<interface_name>_interface`` fields in the node
  list API.

  This feature is guarded by an API version bump (as usual).

* Create a new table ``conductor_hardware_interfaces`` to hold the relationship
  between conductors, hardware types and available interfaces. A warning will
  be issued on conductor start up, if it detects that other conductors have
  a different set of interfaces for the same enabled *hardware type*. This
  will also track the default interface for each hardware type and interface
  type combination.

  This situation is inevitable during live upgrades, so it must not result in
  an error. However, we will document that all conductors should have the same
  set of interfaces for the same enabled *hardware types*.

  This table will not be exposed in the HTTP API for now.

Deprecations
------------

We are **not** planning to deprecate and remove the support for *classic
drivers* in the V1 API.

We are planning to deprecate and remove the *classic drivers* which exist
in-tree. The deprecation procedure may be tricky and will be covered by a
follow-up spec.

Alternatives
------------

* We could put interfaces under a new JSON key on a node. However, we're
  trying to move away from informally defined JSON keys. It would also prevent
  us from being able to implement the filtering of nodes based on a particular
  interface.

* We could create a new API endpoint for updating the interfaces. This will be
  inconsistent with how we update the ``driver`` field though.

  We could then create a new API version, preventing updating ``driver`` via
  the regular node update API, but that would be a breaking change.

* We could create a new field ``hardware_type`` instead of having the existing
  ``driver`` field accept a *hardware type*. This was a part of the
  proposal previously, but we found that it complicates things substantially
  without clear benefits.

* We could create a whole new family of API endpoints instead of reusing
  ``/v1/drivers``, e.g.  ``/v1/hardware-types``. However, it would require us
  to replicate all driver-related functionality nearly intact, for example
  driver vendor passthru. So users would have to somehow figure out which
  vendor passthru endpoint to use based on what kind of a driver is in the
  ``driver`` field.

Data model impact
-----------------

* For each interface, create a new node field ``<interface_name>_interface``
  initially set to ``NULL``.

* Create a new internal table ``conductor_hardware_interfaces``:

  ``conductor_id`` - conductor ID (foreign key to conductors table),

  ``hardware_type VARCHAR(255)`` - *hardware type* entrypoint name,

  ``interface_type VARCHAR(16)`` - interface type name (e.g. ``deploy``),

  ``interface_name VARCHAR(255)`` - interface implementation entry point name.

  ``default TINYINT(1)`` - boolean which denotes if this ``interface_name`` is
                           the default for a given ``hardware_type`` and
                           ``interface_type`` combination.

  This table will get populated on conductor start up and purged on deleting
  the conductor record. On conductor startup, during init_host(), the conductor
  will fetch the list of hardware interfaces supported by all registered
  conductors and compare to its own configuration. If the same *hardware type*
  is enabled on two conductors with a different set of enabled_interfaces, this
  will result in a WARNING log message. The enabled *hardware types* themselves
  do not have to match (just like today, different conductors can have
  different set of drivers).

State Machine Impact
--------------------

None

REST API impact
---------------

* Update ``GET /v1/drivers``:

  Return both *classic drivers* and *hardware types* no matter which API
  version is used.

  New URL parameters:

  * ``type`` (string, one of ``classic``, ``dynamic``, optional) - if provided,
    limit the resulting driver list to only *classic drivers* or *hardware
    types* accordingly.

  New response field:

  ``type`` whether the driver is *dynamic* or *classic*.

  This change is guarded by a new API version.

* Update ``GET /v1/drivers/<NAME>``:

  New response field:

  ``type`` whether the driver is *dynamic* or *classic*.

  New response fields that are not ``None`` only for *hardware types*:

  ``default_<interface_name>_interface``
    the entrypoint name of the calculated default implementation for a
    given interface.

  ``enabled_<interface_name>_interfaces``
    the list of entrypoint names of enabled implementations for a given
    interface.

* Update ``GET /v1/drivers/<NAME>/properties`` and ``GET
  /v1/drivers/<NAME>/vendor_passthru/methods`` and the actual driver vendor
  passthru call implementation:

  When requested for a *dynamic driver*, assume the calculated defaults for
  the ``vendor`` interface implementation as described in Configuration_.
  We will need to support non-default implementations as well, but it goes
  somewhat beyond the scope of this already big spec.

Client (CLI) impact
-------------------

"ironic" CLI
~~~~~~~~~~~~

* Update the node creation command to accept one argument per interface.
  Example::

    ironic node-create --driver=ilo-gen9 --power-interface=redfish

  The same change is applied to the OSC plugin.

* Extend the output of the ``driver-list`` command with the ``Type`` column.

* Extend the ``driver-list`` command with ``--type`` argument, which, if
  supplied, limits the driver list to only *classic drivers* (``classic``
  value) or *hardware types* (``dynamic`` value).

* Extend the output of the ``driver-show`` command with the newly introduced
  fields.

"openstack baremetal" CLI
~~~~~~~~~~~~~~~~~~~~~~~~~

Similar changes to what's in `"ironic" CLI`_ are applied here.

RPC API impact
--------------

* No impact on the hash ring, as both *hardware types* and *classic drivers*
  are used in the same field.

Driver API impact
-----------------

Hardware Types
~~~~~~~~~~~~~~

* Create a new ``AbstractHardwareType`` class as an abstract base class for
  all hardware types. Here is a simplified example implementation, using only
  power, deploy and inspect interfaces::

    import abc, six

    @six.add_metaclass(abc.ABCMeta)
    class AbstractHardwareType(object):
        @abc.abstractproperty
        def supported_power_interfaces(self):
            pass

        @abc.abstractproperty
        def supported_deploy_interfaces(self):
            pass

        @property
        def supported_inspect_interfaces(self):
            return [NoopInspect]

  Note that some interfaces (power, deploy) are mandatory, while the other
  (inspect) are not. A dummy implementation will be provided for all optional
  interfaces. Depending on the specific call it will either do nothing or
  raise an error. For user-initiated calls (e.g. start inspection), an error
  will be returned. For internal calls (e.g. attach cleaning ports), no action
  will be taked.

* Create a new ``GenericHardwareType`` class which most of the actual hardware
  type classes will want to subclass. This class will insert generic
  implementations for some interfaces::

    class GenericHardwareType(AbstractHardwareType):
        supported_deploy_interfaces = [AgentDeploy]
        supported_inspect_interfaces = [NoopInspect, InspectorInspect]

  Note that all properties contain classes, not instances. Also note that
  order matters: in this example ``NoopInspect`` will be the default, if
  both implementations are enabled in the configuration.

* Here is an example of how hardware types could be created::

    class GenericIpmiHardware(GenericHardwareType):
        supported_power_interfaces = [IpmitoolPower, IpminativePower]

    class iLOGen8Hardware(GenericHardwareType):
        supported_power_interfaces = (
            GenericIpmiHardware.supported_power_interfaces
            + [IloPower]
        )
        supported_inspect_interfaces = (
            GenericHardwareType.supported_inspect_interfaces
            + [IloInspect]
        )

    class iLOGen9Hardware(iLOGen8Hardware):
        supported_power_interfaces = (
            iLOGen8Hardware.supported_power_interfaces
            + [RedfishPower]
        )

.. note::
   These definitions use classes, not entrypoints names. These examples assume
   the required classes are imported.

.. note::
    The following entrypoints will have to be defined for these examples to
    work::

        ironic.hardware.types =
            generic-ipmi = ironic.hardware.ipmi:GenericIpmiHardware
            ilo-gen8 = ironic.hardware.ilo:iLOGen8Hardware
            ilo-gen9 = ironic.hardware.ilo:iLOGen9Hardware

        ironic.hardware.interfaces.power =
            ipmitool = ironic.drivers.modules.ipmitool:IpmitoolPower
            ipminative = ironic.drivers.modules.ipmitool:IpminativePower
            ilo = ironic.drivers.modules.ilo:IloPower
            redfish = ironic.drivers.modules.redfish:RedfishPower

        ironic.hardware.interfaces.inspect =
            inspector = ironic.drivers.modules.inspector:InspectorInspect
            ilo = ironic.drivers.modules.ilo:IloInspect

    The following configuration will be required to enable everything in these
    examples::

        [DEFAULT]
        enabled_hardware_types = generic-ipmi,ilo-gen8,ilo-gen9
        enabled_power_interfaces = ipmitool,ipminative,ilo,redfish
        enabled_inspect_interfaces = inspector,ilo

Driver Creation
~~~~~~~~~~~~~~~

* At start up time the conductor instantiates all enabled hardware types,
  as well as all enabled interface implementations for enabled hardware types.

* Each time the node is created or loaded from the database, a thin BareDriver_
  object is created with all interfaces set on it. This is similar to how
  network drivers already work. It gets assigned to ``task.driver``, and after
  that everything works as before this spec.

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

* End users should switch to *hardware types* over time.

Scalability impact
------------------

None

Performance Impact
------------------

* A driver instance will be now created per node as opposed to creating one per
  conductor right now. This will somewhat increase the memory usage per node.
  We can probably define __slots__ on the driver class to reduce this effect.

Other deployer impact
---------------------

* A deployer can set the new ``enabled_hardware_types`` option to enable more
  *hardware types*. Otherwise only the default *hardware types* and already
  enabled classic drivers will be available.

* A deployer can also set any of new ``enabled_<INTERFACE>_interfaces`` options
  to enable more *interfaces* for the enabled *hardware types*.

Developer impact
----------------

This spec changes the way we expect the developers to write their drivers.

* No more new *classic drivers* will be accepted in-tree as soon as this change
  lands.

* Developers should implement *hardware types* and *interfaces* to provide
  new hardware support for Ironic. Built-in *interfaces* implementations will
  be available for reuse both in-tree and out-of-tree.

Implementation
==============

Assignee(s)
-----------

* Dmitry Tantsur (lp: divius, irc: dtantsur)
* Jim Rollenhagen (irc: jroll)

Work Items
----------

* Create base classes supporting *hardware types*.

* Create tables for tracking enabled *hardware interfaces*.

* Load *hardware types* on conductor start up and record them in the internal
  table.

* Create node fields for *interfaces* and expose them in the API.

* Update the drivers API to support *hardware types*.

* Create the *hardware types* for hardware supported directly by the team,
  i.e. the generic IPMI-compatible hardware. The SSH driver might be removed
  soon; it won't get updated in this case.

Dependencies
============

* For the vendor interface to be really pluggable, we need to `promote agent
  passthru to the core API
  <http://specs.openstack.org/openstack/ironic-specs/specs/approved/agent-api.html>`_.

Testing
=======

* Unit test coverage will obviously be provided.

* A new gate job will be created, using a dynamic version of the IPMI driver.
  We will aim to make it the primary approach in the gate over time.

* Grenade testing for upgrades / migration of existing workloads to new
  drivers.

Upgrades and Backwards Compatibility
====================================

This reform is designed to be backward compatible. The *classic drivers* will
be supported for at least some time. A separate spec will cover the
deprecation of the *classic drivers*.

We will recommend switching to using appropriate *dynamic drivers* as soon as
it's possible.

Upgrade flow
------------

#. Ironic is updated to a version supporting *dynamic drivers*.
   The API version used by clients is not updated yet.

#. All nodes are still using *classic drivers*. On a node ``driver=x_y``.

#. Users with an old API version:

   * can set ``driver`` to a *classic driver*.
   * can set ``driver`` to a *hardware type*, which will result in using a
     *dynamic driver* with the default set of interfaces.

#. Users with a new API version:

   * can set ``driver`` to a *hardware type* or a *classic driver*
   * can set non-default interface implementations when ``driver``
     is set to a real *hardware type*

Documentation Impact
====================

* Document switching to *dynamic drivers*

* Document creating new *hardware types*

References
==========

Initial etherpad: https://etherpad.openstack.org/p/liberty-ironic-driver-composition

Newton etherpad: https://etherpad.openstack.org/p/ironic-newton-summit-driver-composition

.. _BareDriver: http://docs.openstack.org/developer/ironic/api/ironic.drivers.base.html#ironic.drivers.base.BareDriver
