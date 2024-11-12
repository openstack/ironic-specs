..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=======================================
System Scoped Role Based Access Control
=======================================

Specification Scope: OpenStack Integrated

https://storyboard.openstack.org/#!/story/2008425

Ironic has long been considered an "admin-only" service. This changed with
recent work contributed to help make Ironic able to provide `multi-tenant
capabilities <https://storyboard.openstack.org/#!/story/2006506>`_.
This work was in support of the the efforts of the `Mass Open Cloud
community <https://massopen.cloud/>`_ to support delineation of access
and resource allocation between the participating organizations through
an ``owner`` and ``lessee`` field.

However there is a growing desire to delineate scopes in which user accounts
have access to the API. This effort is sometimes referred to as "Secure RBAC"
in the OpenStack community, which is an initiative to have scope restricted
authentication across OpenStack services, where the scoping and modeling
is consistent to provide a consistent "authorization experience". This is
achieved via `system scoped role <https://specs.openstack.org/openstack/keystone-specs/specs/keystone/queens/system-scope.html>`_
assignments. In this model, an ``admin``, ``member``, and ``reader`` exists.
The ``admin`` role implies ``member``, and ``member`` implies ``reader``.
These roles exist in one of three scopes, ``system``, ``domain``, and
``project``. The relevant scopes for most services in OpenStack are the
``system`` and ``project`` scopes.

In essence this effort is to group the access and actions behind personas,
which are role and scope permutations that can be applied to a user via role
assignments in keystone.users and then ensuring that the invoked access rights
do not permit inappropriate access such as edit fields as a reader only
role on the system scope. At a high level, this is conceptually modeled into
``admin``, ``member``, and ``reader`` roles. During the
`policy in code <https://governance.openstack.org/tc/goals/selected/queens/policy-in-code.html>`_,
effort the ``admin`` role was modeled the ``baremetal_admin`` role and the
``reader`` role via the ``baremetal_observer`` role, however none of this
is system scoped. The existing access roles are project scoped to a
``baremetal`` project, and Ironic has no concept of token scopes.

Role definitions:

* admin - This is in essence an administrative user with-in the operating
          scope. These are accounts which Create/Delete $things,
          and in keystone default configuration, this role implies
          the ``member`` role. In an Ironic context, we can think of this user
          as the infrastructure administrator who is adding their baremetal
          machines into Ironic.
* member - This is a user which can act upon things. They may be able to read
           and write with-in objects, but cannot create/delete new objects
           unless it is an explicitly permitted action. An Ironic example
           may be that we might want to permit members to be able to
           request allocations, or change a node's provision state.
           Similar to ``admin`` implying ``member``, ``member`` implies
           ``reader``.
* reader - This is a user which needs to be able to have read-only access.
           They can read objects but not change, modify, or delete objects.
           In a ``system`` scope it may be a network operations center
           employee who has a business need to be able to observe the
           status and details. In a ``project`` scope, this may be
           someone attempting to account for resources, or accounts
           for automated processes/reporting.

.. note:: Additional details on default role definitions is covered in the
   `Keystone specification "define default roles" <https://specs.openstack.org/openstack/keystonesspecs/specs/keystone/rocky/define-default-roles.html>`_ or
   the `Keystone administrator's guide <https://docs.openstack.org/keystone/latest/admin/service-api-protection.html>`_.

.. note:: A future potential is that an ``auditor`` role may exist, but it
   would *not* match readers. Auditors would be read-only in nature, but their
   role would likely allow sensitive values to be unmasked. This has not
   been decided upon, and depending on service configuration could likely be
   implemented manually with a custom policy file. That being said,
   this is out of scope of this specification document at this time.
   It is also important to note that the ``admin``, ``member``, and
   ``reader`` roles do not automatically unmask sensitive data, and
   should not be anticipated to do so by default.

When considering the above role definitions and the use case of baremetal,
scope differences will have a major difference between what exists
today and what would exist moving forward. At a high level, you wouldn't
allow a ``project`` scoped ``admin`` to have full administrative access
to Ironic.

Scope definitions:

* system - This is similar to the existing scope of the cloud deployment today.
* domain - This scope, is presently only used in Keystone for associations.
           We do not anticipate this to apply, and the primitives do not exist
           in Ironic.
