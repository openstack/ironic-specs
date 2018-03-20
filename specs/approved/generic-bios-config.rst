..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=========================================
Hardware interface for BIOS configuration
=========================================

https://bugs.launchpad.net/ironic/+bug/1712032

The proposal is intended to create a new hardware interface for BIOS automated
configuration and a method to make BIOS configuration available as part of
manual cleaning [0].

Problem description
===================

* There are several use cases that need to configure BIOS options to enable
  certain functionality or gain performance optimization on OpenStack baremetal
  nodes. For example, in order to use SRIOV [1] or DPDK [2] technologies, the
  'Virtualization Technology' BIOS option shall be enabled; to achieve
  deterministic low packet latency in real time scenario, BIOS options related
  to Power Management, CPU sleep states etc shall be disabled; another good
  example is console redirection BIOS settings.

Proposed change
===============

* After a node is enrolled and the basic hardware information is available, the
  operator can define a BIOS configuration.

* The operator will be able to set the BIOS configuration for a specific node
  using a cleaning step which will be defined on the new ``BIOSInterface``.
  The BIOS settings to be changed will be passed in the form of a JSON
  dictionary as an argument to the cleaning step. This cleaning step will be
  manual at the moment, but it may be extended to be an automated cleaning step
  in the future.

* Similar to the RAIDInterface, this proposes a new hardware interface called
  ``BIOSInterface`` which will be used for out-of-band BIOS configuration for
  hardware types. Calling it BIOSInterface doesn't mean the spec is specific to
  BIOS systems, but a general interface name for systems such as BIOS, UEFI
  etc. Please refer to Driver API impact for a list of methods that will be
  added for this interface.

  .. note::
     The reason of using BIOS instead of others is that it's hard to find a
     proper name that applies to all the systems and BIOS is agreed to be
     close enough.

* The credentials of BIOS configuration which reuse the existing credentials in
  ``driver_info`` will be validated when going from enroll to manageable.

* A new database table ``bios_settings`` will be created if not exist and the
  current BIOS settings will be retrieved and updated for the node as part of
  entering cleaning step in ``_do_node_clean``, this means it will be called
  for both manual and automated cleaning. After the given BIOS options are
  successfully applied in baremetal, it will update the cached bios settings
  with applied changes.

* This interface will not be available with any of the classic drivers. And
  classic drivers would throw 'UnsupportedDriverExtension' for this interface.

* If there is no BIOS interface for a node (i.e. bios_interface='no-bios'),
  an attempt to change BIOS configuration will result in cleaning step not
  found error.


Alternatives
------------

* Operator can change the BIOS configuration manually whenever required. But
  this has to be done for each node which is time-consuming and error-prone.

Data model impact
-----------------

* Unlike the RAID configuration [3], the target BIOS settings will be passed as
  an argument to cleaning step and not stored in the database.

* The current BIOS config will be cached and will be stored in a separate BIOS
  table. The following database table and fields will be added:

  * A new table named ``bios_settings`` will be added with the following
    fields:

    + node_id

      - Integer
      - PrimaryKeyConstraint
      - ForeignKeyConstraint('nodes.id')

    + name

      - String
      - PrimaryKeyConstraint

    + value

      - String

    + created_at

      - DateTime

    + updated_at

      - DateTime

    It will store the cached BIOS information that was retrieved from the node
    and will be updated when the BIOS settings are changed. 'created_at' and
    'updated_at' fields will be updated accordingly when a new record is added
    or the existing record is updated.

  * ``node.bios_interface`` will be added to node table, and it will contain
    the hardware interface we want to use for BIOS automation.

  * New objects ``ironic.objects.bios.BIOSSetting`` and
    ``ironic.objects.bios.BIOSSettingList`` will be added to object model.
    The ``BIOSSetting`` and ``BIOSSettingList`` fields in the python object
    model will be populated on-demand.

State Machine Impact
--------------------

