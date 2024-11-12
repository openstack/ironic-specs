..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=========================================
Modifying Active Nodes with Service Steps
=========================================

https://storyboard.openstack.org/#!/story/2010647

A reality in the operation of systems is that sometimes things need to
be changed. An additional unfortunate reality is that the closer we get
to the underlying infrastructure, the greater the burden it is to take a
model of "just redeploy with new settings".

Unfortunately, Ironic has limited options in this area for infrastructure
operators who wish to automate activities such as "upgrading firmware",
or "changing low level settings" when a system is already deployed.
Today they can possibly leverage the **rescue** process, but that also
means they have to articulate everything after the rescue process had
completed.

Yet Ironic also has quite a bit of tooling to enable settings to be
changed as well as firmware upgraded as part of cleaning and deployment,
and we should provide capability to leverage this tooling on a node in
an **active** state.

Problem description
===================

Deployed systems need to be able to be changed or evaluated:

* Firmware settings and software sometimes need to be modified or updated.

* The introduction of "data processing units" (the further evolution of
  SmartNICs) with full operating systems, means additional maintenance actions
  can arise, and direct access to the device may not be feasible.

* Security Operations teams sometimes need to be able to inspect the
  state of the hardware and software from an "out of bands" process,
  which may result in the hardware being removed from inventory, or returned
  to a running state if no issue are detected.

* Operations teams needing to test the Memory, CPU, or Network in order to
  identify an issue or address a customer concern.

In these cases, it may be that hardware managers and/or vendor driver
methods can facilitate some of the operator required actions. In other cases,
it may require additional tools that may not be suitable to install under
"normal" conditions.

Proposed change
===============

The implementation of a capability to take a node in an **active** state,
execute steps and return the node to an **active** state, as well as a
standing state to allow operators to perform their other needful actions.

To do this, we will implement a **service** API verb which will move a node
into a **servicing** state, in line with the existing cleaning and deploy
processes. The IPA ramdisk will be booted, and the node will enter a
**service wait** state.

Once IPA is online, two possible paths can be taken.

If the **service** verb was invoked with with a ``service_steps`` parameter,
in the same line of ``clean steps``, then the node state will return to the
**servicing** state, heartbeat, and upon all steps completed, the node will
automatically return to the **active** state.

To achieve this, we will also need to:

* Add an additional ``service_step`` field to the Node object. Similar to clean
  steps, a ``service_steps`` entry would also be utilized in the node
  ``driver_internal_info`` field.

* Increment the API version.

* Introduction of a ``unhold`` provision state verb to allow resumption of
  step processing/execution.

* Make appropriate decorator modifications in alignment with deploy steps and
  cleaning steps, which would also be in line with existing deployment
  and cleaning steps.

* Introduction of, or modification of existing housekeeping periodic steps
  to include handling for the newly proposed states. In particular,
  modification is preferred from a database efficiency standpoint, however
  it is ultimately the implementer's prerogative.

In terms of ramdisk usage, the existing ``deploy_kernel`` and
``deploy_ramdisk`` will be used by default for this feature, however
a ``service_kernel`` and ``service_ramdisk`` will also be available as
an override.


To facilitate a handoff or pause/resumption operation, we will introduce two
explicit steps into the step process.

* ``hold`` - This step would hold execution of steps on the current node in
  it's current state unless an ``unhold`` command has been issued, or a new
  set of steps have been received.

* ``pause`` - This step would pause the step execution for a user defined
  period of time. Think of this as "sleep". In all likelihood, this step is
  likely to be constrained with a maximum sleep period of the heartbeat
  window.

* ``wait`` - This step would allow an operator tell Ironic to wait for a
  condition to be met before proceeding with steps. This may be a file
  to appear on the agent, or for a agent local command to execute
  successfully. This step is likely to actively await a true condition
  to be met, which for logical reason would allow automatic resumption.
  For example an async firmware step which needs to be waited upon.

These temporary holding states, when used, will take a case appropriate
path, such as with hold, the node will move to a ``clean hold``,
``deploy hold``, or in this specification's case, ``service hold`` state.
Pause and wait, actions will be situational and will likely be treated
as transitory within to be determined constraints.

As for hold, a conductor failover is not anticipated to be fatal to this
in the long term, as long as the agent continues to heartbeat. An
``unhold`` provision_state action is expected to just remove the current
step name in progress, allowing the next step to proceed upon next heartbeat.

.. NOTE:: Ironic *might* need a step which enables the agent token to be
   removed to allow the agent to be restarted or rebooted. This is not
   anticipated to be a feature, but shouldn't be controversial if deemed
   needed soon afterwards.

Alternatives
------------

One possible alternative appears to be continue and encourage the use of
the rescue framework, which is not ideal and has no capability for step
execution, meaning any action taken would need to be manually composed and
executed externally. Of course, this is possible today to partly achieve
the same basic effect. Rescue itself helped inspire this overall
specification as a superset of functionality.

