..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

======================================================
Out-of-Band Inspection as Clean, Service, Verify Steps
======================================================

https://bugs.launchpad.net/ironic/+bug/2138129

This spec exposes out-of-band (OOB) inspection through the existing step
frameworks, so operators can refresh hardware inventory as a clean step,
a service step, or a verify step — without moving the node through
``manageable`` and without any state machine or API microversion changes.

Problem description
===================

Ironic currently restricts node inspection to nodes in the ``manageable``
provisioning state.  This restriction is appropriate for in-band inspection
drivers such as ``agent``, which must boot the node into an IPA ramdisk to
collect hardware data; an operation that is disruptive while
a workload is running.

Out of Band (OOB) inspection drivers communicate exclusively with the node's
BMC (e.g. via Redfish).  They never touch the host OS and
impose no downtime on the running workload.  Forcing operators to cycle an
``active`` or ``available`` node through ``manageable`` just to refresh
hardware inventory is unnecessary and operationally expensive:

* An ``active`` node must be undeployed and cleaned before it can be moved
  to ``manageable``, breaking the running workload.

* An ``available`` node must likewise be moved to ``manageable``, interrupting
  its readiness for scheduling by Nova.

* Operators repairing running hardware have no way to update inventory without
  full redeploy cycles.

Separately, the products of inspection, inspection hooks and inspection
rules, can only be exercised as a side effect of a full inspection.  When an
operator changes the configured hooks or adds a new inspection rule, there is
no way to re-process the already-stored inspection data; the only option is
another complete inspection pass.

Proposed change
===============

The ``inspect`` driver interface becomes a source of steps.  Three steps are
introduced, and the step frameworks are extended to harvest steps from the
inspect interface during cleaning and servicing (verifying already does).

Enabling the ``inspect`` interface in the step frameworks
---------------------------------------------------------

``'inspect'`` is added to ``CLEANING_INTERFACE_PRIORITY`` and given a
distinct priority in ``SERVICING_INTERFACE_PRIORITY`` in
``ironic/conductor/steps.py`` (``VERIFYING_INTERFACE_PRIORITY`` already
contains ``'inspect'``).  Because the API request schemas for manual
cleaning, servicing and runbooks all derive their allowed ``interface``
values from ``CLEANING_INTERFACE_PRIORITY``, this single change makes
``{"interface": "inspect", ...}`` acceptable everywhere steps are accepted,
including runbooks.  This follows the precedent set by the ``firmware``
interface, which was added the same way without an API microversion.

New steps
---------

Three steps are added.  All are synchronous, purely out-of-band
(``requires_ramdisk=False``) and default to priority ``0`` so that nothing
runs automatically unless an operator opts in.

``inspect``
~~~~~~~~~~~

A full out-of-band inspection: collect inventory from the BMC, run the
configured inspection hooks, apply inspection rules (``main`` phase), and
store the resulting inspection data.  This reuses the driver's existing
``inspect_hardware()`` collection logic.

Arguments:

* ``data_handling`` — how newly collected inspection data (inventory and
  plugin data) interacts with previously stored inspection data.  One of:

  - ``replace`` (default): the new data replaces the stored data.  This
    matches the behaviour of inspection today.
  - ``merge``: the new data is merged over the stored data.  Dictionaries
    are merged recursively; scalar values and lists from the new data
    replace their stored counterparts.  This supports workflows where a
    given pass only collects a subset of data (e.g. refreshing OOB-visible
    data while retaining detail that only a previous in-band inspection
    could collect).

* ``update_properties`` — boolean, default ``true``.  When ``false``, the
  step stores inspection data but does not modify scheduling-related
  ``node.properties`` (``memory_mb``, ``cpus``, ``local_gb``,
  ``capabilities``…).  This lets operators refresh inventory on ``active``
  nodes without perturbing resource-tracking data mid-lifecycle.

This step is exposed only by OOB-capable inspect interface implementations.
The step body is implemented once as a helper on the base
``InspectInterface``; ``RedfishInspect`` exposes it with the step decorators
(and ``idrac-redfish`` inherits it).  Other OOB implementations (``ilo``,
``irmc``) and out-of-tree drivers can opt in the same way in follow-up work.
In-band implementations such as ``agent`` do not advertise the step, so
there is no runtime state in which it can be selected but not executed.
If a driver's ``inspect_hardware()`` reports asynchronous operation
(``INSPECTWAIT``), the step fails cleanly; asynchronous/in-band inspection
steps are explicitly out of scope for this spec.

``run_hooks``
~~~~~~~~~~~~~

Re-run the inspection hooks configured for the node's inspect interface
against the *stored* inspection data, then store the processed result.  No
BMC or host access is performed.  This gives operators a way to apply a
changed hook configuration (e.g. enabling the ``ports`` or
``physical-network`` hook) to existing data without re-inspecting.

Arguments:

* ``hooks`` — optional comma-separated list of hook names overriding the
  interface's configured hook list for this invocation only.

This step is available on all inspect interfaces that support inspection
hooks (currently ``agent`` and ``redfish``-based interfaces).  It fails if
the node has no stored inspection data.

