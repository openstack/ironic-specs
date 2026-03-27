..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=============================
Runbooks with Multiple Traits
=============================

This spec introduces a ``traits`` field on runbooks and removes the
constraint that a runbook's ``name`` must be a valid trait string.
A new ``description`` field is also added, consistent with other
Ironic objects.

Problem description
===================

When runbooks were originally introduced (API v1.92), the runbook
``name`` served a dual purpose:

1. A human-readable identifier for the runbook.
2. A *gate* – to execute a runbook on a node, the node must carry a
   trait whose value equals the runbook name.

This coupling creates several problems:

* Runbook names are forced to follow the trait naming convention
  (``CUSTOM_[A-Z0-9_]+`` or an ``os-traits`` standard trait).  Human
  readable names like ``"wipe-disks-for-decommission"`` or
  ``"firmware-upgrade-gen10"`` are not permitted.

* Each node that could use the runbook would have to have the trait added
  to it which means more data pushed to placement and more data in
  the scheduling filter which we have seen a lot of traits causing
  performance impacts.

* A single runbook can only be "approved" for use via one trait name.
  Operators that want the same runbook to be available across different
  hardware families—each identified by a different trait—must either
  duplicate the runbook or add a single shared trait to all nodes,
  which undermines the per-hardware-family approval intent.

* There is no ``description`` field on the Runbook object, making
  runbooks harder to document and discover compared with other Ironic
  objects (nodes, ports, etc.) which all carry a ``description``.

Proposed change
===============

Runbooks will be associated with multiple traits, and inversely multiple
runbooks may be associated with a single trait.  This improves operator
workflows and reduces the number of traits that need to be assigned to a
node, which alleviates the scheduling performance impact seen when nodes
carry a large number of traits in placement.

1. **Add a ``traits`` field to runbooks.**  A runbook's ``traits`` is
   a set of trait strings (same format as node traits).  Traits must
   begin with ``CUSTOM_`` followed by uppercase letters, digits, or
   underscores.  When a user requests execution of a runbook, the
   system checks that the target node carries *at least one* trait
   that appears in the runbook's ``traits`` set.  Any non-empty
   intersection is sufficient.

2. **Remove the trait-name constraint from runbook names.**  From
   the API microversion introduced by this spec onwards, a runbook ``name``
   may be any valid logical name string (the same format accepted for node
   names), not just a
   trait-formatted string.  Names remain unique and are still used to
   look up runbooks by name.

3. **Add a ``description`` field to runbooks.**  The field accepts a
   nullable string up to 255 characters, consistent with other Ironic
   objects.

4. **Automatic migration.**  During the database migration, each
   existing runbook's current ``name`` value is inserted as the sole
   entry in that runbook's new ``traits`` set.  This preserves the
   existing behaviour so that no operator action is required on
   upgrade.

5. **New trait-management API endpoints** (``/v1/runbooks/{ident}/traits``).
   Following the same design as node traits, operators can list, set,
   add, and remove individual traits on a runbook.  This reuses the
   existing runbook ownership model: project-scoped managers that are
   already trusted to operate the hardware and update their runbooks
   are likewise trusted to manage the runbook's approval traits.

Alternatives
------------

* **Keep name-as-trait, add an optional ``traits`` list.**  Rejected
  because it leaves the confusing dual-role of ``name``, makes the
  migration path awkward, and does not cleanly fix the naming
  restriction.

* **Use a separate field ``allowed_node_traits``.**  Rejected in
  favour of re-using the well-established ``traits`` concept and
  endpoint pattern already present for nodes.

Data model impact
-----------------

* A new ``runbook_traits`` table is created::

      runbook_traits (
          runbook_id  INTEGER  NOT NULL  REFERENCES runbooks(id),
          trait       VARCHAR(255) NOT NULL,
          version     VARCHAR(15),
          created_at  DATETIME,
          updated_at  DATETIME,
          PRIMARY KEY (runbook_id, trait),
      )

* A ``description`` column (``VARCHAR(255)``, nullable) is added to
  the ``runbooks`` table.

* The unique constraint on ``runbooks.name`` is retained; names remain
  unique identifiers.

* **Migration:** for every existing row in ``runbooks``, a row is
  inserted into ``runbook_traits`` with the same ``runbook_id`` and
  with ``trait`` set to the old ``name`` value (which was previously
  required to be a valid trait string).

State Machine Impact
--------------------

No impact.

REST API impact
---------------

**The API microversion introduced by this spec** introduces the following
changes.

All existing endpoints in ``/v1/runbooks`` are modified:

* On **GET** (list and single-item), the response now includes:

  - ``traits``: a list of trait strings (e.g. ``["CUSTOM_FOO",
    "CUSTOM_BAR"]``).
  - ``description``: a nullable string.

* On **POST** (create), the request body may include:

  - ``traits``: optional list of trait strings.  If omitted, defaults
    to an empty list.  A runbook created without any traits is valid
    but will not be eligible to run on any node until traits are later
    assigned through the dedicated trait endpoints.  The name is no
    longer required to be a valid trait string.
  - ``description``: optional nullable string (max 255 chars).

  The ``name`` field now accepts any valid logical name (letters,
  digits, hyphens, dots, underscores; 1–255 characters).

