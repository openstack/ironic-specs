..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=========================
Future of classic drivers
=========================

https://bugs.launchpad.net/ironic/+bug/1690185

This specification discusses the future of the classic drivers after the
:doc:`../7.0/driver-composition-reform` was implemented in the Ocata
cycle. Terminology here follows one of that specification.

Problem description
===================

We do not want to maintain two approaches to building drivers long-term.
It increases complexity of the source code (see e.g. `driver_factory.py`_)
and the amount of testing for 3rdparty CI.

Proposed change
===============

The change covers several cycles:

**Pike**

In the Pike cycle hardware types and classic drivers will co-exist as equally
supported ways of writing drivers.

* Dynamic drivers and all related API are considered stable and ready
  for production use.

  .. note::
     In the Ocata release notes we called the related API additions
     experimental.

* No more classic drivers are accepted in tree.

* No new interfaces are added to the existing classic drivers.

* No interface implementations are changed in the existing classic drivers.

* We *recommend* the vendors to provide hardware types analogous to their
  existing classic drivers. 3rd party CI should provide the complete coverage
  of all supported boot, deploy, management and power interface combinations.
  It's up to the vendors to decide whether to use classic drivers or hardware
  types to achieve that.

**Queens**

In the Queens cycle we will deprecate classic drivers.

* We will *require* the vendors to provide hardware types analogous to their
  existing classic drivers. It is up to the vendors to choose the combination
  of interfaces to support. It will be *recommended*, however, to keep support
  for standard deploy and inspect interface implementations, if possible.

* 3rd party CI will have to cover all hardware types and all supported
  combinations of the boot, deploy, management and power interfaces.
  3rd party CI will be able to stop covering supported classic drivers, when
  their functionality is covered through hardware types.

* The classic drivers mechanism will be deprecated, and loading any classic
  driver (in-tree or out-of-tree) will result in a deprecation warning.
  The ``enable_drivers`` configuration option will be also deprecated.

  .. note::
     In the Queens release we will continue running regular CI against
     classic drivers still.

* Existing (in-tree) classic drivers will only receive critical bug fixes as
  related to the classic interface (i.e. they will still be affected by fixes
  in the interface implementations they share with hardware types).

* Most of the upstream CI will run on the dynamic drivers (``ipmi``, ``snmp``
  and ``redfish``). The standalone job will provide coverage for classic
  drivers. Grenade will be testing switch from classic drivers (e.g.
  ``pxe_ipmitool``) to hardware types (e.g. ``ipmi``).

* Deprecate ``-t``/``--type`` argument to driver listing commands in
  ``python-ironicclient``.

  .. note::
     Deprecating or removing the ``type`` argument to the driver listing API
     is outside of the scope of this proposal.

* Extend the upgrade documentation to contain a full mapping between supported
  classic drivers and associated combination of a hardware type and hardware
  interfaces. Explicitly mention classic drivers that will not receive a new
  counterpart per vendor decision, and which replacement is recommended for
  such drivers.

* Update the whole documentation to only mention hardware types, except for
  the driver-specific documentation and the upgrade documentation bit explained
  above.

* Provide automatic migration to hardware types as part of the
  ``online_data_migration`` command - see `Automatic migration`_.

  .. note::
    We decided to not provide any automatic migration on the API level in the
    node create and update API. Doing so would require us to maintain mapping
    between classic drivers and corresponding hardware types/interfaces
    foreever. It also may be confusing for operators, if, for example, the
    result of the node creation request differs from the outcome.

**Rocky**

In the Rocky release the support for classic drivers is removed.

* Remove all in-tree classic drivers.

* Remove support for loading classic drivers from `driver_factory.py`_.

* Remove the ``enable_drivers`` configuration option.

* Remove CI coverage for classic drivers.

* Remove ``-t``/``--type`` argument to driver listing commands in
  ``python-ironicclient``.

* Update the driver listing API to always return an empty result when
  ``classic`` type is requested.

Automatic migration
-------------------

To simplify transition for operators, make ``online_data_migration`` in the
Queens release automatically update nodes.

* Extend BaseDriver_ with a new class method:

  .. code-block:: python

    @classmethod
    def to_hardware_type(cls):
        """Return corresponding hardware type and hardware interfaces.

        :returns: a tuple with two items:

            * new driver field - the target hardware type
            * dictionary containing interfaces to update, e.g.
              {'deploy': 'iscsi', 'power': 'ipmitool'}
        """

  For example, for the ``agent_ipmitool`` driver:

  .. code-block:: python

    @classmethod
    def to_hardware_type(cls):
        if CONF.inspector.enabled:
            inspect_interface = 'inspector'
        else:
            inspect_interface = 'no-inspect'

        return 'ipmi', {'boot': 'pxe',
                        'deploy': 'direct',
                        'inspect': inspect_interface,
                        'management': 'ipmitool',
                        'power': 'ipmitool',
                        'raid': 'agent'}

