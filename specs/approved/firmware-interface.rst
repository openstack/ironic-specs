..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==================
Firmware interface
==================

https://storyboard.openstack.org/#!/story/2010659

This spec proposes to implement a new hardware interface for automated
firmware updates.


Problem description
===================

Some operators would like to make sure that their hardware is using
specific versions of firmware on different hardware components (e.g. BIOS,
NICs, BMC, etc), main reason being they like their machines in cluster to be
homogeneous.
When they get a new machine they need to update all components
firmware by doing upgrade or downgrade.

Currently in Ironic we have support to update the firmware, the operator can
achieve this by invoking manual cleaning on the node by enabling the clean
step ``update_firmware``; the problem is that it requires knowledge about the
clean step name and parameters.

* As an operator I want to install specific versions of firmware in my
  machines (BIOS, NICs, DPUs, GPUs, BMC) before installing the Operating
  System.


Proposed change
===============

* After a node is enrolled and the basic hardware information is available,
  an operator can define a Firmware Update config.

* The work to be done here is similar to what we did for ``BIOSInterface``
  and ``RAIDInterface``. A new interface ``FirmwareInterface`` will be created
  that allows retrieving current installed firmware version of the hardware
  components in a node and also update their firmware.

* The information about the current firmware version of each hardware
  component on the node will be collected out-of-band and should be available
  after we enroll the node via verify step.

* A new clean step ``update`` will be created for the ``FirmwareInterface``, it
  will be used to update the firmware of each hardware component on the node.

* A new database table ``firmware_information`` will be created if it doesn't
  exist. It will contain the information about the current firmware version of
  each hardware component on a node, the information is updated in case the
  clean step ``update`` is called.

* We intend this to start only on the redfish interface, all others will
  default to ``no-firmware``. If other hardware vendors wish to implement it,
  they are welcome to.

.. note:: This spec describes the out of band interface. An in-band
          interface is planned to be implemented later, it can be called
          ``AgentFirmware``, changes on IPA-level APIs will have to be defined.
          Other implementations can support going through this interface to
          execute the necessary in-band steps.


Alternatives
------------

We can use the current ``update_firmware`` clean step via manual cleaning [0]_,
but the downside is that we don't know which hardware components are
upgradable and what their present firmware versions are on the node.

Data model impact
-----------------

* New object ``ironic.objects.firmware.Firmware`` will be created.

* A new field ``firmware_interface`` will be added to the ``Node`` object.

* A new table ``firmware_information`` will be created, it will store
  the firmware information of each hardware component of a Node.

  * Table description:

    + node_id

      - Integer
      - PrimaryKeyConstraint('nodes.id')

    + component

      - String
      - PrimaryKeyConstraint

    + initial_version - stored when we create the entry

      - String

    + current_version

      - String

    + last_version_flashed

      - String

    + created_at

      - DateTime

    + updated_at - when the component was last flashed

      - DateTime


State Machine Impact
--------------------

None

REST API impact
---------------

A new step is proposed to be implemented on the ``FirmwareInterface``:

* ``firmware.update``: it will trigger the firmware update for each component
  that is specified. For example::

    {
      "target":"clean",
      "clean_steps": [{
        "interface": "firmware",
        "step": "update",
        "requires_ramdisk": true,
        "args": {
          "settings": [
            {
              "component": <name>,
              "url": <value>
            },
            {
              "component": <name>,
              "url": <value>
            }
          ]
        }
      }]
    }


* A new REST API will be introduced to get the cached Firmware information
  for a node::

    GET /v1/nodes/<node_ident>/firmware

  The operation will return the currently cached settings with the following
  data schema:

