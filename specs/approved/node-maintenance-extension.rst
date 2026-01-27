..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===================================
Node Maintenance: Extensible Model
===================================

Extract node maintenance from a single boolean into a dedicated table of
typed entries, and add an API to assert and release them individually,
so future per-type maintenance behaviour can be composed on top rather
than re-plumbing the same flag for each new use case.

Problem description
===================

Node maintenance today is a single boolean (``node.maintenance``) plus a
free-text reason (``node.maintenance_reason``). The model is too thin
for the operational shape it has accumulated:

- **No audit.** Who set maintenance, when, and who cleared it are not
  recorded.
- **No category.** Operator-set, conductor auto-set on fault, scheduled
  window, and legal hold all collapse to the same flag with no way to
  tell them apart. Operators compensate by encoding categories into the
  reason text by local convention. For example a prefix list such as
  ``LK_OP|HW_ERR: <text>``, which is invisible to RBAC, fragile to
  parse, and lost entirely on the first unset.
- **No scoping.** A lessee cannot hold their own node without admin
  permissions; there is no place to record who the hold is *for*.
- **No concurrent reasons.** Releasing one cause clears the flag for
  all, so two parties cannot independently assert and release holds on
  the same node.
- ``node.fault`` already lives in parallel because the boolean cannot
  carry structured failure information, a sign the model is overloaded.

Each new requirement (lockouts, scheduled windows, multi-party holds,
legal holds, richer fault tracking) ends up either bolted onto the same
boolean or living in its own parallel table. The shared modelling work
gets done repeatedly with no shared audit, scoping, or release story.

Proposed change
===============

Introduce a ``node_maintenance`` table. Each row is one **active**
maintenance entry on one node, carrying:

- ``type``, which identifies the entry's category. It is a free-form string
  in the schema so new categories slot in without a migration, and is
  validated at the API against a registry of known types (see
  `Maintenance types`_)
- ``reason``, ``scope`` (see `Scoping`_), ``extra`` (per-type metadata
  escape hatch)
- ``asserted_by`` / ``asserted_by_project`` / ``asserted_at``
- FK to ``nodes.id`` with ``ON DELETE CASCADE``

An entry is active for exactly as long as its row exists: releasing an
entry **hard-deletes** the row. There are no soft-delete columns and no
separate cleanup mechanism; the historical record (who asserted, who
released, when, and why) is written to node history as ``maintenance``
events at assert and release time, where the existing node-history
retention configuration already governs cleanup.

``node.maintenance`` stays on the ``nodes`` table as a denormalised
cache: it is ``true`` exactly while at least one entry row exists, and
both representations are always updated in the same database
transaction. Every existing programmatic "is this node in maintenance?"
check keeps reading the boolean and needs no join.

``node.maintenance_reason`` is retired as a stored field. The API field
remains and is synthesised from the active entries (see `REST API
impact`_); the database column is deprecated and continues to be
written with the synthesised value for at least one cycle, longer if
the team decides, to keep rolling upgrades safe, then dropped in a
later cycle.

A new API microversion, numbered when the implementation lands,
exposes the entries directly: list the active entries on a node, add a
typed entry, release one entry by UUID, or release them all. Below the
new microversion, and for the existing ``PUT`` / ``DELETE`` boolean
endpoints at every version, behaviour is preserved: legacy calls are
mapped onto a ``legacy``-typed entry.

The work splits into two self-contained patches:

#. The table, the migration with backfill, the ``NodeMaintenance``
   object and DB primitives, the boolean mirroring, and the node
   history events. No user-visible behaviour changes.
#. The new microversion's API surface, its policies, and the
   client/SDK support.

Further *types* and the behaviour they gate (lockouts, scheduled
windows, legal holds, ...) remain future specs layered on this
foundation; none of them requires further schema work.

Maintenance types
-----------------

The schema stores ``type`` as a plain string, but the API only accepts
types registered in code. This spec defines:

``legacy``
  Reserved; never accepted from the typed API. Created through the
  boolean ``PUT``, which updates the reason of an existing entry but
  never re-stamps its asserter or scope, and releasable by anyone
  passing the ``clear_maintenance`` / ``remove`` policies regardless
  of scope: exactly the boolean API's contract today. At most one per
  node, an invariant enforced in code under the node lock.