* Update the ``online_data_migrations`` to accept options for migrations in
  the form of ``--option <MIGRATION NAME><KEY>=<VALUE>``. They will be passed
  as keyword arguments to the migration matching the provided name.

* Update the ``online_data_migrations`` command with a new migration
  ``migrate_to_harware_types``. It will accept one option
  ``reset_unsupported_interfaces``, which is a boolean value with the default
  of ``False``. The migration will do the following:

  #. Load classes for all classic drivers in the ``ironic.drivers`` entrypoint
     (but do not instantiate them).

  #. For each classic driver:

     #. Calculate required changes using ``DriverClass.to_hardware_type``.

        Missing interfaces, other than ``boot``, ``deploy``, ``management``
        and ``power``, are defaulted to their no-op implementations
        (``no-***``).

        .. note::
            We consider ``boot``, ``deploy``, ``management`` and ``power``
            mandatory, as they do not have a no-op implementation.

     #. If the hardware type is not in ``enabled_hardware_types``, issue a
        and skip all nodes with this classic driver.

     #. If any interface is not enabled (not in ``enabled_***_interfaces``):

        #. if this interface is one of ``boot``, ``deploy``, ``management``
           or ``power``, or if ``reset_unsupported_interfaces`` is ``False``,
           issue a warning and skip the nodes.

        #. otherwise try again with resetting the interface to its no-op
           implementation (``no-***``).

     #. Update the node record in the database.

     .. note::
         Due to idempotency of the migrations, operators will be able to
         re-run this command after fixing the warnings to update the
         skipped nodes.

* In the **Rocky** cycle, update the ``dbsync`` command with a check that no
  nodes are using classic drivers. As the list of classic drivers will not be
  available at that time (they will be removed from the tree), maintain the
  list of classic driver names that used to be in tree and check nodes against
  this list. Remove this check in the release after Rocky.

Alternatives
------------

* Keep classic drivers forever. Complicates maintenance for unclear reasons.

* Start deprecation in the Pike cycle. We wanted to have at least one cycle
  where hardware types are fully supported before we jump into deprecation.
  Also, in this case we will have to rush the vendors into creating and
  supporting their hardware types before end of Pike.

Data model impact
-----------------

None

State Machine Impact
--------------------

None

REST API impact
---------------

Due to the way we designed :doc:`../approved/driver-composition-reform`,
dynamic drivers look very similar to the classic drivers for API point of view.

We could deprecate the ``type`` argument to the driver listing API. However,

#. API deprecations are hard to communicate,
#. due to API versioning, we will still have to support it forever.

Thus, this specification does not propose deprecating anything in the API.

Client (CLI) impact
-------------------

"ironic" CLI
~~~~~~~~~~~~

Deprecate ``-t`` argument to the ``driver-list`` command in the Queens cycle
and remove it in Rocky.

"openstack baremetal" CLI
~~~~~~~~~~~~~~~~~~~~~~~~~

Deprecate ``--type`` argument to the ``baremetal driver list`` command in the
Queens cycle and remove it in Rocky.

RPC API impact
--------------

None

Driver API impact
-----------------

* In the Queens release, all classic drivers will behave as if they had
  ``supported = False``.

* In the Rocky release, support for loading classic drivers will be removed.
  ``BaseDriver`` will be merged with ``BareDriver``, code in
  `driver_factory.py`_ will be substantially simplified.

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

Users of Ironic will have to switch their deployment to hardware types before
upgrading to Rocky.

Scalability impact
------------------

None

Performance Impact
------------------

None

Other deployer impact
---------------------

See `Upgrades and Backwards Compatibility`_.

Developer impact
----------------

Out-of-tree classic drivers will not work with the Rocky release of Ironic.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Dmitry Tantsur (IRC: dtantsur, LP: divius)

Work Items
----------

See `Proposed Change`_ for the quite detailed breakdown.

Dependencies
============

None

Testing
=======

Starting with the Queens release, our CI will mainly test hardware types.

We will modify the Grenade job testing Pike -> Queens upgrade to switch
from ``*_ipmitool`` to ``ipmi`` during the upgrade.

Upgrades and Backwards Compatibility
====================================

Removing the drivers and the classic driver mechanism is going to be a
breaking change and has to be communicated accordingly.

Operators will have to enable appropriate hardware types and hardware
interfaces in the Queens release.

Documentation Impact
====================

The upgrade guide will be updated to explain moving from classic drivers
to hardware types with a examples and a mapping between old and new drivers.

References
==========

.. _driver_factory.py: https://opendev.org/openstack/ironic/src/branch/master/ironic/common/driver_factory.py
.. _BaseDriver: https://docs.openstack.org/ironic/latest/contributor/api/ironic.drivers.base.html#ironic.drivers.base.BaseDriver