Another possibility could be to extend the existing rebuild verb to allow
steps to be passed in a non-destructive, non-redeploy scenario. However
the rebuild verb has always suggested "re-deployment", and separating that
identity might prove difficult and time consuming to deliver only part
of the needful functionality. Contributors are not convinced this is even
a viable alternative and have also noted concerns of operator confusion,
resulting in this being a further unlikely alternative.

Data model impact
-----------------

Addition of a new ``node`` field ``service_step``, which will require a new
column to be added to the database, however that is a relatively low impact
database change. This field will not be indexed.

Use of subfield values **driver_internal_info['service_steps']** and
**driver_internal_info['service_step_index']**.

State Machine Impact
--------------------

New states will be added to the state machine:

+---------------------+-------------------------------------------------------+
| State               | Description                                           |
+---------------------+-------------------------------------------------------+
| states.SERVICING    | Modifying "unstable" state indicating a lock is held  |
|                     | and action is occurring.                              |
+---------------------+-------------------------------------------------------+
| states.SERVICEWAIT  | An intermediate unstable state where Ironic is        |
|                     | waiting for an action such as a `heartbeat`           |
|                     | from the agent to begin.                              |
|                     | begin.                                                |
+---------------------+-------------------------------------------------------+
| states.SERVICEFAIL  | An error state to indicate there was an error in the  |
|                     | process of handling the request. This is a stable     |
|                     | state until the operator removes the node from it.    |
|                     | This could be a result of any failure in any service  |
|                     | or unservice process.                                 |
+---------------------+-------------------------------------------------------+
| states.SERVICEHOLD  | A stable state for nodes being held in a state based  |
|                     | upon use of the ``hold`` step. Removal of the node    |
|                     | from the hold state would involve the ``unhold``      |
|                     | provision state verb.                                 |
+---------------------+-------------------------------------------------------+

The general flow will be:

  **ACTIVE** -> **SERVICING** -> **SERVICEWAIT** -> **SERVICE**

In the case of an automated flow:

  **ACTIVE** -> **SERVICING** -> **SERVICEWAIT** -> **SERVICING** ->

In the event that the a user determines they need to stage actions, a service
step should be able to be called while already in the service state.

  **SERVICE** -> **SERVICING** -> **SERVICEWAIT** -> **SERVICE**

In the caes of entirely conductor side modifications, such as Out-of-Band
firmware updates being applied:

  **ACTIVE** -> **SERVICING** -> **ACTIVE**

In the event of an error, the operation can be retired or the node
returned to an *active* state:

  **SERVICING** -> **SERVICEFAIL** -> **ACTIVE**
  **SERVICING** -> **SERVICEFAIL** -> **SERVICING**

To facilitate the workflow enhancements related to this, additional states
will be added for alignment with existing step framework changes.

+---------------------+-------------------------------------------------------+
| State               | Description                                           |
+---------------------+-------------------------------------------------------+
| states.DEPLOYHOLD   | A hold state to allow use for the ``hold`` step name  |
|                     | to allow cross-step framework capabilities.           |
+---------------------+-------------------------------------------------------+
| states.CLEANHOLD    | An identical state with different state name to the   |
|                     | previously indicated ``deploy hold`` state.           |
|                     | The delineated names in large part to prevent         |
|                     | confusion and the need for additional logic for       |
|                     | ``target_provision_state``.                           |
+---------------------+-------------------------------------------------------+

In addition to these new states, new state verbs are anticipated:

* service - The verb to trigger service steps framework.
* unhold - The verb to trigger release of a holding state and enable
  steps to continue to execute.

In the process of moving back from a service state, the node will have a boot
to the default boot device if the ramdisk is booted in the process of
of executing the service request.

REST API impact
---------------

In line with existing community practice in regards to the node's provision
state field, the contents of the ``provision_state`` field will not be version
guarded.

.. NOTE::
   While this seems like a potentially breaking change, we have only done this
   when we've renamed or changed the overall meaning of a state. i.e.
   None -> Available and Inspect Wait -> Inspecting for older API clients.
   In other words, these being net-new should not be breaking.

.. NOTE::
   Nova impact is covered below.

The ability to submit the new provision state verbs to the API will be
version guarded, and the payload of the new ``service_steps`` will align
with existing ``clean_steps`` and ``deploy_steps`` through use of a JSON
payload. Ability to process the request will also be dependent upon the
RPC version in use.

A corresponding API client change will also be required, and an RBAC policy
will also be added to allow for restriction of the service verb, as project
scoped ``lessee-admin`` users are able to issue provision state changes.
The access scope for the rule is anticipated to be restricted to appropirate
system scoped and project scoped owner roles, in line with the existing
policy alias of ``SYSTEM_MEMBER_OR_OWNER_ADMIN``.

