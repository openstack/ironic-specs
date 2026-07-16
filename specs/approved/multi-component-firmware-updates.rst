..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

========================================
Multi-Component Batched Firmware Updates
========================================

https://bugs.launchpad.net/ironic/+bug/2153965

Reduce downtime related to applying firmware updates by improving
``RedfishFirmware`` ("firmware updates 2.0"): batch non-BMC components
into one host reboot, process BMC updates in a separate phase before
other components, and extend component support where Redfish
``SimpleUpdate`` allows.  This also simplifies the per-component
reboot logic in the driver.


Problem description
===================

``RedfishFirmware`` today runs each requested component through its own
reboot and sequencing path.  That hurts **performance** (multiple host
reboots for a BIOS+NIC bundle; worse as more components are added) and
**complexity** (per-component conditionals for BMC, BIOS, and NIC paths
that are hard to reason about and extend).

BMC firmware cannot safely share a reboot batch with other components on
certain platforms (for example Dell R640/XR8620t or HP DL380/DL110).
Non-BMC ``SimpleUpdate`` requests can often be staged (submitted via
``SimpleUpdate`` with ``@Redfish.SettingsApplyTime: OnReset``) and
applied together after one reboot, with platform-specific submission
pacing (Dell vs HPE).

Redfish ``SimpleUpdate`` is largely image-driven; components beyond
``bmc``, ``bios``, and ``nic:<Id>`` may be added incrementally once JSON
Schema validation and ``cache_firmware_components()`` support them.


Proposed change
===============

The aim is to support a scenario where an operator can request firmware
updates on multiple components in a time-optimised manner (minimal host
reboots and BMC disruption).  To achieve this, when single-reboot flow
is requested, components must be listed in an order that is optimal for
the hardware—typically ``bmc`` first, followed by ``bios`` and other
non-BMC components.  **Ironic will not reorder** the ``settings`` list;
the operator (or upstream tooling) is responsible for supplying
components in the correct sequence.
Ironic will **not reject** a sub-optimal ordering (e.g. BMC listed
after BIOS); however, the single-reboot efficiency may be lost—the
Redfish firmware interface will fall back to per-step reboots where
necessary to preserve correctness, and the operation may fail on
platforms that require strict ordering.

To enable batching multiple firmware updates into a single reboot, a
new boolean ``allow_grouping_reboots`` argument is added to the
``firmware.update`` step ``args``.  It defaults to ``False``, preserving
the current per-component reboot behaviour.  When set to ``True``, the
Redfish firmware interface consolidates all non-BMC reboots into one at
the end of the step.

Keep the existing ``firmware.update`` step API
(``[{"component": ..., "url": ...}, ...]``).  Change orchestration
(when ``allow_grouping_reboots=True``):

1. **BMC phase** — when ``bmc`` appears before non-BMC entries, process
   it and wait for BMC recovery before continuing.
2. **Non-BMC batch** — submit ``SimpleUpdate`` per component (``bios``,
   ``nic:<Id>``); track Redfish tasks/jobs (parallel submit or
   sequential, per platform).
3. **One host reboot** — apply all staged non-BMC firmware updates.
4. **Validate** — refresh firmware component cache; confirm versions
   match expected values after reboot.

**Error handling:** if any staging step fails (e.g. BIOS firmware is
staged successfully but a subsequent NIC firmware ``SimpleUpdate``
submission fails), the entire servicing operation is considered failed
and the node transitions to ``servicing failed``.  No consolidated
reboot is issued in this case.  In the event of a partial failure, the
operator should check ``last_error`` and node history for the cause,
inspect the BMC for any remaining pending Redfish Tasks/Jobs (deleting
them if necessary), and abort servicing.  The failed operations may
then be re-attempted once the underlying cause is addressed.

**Component rules:** validation stays strict (today: ``bmc``, ``bios``,
``nic:.*`` [3]_).  Adding new component identifiers is out of scope for
this spec and may be revisited separately.

