..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=====================================
Firmware endpoint hardware identity
=====================================

https://bugs.launchpad.net/ironic/+bug/2149880

Ironic stores per-component firmware versions from Redfish.  The
``GET /v1/nodes/{ident}/firmware`` endpoint exposes only version-tracking
fields with no hardware identity — vendor, model, or serial number.  The
``GET /v1/nodes/{ident}/inventory`` endpoint exposes NIC inventory including
vendor and product identifiers but no firmware versions.  This spec extends
the firmware endpoint with vendor, model, and serial number to allow
correlation between firmware and inventory records.


Problem description
===================

An operator cannot answer ``what firmware version has the Intel E810 NIC`` of a
server.  This happens because: an operator can query the inventory endpoint to
get the NIC vendor as a PCI identifier:

.. code-block:: console

 GET /v1/nodes/{ident}/inventory

.. code-block:: json

  {
    "inventory": {
      "interfaces": [
        {
          "name": "eth0",
          "mac_address": "52:54:00:5e:09:ff",
          "ipv4_address": "192.168.1.10",
          "has_carrier": true,
          "vendor": "0x8086",
          "product": "0x1572",
          "biosdevname": null,
          "speed_mbps": 25000
        }
      ]
    }
  }

Then query the firmware endpoint to get the version

.. code-block:: console

 GET /v1/nodes/{ident}/firmware

.. code-block:: json

    {
      "firmware": [
        {
          "component": "NIC:ABC12345",
          "initial_version": "22.0.9",
          "current_version": "22.5.0",
          "last_version_flashed": "22.5.0",
          "created_at": "2024-01-01T00:00:00+00:00",
          "updated_at": "2024-06-01T00:00:00+00:00"
        }
      ]
    }


But there is no common field to associate an entry in the inventory to an entry
in the firmware components.

As a solution we leverage the fact that the Redfish ``NetworkAdapter``
resource (DMTF schema ``NetworkAdapter.v1_3_0``) that Ironic already
queries for firmware version carries hardware identity fields:

* ``Manufacturer`` – e.g. ``"Intel Corporation"`` (exposed as ``vendor``
  in the Ironic API)
* ``Model`` – e.g. ``"Intel(R) 25GbE 2P XXV710 Adptr"``
* ``SerialNumber`` – e.g. ``"ABC12345"`` (already used to build the
  component identifier, but not returned as a structured field)

These fields are already fetched at the time ``cache_firmware_components``
runs — no new Redfish calls are required.  They are simply never stored
or returned.

The operator can heuristically correlate the human-readable identity from
the firmware endpoint to the PCI identifiers in the inventory. Redfish
returns ``Manufacturer`` and ``Model`` as vendor-chosen strings; the
inventory exposes ``vendor`` and ``product`` as raw PCI IDs. The mapping
is approximate: ``vendor: "Intel Corporation"`` corresponds to
``vendor: "0x8086"`` via PCI ID resolution, and ``model: "Intel(R)
E810-CQDA2"`` approximates the device string for ``product: "0x1592"``.
This is the best correlation possible given the data each subsystem
exposes.


Proposed change
===============

Three nullable string fields — ``vendor``, ``model``,
``serial_number`` — are added to the firmware component response.

1. **NIC**: one ``NetworkAdapter`` resource per physical card, iterated
   from ``Systems/{id}/NetworkAdapters/``.  The component identifier
   ``"NIC:{serial}"`` is built from ``NetworkAdapter.SerialNumber``; the
   identity fields are sourced from the same resource with no additional
   Redfish traversal.

   +-------------------+--------------------------------+
   | API field         | Redfish property               |
   +===================+================================+
   | ``vendor``        | ``NetworkAdapter.Manufacturer``|
   +-------------------+--------------------------------+
   | ``model``         | ``NetworkAdapter.Model``       |
   +-------------------+--------------------------------+
   | ``serial_number`` | ``NetworkAdapter.SerialNumber``|
   +-------------------+--------------------------------+

   All fields are optional in the Redfish schema.  Example values:
   ``vendor`` = ``"Intel Corporation"``,
   ``model`` = ``"Intel(R) 25GbE 2P XXV710 Adptr"``,
   ``serial_number`` = ``"ABC12345"``.