Client (CLI) impact
-------------------

"openstack baremetal" CLI
~~~~~~~~~~~~~~~~~~~~~~~~~

Addition of a ``baremetal node service`` and ``baremetal node unservice``
commands will need to be added to the client.

"openstacksdk"
~~~~~~~~~~~~~~

The ``set_provision_state`` method in OpenStackSDK's will need an additional
argument to enable passing through service steps.

RPC API impact
--------------

A new ``do_node_service`` RPC method will be required which will also require
the RPC interface version to be incremented.

The act of removing a node from the service state is anticipated to use the
``do_provision_action`` RPC method, but the API may need to validate the
running RPC version before making the call.

Because of this addition, both services will need to be upgraded before this
feature can be utilized.

Driver API impact
-----------------

Decorators will need to be added/modified to enable the steps to be
appropriately validated and invoked when the feature is needed. No other
driver API changes are anticipated. It should be noted this is not a breaking
change, we only note it because it will need to be performed on relevant
actions/steps.

Nova driver impact
------------------

A review of Nova's virt/ironic/driver.py code suggests that no impact is to
be anticipated through the introduction of new states as they are ignored.
As such, considering our practice of not concealing new states behind API
version changes when not impacting to Nova, we believe no additional handling
will be needed.

We *may* want to introduce a version guard to return a VirtDriverNotReady
exception should an action such as unprovisioning or vif actions are attempted
by a Nova user while the baremetal node is in one of these states, as this is
a generally non-fatal "not ready at the moment" exception, but that should be
further discussed with the Nova team.

Ramdisk impact
--------------

A ``get_service_steps`` and ``execute_service_step`` methods are anticipated
as being needed to support this functionality in the agent. A lack of these
agent side commands are not to be considered faults.

It is expected that we would likely want the agent to just to continue to
heartbeat while waiting for work to do, which is not breaking for older
versions of the agent.

Security impact
---------------

A potential security impact exists in that under Ironic's default security
model, a lessee admin is able to trigger provision state changes. It *is*
an operationally valid use case to permit a lessee, at least a lessee who
was manually assigned, to be able to service firmware as long as it is inline
with "approved" and "known" versions.

It might be best to drive forward keylime integration as well, as well as
place a policy rule on use of the service verb.

.. NOTE:: We may wish to consider permitting the agent to heartbeat and
   the callback URL if it has been moved to a different network. This does
   have a security impact, but would allow fast-track to be applied on a
   more consistent basis.

Other end user impact
---------------------

None

Scalability impact
------------------

To reconcile errors, it may be necessary to introduce an additional periodic
task in order to identify failures. Beyond this potential additional periodic
state, no scalability impact is anticipated.

Performance Impact
------------------

No performance impact is anticipated.

Other deployer impact
---------------------

This feature acknowledges and encourages operators to integrate in
ways that recognize we may not be the driver of the workflow, but that
the node needs to be put into a particular state before proceeding.

With that being said, no direct deployer impact is anticipated, but operators
will likely need and anticipate quite a bit of information to appropriately
explain the feature, and how they can leverage it to both automate their
workflows and have a consistent operational experience.

Developer impact
----------------

None anticipated.

Implementation
==============

Assignee(s)
-----------

.. todo::
   Volunteers? Happy to hack on this if I can get people to commit to review.

Primary assignee:
  <IRC handle, email address, or None>

Other contributors:
  <IRC handle, email address, None>

Work Items
----------

* Add ``service_step`` to the node object model and database.
* Update the state machine configuration
* Add step retrieval methods to the agent.
* Add conductor internal methods for triggering state actions and calls.
* Add agent client method call to retrieve a list of steps from the agent.
* Add an agent client method call to re-trigger DHCP of the agent as a service
  step as well.
* Add RPC method for service action.
* Add API support for service verb.
* Add networking internals to place the machine on to a
  valid network for the service operations.
* Decorate appropriate step actions as "service steps".
* Compose tempest test schenario.

Dependencies
============

None

Testing
=======

A tempest scenario test for this will be needed. It is expected that a test
scenario will exercuse one of the ``pause``, ``wait``, or ``hold`` steps.

Upgrades and Backwards Compatibility
====================================

No additional upgrade or compatibility issues are anticipated aside from
what has already been noted and explored in this document.

Documentation Impact
====================

Our "admin" documentation will need an additional section added to cover this
feature, much as other major features have needed in the past.

References
==========

* https://specs.openstack.org/openstack/ironic-specs/specs/11.1/deployment-steps-framework.html
* https://specs.openstack.org/openstack/ironic-specs/specs/16.0/in-band-deploy-steps.html
* https://specs.openstack.org/openstack/ironic-specs/specs/10.1/implement-rescue-mode.html