**Prerequisites:** On certain platforms, NIC updates require
``NetworkAdapters`` visibility, which means an OS must be running (IPA
ramdisk or the deployed instance OS) [2]_.  For day-0 flows this may be
satisfied by fast-track after inspection; for day-2/servicing flows, NIC
updates may have to complete while the instance OS is still up, before
the consolidated host reboot that applies the batched non-BMC updates.

Hypothetical CLI example (firmware updates, one non-BMC reboot)::

  openstack baremetal node service \
    --service-steps '[
      {"interface": "firmware", "step": "update", "args": {
        "settings": [
          {"component": "bmc", "url": "https://example.com/bmc.bin"},
          {"component": "bios", "url": "https://example.com/bios.exe"},
          {"component": "nic:NIC.Integrated.1-1-1",
           "url": "https://example.com/nic.zip"}
        ],
        "allow_grouping_reboots": true
      }}
    ]' mynode

With ``allow_grouping_reboots=true``, the Redfish firmware interface
stages all non-BMC firmware updates, then issues a single consolidated
reboot after the batch completes.


**Out of scope:** in-band delivery.


Alternatives
------------

* Per-component reboot logic — rejected (poor performance, growing
  complexity).
* BMC in the same batch as non-BMC — rejected (known failures).
* Automatic reordering of ``settings`` — rejected; operator supplies
  hardware-optimal component order.
* Unvalidated open-ended component names — rejected (Ironic validates
  today; extending component vocabulary is out of scope for this spec).


Data model impact
-----------------

None


State Machine Impact
--------------------

None


REST API impact
---------------

None.  The ``allow_grouping_reboots`` boolean lives inside the
``firmware.update`` step ``args``; no new top-level API parameter is
required.


Client (CLI) impact
-------------------

"openstack baremetal" CLI
~~~~~~~~~~~~~~~~~~~~~~~~~

None.  Operators pass ``allow_grouping_reboots`` inside step ``args``.

"openstacksdk"
~~~~~~~~~~~~~~

None.


RPC API impact
--------------

None.  ``allow_grouping_reboots`` is handled inside the Redfish
firmware interface; the RPC layer does not need changes.


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

Fewer host reboots (primary win).  Step may hold the node lock longer;
bound task polling.


Other deployer impact
---------------------

None


Developer impact
----------------

Other ``FirmwareInterface`` implementations unaffected; Redfish is the
reference.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  janders

Other contributors:
  iurygregory
  dtantsur
  cardoe

Work Items
----------

1. ``allow_grouping_reboots`` step argument handling in the Redfish
   firmware interface.
2. BMC / non-BMC phasing in ``RedfishFirmware.update()``.
3. Task tracking and platform-specific submission pacing.
4. Single non-BMC reboot and post-reboot validation.
5. Documentation: trade-offs, correct update sequence, error recovery.
6. Unit tests.
7. Documentation, including recommended sequence of updates and
   trade-offs introduced if the operator opts in for the single-reboot
   flow.
8. Third-party CI.


Dependencies
============

* ``FirmwareInterface`` [0]_, NIC updates [2]_,
  2026.2 firmware priorities [1]_.


Testing
=======

Unit tests with fake Redfish responses covering BMC/non-BMC phasing,
reboot consolidation, and post-update validation.  Regression tests
for single-component updates.

Integration tests on real hardware via third-party CI.  Improving
sushy-tools firmware update emulation (to better simulate staging, task
tracking, and reboot behaviour).


Upgrades and Backwards Compatibility
====================================

Backwards compatible.  Existing ``bmc``/``bios``/``nic:<Id>`` steps are
unchanged.  Operators may perform
multi-component updates in one reboot cycle or continue updating each
component separately.


Documentation Impact
====================

Update firmware management guide: phasing, prerequisites, examples,
supported components matrix.


References
==========

.. [0] ``specs/approved/firmware-interface.rst``
.. [1] ``priorities/2026-2-workitems.rst``
.. [2] ``specs/approved/nic-firmware-updates.rst``
.. [3] ``ironic/drivers/modules/redfish/firmware_utils.py``
.. [4] https://etherpad.opendev.org/p/ironic-firmware-updates-v2