2. **BMC**: one ``Manager`` resource per node.

   +-------------------+--------------------------------+
   | API field         | Redfish property               |
   +===================+================================+
   | ``vendor``        | (not available)                |
   +-------------------+--------------------------------+
   | ``model``         | ``Manager.Model``              |
   +-------------------+--------------------------------+
   | ``serial_number`` | (not available)                |
   +-------------------+--------------------------------+

   ``Manager.Model`` (e.g. ``"iDRAC 9"``, ``"iLO 5"``) populates
   ``model``.  ``Manager`` has no ``Manufacturer`` or ``SerialNumber``
   property, so ``vendor`` and ``serial_number`` are ``null``.

3. **BIOS**: all fields ``null``.

   +-------------------+--------------------------------+
   | API field         | Redfish property               |
   +===================+================================+
   | ``vendor``        | (not available)                |
   +-------------------+--------------------------------+
   | ``model``         | (not available)                |
   +-------------------+--------------------------------+
   | ``serial_number`` | (not available)                |
   +-------------------+--------------------------------+

   ``ComputerSystem`` carries ``Manufacturer``, ``Model``, and
   ``SerialNumber`` but these describe the server chassis, not the
   BIOS component; Redfish does not expose BIOS-chip-specific identity.

.. note::
   Items 2 and 3 are documented here because BMC and BIOS share the
   same ``firmware_information`` DB schema as NICs.  The fields exist
   on every row; ``null`` is the honest value when Redfish provides no
   component-specific identity.


Alternatives
------------

**Live Redfish fetch at request time** rather than caching in the
database adds per-request BMC calls to a read path that currently
requires no out-of-band contact, increasing latency and BMC load.

**A separate sub-endpoint** (e.g.
``GET /v1/nodes/{ident}/firmware/{component}/identity``) adds complexity
without benefit since the data is colocated with the firmware record and
is small.


Data model impact
-----------------

Three nullable ``VARCHAR(255)`` columns are added to the
``firmware_information`` table: ``vendor``, ``model``,
``serial_number``.  A single Alembic migration adds all three.
Existing rows are unaffected (columns default to ``NULL``).  No
back-fill is performed; new values are populated on the next inspection
or cleaning pass.  The table is bounded by the number of firmware
components per node (typically fewer than 20), so the additional columns
have negligible storage and query impact.


State Machine Impact
--------------------

None.


REST API impact
---------------

One existing endpoint is modified.

``GET /v1/nodes/{node_ident}/firmware``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Method: GET
* Normal response: 200
* Error responses:

  * 404 if the node does not exist.
  * 403 if the caller lacks ``baremetal:node:firmware:get`` policy.
  * 406 if any of ``vendor``, ``model``, ``serial_number`` appears in
    the ``?fields=`` query parameter and is not supported by the server
    version.

Response body (with new fields):

.. code-block:: json

    {
      "firmware": [
        {
          "component": "BMC",
          "initial_version": "2.10.0",
          "current_version": "2.10.0",
          "last_version_flashed": null,
          "model": "iDRAC 9",
          "vendor": null,
          "serial_number": null,
          "created_at": "2024-01-01T00:00:00+00:00",
          "updated_at": null
        },
        {
          "component": "BIOS",
          "initial_version": "3.5.0",
          "current_version": "3.5.0",
          "last_version_flashed": null,
          "model": null,
          "vendor": null,
          "serial_number": null,
          "created_at": "2024-01-01T00:00:00+00:00",
          "updated_at": null
        },
        {
          "component": "NIC:ABC12345",
          "initial_version": "22.0.9",
          "current_version": "22.5.0",
          "last_version_flashed": "22.5.0",
          "model": "Intel(R) 25GbE 2P XXV710 Adptr",
          "vendor": "Intel Corporation",
          "serial_number": "ABC12345",
          "created_at": "2024-01-01T00:00:00+00:00",
          "updated_at": "2024-06-01T00:00:00+00:00"
        }
      ]
    }

