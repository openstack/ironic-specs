..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===================================================
Provide Redfish BIOS Attribute Registry data in API
===================================================

https://storyboard.openstack.org/#!/story/2008571

This proposal is to retrieve the Redfish BIOS Attribute Registry when using
the Redfish driver and provide it as additional data in the bios API endpoint.

Problem description
===================

The Redfish BIOS Attribute Registry (aka BIOS Registry) is defined in the DMTF
Redfish specification [0]_ as a way to describe the semantics of each property
in a BIOS settings resource. This JSON encoded registry contains descriptions
of each property and other information, such as data type, allowable values,
and whether the attribute is read-only.

When a user attempts to set a BIOS attribute through clean steps [1]_ it is not
obvious which name should be used for the attribute, what its allowable values
are, or even if the attribute is writeable. It is useful to expose the
BIOS Registry through an API so that it can be used as a form of documentation
when setting BIOS attributes.

An example of an entry in BIOS Registry returned from a BMC for an attribute::

     {
        "AttributeName": "SriovGlobalEnable",
        "CurrentValue": null,
        "DisplayName": "SR-IOV Global Enable",
        "DisplayOrder": 2331,
        "HelpText": "Enables or disables the BIOS configuration of Single Root
                     I/O Virtualization (SR-IOV) devices. Enable this feature
                     if booting to a virtualization operating system that
                     recognize SR-IOV devices. ",
        "Hidden": false,
        "Immutable": false,
        "MenuPath": "./IntegratedDevicesRef",
        "ReadOnly": false,
        "ResetRequired": true,
        "Type": "Enumeration",
        "Value": [
          {
            "ValueDisplayName": "Enabled",
            "ValueName": "Enabled"
          },
          {
            "ValueDisplayName": "Disabled",
            "ValueName": "Disabled"
          }
        ],
        "WarningText": null,
        "WriteOnly": false
      }

This change was discussed at the Wallaby mid-cycle, see notes [2]_.

Proposed change
===============

The effort will encompass the following changes:

* Support for getting the BIOS Registry in Sushy. Retrieving the BIOS
  Registry requires multiple Redfish requests as the base URI -
  ``/redfish/v1/Registries``, provides the BIOS Registry URI with a vendor
  specific name. The registry will be a list of dictionary entries, one for
  each BIOS attribute.

* Changes to Ironic to retrieve the Redfish BIOS Registry for a node when
  it gets the BIOS settings; currently this is when Ironic moves the node to
  ``manageable`` or ``cleaning`` and after changing the BIOS settings.

* Filtering of the BIOS registry received from Sushy to only save the entries
  that match the BIOS settings received from Sushy, based on the
  ``AttributeName`` field in the BIOS Registry entries.

* Storing the registry data in the Ironic DB associated with each BIOS setting.

* Exposing the BIOS Registry data via the REST API. No new endpoints will
  be added. The registry data will be included in the
  ``/v1/nodes/<node>/bios`` endpoint only if ``?detail=True`` is set. The
  registry data will always be included in ``/v1/nodes/<node>/bios/<setting>``.
  This is similar to how the API for nodes currently works e.g. ``/v1/nodes``,
  ``/v1/nodes?detail=True``, and ``/v1/nodes/<node>``

Alternatives
------------

* An operator can continue to set the BIOS settings in clean steps perhaps
  by using vendor documentation or only making simple changes to Boolean
  values.

* Instead of retrieving the registry and caching it, Ironic could do a
  synchronous get from the API. However, this may lead to performance problems
  especially when handling multiple API requests.

Data model impact
-----------------

* There is a schema defined for the BIOS Registry, for example [3]_, however
  it is vendor dependent as to which attribute fields are stored in the
  registry. Sushy should parse the following common fields which are present
  in the registry of typical vendors, for example Dell, HPE, and SuperMicro::

    * AttributeName
    * DefaultValue
    * Type
    * Immutable
    * ReadOnly
    * ResetRequired
    * IsSystemUniqueProperty
    * LowerBound
    * UpperBound
    * MinLength
    * MaxLength
    * Value (possible values for enumeration types)
      * ValueName

* The BIOS Registry will be stored in the Ironic DB along with the BIOSSetting,
  see [4]_. The following columns will be added and must be included in the
  migration code:

    * ``attribute_type`` (string)
    * ``allowable_values`` (list)
    * ``lower_bound`` (integer)
    * ``max_length`` (integer)
    * ``min_length`` (integer)
    * ``read_only`` (boolean)
    * ``reset_required`` (boolean)
    * ``unique`` (boolean)
    * ``upper_bound`` (integer)

For each setting only the relevant fields for ``attribute_type`` will be stored
as returned from the BMC. For example, for an Enumeration type only
``allowable_values`` will be stored and for an Integer only ``min_length`` and
``max_length``.

In addition, the BIOSSetting ``name`` field should be indexed for faster
retrieval.

State Machine Impact
--------------------

The BIOS Registry will be retrieved from the BMC upon transition to
``manageable`` and ``cleaning`` states using multiple Redfish requests. This
may add some additional time to the state transition but it is not
foreseen that this will have an impact on the state transition performance.

REST API impact
---------------

* No new REST API endpoints will be added. The
  ``/v1/nodes/<node>/bios/<attribute>`` endpoint will be changed to include
  the new registry fields. The ``/v1/nodes/<node>/bios`` endpoint
  will only include this data per attribute if ``?detail=True`` is set,
  similar to how the ``/v1/nodes/`` endpoint works. The query can also be
  used to retrieve only particular fields.