``fault``
  Reserved for the conductor, asserted under its service identity at
  ``system`` scope with an empty project. At most one per node; the
  fault kind (power failure, clean failure, rescue abort failure)
  travels in ``extra``, and a re-asserted fault updates the entry in
  place. The conductor releases it when automatic recovery succeeds,
  and, matching today's recovery flow, any caller passing the
  ``remove`` / ``clear_maintenance`` policies may release it after
  repairing the node. Wiring the conductor's fault handling to this
  type is a follow-up patch, after which the parallel ``node.fault``
  modelling can be deprecated in its own right.

``hardware_failure``
  Operator-asserted hardware problem (the typed successor of reason
  prefixes like ``HW_ERR``).

``operator_hold``
  General-purpose operator- or user-asserted hold with no more
  specific type; the typed successor of a plain ``maintenance set``.

Adding a new type later is a code-only change: register the constant,
write the rows where the relevant event happens, add tests. Requests
naming an unregistered or reserved type are rejected with ``400``.

Scoping
-------

Each entry records the ``scope`` it was asserted at (``system``,
``owner``, or ``lessee``) and the asserting project
(``asserted_by_project``). Scope is not requested in the API; it is
derived from the caller's effective authority on the node. A caller
passing the system-level admin check asserts at ``system``, whether
through a system-scoped token or a project-scoped admin role, so
deployments running with ``enforce_scope = False`` keep full
authority. A member of ``node.owner`` asserts at ``owner``, and a
member of ``node.lessee`` asserts at ``lessee``.
``asserted_by_project`` records the caller's project, and is empty
for system-internal asserts (the conductor, the migration backfill).

Release authority is checked in addition to policy:

- a caller whose scope strictly outranks the entry's may release it
  (``system`` > ``owner`` > ``lessee``);
- at equal scope, the caller's project must also match the entry's
  ``asserted_by_project``, except at ``system`` scope: any caller
  with system authority may release any ``system`` entry, since the
  operator side is one trust domain and the project recorded there
  is audit-only;
- ``legacy`` and ``fault`` entries are exempt from both checks and
  are governed by policy alone, preserving exactly who can clear
  boolean- and conductor-set maintenance today (see `Maintenance
  types`_).

Within a project, any member passing the ``remove`` policy may
release a teammate's entry: the project is the trust boundary here,
as for other OpenStack resources. Deployers can tighten release to
the asserting user alone through policy (see `Security impact`_).

With default policy, a project-scoped caller can **not** release a
``system``-scope entry; the attempt fails with ``403`` and is shown in
`Scenario 5: scoped holds and RBAC denials`_.

Entries persist when ``node.owner`` or ``node.lessee`` is reassigned,
and lessee churn is routine (the Nova driver records the instance's
project in ``node.lessee``). A former lessee's project loses access
to the node with the field change, so its still-active entries become
stale: releasable by ``owner`` or ``system`` through strict
outranking, but not by the new lessee, whose project does not match.
The same applies one rank up. ``owner``-scope entries surviving an
ownership transfer are releasable only at ``system``, so auditing
maintenance entries belongs in owner/lessee transfer runbooks; see
`Scenario 6: holds across a lease change`_. Asserting *below* one's
own scope (an operator placing a hold for the lessee to release) was
considered and deferred; see `Alternatives`_.

What this enables
-----------------

Delivered by this spec: typed entries with audit, concurrent holds
releasable one at a time, and per-scope release rules. Each item below
is a future spec/patch landing on top, with no further schema work:

- **Fault types**: give existing ``node.fault`` values their own typed
  rows; remove the parallel modelling.
- **Power lock**: a ``lockout`` type that gates power and provisioning
  operations, with an active row, audit trail, and per-scope release
  policy.
- **Scheduled maintenance windows**: entries created with a planned
  end time (carried in ``extra`` or a column added by that spec) that
  the conductor releases automatically.
- **Legal holds**: non-technical, indefinite holds with an audit
  trail.
- **Audit history**: every assert and release is already recorded in
  node history with who, when, and why; future work can add richer
  querying.

Usage scenarios
---------------