Response body (prior to this change): unchanged — the three new fields
are absent.  No policy changes.  No new endpoints.


Client (CLI) impact
-------------------

``python-ironicclient`` will be updated. The ``baremetal node firmware
list`` command will display the new ``Vendor``, ``Model``, and
``Serial Number`` fields in its tabular output. The fields are only
queried and displayed when the command targets a server that supports
the new API microversion.


RPC API impact
--------------

None.


Driver API impact
-----------------

None.


Nova driver impact
------------------

None.


Ramdisk impact
--------------

None.


Security impact
---------------

None.


Other end user impact
---------------------

Baremetal operators consuming Ironic through higher-level clients such
as gophercloud should adapt their clients to make use of the new
fields.


Scalability impact
------------------

None beyond what is noted in the Data model impact section.


Performance Impact
------------------

None.


Other deployer impact
---------------------

None.


Developer impact
----------------

None beyond the standard versioned-object conventions.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  karampok

Other contributors:
  None

Work Items
----------

1. **Database**: Alembic migration adding nullable ``VARCHAR(255)``
   columns ``vendor``, ``model``, ``serial_number`` to the
   ``firmware_information`` table.
2. **Object**: Add the three fields to the ``FirmwareComponent``
   versioned object; implement ``obj_make_compatible`` to strip them
   when communicating with conductors pinned below the new version.
3. **Driver**: Update ``cache_firmware_components`` in the Redfish
   hardware type to populate the new fields from ``NetworkAdapter``
   (NICs) and ``Manager`` (BMC).
4. **API**: Define a new microversion; update the
   ``GET /v1/nodes/{node_ident}/firmware`` controller to return the
   new fields for requests at or above that version.


Dependencies
============

None.


Testing
=======

* Unit tests will be added conforming to Ironic testing requirements.
* CI coverage may be extended by adding the new identity fields to the
  sushy-tools virtual Redfish resources used in the gate.


Upgrades and Backwards Compatibility
=====================================

**REST API**: clients that do not declare the new API version receive
the unchanged response.  Requesting any new field explicitly on an
older server returns ``406 Not Acceptable``.

**Database**: new columns are nullable (default ``NULL``).  The
migration completes without touching existing rows.  New values are
populated only when ``cache_firmware_components`` next runs (inspection
or cleaning).  No back-fill is performed.

**Rolling upgrades**: ``FirmwareComponent.obj_make_compatible`` strips
``vendor``, ``model``, and ``serial_number`` from primitives sent to
conductors pinned below the new object version.  No data is lost.

No operator action is required.


Documentation Impact
====================

``doc/source/contributor/webapi-version-history.rst``,
``api-ref/source/baremetal-api-v1-nodes-firmware.inc``, and the API ref
sample JSON require updates for the new microversion and fields.


References
==========

* Original firmware interface specification:
  https://specs.openstack.org/openstack/ironic-specs/specs/approved/firmware-interface.html

* Redfish NetworkAdapter schema (DMTF):
  https://redfish.dmtf.org/schemas/v1/NetworkAdapter.v1_3_0.json

* Redfish Manager schema (DMTF):
  https://redfish.dmtf.org/schemas/v1/Manager.v1_0_0.json

* Redfish ComputerSystem schema (DMTF):
  https://redfish.dmtf.org/schemas/v1/ComputerSystem.v1_0_0.json

* Related spec — NIC firmware updates:
  https://review.opendev.org/c/openstack/ironic-specs/+/948503