.. code-block:: json

    [
      {
        "component":"bios",
        "initial_version": "v1.0.0.0 (01.02.2022)",
        "current_version": "v1.2.3.4 (01.02.2023)",
        "last_version_flashed": "v1.2.3.4 (01.02.2023)",
        "created_at": "2023-02-01 09:00:00",
        "updated_at": "2023-03-01 10:00:00"
      },
      {
        "component": "bmc",
        "initial_version": "v1.0.0",
        "current_version": "v1.0.0",
        "last_version_flashed": "",
        "created_at": 2023-02-01 09:00:00",
        "updated_at": ""
      }
    ]



Client (CLI) impact
-------------------

openstackSDK will be updated

* Retrieve all firmware information about the node:

.. code-block:: console

   $ openstack baremetal node firmware list <node-uuid>
   +----+-----------+-----------------------+-----------------------+-----------------------+----------------------------+----------------------------+
   | ID | Component | Initial Version       | Current Version       | Last Version Flashed  | created_at                 | Updated At                 |
   +----+-----------+-----------------------+-----------------------+-----------------------+----------------------------+----------------------------+
   |  1 | bios      | v1.0.0.0 (01.02.2022) | v1.2.3.4 (01.02.2023) | v1.2.3.4 (01.02.2023) | 2023-02-01T09:00:00.000000 | 2023-03-01T10:00:00.000000 |
   +----+-----------+-----------------------+-----------------------+-----------------------+----------------------------+----------------------------+
   |  2 | bmc       | v1.0.0                | v1.0.0                |                       | 2023-02-01T09:00:00.000000 |                            |
   +----+-----------+-----------------------+-----------------------+-----------------------+----------------------------+----------------------------+


RPC API impact
--------------

* None - we already have ``do_node_clean``

Driver API impact
-----------------

A new interface ``FirmwareInterface`` will be available for drivers
to allow them to implement the firmware update. The following methods will
be available:

* ``update(settings)`` - This is the step responsible to update the
  firmware of the components in the node. The ``settings`` parameter is a list
  of dictionaries

.. code-block:: json

  [{"component": "bmc", "url":"<url_new_bmc_fw>"},
   {"component": "bios", "url":"<url_new_bios_fw>"}]


* ``cache_firmware_information()`` - this method will be called to update the
  firmware information in the ``firmware_information`` database table. It will
  store the Firmware information for a node, or update the information in case
  the ``update`` step was called.


Nova driver impact
------------------

* None

Ramdisk impact
--------------

* Currently there is no impact for ramdisk, because we will be focusing on OOB
  upgrades, the current interface will be created so it can handle in-band
  upgrades.

Security impact
---------------

* None

Other end user impact
---------------------

* None

Scalability impact
------------------

* None

Performance Impact
------------------

* The firmware update may extend the time required for manual cleaning on the
  nodes.

Other deployer impact
---------------------

* New config options in ``ironic.conf``

  - ``enabled_firmware_interfaces``: a list of enabled firmware interfaces.
  - ``default_firmware_interface``: default firmware interface to be used.

* Operators can use the new steps as part of manual cleaning tasks.


Developer impact
----------------

* Developers may implement the ``FirmwareInterface`` for respective drivers.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
*  <iurygregory, imelofer@redhat.com or iurygregory@gmail.com>

Other contributors:
*  <dtantsur, dtantsur@protonmail.com>
*  <janders, janders@redhat.com>

Work Items
----------

* Add the firmware_interface field in the Node object
* Create the Firmware object
* Create the ``FirmwareInterface`` structure. Includes the redfish
  implementation
* Implement ``no-firmware`` and ``fake`` for the ``FirmwareInterface``
* Create REST API
* Implement OSC baremetal CLI changes


Dependencies
============

* This feature is targeting only hardware that supports Redfish.


Testing
=======

* Unit tests will be added for the code.
* Tempest tests will be added using fake driver.

Upgrades and Backwards Compatibility
====================================

* Raise errors when there is no ``FirmwareInterface`` support in driver.

Documentation Impact
====================

* New Documentation will be provided on how to use.


References
==========

.. [0] Cleaning Steps - https://docs.openstack.org/ironic/latest/admin/cleaning.html