Each scenario below follows the same three steps: how the use case is
(or is not) achieved today, what happens to it as the deployment
upgrades, and how it is achieved through the new API. CLI examples use
the ``openstack baremetal`` plugin; REST examples show the request and
response against ``/v1/nodes/{node_ident}/maintenance``.

The transition story is shared by all scenarios, so it is stated once:
the upgrade migration backfills one ``legacy`` entry per node currently
in maintenance, copying its reason, so the new table reflects live
state from day one. Nothing an operator runs today changes meaning or
stops working; the typed commands become available once the deployment
and client negotiate the new microversion. Existing scripts can be
converted to typed entries at leisure, per scenario below.

Scenario 1: hardware replacement hold
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A project owner knows a machine is going for hardware replacement.

**Today** the category is a naming convention inside free text:

.. code-block:: console

   $ openstack baremetal node maintenance set myNode \
         --reason "HW_ERR: Disk 3 has bad sectors, see CIDTEAM-3743"

Nothing records who set it or when, tooling has to parse the prefix
convention back out of the reason, and the category is lost the moment
anyone unsets maintenance.

**After upgrade** the category is a first-class typed entry:

.. code-block:: console

   $ openstack baremetal node maintenance add myNode \
         --type hardware_failure \
         --reason "Disk 3 has bad sectors, scheduled for replacement, \
   see ticket https://myjira/CIDTEAM-3743"

.. code-block:: text

   POST /v1/nodes/myNode/maintenance
   {
       "type": "hardware_failure",
       "reason": "Disk 3 has bad sectors, scheduled for replacement,
                  see ticket https://myjira/CIDTEAM-3743"
   }

   HTTP/1.1 201 Created
   {
       "uuid": "8d8d9a25-c1d0-4d4c-93a6-2a4a7e2bf7d8",
       "type": "hardware_failure",
       "reason": "Disk 3 has bad sectors, scheduled for replacement,
                  see ticket https://myjira/CIDTEAM-3743",
       "scope": "owner",
       "asserted_by": "1f2e3d4c5b6a",
       "asserted_by_project": "9c84d2e0f1a3",
       "asserted_at": "2026-06-10T10:30:00+00:00",
       "extra": {}
   }

A client at an older microversion reading the node still sees
``maintenance: true`` and a ``maintenance_reason`` synthesised from the
entry, so monitoring built on the old fields keeps working.

Scenario 2: a second hold on an already-maintained node
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

While the disk replacement above is pending, the DC team needs to hold
the same node for electrical work.

**Today** this is not achievable: a second ``maintenance set``
overwrites the first reason, and whichever party unsets first clears
maintenance for both. The workaround is hand-merging prefixes into one
reason string (``"LK_OP|HW_ERR: ..."``) and coordinating out of band.

**After upgrade** the second hold is simply a second entry:

.. code-block:: console

   $ openstack baremetal node maintenance add myNode \
         --type operator_hold \
         --reason "Row C power work, change window CHG-2211"
   $ openstack baremetal node maintenance list myNode
   +--------------+------------------+----------------------------+--------+
   | UUID         | Type             | Reason                     | Scope  |
   +--------------+------------------+----------------------------+--------+
   | 8d8d9a25-... | hardware_failure | Disk 3 has bad sectors,... | owner  |
   | 3c1a7b90-... | operator_hold    | Row C power work, chang... | system |
   +--------------+------------------+----------------------------+--------+

.. code-block:: text

   GET /v1/nodes/myNode/maintenance

   HTTP/1.1 200 OK
   {
       "maintenance": [
           {"uuid": "8d8d9a25-...", "type": "hardware_failure", ...},
           {"uuid": "3c1a7b90-...", "type": "operator_hold", ...}
       ]
   }

``node.maintenance`` stays ``true`` until **both** entries are
released. Re-asserting an identical entry (same type and scope from
the same project) returns ``409 Conflict`` rather than stacking
duplicates: a project's hold is one logical entry no matter which
member asserted it.

Scenario 3: releasing one hold at a time
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The electrical work finishes first; the disk is still bad.

**Today** this is not achievable since there is one flag, and unsetting it
releases every cause at once.

**After upgrade** each entry is released by UUID:

.. code-block:: console

   $ openstack baremetal node maintenance remove myNode 3c1a7b90-...