* If BIOS Registry could not be retrieved from the node then the registry
  fields will be set to ``null``.

* For allowable_values, some vendors include both ValueName and
  ValueDisplayName in the response. The API will just show a list of the
  allowable values.

* An example response for ``/v1/nodes/<node>/bios/ProcVirtualization``, an
  enumeration type, with the new registry fields is as follows::

    { "ProcVirtualization":
        { "created_at": "2021-03-31T13:50:51+00:00",
          "updated_at": null,
          "name": "ProcVirtualization",
          "value": "Enabled",
          "allowable_values": ["Enabled","Disabled"]
          "lower_bound": null,
          "max_length": null,
          "min_length": null,
          "read_only": false,
          "reset_required": null,
          "type": "Enumeration",
          "unique": null,
          "upper_bound": null,
          "links": [
          {
            "href": "http://IP/v1/nodes/1b1c6edf-4459-4172-b069-5c6ca3e59e03/bios/ProcVirtualization",
            "rel": "self"
          },
          {
            "href": "http://IP/nodes/1b1c6edf-4459-4172-b069-5c6ca3e59e03/bios/ProcVirtualization",
            "rel": "bookmark"
          }
        ]
      }
    }

* An example response for ``/v1/nodes/<node>/bios/SerialNumber``, a
  String type unique to this node, is as follows::

    { "SerialNumber":
        { "created_at": "2021-03-31T13:50:51+00:00",
          "updated_at": null,
          "name": "SerialNumber",
          "value": "Q95102Q8",
          "allowable_values": [],
          "lower_bound": null,
          "max_length": 16,
          "min_length": null,
          "read_only": false,
          "reset_required": null,
          "type": "String",
          "unique": true,
          "upper_bound": null,
          "links": [
          {
            "href": "http://IP/v1/nodes/1b1c6edf-4459-4172-b069-5c6ca3e59e03/bios/SerialNumber",
            "rel": "self"
          },
          {
            "href": "http://IP/nodes/1b1c6edf-4459-4172-b069-5c6ca3e59e03/bios/SerialNumber",
            "rel": "bookmark"
          }
        ]
      }
    }


Client (CLI) impact
-------------------

"baremetal" CLI
~~~~~~~~~~~~~~~~~~~~~~~~~

* The bios command ``baremetal node bios`` will change as follows.

  * This command will now include the registry data as an additional
    fields, for example::

      $ baremetal node bios setting show hp-910 ProcVirtualization -f json
      {
        "created_at": "2021-03-31T13:50:51+00:00",
        "name": "ProcVirtualization",
        "updated_at": null,
        "value": "Enabled"
        "allowable_values": ["Enabled","Disabled"]
        "lower_bound": null,
        "max_length": null,
        "min_length": null,
        "read_only": false,
        "reset_required": null,
        "type": "Enumeration",
        "unique": null,
        "upper_bound": null,
      }

* A new parameter ``--long`` will be added to the ``baremetal node bios list``
  command to include the registry data for each attribute. It will not be
  included by default. This is similar to ``baremetal node list <node> --long``
  command.

"openstacksdk"
~~~~~~~~~~~~~~

Openstacksdk does not currently have support for bios settings. Although not a
requirement for this specification. bios should be added to openstacksdk and
the detailed registry information should be included.

RPC API impact
--------------

A new method to get the BIOS registry will be added to the RPC API.

Driver API impact
-----------------

* The ``cache_bios_settings`` method in the Redfish driver will now also get
  the BIOS Registry from Sushy.

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
disruptive consequence. It's recommended that this kind of ability is
restricted to administrative roles.

Other end user impact
---------------------

None

Scalability impact
------------------

The Redfish requests to retrieve BIOS Registry data will increase the traffic
to the BMC however, since these requests will only be when the node
transitions to ``manageable`` or ``cleaning``, it should not impact
scalability.

The BIOS Registry data will be stored in the Ironic DB along with the BIOS
setting that it corresponds to. This will add to the size of the Ironic DB
but its not expected to be prohibitive as the BIOS settings list, although
it varies per vendor, is approximately 100 to 200 items.

Performance Impact
------------------

It is not expected that this change will introduce a performance impact
on the time it takes for nodes to transition to ``manageable`` or ``cleaning``.

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
  bfournie@redhat.com

Work Items
----------

* Add support for BIOS Registry to Sushy
* Add caching support for the registry to Ironic.
* Add retrieval of the registry in Ironic when transitioning the node
  to ``cleaning`` or ``manageable`` and store/update the cache.
* Add the API to get the BIOS Registry for the node.
* Add configuration items for ``bios_registory_lang`` and
  ``bios_registry_enable`` to ironic.conf.


Dependencies
============

None

Testing
=======

* Unit testing will be added with sample vendor data but it will necessary
  for 3rd party testing to be added to test each vendor's interface.

Upgrades and Backwards Compatibility
====================================

None

Documentation Impact
====================

* API reference will be updated.

References
==========

.. [0] DMTF Redfish Specification - http://redfish.dmtf.org/schemas/DSP0266_1.11.0.html
.. [1] BIOS configuration - https://github.com/openstack/ironic-specs/blob/master/specs/approved/generic-bios-config.rst
.. [2] Discussion at Wallaby mid-cycle - https://etherpad.opendev.org/p/ironic-wallaby-midcycle
.. [3] AttributeRegistry schema - https://redfish.dmtf.org/schemas/v1/AttributeRegistry.v1_3_4.json
.. [4] BIOSSetting in Ironic DB - https://opendev.org/openstack/ironic/src/branch/master/ironic/db/sqlalchemy/models.py#L326