* project - This is the logical grouping in which users are members of projects
            and have some level of implied member rights with-in that project.
            This is tracked and associated using the ``project_id`` value.

Additional information can be found in the
`Keystone administration - tokens <https://docs.openstack.org/keystone/latest/admin/tokens-overview.html#authorization-scopes>`
documentation and the `Keystone contributor - services <https://docs.openstack.org/keystone/latest/contributor/services.html#authorization-scopes>`_
documentation.

Problem description
===================

The fundamental issue at hand is Ironic does not understand scoped access.
This lack of understanding of scoped access coupled with existing project
scoped role/access creates a confusing and different authentication
experience from other services which have implemented the ability to have
scope delineated access, being ``Keystone`` and ``Nova`` as of the point
in which this specification was authored.

Coincidentally there is a desire from larger OpenStack operators to
have the ability to delineate access. In other words permit operations
centers to be able to view status, but not be able to act upon nodes.
This may be a ``reader`` scoped user in the scope of a project, or
in the scope of the entire system.

As projects within OpenStack implement Scope and Role delineation, and
enable scope based access restriction, a risk exists that Ironic will
become incompatible with the models attempting to be represented.

And thus we must implement support to delineate scopes, roles, and
ultimately what may be a differing access model for some remote resources.
In particular, risk exists with existing integrations as they may grow to
expect only Project scoped requests, and refuse a System scoped member
request. These sorts of issues will need to be identified and
appropriately navigated.

In summary, the purpose of this specification is to make changes in
*ironic* and *ironic-inspector* to be consistent and future compatible
with the rest of the OpenStack community. This will further enable
infrastructure operators where they can leverage the prior community
policy work in the OpenStack community to override the policy defaults
the community reaches.

Proposed change
===============

At a high level, the desire is to:

a) Have greater consistency through the adoption of standard roles.
b) Implement the ability to move to the standard scope based
   restriction where the new standardized roles would apply.
c) Move services, such as ironic from the concept of `admin projects`
   to a `system scope`.

We will do this by:

1) Constructing a new set of policies to reflect the secure
   RBAC model where the "scope" is included as part of the definition.
2) Deprecating the previous policies in code which consist of roles
   scoped to the ``baremetal`` project. These should be anticipated to be
   removed at a later point in time.
3) Implementing explicit testing to ensure scopes are handled as we expect.
4) Creating an integration test job leveraging the ``oslo.policy`` setting
   to enforce scope restriction to help ensure cross-service compatibility
   and potentially having to alter some cross-service interactions to ensure
   requests are appropriately modeled. It should be expected that this may
   make visible any number of possible issues which will need to be addressed.

During the deprecation period, operators will continue to be able to leverage
the previous authentication model.

These new policies would model our existing use and data model however
with scope applied *and* multi-tenant access enabled. This will enable
a "friendly" default usage path which will still be opt-in unless the node
``owner`` or ``lessee`` field is populated on a node object.

Combining the three defined roles of ``admin``, ``member``, and ``reader``,
with the three scopes, ``system``, ``domain``, ``project`` results in a matrix
of possibilities. But, the ``domain`` is not anticipated to be needed, thus
leaving six access scenarios or personas that have to be considered.

Please consult the `High level matrix`_ for a high level overview as to the
anticipated use model.

In order to have a consistent use pattern moving forward, the existing
role definitions of ``baremetal_admin`` and ``baremetal_reader`` will be
deprecated and removed, however they will also not be effective
once the ``[oslo_policy]enforce_scope`` and
``[oslo_policy]enforce_new_defaults`` parameters are set to ``True``.

Above and beyond new policy definitions, the creation of additional tests
will be needed in the ``ironic`` and ``ironic-inspector`` projects to validate
enforcement or appropriate resource denial based upon the scope.

Additional issues and rights validation logic may need to be applied, however
that will likely require adjacent/integrated projects to change their policy
enforcement.

.. note::
   Adjacent/integrated projects/services, for example is the interaction
   between Nova, Neutron, Cinder, Glance, Swift, and Ironic. Services do
   convey context on behalf of the original requester for a period of time,
   and can make access control decisions based up on this. Ironic has
   previously had to address these sorts of issues in the Neutron
   and Cinder integrations.