.. code-block:: text

   DELETE /v1/nodes/myNode/maintenance/3c1a7b90-...

   HTTP/1.1 204 No Content

The ``hardware_failure`` entry remains, so ``node.maintenance`` is
still ``true`` and old-microversion readers now see only the remaining
reason. The release is recorded in node history with the releasing
identity and the released entry's type and reason.

Scenario 4: releasing everything at once
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The node is fully repaired and should return to service.

**Today**:

.. code-block:: console

   $ openstack baremetal node maintenance unset myNode

**After upgrade** the same command (and the same ``DELETE`` it issues)
keeps working: it releases every active entry, succeeding only when
the caller may release all of them. The typed CLI offers an explicit
spelling:

.. code-block:: console

   $ openstack baremetal node maintenance remove myNode --all

.. code-block:: text

   DELETE /v1/nodes/myNode/maintenance

   HTTP/1.1 204 No Content

If every active entry was released, ``node.maintenance`` flips to
``false``. If any active entry is outside the caller's release
authority, the request fails with ``403`` and releases nothing (see
Scenario 5), so a partial release never masquerades as a full one.

Scenario 5: scoped holds and RBAC denials
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A system operator has asserted a ``hardware_failure`` entry; the
node's lessee has their own ``operator_hold`` on it and, done with
their work, tries to clear the node.

**Today** there is nothing to deny: scoping is not recorded, and any
caller passing the ``clear_maintenance`` policy clears every cause at
once; including the operator's.

**After upgrade** the lessee's bulk release is refused because the
system-scope entry is not theirs to release:

.. code-block:: text

   DELETE /v1/nodes/myNode/maintenance

   HTTP/1.1 403 Forbidden
   {
       "error_message": "Cannot release maintenance entry
        8d8d9a25-... (type hardware_failure, scope system):
        not permitted at lessee scope"
   }

Releasing their own entry by UUID succeeds:

.. code-block:: console

   $ openstack baremetal node maintenance remove myNode f00dfeed-...

The node remains in maintenance under the operator's entry alone.

Scenario 6: holds across a lease change
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Lessee project A holds its node (``operator_hold`` at ``lessee``
scope) when the lease ends, and the owner re-assigns ``node.lessee``
to project B. Lessee churn is routine, since the Nova driver writes
the instance's project into ``node.lessee``, so this is an expected
state rather than a corner case.

**Today** the flag has no provenance: project B (or anyone else
passing ``clear_maintenance``) simply clears it, silently releasing
whatever cause project A, or an operator, still had.

**After upgrade** the entry persists across the re-assignment, but
project A's standing on the node ended with the lease, and project B
cannot release a ``lessee``-scope entry asserted by a project that is
not theirs:

.. code-block:: text

   DELETE /v1/nodes/myNode/maintenance

   HTTP/1.1 403 Forbidden
   {
       "error_message": "Cannot release maintenance entry
        f00dfeed-... (type operator_hold, scope lessee, asserted by
        project a0a0a0...): not asserted by your project"
   }

The owner or a system operator, outranking ``lessee`` scope, cleans
up the stale hold:

.. code-block:: console

   $ openstack baremetal node maintenance remove myNode f00dfeed-...

The same situation one rank up, an ``owner``-scope entry surviving an
ownership transfer, is releasable only at ``system``, which is why
auditing maintenance entries belongs in transfer runbooks.

Scenario 7: legacy automation, unchanged
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

An existing fleet-management script sets and clears maintenance through
the boolean API and never upgrades its client.

**Today and after upgrade, identically**:

.. code-block:: text

   PUT /v1/nodes/myNode/maintenance
   {"reason": "rebalancing rack"}

   HTTP/1.1 202 Accepted

Under the hood the ``PUT`` creates (or updates the reason of) the
node's single ``legacy`` entry, and ``DELETE`` releases all active
entries, all-or-nothing, exactly as in Scenario 4. When the only
entry on a node is its ``legacy`` one, ``maintenance_reason`` is
reproduced verbatim, so the script reads back exactly the string it
wrote. The script never needs to change for nodes it manages alone;
should a typed entry outside its authority appear, its unset fails
with a ``403`` that names every blocking entry rather than silently
releasing someone else's hold.