``apply_rules``
~~~~~~~~~~~~~~~

Run the inspection rules engine against the stored inspection data.  No BMC
or host access is performed.  This lets operators apply newly created or
modified inspection rules to the existing inventory.

Arguments:

* ``phase`` — optional, defaults to ``main``.  Which rule phase to apply.
  Only ``main`` exists today; the argument future-proofs the step for
  additional phases.

This step is available on all inspect interfaces and fails if the node has
no stored inspection data.

Step framework integration
--------------------------

* **Manual cleaning**: ``{"target": "clean", "clean_steps": [{"interface":
  "inspect", "step": "inspect", "args": {"data_handling": "merge"}}]}``
  from ``manageable``.  Because the steps are ``requires_ramdisk=False``,
  they work with ``disable_ramdisk=true``, so a pure-OOB refresh never
  boots the node.

* **Automated cleaning**: the steps default to priority ``0`` and therefore
  never run automatically.  Operators may opt in via the existing
  ``[conductor]clean_step_priority_override`` option (e.g. to refresh
  inventory on every teardown) or via runbook-based automated cleaning.

* **Servicing**: ``{"target": "service", "service_steps": [...]}`` from
  ``active`` — this is the path that addresses the original problem of
  refreshing inventory on deployed nodes without disturbing the workload.

* **Verifying**: the ``inspect`` step is also decorated as a verify step
  with default priority ``0``.  Operators enable it with the existing
  ``[conductor]verify_step_priority_override`` option (e.g.
  ``inspect.inspect:5``) to get an automatic OOB inventory collection every
  time a node passes through ``verifying`` (``enroll`` → ``manageable``).
  Verify steps take no arguments, so the defaults (``replace``,
  ``update_properties=true``) apply.

* **Runbooks**: since runbook step validation derives from the same
  interface list, operators can publish e.g. a ``CUSTOM_REFRESH_INVENTORY``
  runbook containing the ``inspect`` step and delegate its use with
  runbook-scoped RBAC, without granting the ability to run arbitrary steps.

Failure handling, locking, power state assertions, history records and
notifications all come from the step frameworks unchanged: a failed step
moves the node to ``clean failed`` / ``service failed`` / ``enroll`` exactly
as any other step failure would.  The node never enters ``inspecting`` /
``inspect failed`` when inspection runs via a step; those states remain the
domain of the classic ``inspect`` provision verb.

Out of scope / future work
--------------------------

* Asynchronous (in-band) inspection as a step, e.g. booting IPA during
  cleaning to run a full in-band inspection.  The synchronous design here
  does not preclude it: a driver could later return ``CLEANWAIT`` /
  ``SERVICEWAIT`` from its own step implementation.
* A periodic conductor task for scheduled inventory refresh.  Operators can
  approximate this today by triggering servicing externally.
* A deploy-step variant of the ``inspect`` step, so that a deployment
  template (or driver default) could capture a fresh hardware inventory at
  deploy time, recording exactly what was delivered to the instance.  The
  same base-class helper would simply be exposed with the ``deploy_step``
  decorator, plus ``'inspect'`` added to ``DEPLOYING_INTERFACE_PRIORITY``.
* Additional inspection rule phases (e.g. rules scoped to run only during
  servicing); the ``phase`` argument on ``apply_rules`` anticipates this.

Alternatives
------------

* **Extend the state machine** (the previous revision of this spec): allow
  the ``inspect`` provision verb from ``available``, ``active`` and
  ``rescue``, gated by a new ``is_oob()`` driver method.  Rejected by
  review: it adds state machine transitions, a new API microversion, client
  changes and a new driver-capability mechanism, all to model something the
  step frameworks already express.  The step approach also composes with
  other steps (e.g. "update firmware, then re-inspect") which the provision
  verb never could.

* **Do nothing; document the manual workaround.**  Operators can move nodes
  to ``manageable`` themselves.  Rejected because the round-trip through
  cleaning is costly and the restriction is purely artificial for OOB
  drivers.

* **A vendor passthru method.**  Rejected: not discoverable, not composable
  with steps or runbooks, and bypasses the step frameworks' error handling.

Data model impact
-----------------

None.

State Machine Impact
--------------------

None.  Inspection steps run inside the existing ``cleaning``, ``servicing``
and ``verifying`` states.

REST API impact
---------------

No new endpoints and no new microversion.  ``inspect`` becomes an accepted
``interface`` value in the clean step, service step and runbook step
schemas, consistent with how the ``firmware`` interface was introduced.
The new steps and their ``argsinfo`` are discoverable wherever driver steps
are already surfaced.

Client (CLI) impact
-------------------

"openstack baremetal" CLI
~~~~~~~~~~~~~~~~~~~~~~~~~

None required.  Steps are passed as data to the existing ``node clean``,
``node service`` and runbook commands.

"openstacksdk"
~~~~~~~~~~~~~~

None.

RPC API impact
--------------

None.

Driver API impact
-----------------