In terms of ``ironic-inspector`` and its API, the resulting default policies
for this effort would be entirely system scoped and no other scope is
anticipated to need implementation as the ``ironic-inspector`` is
purely an admin-only and hardware data collection oriented service.

.. NOTE::
   In review of this specification document, it has been highlighted that
   a tenant may find it useful to have the ability to trigger inspection
   of a node, and have it report to *their* own ``ironic-inspector``
   instance. This is an intriguing possibility, but would be a distinct
   feature above and beyond the scope of this specific work. The benefit
   of the previous "policy in code" effort, is operators should be able
   to simply update the policy in this case, if operationally permissible
   in that Operator's security posture.


High level matrix
-----------------

The table below utilizes two definitions which hail back to the existing
multitenancy work that is present in ironic. They are not the proposed new
name, but used to provide conceptual understanding of what the alignment
of the policy rule represents since there are technically several different
access matrices based upon the variation and ultimately the agreement
reached within the community. The end name definition may be something
similar, but that is an implementation naming decision,
not higher level design decision.

* `is_node_owner` - When the API consumer's project ID value is populated in
                    the Ironic node object's ``owner`` field. This represents
                    that they are the authoritative
                    `owner <https://specs.openstack.org/openstack/ironic-specs/specs/approved/node-owner-policy.html>`_
                    of the baremetal node.
* `is_node_lessee` - When the API consumer's project ID value is populated in
                     the Ironic node object's ``lessee`` field. This is
                     considered the current or assigned user of the node.
                     See the
                     `Allow Leasable Nodes <https://specs.openstack.org/openstack/ironic-specs/specs/15.0/node-lessee.html>`_
                     specification for additional details.

.. NOTE::
   It is important to stress, that the table below are general guidelines.
   A higher level of detail is available below in `Project Scope`_
   and `Endpoint Access Rights`_.

+-------------+----------------------+---------------------------------------+
| Role        | System Scope         | Project Scope                         |
+-------------+----------------------+---------------------------------------+
| admin       | Effectively the same | Project ``admin`` able to have        |
|             | as the existing      | equivalent access to the API as       |
|             | "baremetal_admin"    | ``system`` scoped ``member`` with a   |
|             | role.                | filtered view matching                |
|             |                      | `is_node_owner`.                      |
|             |                      | ``owner`` field updates are blocked.  |
|             |                      | Some sensitive fields may be redacted |
|             |                      | or be restricted from update.         |
+-------------+----------------------+---------------------------------------+
| member      | New concept for a    | Project members will be able to use   |
|             | *do-er* user or      | a baremetal node if `is_node_lessee`  |
|             | service account.     | or `is_node_owner`                    |
|             |                      | is matched and perform field/state    |
|             | Can't add or delete  | updates on individual nodes with the  |
|             | nodes, but can       | exception of the ``owner`` and        |
|             | do things like       | ``lessee`` fields. Some additional    |
|             | provision_state      | fields or update restrictions will    |
|             | changes.             | exist.                                |
+-------------+----------------------+---------------------------------------+
| reader      | Effectively the same | This is a read-only user concept      |
|             | as the existing      | where a project ``reader`` would be   |
|             | "baremetal_observer" | able to view a node if                |
|             |                      | `is_node_owner` or `is_node_lessee`   |
|             |                      | applies. This role is expected to     |
|             |                      | still have a restricted view, which   |
|             |                      | will likely vary based on which type  |
|             |                      | of granted rights.                    |
+-------------+----------------------+---------------------------------------+

.. note:: An ``auditor`` role has not been proposed in this work, but *does*
   make eventual sense in the long term, and should be logically considered as
   reader does not equal an auditor in role. The concept for ``auditor`` would
   expect to allow secrets such as masked fields to be unmasked.

.. note:: Some role/scope combinations may be combined in discussions and
   communication in a {scope}-{role} format. This is effectively the persona
   being defined. Such as `system-admin` for a system wide scope or
   `project-admin` for a user who is a project administrator.