Alternatives
------------

- **Keep extending the boolean.** The status quo. Each new requirement
  either overloads the existing flag or adds parallel state; the audit
  and concurrency problems compound.
- **Formalise the reason-prefix convention.** Standardise strings like
  ``LK_OP|HW_ERR:`` and teach tooling to parse them. Keeps the single
  flag's concurrency problem, gives RBAC nothing to act on, and bakes
  string parsing into every consumer.
- **One dedicated table per feature.** Power-lock table, window table,
  legal-hold table, ... each with its own audit, RBAC, and release
  paths. Fragments the operator story and duplicates modelling work.
- **Requestable assert scope.** Letting a caller assert at a scope
  below their own (an operator placing a hold for the lessee to
  release) requires on-behalf-of semantics: the entry would have to
  record the delegate's project for release matching to work.
  Deferred to a future spec rather than shipped as a footgun.

Data model impact
-----------------

New ``node_maintenance`` table:

- ``id`` (Integer, PK, autoincrement)
- ``uuid`` (String(36), unique)
- ``node_id`` (Integer, FK to ``nodes.id``, ``ON DELETE CASCADE``)
- ``type`` (String(64))
- ``reason`` (Text, nullable)
- ``scope`` (String(64))
- ``asserted_by`` (String(255))
- ``asserted_by_project`` (String(255); empty rather than ``NULL``
  for system-internal asserts, so the unique constraint below
  applies)
- ``asserted_at`` (DateTime)
- ``extra`` (Text, nullable; JSON-encoded as elsewhere)
- ``version``, ``created_at``, ``updated_at`` (oslo conventions)

Index on ``(node_id)``; unique constraint on
``(node_id, type, scope, asserted_by_project)``, which serves the
per-type readers and backs the ``409`` duplicate guard at the same
boundary release authority uses: the project. ``asserted_by`` is
audit data, not identity. Per-node invariants the constraint cannot
express portably (one ``legacy`` row, one ``fault`` row) are enforced
in code under the node lock.

Rows are hard-deleted on release; the table only ever holds the active
entries, and the durable audit trail lives in node history (event type
``maintenance``), reusing its existing retention and cleanup
configuration. There are no ``released_by`` / ``released_at`` columns.

On the ``nodes`` table: ``maintenance`` is retained as a denormalised
cache of "any active entry exists", updated in the same transaction as
entry change. ``maintenance_reason`` is deprecated: it continues
to be written (with the synthesised value) for at least one cycle,
longer if the team decides, so that services still reading it during
a rolling upgrade stay correct, and is dropped by a follow-up
migration in a later cycle.

The migration backfills one ``legacy`` row per currently maintained
node, copying ``maintenance_reason`` and stamping ``asserted_by`` as
the migration, at ``system`` scope with an empty project (the
original asserter is unknowable). Because ``legacy`` release is
policy-only, those stamps are audit data and change nothing about who
can clear the entry: exactly the callers who could clear the boolean
the day before the upgrade.

State Machine Impact
--------------------

None.

REST API impact
---------------

The typed-entry endpoints below are gated behind one new microversion,
numbered when the implementation lands. Below it the API is
byte-for-byte unchanged.

``GET /v1/nodes/{node_ident}/maintenance`` (new microversion)
  List the node's active maintenance entries.

  Response: ``200`` with ``{"maintenance": [<entry>, ...]}``.
  Errors: ``403`` (policy), ``404`` (node not found, or a request
  below the new microversion).

``POST /v1/nodes/{node_ident}/maintenance`` (new microversion)
  Add a typed entry. Body: ``type`` (required; a registered,
  non-reserved type), ``reason`` (optional string), ``extra``
  (optional object). ``scope``, ``asserted_by``, and
  ``asserted_by_project`` are derived from the request context per
  `Scoping`_, never supplied by the caller.

  Response: ``201`` with the created entry, as in Scenario 1.
  Errors: ``400`` (unregistered or reserved ``type``), ``403``
  (policy), ``404`` (node), ``409`` (identical active entry already
  exists: same type and scope from the same project).

