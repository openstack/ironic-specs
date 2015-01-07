..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

============================================
A proposal for the New Ironic State Machine.
============================================

https://blueprints.launchpad.net/ironic/+spec/new-ironic-state-machine

This blueprint suggests reworking the Ironic provisioning state machine
to fix some current shortcomings and to make it easier for drivers and
external orchestration agents to manage nodes in Ironic.

NOTE: This blueprint describes the functionality we intend the new
state machine to have.  Actual implementation of this spec, including
detailed upgrade paths and technical arcana will be handled by other
specs.

Problem description
===================

The current Ironic state machine has a few shortcomings:

* NOSTATE is a state that indicates we have no state information about a node.
  This may be fine for talking about the node's power state, but we should
  always know what provisioning state a node is in.

* We also need a state to put nodes in when they are performing configuration
  tasks that can reasonably be expected to take hours to complete, such as RAID
  configuration and burn in.  It is unreasonable to force upstream consumers of
  Ironic managed nodes to wait hours between the time they request a node and
  get it, so running these tasks as part of DEPLOYING or DEPLOYWAIT is
  nonviable.

* We also need a place to handle node decommissioning tasks.  The current
  decommissioning blueprints handle this add 'decommissioning' and
  'decommissioned' states, but it would also be useful to perform
  decommissioning tasks on freshly-added nodes.

* We also need to let external orchestration systems hook into parts of the
  state machine for each node to let them manage parts of the node life cycle
  without having to import that functionality into Ironic.  Details of
  how that will happen will be covered in a different spec.

Proposed change
===============