.. note:: Field restriction are likely to be controlled by additional policy
   rules, which MAY cascade in structure where if full general update access
   is not granted then lower level policies should be enumerated through.
   Similar logic is already present in ironic.

In effect, a ``PROJECT_ADMIN``, if defined in the terms of a rule, would
match upon a ``project_id`` matching the ``owner`` and the user having an
admin role. A ``PROJECT_MEMBER`` includes ``PROJECT_ADMIN`` *or* where
``project_id`` matches ``lessee`` and the role is ``member``.

Alternatives
------------

No alternative is available as the model of implementation. This is due to
it attempting to conform to the overall OpenStack model. Fine details should
likely be discussed with-in the implementation.

Data model impact
-----------------

None

State Machine Impact
--------------------

None

REST API impact
---------------

The overall high level behavior of this change will be
settings enforced through ``oslo_policy`` until the deprecated policies are
removed from Ironic.

In accordance with API standards, even though it will not modify functional
behavior this change will increment the API micro-version. This is to enable
API consumers to be able to navigate around possible logic or policy changes
around an upgrade. This is unrelated to policy enforcement specifics which
cannot be permitted to be visible via the API surface.

End API user behavior is not anticipated to be changed, however with scope
enforcement set in ``oslo.policy``, an appropriately scoped user will be
required.

System Scope
~~~~~~~~~~~~

The transition for System scoped roles is fairly straight forward as described
by the chart `High Level Matrix`_ in `Proposed Change`_.
Existing Admin/Observer roles would be translated to System-Admin
and System-Reader respectively.

The addition to this scope is the ``member`` role concept. This is a user
who can *Read* and *Update*, but that cannot *Create* or *Delete*
records. In other words, the API consumer can deploy a node, they can update
a node, but they are unable to remove a node. They should be able to
attach/detach VIFs, and ultimately this should be able to be the rights
granted to the service account used by the ``nova-compute`` process.

A user with a system scope of any valid role type should be anticipated as
having full API surface visibility with exception of the special purpose
``/v1/lookup`` and ``/v1/heartbeat`` endpoints. This will be different for
`Project Scope`_ based access where nodes will only be visible if owner
or lessee are populated.

.. TODO:: Follow-up with neutron regarding port attach/detach.

.. TODO:: Follow-up with Cinder regarding volume attach/detach.

.. TODO:: Follow-up with Nova regarding rights passed through on context.

.. NOTE::
   The primary focus of this specification is targeted at the Wallaby
   development cycle where the System scope is most beneficial to
   support. Given time constraints and cross-project mechanics
   we will likely see additional work to refine scope interactions
   under this spec as time progresses. Some of these things may be
   related to ``volume`` or ``port`` attachments, or possibly even
   tighter integration of this functionality in ``nova-compute``.
   All of these things will evolve over time, and we cannot answer
   them until we reach that point in time.

Project Scope
~~~~~~~~~~~~~

The Project scoped restrictions in the secure RBAC model are dramatically
different, however precedent already exists with the addition of the
`is_node_owner` and `is_node_lessee` logic which would apply to project
scoped interactions.

API consumers seeking to ``GET`` resources in the project scope would only be
able to view resources which match the ``is_node_owner`` and/or
``is_node_lessee`` which are associated to the ``owner`` and ``lessee``
fields.

.. NOTE::
   A node CAN have an ``owner`` and/or ``lessee`` independently, and at
   present the policy model delineates access separately.

In this case, a Project-Admin would have similar rights to a System-Member
where they would be able to update hardware focused fields such as
``driver_info``, however only if ``is_node_owner`` matches.
Project admins who match ``is_node_lessee`` should not be permitted
the ability to update fields such as ``driver_info``.

.. TODO:: We may wish to evaluate if it is useful to permit updating
   ``driver_info`` as a project admin. Dtantsur thinks, and I agree that this
   is likely highly deployment and operationly specific, and it may be we
   need a knob to govern this behavior.

A Project-Member would again be scoped to the appropriate database entries
which apply to their user's scope. They should be enabled to update fields
such as ``instance_info``, and provision, unprovision, and potentially update
VIFs.