``DELETE /v1/nodes/{node_ident}/maintenance/{entry_uuid}`` (new microversion)
  Release one entry. The row is deleted, the release is recorded in
  node history, and ``node.maintenance`` recomputed, all in one
  transaction.

  Response: ``204``.
  Errors: ``403`` (policy; entry scope above the caller's; or equal
  scope with a different asserting project, per `Scoping`_), ``404``
  (node or entry).

``DELETE /v1/nodes/{node_ident}/maintenance`` (all versions)
  Existing endpoint, generalised semantics: release **all** active
  entries. If any active entry is outside the caller's release
  authority, the request fails with ``403`` and nothing is released;
  otherwise ``204``. The ``403`` message enumerates every blocking
  entry (uuid, type, scope), since it is the only diagnostic a client
  below the new microversion gets. For nodes that only ever see
  boolean-API usage (a single ``legacy`` entry) this is
  indistinguishable from today's behaviour.

``PUT /v1/nodes/{node_ident}/maintenance`` (all versions)
  Existing endpoint, unchanged request/response shape. Creates the
  node's ``legacy`` entry or updates its reason; the asserter and
  scope recorded at creation are never re-stamped, which stays safe
  because ``legacy`` release is policy-only (`Scoping`_).

The node's ``maintenance`` field is unchanged at every version:
``true`` while any entry is active. ``maintenance_reason`` is
synthesised: when the node's only entry is a ``legacy`` one, its
reason is returned verbatim (legacy round-trip fidelity); otherwise
the active entries are rendered as ``<type>: <reason>`` joined with
``"; "`` in ``asserted_at`` order.

An entry object serialises as: ``uuid``, ``type``, ``reason``,
``scope``, ``asserted_by``, ``asserted_by_project``, ``asserted_at``,
``extra``, ``links``. ``asserted_by`` records the authenticated user
and ``asserted_by_project`` their project; the conductor uses a
single logical service identity and an empty project for ``fault``
entries. On entries whose scope strictly outranks the caller's, the
two asserter fields are masked in responses: a lessee can see that a
``system`` hold exists, and why, without learning operator
identities.

Policy changes are described under `Security impact`_. The change is
discoverable through standard microversion negotiation; older clients
continue against the unchanged boolean surface.

Client (CLI) impact
-------------------

"openstack baremetal" CLI
~~~~~~~~~~~~~~~~~~~~~~~~~

``maintenance set`` / ``maintenance unset`` are unchanged. New
commands, available once the negotiated microversion includes the
typed maintenance API:

.. code-block:: console

   $ openstack baremetal node maintenance add <node> \
         --type <type> [--reason <text>]
   $ openstack baremetal node maintenance list <node>
   $ openstack baremetal node maintenance remove <node> <entry-uuid>
   $ openstack baremetal node maintenance remove <node> --all

"openstacksdk"
~~~~~~~~~~~~~~

A ``NodeMaintenanceEntry`` resource with list/create/delete on
``/v1/nodes/{node_ident}/maintenance``, plus convenience methods on the
node proxy mirroring the CLI verbs.

RPC API impact
--------------

None. As with the boolean endpoints today, the API service performs
the writes directly; the DB API gains create / destroy / get / list
primitives on the new table. During a rolling upgrade the standard
release pinning applies: while pinned, the boolean remains canonical
and not-yet-upgraded services may flip it without touching the table;
when the pin is lifted, the backfill logic is re-run once to reconcile
any rows missed in that window.

Driver API impact
-----------------

None.

Nova driver impact
------------------

None. Nova's view of maintenance is the unchanged ``node.maintenance``
boolean.

Ramdisk impact
--------------

None.

Security impact
---------------

Existing ``baremetal:node:set_maintenance`` and
``baremetal:node:clear_maintenance`` policies continue to govern the
unchanged ``PUT`` / ``DELETE``. New policies for the typed endpoints:

- ``baremetal:node:maintenance:get``: defaults to the same level as
  reading node details.
- ``baremetal:node:maintenance:add``: defaults to the same level as
  ``set_maintenance``.
- ``baremetal:node:maintenance:remove``: defaults to the same level
  as ``clear_maintenance``.