Current state machine::

           NOSTATE//NONE +----------+------+\     [DEPLOYWAIT//DEPLOYDONE]
                ^             R:active      +         ^
                |                           |         |
                +                           v         v
         [DELETING//DELETED]        +--->[DEPLOYING//DEPLOYDONE]
           +    ^                   |       +               +
           |    |          R:rebuild|       |               |
           v    |                   |       |               v
    ERROR//NONE |                   |       |          DEPLOYFAIL//NONE
                |                   |       v
                |                   +---+ACTIVE//NONE
                |    R:deleted              +
                +---------------------------+


Legend for the current state machine:

* [STATE] indicates an active state. Ironic is doing something to the node.
* STATE indicates a passive state. Ironic will not transition unless
  receiving a request via the API.
* R:request indicates the request which must be passed to the API to
  initiate a transition out of a passive state.

Ironic's API presents two fields for the provision_state of a node:
current and target.  Thus, in this diagram, all states are represented as
"CURRENT-slash-slash-TARGET" state.

Descriptions of the states for the current state machine can be found `here
<https://github.com/openstack/ironic/blob/stable/icehouse/ironic/common/states.py>`.

New state machine::

  ENROLL -----------> [VALIDAT*/MANAGED]
          R:validate          |
                              v
                  +------->MANAGED<-----------+
                  |        +  + ^ |           |
                  |   R:zap|  | | |R:inspect  |
                  +        |  | | |           +
         [ZAP*/MANAGED]<---+  | | +->[INSPECT*/MANAGED]
                              | |
                     R:provide| +----------+
                      +-------+   R:manage |
                      v                    +
             [CLEAN*/AVAILABLE]+------->AVAILABLE
                      ^                   +
                      |                   |R:active
                      +                   v
            [DELET*/AVAILABLE]         [DEPLOY*/ACTIVE]
                      ^                   +  ^
                      |R:delete           |  |R:rebuild
                      |                   v  +
                      +------------------+ACTIVE+-----------+
                      |                      ^              |R:rescue
                      |                      |              v
                      |                      +        [RESCU*/RESCUE]
                      |                [UNRESCU*/ACTIVE]    +
                      |                      ^              |
                      |                      |R:unrescue    |
                      |                      |              v
                      +----------------------+----------+RESCUE


Legend for the new state machine:

[STATE*/TARGET]
  STATE* indicates an active state, a momentary state, and a fail
  state. The active state has an -ING suffix, the momentary state has
  a -ED suffix, and the fail state has a -FAIL suffix.   In the active
  state, Ironic is doing something to the node.

  * If the steps taken during the active (-ING) state succeed, Ironic
    will automatically transition to the momentary (-ED) state and then
    to the next indicated state on the graph. Unless there are special
    rules for momentary states, they will not be separately described.
  * If it fails, Ironic will transition to the fail (-FAIL)
    state. Unless there are special rules for the fail state, it will
    not be separately described.

  TARGET indicates the target state that Ironic will try to
  transition the node to from the active state. TARGET must be a
  passive state.

STATE
  A passive state, usually the target of a particular set of state
  transitions. Ironic will not transition away from this state without
  an API request to do so.

R:request
  Indicates that the transition so labeled happens as a result of
  this particular API call.

Descriptions of the new states:

ENROLL
  This is the state that all nodes start off in. When a node is in
  ENROLL, the only thing Ironic knows about it is that it exists, and
  Ironic cannot take any further action by itself.  Once a node has
  its drivers and the required information for each driver in
  node.properties, the node can be transitioned to VALIDATING via the
  validate API call

VALIDATING
  Ironic will validate that it can manage the node with the drivers
  and the credentials it has been assigned.  For drivers that manage
  power state of the node, this must involve actually going out and
  confirming that the credentials work to access whatever node control
  mechanism they talk to.

MANAGED
  Once Ironic has verified that it can manage the node using the
  driver and credentials passed in at node create time, the node will
  be transitioned to MANAGED and (optionally) powered off.  From
  MANAGED, nodes can transition to:

  * MANAGED (through ZAPPING) via the zap API call,
  * MANAGED (through INSPECTING) via the inspect API call, and
  * AVAILABLE (through CLEANING) via the provide API call.

ZAPPING
  Nodes in the ZAPPING state are performing (potentially) long-running and
  destructive tasks, such as:

  * changing RAID levels,
  * updating firmware,
  * going through burn in.

  Management of tasks for ZAPPING shall be handled as outlined in `the
  zapping spec <https://review.openstack.org/#/c/102685/>`_.
  ZAPPING tasks must not rely on the information in node.properties
  being correct beyond the information that each driver needs to
  connect to the system.

ZAPFAIL
  Nodes that transition into ZAPFAIL will automatically enter
  maintenance mode, as failure to ZAP a machine usually indicates a
  hardware failure or something else that requires remote hands to fix.

INSPECTING
  INSPECTING will utilize node introspection to update
  hardware-derived node properties to reflect the current state of the
  hardware. We expect this state to get its data via the driver
  introspection interface (reference to spec forthcoming). If
  introspection fails, the node will transition to INSPECTFAIL.

CLEANING
  Nodes in the CLEANING state are being scrubbed in preparation to
  being made AVAILABLE.  Good candidates for CLEANING tasks include:

  * Erasing the drives.
  * Validating firmware integrity.
  * Verifying that the actual hardware configuration matches what is
    described in node.properties.
  * Booting to a `long running deploy ramdisk
    <https://review.openstack.org/#/c/102405/>`_, if you want the
    machine to stay on while in AVAILABLE.

  Management of CLEANING tasks should be handled in the same fashion
  as ZAPPING tasks.

  No matter what tasks are performed during CLEANING, the apparent
  configuration of the system must not change.  For instance, if you
  tear down a set of RAID volumes to securely erase each physical disk
  separately, you must rebuild the RAID volumes you tore down.

AVAILABLE
  Nodes in the AVAILABLE state are cleaned, preconfigured,  and ready
  to be provisioned. From AVAILABLE, nodes can transition to:

  * ACTIVE (through DEPLOYING) via the active API call.
  * MANAGED via the manage API call

DEPLOYING
  Nodes in DEPLOYING are being actively prepared to run a workload on them.
  This should mainly consist of running a series of short-lived tasks,
  such as:

  * Setting appropriate BIOS configurations
  * Partitioning drives and laying down file systems.
  * Creating any additional resources (node-specific network config, etc.)
    that may be required by additional subsystems.

  Tasks for DEPLOYING should be handled in a manner similar to how
  they are handled for ZAPPING (details to be addressed in a different
  spec).

ACTIVE
  Nodes in ACTIVE have a workload running on them.  Ironic may
  collect out-of-band sensor information (including power state)
  on a regular basis, but will otherwise leave them alone. Nodes in
  ACTIVE can transition to:

  * RESCUE (through RESCUING) via the rescue API call,
  * AVAILABLE (through DELETING and CLEANING) via the delete API call,
    or
  * ACTIVE (through DEPLOYING) via the rebuild API call.

RESCUING
  Nodes in RESCUING are being booted into a temporary operating
  environment for troubleshooting or maintenance related reasons.

RESCUE
  RESCUE exists to allow Ironic to be aware of a node that would be
  otherwise running a workload, but that is is booted into a different
  operating environment for maintenance or troubleshooting reasons.
  From RESCUE, nodes can transition to:

  * ACTIVE (through UNRESCUING) via the unrescue API call, or
  * AVAILABLE (through DELETING and CLEANING) via the delete API call.

UNRESCUING
  Nodes in UNRESCUING are being transitioned back to ACTIVE from
  RESCUE.  Ironic will unwind whatever it needed to do to get the node
  into RESCUE

DELETING
  Nodes in DELETING state are being torn down from running an active
  workload.  In DELETING, Ironic should tear down or remove any
  configuration or resources it added in DEPLOYING.

Alternatives
------------

No reasonable ones that we could think of at the summit.

Data model impact
-----------------

Under the current state machine, NOSTATE is represented by a NULL in
the database.  This will require a database migration to change all
NULLs to "AVAILABLE" along with special-case API handling during the
migration. The additional states should not require changes to the
data model.

REST API impact
---------------

We will provide the following verbs to manage the node lifecycle in
the state machine:

+-----------+--------------+--------------------------+-----------+
| Verb      | Initial State| Intermediate States      | End State |
+===========+==============+==========================+===========+
| validate  | ENROLL       | VALIDATING -> VALIDATED  | MANAGED   |
+-----------+--------------+--------------------------+-----------+
| zap       | MANAGED      | ZAPPING -> ZAPPED        | MANAGED   |
+-----------+--------------+--------------------------+-----------+
| inspect   | MANAGED      | INSPECTING -> INSPECTED  | MANAGED   |
+-----------+--------------+--------------------------+-----------+
| provide   | MANAGED      | CLEANING -> CLEANED      | AVAILABLE |
+-----------+--------------+--------------------------+-----------+
| manage    | AVAILABLE    | (none)                   | MANAGED   |
+-----------+--------------+--------------------------+-----------+
| active    | AVAILABLE    | DEPLOYING -> DEPLOYED    | ACTIVE    |
+-----------+--------------+--------------------------+-----------+
| rebuild   | ACTIVE       | DEPLOYING -> DEPLOYED    | ACTIVE    |
+-----------+--------------+--------------------------+-----------+
| rescue    | ACTIVE       | RESCUING -> RESCUED      | RESCUE    |
+-----------+--------------+--------------------------+-----------+
| unrescue  | RESCUE       | UNRESCUING -> UNRESCUED  | ACTIVE    |
+-----------+--------------+--------------------------+-----------+
| delete    | ACTIVE       | DELETING -> DELETED ->   | AVAILABLE |
|           |              | CLEANING -> CLEANED      |           |
+-----------+--------------+--------------------------+-----------+
| delete    | RESCUE       | DELETING -> DELETED ->   | AVAILABLE |
|           |              | CLEANING -> CLEANED      |           |
+-----------+--------------+--------------------------+-----------+

The API will remain backwards compatible with the active, rebuild, and
delete verbs.

Unless otherwise required for backwards compatibility, the verbs must
be called when the node is in the Initial State, and Ironic will
perform all actions and transitions needed to move through the
Intermediate States to the End State.

Since we are adding new states, older API clients may behave
unexpectedly when they encounter a node in a state they do not understand.

RPC API impact
--------------

Not as a direct impact of this spec (beyond what is mentioned in the
REST API impact section), but all the to-be-written specs which will
actually implement the new states will have significant RPC and REST
api impact.

Driver API impact
-----------------

Yes. Large swaths of driver code will need a refactor to cooperate
with the new per-node state machines.

Nova driver impact
------------------

NOSTATE has been renamed to AVAILABLE. This will require some glue
code and creating an upgrade path.

Security impact
---------------

Probably not, assuming perfect coding.

Other end user impact
---------------------

Yes.

Scalability impact
------------------

Probably nothing significant.

Performance Impact
------------------

Ditto.

Other deployer impact
---------------------

Nodes will not automatically transition from ENROLL to MANAGED.
Deployers must assign drivers and add credentials to the node and then
call the validate API before Ironic can manage the node.

Nodes will not automatically transition from MANAGED to AVAILABLE,
deployers will need to do that via the API before nodes can be scheduled.

Developer impact
----------------

Current and new Ironic drivers will need rework to comply with the new
state machine.

Implementation
==============

Assignee(s)
-----------

None yet.

Work Items
----------

Specs need written to hash out the implementation details that the new
state machine implies.

Dependencies
============

Most every blueprint that touches on the Ironic drivers will be
affected, but this blueprint is vendor-agnostic.

Testing
=======

None for this spec, but the implementation specs will need to address
testing impacts of the changes they recommend.

Upgrades and Backwards Compatibility
====================================

None for this spec, but the implementation specs will need to address
upgrade and backwards compatibility.

Documentation Impact
====================

This spec should be used as initial documentation for the new state machine.


References
==========

Anyone have a link to some developer session notes?  I was sorta busy
being a whiteboard monkey:  https://i.imgur.com/tCxUCYk.jpg