VIFs being set will need to have some additional code to perform an access
rights verification to ensure that a project member is attempting to bind
to a VIF which matches their node ownership and their user's entry, or the
value of the lessee field and that requesting user's project.

With the physical nature of assets, project scoped users are unable to
create or delete any records.

Project scoped readers, again would only have a limited field view
with the associated ``is_node_lessee`` or ``is_node_owner``.

Endpoint Access Rights
++++++++++++++++++++++

This list is based upon the published information in the `Baremetal API
Reference <https://docs.openstack.org/api-ref/baremetal/>`_. Not all
actions on the node object are covered in this list. Some field restrictions
apply. See `Node object field restrictions`_ for details with a Node object.

.. NOTE:: This list does not include all possible actions on a node
   at this time.

+------------------------------------+----------------------------------------+
| Endpoint                           | Project Scope Accessible               |
+------------------------------------+----------------------------------------+
| /                                  | Yes, Public endpoint                   |
+------------------------------------+----------------------------------------+
| /v1                                | Yes, Public endpoint                   |
+------------------------------------+----------------------------------------+
| /v1/nodes                          | Filtered View and access rights        |
|                                    | which will necessitate additional      |
|                                    | policy rules to be added.              |
+------------------------------------+----------------------------------------+
| /v1/nodes/{uuid}                   | Filtered view and access rights        |
+------------------------------------+----------------------------------------+
| /v1/nodes/{uuid}/vendor_passthru   | No, Will not be permitted as this is a |
|                                    | open-ended vendor mechanism interface. |
+------------------------------------+----------------------------------------+
| /v1/nodes/{uuid}/traits            | Yes, accessible to ``owner`` to manage |
+------------------------------------+----------------------------------------+
| /v1/nodes/{uuid}/vifs              | Yes, write access requires additional  |
|                                    | validations.                           |
+------------------------------------+----------------------------------------+
| /v1/portgroups                     | Yes, Filtered view and Read-Only       |
|                                    | for ``owner`` managability.            |
+------------------------------------+----------------------------------------+
| /v1/nodes/{uuid}/portgroups        | Filtered view and Read-Only            |
+------------------------------------+----------------------------------------+
| /v1/ports                          | Yes, Filtered view and access rights   |
|                                    | for ``owner`` managability.            |
+------------------------------------+----------------------------------------+
| /v1/nodes/{uuid}/ports             | Filtered view and access rights.       |
+------------------------------------+----------------------------------------+
| /v1/volume/connectors              | Yes, Filtered view, Read-only.         |
+------------------------------------+----------------------------------------+
| /v1/volume/target                  | Filtered view, will require extra      |
|                                    | to prevent target requested is valid   |
|                                    | for the user/project to request.       |
+------------------------------------+----------------------------------------+
| /v1/nodes/{uuid}/volume/connectors | Filtered view, read-only.              |
+------------------------------------+----------------------------------------+
| /v1/nodes/{uuid}/volume/targets    | Filtered view, read-only.              |
+------------------------------------+----------------------------------------+
| /v1/drivers                        | No, `system` scope only.               |
+------------------------------------+----------------------------------------+
| /v1/nodes/{uuid}/bios              | Yes, Filtered view based on access     |
|                                    | rights to the underlying node.         |
+------------------------------------+----------------------------------------+
| /v1/conductors                     | No, `system` scope only.               |
+------------------------------------+----------------------------------------+
| /v1/allocations                    | Project scoped, however the access     |
|                                    | model is geared towards owners using   |
|                                    | this endpoint.                         |
+------------------------------------+----------------------------------------+
| /v1/deploy_templates               | No, `system` scope only at this time.  |
|                                    | as the table/data structure is not     |
|                                    | modeled for compatibility.             |
+------------------------------------+----------------------------------------+
| /v1/chassis                        | No, `system` scope only.               |
+------------------------------------+----------------------------------------+
| /v1/lookup                         | No, Agent reserved endpoint.           |
+------------------------------------+----------------------------------------+
| /v1/heartbeat                      | No, Agent reserved endpoint.           |
+------------------------------------+----------------------------------------+

.. WARNING:: Port support will require removal of legacy neutron port
             attachment through ``port.extra['vif_port_id']``

