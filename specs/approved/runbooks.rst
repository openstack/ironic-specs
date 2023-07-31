..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=========================
Self-Service via Runbooks
=========================

https://bugs.launchpad.net/ironic/+bug/2027690

With the addition of service steps, combined with owner/lessee, we now have an
opportunity to allow project members to self-serve many maintenance items by
permitting them access to curated runbooks of steps.

This feature will primarily involve extending creating a new runbook concept,
allowing lists of steps to be created, associated with a node via traits.
These runbooks will then be able to be used in lieu of a list of steps
when performing manual cleaning or node servicing.

Problem description
===================

Currently, users of the Ironic API as a project-scoped member have limited
ability to self-serve maintenance items. Ironic operators are given the
difficult choice of giving users broad access to nodes, allowing them to
run arbitrary manual cleaning or service steps with the only alternative
being permitting no access to self-serve these maintenance items.

Use cases include:

- As a project member, I can execute runbooks via Node Servicing without
  granting the ability to execute arbitrary steps on a node.

- As an system manager, I want to store a list of steps to perform an action
  in an identical manner across many similar nodes.


Proposed change
===============

The proposed change is to create a new API concept, runbooks, which can
be used with any API flow which currently takes explicit lists of steps.

Those runbooks can then be used instead of a list of clean_steps or
service_steps [0]_ when setting node provision state. These are expected
to behave identical to API calls with ``clean_steps`` or ``service_steps``
provided, including honoring the ``disable_ramdisk`` field, and providing
explicit ordering rather than the priority-based ordering that is used in
automated cleaning and deploys.

Additionally, we will ensure that the full CRUD lifecycle of runbooks is
made role-aware in the code, so that a project can limit who can create,
delete, edit, or mark runbooks as public all as separate policy toggles.
We will also ensure deployers can separately toggle the ability to run
step-based flows via runbooks versus step-based flows with arbitrary
step lists.

A runbook will only run on a node who has a trait equal to the runbook name,
to ensure the runbook has been approved for use on a given piece of hardware,
as an extra precaution against hardware breakage.

Alternatives
------------
We considered, originally, repurposing the existing deploy templates into a
generic concept of templates. This was abandoned due to deploy templates
containing implicit steps, making it difficult to reason about them. This is
why we instead chose to call them runbooks, which are entirely specified as
opposed to templates, which are partially specified and have implicit steps
integrated.

Data model impact
-----------------

Create new tables described below::

  ``runbooks`` (same as ``deploy_templates`` except addition of ``owner`` and ``public``)
    - id (int, pkey)
    - uuid
    - name (string 255)
    - public (bool) - When true, template is available for use by any project.
    - owner (nullable string, usually a keystone project ID)
    - disable_ramdisk - When true, similar behavior to disable_ramdisk in manual cleaning -- do not boot IPA
    - extra json/string
    - steps list of ids pointing to ``runbook_steps``

  ``runbook_steps``
    - id (int, pkey)
    - runbook_id (Foreign Key to runbooks.id)
    - interface
    - step
    - args
    - order (or some other field/method to indicate how the steps were ordered coming into the API)


Note: Ensure all queries to ``runbooks`` only pull in ``runbook_steps`` if
needed.


State Machine Impact
--------------------

While no states or state transitions are being proposed, the APIs to invoke
some of those state transitions will need to change to become runbook-aware.

REST API impact
---------------
A new top level REST API endpoint, ``/v1/runbooks/`` will be added, with basic
CRUD support.

The existing ``/v1/nodes/<node>/states/provision`` API will be changed to
accept a ``runbook`` (name or uuid) in lieu of ``clean_steps`` when being used
for servicing or manual cleaning.


Client (CLI) impact
-------------------
The CLI will be updated to add support for the new API endpoints.

Some examples of CLI commands that will be added, and how they interact with
RBAC::

  - baremetal runbook create X [opts] # as system-scoped manager
    - owner: null
    - public: false
  - baremetal runbook create X [opts] # as project-scoped manager
    - owner: projectX
    - public: false
  - baremetal runbook set X --public # as system-scoped manager
    - owner: null
    - public: true
    - Note: Owner field is nulled even if it previously set.
  - baremetal runbook set X --public # as project-scoped manager
    - Forbidden! Requires system-scoped access.
  - baremetal runbook unset X --public # as system-scoped manager
    - owner: null
    - public: false
  - baremetal runbook set X --owner projectX # as system-scoped manager
    - owner: projectX
    - public: false
    - Note: Will return an error if ``runbook.public`` is true.
  - baremetal node service N --runbook X
  - baremetal node clean N --runbook X
  - baremetal node service N --runbook X --service-steps {} # NOT PERMITTED
  - baremetal node clean N --runbook X --clean-steps {} # NOT PERMITTED