* The base ``InspectInterface`` gains the ``run_hooks`` and ``apply_rules``
  steps and an undecorated helper implementing the full ``inspect`` step
  body.  A small refactor exposes each interface's configured inspection
  hooks through a common accessor so the base-class steps can resolve them.
* ``RedfishInspect`` decorates the ``inspect`` step (clean, service and
  verify variants); ``idrac-redfish`` inherits it.
* Out-of-tree OOB inspect interfaces opt in by applying the step decorators
  to the inherited helper.  Interfaces that do nothing remain exactly as
  they are today.
* The previously proposed ``is_oob()`` method is no longer needed and is
  not introduced.

Nova driver impact
------------------

None.

Ramdisk impact
--------------

None.

Security impact
---------------

OOB inspection communicates with the BMC using credentials already stored in
``node.driver_info``.  No new credential types or trust boundaries are
introduced.  The steps are invoked through the existing provisioning APIs
and are governed by the existing cleaning/servicing/verifying policies; the
runbook RBAC model applies unchanged.  Inspection rules run by
``apply_rules`` can modify node attributes, which is the same power the
rules engine already has during inspection.

Other end user impact
---------------------

Operators gain the ability to refresh hardware inventory without
interrupting running workloads or removing nodes from scheduling, and to
re-run hooks and rules on stored data after configuration changes.
Behaviour of the classic ``inspect`` provision verb is entirely unchanged.

Scalability impact
------------------

None.  The steps are operator-initiated (or opt-in via priority overrides);
no new polling or periodic work is introduced.

Performance Impact
------------------

None.

Other deployer impact
---------------------

Deployers using redfish-based inspect interfaces can use the new steps
immediately after upgrade.  No configuration changes are required; the
``verify_step_priority_override`` and ``clean_step_priority_override``
options can optionally enable automatic execution.

Developer impact
----------------

Authors of OOB inspect drivers can expose the ``inspect`` step by
decorating the base-class helper.  Authors of in-band inspect drivers need
not make any changes.

Implementation
==============

Assignee(s)
-----------

Primary assignee: Doug Goldstein <cardoe@cardoe.com>

Other contributors:
  None

Work Items
----------

* Add ``'inspect'`` to ``CLEANING_INTERFACE_PRIORITY`` and
  ``SERVICING_INTERFACE_PRIORITY`` in ``ironic/conductor/steps.py``.
* Refactor ``RedfishInspect.inspect_hardware()`` to separate data
  collection from storage/property updates so the step helper can
  implement ``data_handling`` and ``update_properties``.
* Implement the ``inspect`` step helper, ``run_hooks`` and ``apply_rules``
  on ``InspectInterface`` in ``ironic/drivers/base.py`` (with the hook
  accessor refactor in ``ironic/drivers/modules/inspect_utils.py``).
* Implement merge semantics for stored inspection data in
  ``ironic/drivers/modules/inspect_utils.py`` (database and Swift
  backends).
* Decorate the steps on ``RedfishInspect`` (clean, service and verify).
* Ensure ``NoInspect`` does not advertise the base-class steps.
* Add release notes.

Dependencies
============

None.

Testing
=======

* Unit tests for step discovery: OOB interfaces advertise ``inspect``;
  in-band and ``no-inspect`` interfaces do not; all data-capable interfaces
  advertise ``run_hooks`` and ``apply_rules``.
* Unit tests for ``data_handling`` merge/replace semantics against both
  data backends, and for ``update_properties=false``.
* Unit tests for ``run_hooks`` / ``apply_rules`` against stored data,
  including the no-stored-data failure path.
* Tempest scenario: manual clean and servicing with the ``inspect`` step
  against a virtual Redfish (sushy-tools) node, verifying the node returns
  to its originating state with refreshed inspection data.

Upgrades and Backwards Compatibility
=====================================

Existing behaviour is fully preserved.  All new steps default to priority
``0``, so no automated flow changes until an operator opts in.  The classic
``inspect`` provision verb, the state machine and the API surface are
untouched.  Rolling upgrades are safe: the steps appear once conductors are
upgraded; API nodes not yet upgraded simply reject ``interface: inspect``
in step requests as they do today.

Documentation Impact
====================

* ``doc/source/admin/inspection/index.rst`` — document the new steps, their
  arguments and the hooks/rules re-processing workflow.
* ``doc/source/admin/cleaning.rst``, ``doc/source/admin/servicing.rst``,
  ``doc/source/admin/verifying.rst`` — reference the inspect steps.
* ``doc/source/admin/runbooks.rst`` — example inventory-refresh runbook.

References
==========

* `Redfish OOB inspection spec
  <https://specs.openstack.org/openstack/ironic-specs/specs/approved/redfish-inspection.html>`_
* `Servicing spec
  <https://specs.openstack.org/openstack/ironic-specs/specs/approved/servicing.html>`_
* `Inspection rules spec
  <https://specs.openstack.org/openstack/ironic-specs/specs/approved/inspection-rules.html>`_
* `Ironic state machine documentation
  <https://docs.openstack.org/ironic/latest/contributor/states.html>`_