.. NOTE:: Contributor consensus is that ``port`` objects do not require
          project scoped access, however one important item to stress
          is that the ``owner`` may be viewed as the ultimate ``manager``
          of a physical node, and the ``system``, or ``ironic`` itself
          just provides the management infrastructure. This is a valid case
          and thus it may be reasonable that we settle on permitting owner
          far more access rights than node lesses in a project scope.

.. NOTE:: Contributor consensus is that resource class and trait records
          may only be necessary for a ``system`` scoped user to edit, however
          the case can also be made that this should be able to be delegated
          to the ``owner``. This specification, itself, is not calling for
          a specific pattern, but more so anticipates this will be an
          implementation detail that will need to be sorted out. It may start
          as something only ``system`` scoped users with the appropriate role
          can edit, and may evolve, or it may not be needed.


Node object field restrictions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. NOTE:: These are proposed, however not final. Implementation of
   functionality will determine the final field behavior and
   access.

* uuid - Read-Only
* name - Read/Write for Project Admins if the project owns the
  physical machine.
* power_state - Read-Only
* target_power_state - Read-Only
* provision_state - Read-Only
* target_provision_state - Read-Only
* maintenance - Read/Write
* maintenance_reason - Read/Write
* fault - Read/Write
* last_error - ???
  .. TODO:: The issue with ``last_error`` is that it can leak infrastructure hostnames of conductors, bmcs, etc. For BMaaS, it might make sense?
* reservation - Returned as a True/False for project users.
* driver - Read-Only
* driver_info - Likely returns as an empty dictionary, although
  alternatively we can strip the URLs out, but that seems a little
  more complicated.
* driver_internal_info - Likely will return an empty dictionary as
  Project Admins and Project Members should not really need to see
  the inner working details of the driver.
* properties - Read-Only
* instance_info - Project Admin/Project Member Read-Write
* instance_uuid - Read/Write for Project Admin/Project Member
* chassis_uuid - Returns None
* extra - Project Admin/Project Member Read-Write
  .. TODO:: another reason to remove old vif handling logic is the extra field.
* console_enabled - Project Admin/Project Member Read/Write
* raid_config - Read-Only
* target_raid_config - Read-Only
* clean_step - Read-Only
* deploy_step - Read-Only
* links - Read-Only
* ports - Read-Only
* portgroups  - Read-Only
* resource_class - Read-Only
* boot_interface - Read-Only
* console_interface - Read-Only
* deploy_interface - Read-Only
* inspect_interface - Read-Only
* management_interface - Read-Only
* network_interface - Read-Only
* power_interface - Read-Only
* raid_interface - Read-Only
* rescue_interface - Read-Only
* storage_interface - Read-Only
* traits - Read-Only
* vendor_interface - Read-Only
* conductor_group - Returns None/Read-only
* protected - Read/Write
* protected_reason - Read/Write
* owner - Read-Only and lessee will be able to see the owner ID.
* lessee - Project Admin/Project Member Read-Write. Lessee will be forbidden
  from changing the field value.
* description - Read-Write
* conductor - Returns None as it provides insight into the running
  infrastructure configuration and state, i.e. System visible is the
  only appropriate state.
* allocation_uuid - Read Only

Special areas:

volume - This represents volume targets and connectors. All values
         visible through this path should be read-only. Connector logic
         should be read/write accessible to Project Admins or Project
         members where applicable, however additional logic checks
         need to exist under the hood to validate permission access
         for the project and user.
state - This is the entry path towards changing state, indicators,
        provisioning, etc. This should be permitted for Project
        Admin or Project Member IF it maps the associated owner or
        lessee field.
vendor_passthru - Vendor passthrough will not be available to project
                  scoped users in the RBAC model.

.. note:: All fields that are scrubbed, i.e. set to None or {} are expected
          to be read-only fields to project scoped accounts in the new
          RBAC model.

Client (CLI) impact
-------------------

"openstack baremetal" CLI
~~~~~~~~~~~~~~~~~~~~~~~~~

None anticipated.

"openstacksdk"
~~~~~~~~~~~~~~

None anticipated.

RPC API impact
--------------