RPC API impact
--------------
RPC API will be modified to support runbooks in lieu of steps where necessary.
They will be properly versioned to ensure a smooth upgrade.

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
Operators are warned that even with use of this feature, users may be able to
leverage steps or access which are innocuous on their own, but malicious when
combined.

Deployers should ensure they have reviewed all possible threat models when
granting additional access to less-trusted individuals -- including
restricting unsafe node actions, such as replacing ``deploy_ramdisk`` to
ensure runbooks (and other step-based workflows) operate as expected.

Things for the implementer to avoid to ensure secure implementation:

- Do not permit a project-scoped API user to change ``runbooks.public``
  by default.
- Do not permit a project-scoped API user change ``runbooks.owner`` by default.
- Anything that would *implicitly* mark a runbook as non-public.
- Ensure we check if nodes are able to run a given runbook using node traits,
  in a similar method to how we do so with deploy templates.

RBAC Impact
>>>>>>>>>>>
There are two primary ways this feature interacts with RBAC, beyond the
obvious CRUD for runbooks.

First, the ``runbooks.owner`` and ``runbooks.public`` fields are relevant
for determining if a runbook is scoped to a project or to a system. If
``owner`` is non-null and ``public`` is false, the runbook is scoped to the
project set in that field and is only usable on nodes owned or leased by that
project. If ``owner`` is null and ``public`` is false, the runbook is only
able to be used or access by system-scoped users. If ``owner`` is null and
``public`` is true, a system-scoped member can modify the runbook and a
project-scoped member could use it on a compatible node. Additionally,
the ``owner`` field will only be settable when ``public`` is false or being
set to false, and setting ``public`` to true will null the owner field.

Second, the node change provision state [0]_ API will have a ``runbook`` field
added, and policy will be different for cases where ``runbook`` is specified
instead of ``clean_steps``. Default policy will be to permit manual cleaning
and servicing for a node owner or lessee-scoped member when using a runbook,
but to disallow it when specifying ``clean_steps``. Combining ``clean_steps``
and ``runbook`` will not be permitted.

Expected access after this implementation is complete::

  System
  - Admin
  - Manager
  - Member
  --> Can CRUD system-scoped templates (template.owner=null)
  --> Can CRUD project-scoped templates (template.owner=PROJECT)
  --> Can unset template.owner, changing a template to system-scope
  --> Can mark system-scoped templates as public (template.public=True)
  - Reader
  --> Can list all templates

  Project
  - Admin
  - Manager
  --> Can CRUD project-scoped templates (template.owner=PROJECT)
  --> Cannot set a template to public (template.public=True).
  - Member
  --> Can execute public templates or templates owned by their project.
  - Reader
  --> Can list public templates and templates owned by their project.

Other end user impact
---------------------

None

Scalability impact
------------------

None

Performance Impact
------------------

None

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
  JayF <jay@jvf.cc>

Other contributors:
  TheJulia <juliaashleykreger@gmail.com>

Work Items
----------
- Create Runbooks
  - Object layer
  - DB layer
  - API layer
- Add policy checking tests for /v1/runbooks
- Ensure tempest API tests exist for new API endpoints
- Update API-Ref
- Update Manual Cleaning and Node Servicing documentation

Dependencies
============
All dependencies have been resolved.

Testing
=======
Unit tests will be added to test the new functionality. Integration tests will
be added to test the new API endpoints and CLI commands.

Upgrades and Backwards Compatibility
====================================
The changes are backwards compatible. Existing API endpoints will continue to
function as before, and we will gate all API changes behind microversion
checks.

Documentation Impact
====================
The new functionality will need to be documented. This includes documentation
for the new API endpoints and CLI commands, as well as documenting security
caveats detailed above.

References
==========
.. [0] *Change Node Provision State*: https://docs.openstack.org/api-ref/baremetal/#change-node-provision-state