* When going from enroll to manageable, credentials are validated to make sure
  user has the proper rights to access the BIOS config.

REST API impact
---------------

Two new cleaning steps are proposed to be implemented on the ``BIOSInterface``:

* bios.factory_reset. It will trigger the BIOS settings factory reset for
  a given node. For example::

    {
      "target":"clean",
      "clean_steps": [{
        "interface": "bios",
        "step": "factory_reset"
      }]
    }

* bios.apply_configuration. It will set the given settings to the BIOS
  of a given node. For example::

    {
      "target":"clean",
      "clean_steps": [{
        "interface": "bios",
        "step": "apply_configuration",
        "args": {
          "settings": [
            {
              "name": <name>,
              "value": <value>
            },
            {
              "name": <name>,
              "value": <value>
            }
          ]
        }
      }]
    }

* A new REST API will be introduced to get the cached BIOS config for a node::

    GET /v1/nodes/<node_ident>/bios

  The operation will return the currently cached settings with the following
  data schema::

    {
      "bios": [
        {
          "links": [
            {
              "href": "http://127.0.0.1:6385/v1/nodes/<node_ident>/bios/<name>",
              "rel": "self"
            },
            {
              "href": "http://127.0.0.1:6385/nodes/<node_ident>/bios/<name>",
              "rel": "bookmark"
            }
          ],
          "name": <name>,
          "value": <value>
        },
        {
          "links": [
            {
              "href": "http://127.0.0.1:6385/v1/nodes/<node_ident>/bios/<name>",
              "rel": "self"
            },
            {
              "href": "http://127.0.0.1:6385/nodes/<node_ident>/bios/<name>",
              "rel": "bookmark"
            }
          ],
          "name": <name>,
          "value": <value>
        }
      ]
    }

  The API will return HTTP 400 (Bad Request) if driver doesn't support BIOS
  configuration or 404 (Resource Not Found) if node BIOS has not yet been
  configured. Otherwise it will return HTTP 200 (OK).

* To get a specified BIOS setting for a node::

    GET /v1/nodes/<node_ident>/bios/<setting name>

  The operation will return the specified BIOS setting with the following
  data schema::

    {
      "<setting name>":
        {
          "name": <setting name>,
          "value": <value>
        }
    }

Client (CLI) impact
-------------------

"ironic" CLI
~~~~~~~~~~~~

The ironic CLI will not be updated.

"openstack baremetal" CLI
~~~~~~~~~~~~~~~~~~~~~~~~~

* To retrieve the cached BIOS configuration with node-uuid::

   $ openstack baremetal node bios setting list <node-uuid>

* To show a specified BIOS setting with node-uuid::

   $ openstack baremetal node bios setting show <node-uuid> <setting-name>

* The validation result of BIOS Interface will be returned through the standard
  validation interface.


RPC API impact
--------------

None

Driver API impact
-----------------

A new ``BIOSInterface`` will be available for the drivers to allow them to
implement BIOS configuration. There will be several new methods and cleaning
steps in the interface:

- ``do_factory_reset()`` - This method is called to reset all the BIOS
  settings supported by driver to factory default. It will also update
  the records of ``bios_settings`` database table to the known defaults once
  reset action succeeds. It is up to the vendor to decide the BIOS defaults
  settings that will be set.

- ``factory_reset()`` - This cleaning step will delegate the actual reset
  work into the abstract method ``do_factory_reset()``.

  The operator can choose to call it as part of manual cleaning steps. The
  corresponding manual cleaning step will be ``bios.factory_reset``.

- ``do_apply_configuration(configuration={})`` - The driver implementation
  of this method will take the settings from the configuration dictionary
  and will apply BIOS configuration on the bare metal. The driver is
  responsible for doing the corresponding validation before applying the
  settings, and/or manage failures when setting an invalid BIOS config.
  Implementation of this method needs to rollback previous settings upon
  first failure. In the case of needing password to update the BIOS config,
  it will be taken from the ``driver_info`` properties. The implementation
  detail is up to the driver.