Release authority (`Scoping`_) is enforced in code in addition to
policy: passing the ``remove`` policy is necessary but not sufficient
to release an entry asserted at a higher scope or by another project.
These checks are floors that policy can tighten but not relax, so a
misconfigured policy file cannot let a lessee release a system hold.
Deployers who relax the ``add`` policy toward owners/lessees should
note that maintenance still gates conductor behaviour, so granting it
grants the ability to take a node out of service.

The ``remove`` policy is enforced per entry, including once per entry
during a collection ``DELETE``, with the entry's ``type``, ``scope``,
``asserted_by``, and ``asserted_by_project`` exposed as policy target
attributes alongside the node's fields. Deployers can therefore
tighten release to the asserting user alone, lockout/tagout style:

.. code-block:: yaml

   "baremetal:node:maintenance:remove":
       "role:member and user_id:%(maintenance.asserted_by)s"

Maintenance entries reveal who asserted them; on entries whose scope
strictly outranks the caller's, the asserter fields are masked (see
`REST API impact`_), so lessees cannot enumerate operator identities.

``reason`` and ``extra`` are user-provided data; they are stored and
echoed back but never interpreted, matching the handling of the
existing reason field.

Other end user impact
---------------------

None.

Scalability impact
------------------

The table holds only active entries (hard delete on release), so its
size is bounded by concurrently maintained nodes, not by history.
Historical growth lands in node history, which has existing retention
controls. Writes are infrequent (operator action or conductor fault),
and reads on hot paths stay on the cached boolean with no join.

Performance Impact
------------------

Negligible. The boolean remains the canonical fast-path read; the new
table is only consulted by the typed endpoints and by the boolean
endpoints when releasing entries.

Other deployer impact
---------------------

One additive migration on upgrade; backfill is bounded by the number
of currently maintained nodes. Maintenance assert/release events add
node history rows, governed by the existing node history configuration
options. The ``maintenance_reason`` column removal lands in a later
cycle as its own migration, after the deprecation period.

Developer impact
----------------

Future maintenance-related work has a place to land. Adding a new type
is a code-only change: register a constant, write the rows where the
relevant event happens, add tests. No schema work, no new tables.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  cid <afonnepaulc@gmail.com>

Other contributors:
  None

Work Items
----------

Milestone 1, the model (no user-visible change):

- Migration creating ``node_maintenance`` and backfilling ``legacy``
  entries for currently maintained nodes.
- ``NodeMaintenance`` versioned object, DB-API CRUD primitives, and
  associated exception classes.
- Mirror existing boolean ``PUT`` / ``DELETE`` into the table as type
  ``legacy``; keep the boolean transactionally in sync.
- Node history events on assert and release.

Milestone 2, the API:

- The new microversion: list/add/release endpoints, type registry
  validation, scope derivation and release-authority checks, policies.
- Synthesised ``maintenance_reason`` and column deprecation.
- python-ironicclient / OSC plugin and openstacksdk support.
- API reference and admin documentation; release notes for both
  patches.

Dependencies
============

None.

Testing
=======

Unit tests cover the DB-API CRUD, the object, the boolean mirroring,
the reason synthesis, the type registry, and the release-authority
matrix: scope precedence, project matching, and the ``legacy`` /
``fault`` exemptions. API (functional) tests exercise the new
endpoints across microversions, including the ``400`` / ``403`` /
``409`` paths shown in the scenarios. Existing API tests continue to
verify the boolean contract, including legacy reason round-trip
fidelity. A tempest API test covers add/list/remove against a deployed
service.

Upgrades and Backwards Compatibility
====================================

- The migration is additive (new table only) and backfills currently
  maintained nodes as ``legacy`` so the table reflects live state from
  day one.
- ``node.maintenance`` remains at the API surface unchanged;
  ``maintenance_reason`` remains at the API surface as a synthesised
  field, byte-identical for boolean-only usage. Existing clients see
  no change at any microversion they already use.
- The ``maintenance_reason`` database column is deprecated but still
  written for at least one cycle, or longer if the team decides
  (rolling-upgrade safety), then dropped.
- Standard release pinning covers the mixed-version window; the
  backfill is re-run once when the pin is lifted to reconcile boolean
  flips made by old services.

Documentation Impact
====================

API reference gains the new endpoints; the admin maintenance
documentation is rewritten around typed entries with the boolean
behaviour described as the compatibility surface. Release notes for
both patches.

References
==========

None.