At this time, no impact to the RPC API is anticipated. That being said
the possibility does exist, given the nature of the security changes,
some changes may be required should an additional argument be required.
Existing patterns already exist for this and any such changes would be
navigated with the existing rpc version maximum and pin capability.

Driver API impact
-----------------

None.

Nova driver impact
------------------

We may wish to go ahead and establish the ability for nova to store the
user's project ID in the node ``lessee`` field. In the new use model,
this would allow a more "natural" use pattern and allow users to be able
to leverage aspects like power operations or reboot or possibly even rebuild
of their deployed instances.

.. TODO:: We should discuss this further. It likely just ought to be a
   knob for nova-compute with the Ironic virt driver.

Ramdisk impact
--------------

None anticipated as the existing heartbeat and lookup resources of the
API would not be modified.

Security impact
---------------

The overall goal of the Secure RBAC work is to enable and allow an operator
to be able to run a service in a more restrictive and constrained model
where greater delineation exists between roles.

In a sense, the system scoped operating mode will eventually become the
normal operating mode. This is in order to encourage more secure environments,
however this will entirely depend upon the default policies *and* the
policies operators put in place which may override the default policy.
The overall goal of this specification also being to help identify the
new policy mechanics.

In order to help manage this and ensure the overall behavior is enforced
as expected, we anticipate we will need to create API behavior testing
to ensure operational security and validate that future code changes do
not adversely impact permission enforcement.

Other end user impact
---------------------

No direct end-user impact is anticipated.

Scalability impact
------------------

None.

Performance Impact
------------------

No direct performance impact is anticipated. The object model already
pushes the list filtering down to the DBAPI level, which is ideal for
overall performance handling. It is likely some additional checks will
produce a slight overhead, but overall it should be minimal and confined
to logic in the API services.

Other deployer impact
---------------------

Cloud infrastructure operators are anticipated to possibly need to adjust
``oslo_policy`` settings to enable or disable these new policies. This may
include cloud operators continuing to use older or other more restrictive
policies to improve operational security.

Developer impact
----------------

None anticipated at this time.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
    Julia Kreger (TheJulia) <juliaashleykreger@gmail.com>

Other contributors:
    Steve Baker (stevebaker) <sbaker@redhat.com>

Work Items
----------

* Creation of positive/negative policy check tests that represent the
  current interaction models.
* Creation of scoped policy definitions and associated positive/negative
  behavior tests:

  * Creation/migration of such for System-Admin where the "admin" tests
    appropriately enforce that continity is the same for a scoped admin
    as with previous tests.
  * Creation/migration of such for System-Reader where values are visible
    but not able to be written to.
  * Creation of similar for System-Member
  * Creation of similar for Project-Admin
  * Creation of similar for Project-Member
  * Creation of similar for Project-Reader

* Implementation of a CI job which operates a full integration sequence *with*
  scope policy enforcement enabled via the ``[oslo_policy]``
  configuration.
* Documentation!

Phases
------

The initial phase for deployment is scoped for the eqiuvalent of the existing
project admin scoped authentication for system scoped use.

The next phase, presumably spanning a major release would then cover the
project scoped access rights and changes.

Dependencies
============

Minimum versions of ``oslo_policy`` will need to be updated to match the
Victoria development cycle's work product, however this is anticipated
to be completed as part of the JSON to YAML policy migration effort.

Testing
=======

An CI integration job is anticipated and should be created or one already
leveraged which is utilising the widest configuration of integrated components
to ensure that policies are enforced and this enforcement works across
components. Due to the nature and scope of this effort, it may be that
Ironic alone is first setup to scope limit authorizations as other projects
also work in this direction.

Upgrades and Backwards Compatibility
====================================

Not applicable.

Documentation Impact
====================

Release note will need to be published with the prior policy deprecation
as well as primary documentation updated to reflect the scope based
configuration. An in-line documentation warning will likely be necessary
depending on what the larger community decides in terms of the RBAC policy
efforts and end-user/operator needs to be.

References
==========

* https://review.opendev.org/c/openstack/ironic/+/763255
* https://review.opendev.org/q/topic:%2522secure-rbac%2522+(status:open+OR+status:merged)+project:openstack/ironic
* http://lists.openstack.org/pipermail/openstack-discuss/2020-November/018800.html