- ``apply_configuration(configuration={})`` - This cleaning step will
  delegate the actual configuration work into the abstract method
  ``do_apply_configuration(configuration={})``.

  The operator can choose to call it as part of manual cleaning steps. The
  corresponding manual cleaning step will be ``bios.apply_configuration``.

- ``cache_bios_settings()`` - This method will be called to update BIOS
  configuration in ``bios_settings`` database table. It will attempt to
  get the current BIOS settings and store them in the ``bios_settings``
  database table. It will also update the timestamp fields of 'created_at'
  and 'updated_at' accordingly. The implementation detail is up to the
  driver, for example, whether to have a sub method shared by
  ``do_factory_reset``, ``do_apply_configuration`` and
  ``cache_bios_settings`` to retrieve and save bios information in
  ``bios_settings`` table.


Nova driver impact
------------------

None

Ramdisk impact
--------------

None

Security impact
---------------

Unprivileged access to the BIOS configuration can expose sensitive BIOS
information and configurable BIOS options to attackers, which may lead to
disruptive consequence. It's recommended that this kind of ability is only
restricted to administrative roles. Changing BIOS settings requires
credentials which will reuse the existing credentials in ``driver_info``
instead of creating new fields.

Other end user impact
---------------------

None

Scalability impact
------------------

None

Performance Impact
------------------

BIOS configuration may extend the time required for manual cleaning on the
nodes.

Other deployer impact
---------------------

* Add new config options:

  - ``enabled_bios_interfaces``: a list of enabled bios interfaces.
  - ``default_bios_interface``: default bios interface to be used.

* Operator can use ``bios.apply_configuration`` and ``bios.factory_reset``
  as manual cleaning tasks for doing BIOS management.

Developer impact
----------------

Developer may implement the ``BIOSInterface`` for respective drivers.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  zshi
  yroblamo

Work Items
----------

* Add bios interface field in Node object.
* Create database model & api for nodes bios table and operations.
* Create ``BIOSInterface`` which includes the following items:

  + Add new methods in ``BIOSInterface`` base driver, such as
    ``do_apply_configuration``, ``do_factory_reset`` and
    ``cache_bios_settings``.
  + Add new cleaning steps in ``BIOSInterface`` base driver, such as
    ``apply_configuration``, ``factory_reset``.
  + Add caching of BIOS config as part of entering cleaning step in
    ``_do_node_clean``.

* Create 'fake' & 'no-bios' implementation derived from ``BIOSInterface``.
* Create REST API endpoints for BIOS configuration.
* Create RPC objects for BIOS configuration.
* Implement OSC baremetal CLI changes.

Dependencies
============

None

Testing
=======

* Unit tests will be added for the code. A fake implementation of the
  ``BIOSInterface`` will be provided with ``do_apply_configuration``
  method for testing purposes and this can be run as part of manual
  cleaning.

* Each driver is responsible for providing the third party CI for testing the
  BIOS configuration.

* Tempest tests will be added using fake driver.

Upgrades and Backwards Compatibility
====================================

* Raise errors when there is no BIOSInterface support in driver.

Documentation Impact
====================

* Documentation will be provided on how to configure a node for BIOS.
* API reference will be updated.
* Respective vendors should document the default BIOS values for reference.

References
==========

.. [0] Manual cleaning - https://github.com/openstack/ironic-specs/blob/master/specs/approved/manual-cleaning.rst
.. [1] SRIOV BIOS settings - https://docs.openstack.org/neutron/latest/admin/config-sriov.html#create-virtual-functions-compute
.. [2] DPDK BIOS settings - http://dpdk.org/doc/guides/linux_gsg/sys_reqs.html
.. [3] RAID configuration - https://github.com/openstack/ironic-specs/blob/master/specs/approved/ironic-generic-raid-interface.rst