* On **PATCH** (update), the ``name`` field may now be patched to any
  valid logical name.  The ``description`` field may also be patched.
  (Direct patching of ``traits`` via the runbook PATCH endpoint is not
  supported; use the dedicated trait endpoints instead.)

**New sub-resource endpoints:**

``GET /v1/runbooks/{runbook_ident}/traits``
  List the traits associated with the runbook.

  *Response body*::

      {"traits": ["CUSTOM_FOO", "CUSTOM_BAR"]}

``PUT /v1/runbooks/{runbook_ident}/traits``
  Replace all traits for a runbook.

  *Request body*::

      {"traits": ["CUSTOM_FOO"]}

``PUT /v1/runbooks/{runbook_ident}/traits/{trait}``
  Add a single trait to the runbook (idempotent).

  *No request body.*

``DELETE /v1/runbooks/{runbook_ident}/traits/{trait}``
  Remove a single trait from the runbook.

All trait management endpoints require appropriate policy authorisation
(``baremetal:runbook:update``).  This is intentional: deployments that
delegate runbook updates to project-scoped managers are treating those
managers as the operators for that hardware, so the same role that can
maintain the runbook may also maintain its trait gate.

Client (CLI) impact
-------------------

"openstack baremetal" CLI
~~~~~~~~~~~~~~~~~~~~~~~~~

* ``python-ironicclient`` / the ``openstack baremetal`` plugin will
  need updates to expose ``traits`` in the CLI output for
  ``baremetal runbook create``, ``show``, and ``list``.
* New ``baremetal runbook add trait`` / ``remove trait`` /
  ``set traits`` commands should be added, matching the existing
  ``baremetal node *trait`` commands.

"openstacksdk"
~~~~~~~~~~~~~~

None.

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

None beyond what was already documented in the original runbooks spec.
The trait-intersection check maintains the same operator-controlled
gate within the existing runbook RBAC model: before a runbook can run
on a node, a manager that is already authorised to operate that
hardware must explicitly add a matching trait to the node or to the
runbook.

Other end user impact
---------------------

Consumers of the existing ``baremetal.runbook.*`` notifications will
see ``traits`` and ``description`` added to the payload.

Scalability impact
------------------

The ``runbook_traits`` table is expected to be small (at most ~50
rows per runbook, matching the node-traits limit).

Performance Impact
------------------

Minimal.  Trait lookups are indexed on ``runbook_id``.

Other deployer impact
---------------------

* On upgrade, the database migration automatically populates
  ``runbook_traits`` from existing runbook names.  No manual operator
  action is required.
* Operators may subsequently rename runbooks (to non-trait-format
  names) and add multiple traits per runbook.

Developer impact
----------------

None beyond the normal versioned-object and API-microversion
conventions.

Implementation
==============

Assignee(s)
-----------

Primary assignee: Doug Goldstein <cardoe@cardoe.com>

Other contributors:
  None

Work Items
----------

* Database model: add ``description`` to ``Runbook``; add
  ``RunbookTrait`` model.
* Database API: add CRUD methods for runbook traits.
* Alembic migration: create ``runbook_traits``; add ``description``
  column; migrate names to traits.
* Versioned object: bump ``Runbook`` to v1.2 adding ``description``
  and ``traits`` fields; add ``RunbookTrait`` and ``RunbookTraitList``
  objects.
* API controller:

  - Relax ``name`` validation from the new microversion onwards.
  - Include ``description`` and ``traits`` in responses from the new
    microversion onwards.
  - Implement ``RunbookTraitsController``.
  - Keep pre-updated-microversion create/update flows synchronized by
    mirroring the legacy ``name`` field into ``runbook_traits``.

* Update node provision API to check runbook traits instead of name.
* Update conductor manager automated-cleaning validation to check
  runbook traits instead of name.
* Update API documentation and release notes.

Dependencies
============

None.

Testing
=======

* Unit tests for all new DB methods, object methods, and API endpoints.
* Tempest API tests for the new ``/traits`` sub-resource.
* Migration unit test verifying that existing runbook names are
  correctly migrated to the new ``traits`` table.

Upgrades and Backwards Compatibility
====================================

When the API version is below the microversion introduced by this spec,
existing behaviour is unchanged:
a runbook's name is still validated as a trait string, the ``traits``
and ``description`` fields are not returned, and the
``/v1/runbooks/{ident}/traits`` sub-resource is not accessible.

To preserve the legacy execution semantics after compatibility checks
move to ``runbook.traits``, pre-updated-microversion runbook create requests
also add the submitted ``name`` into ``runbook_traits``.  Likewise,
pre-updated-microversion name updates keep ``runbook_traits`` synchronized
with the submitted
legacy name so that old clients continue to observe name-based
behaviour.

Documentation Impact
====================

* ``doc/source/admin/runbooks.rst`` – update to describe the new
  trait-set model.
* API reference (``api-ref/source/baremetal-api-v1-runbooks.inc``) –
  document new fields and endpoints.
* Web API version history.

References
==========

* `Original runbooks specification
  <https://specs.openstack.org/openstack/ironic-specs/specs/approved/runbooks.html>`_
* `Node traits specification
  <https://specs.openstack.org/openstack/ironic-specs/specs/approved/node-traits.html>`_
