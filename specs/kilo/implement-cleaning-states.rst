..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Implement Cleaning States
==========================================

https://blueprints.launchpad.net/ironic/+spec/implement-cleaning-states

When a node has finished a workload, driver interfaces should have the
opportunity to run a set of tasks immediately after tear down and before the
node is available for scheduling again.


Problem description
===================

* When hardware is recycled from one workload to another,
  there should be some work done to it to ensure it is ready for another
  workload. Users will expect each baremetal node to be the same.
  Applying these baseline tasks will ensure a smoother experience for end
  users.

* These steps can also be performed (if enabled) on newly enrolled nodes moving
  from MANAGED to AVAILABLE.

* These baseline tasks should be any task that a) prepares a node for being
  provisioned to, including making it consistent with other nodes and b)
  doesn't change the apparent configuration of the machine.

* At a minimum, hard drives should be erased (if enabled)

* Other potentially useful tasks would be resetting BIOS, applying BIOS
  settings (uniform settings for all nodes, rather than individually on each
  node), validating firmware integrity and version, verifying hardware matches
  the node.properties, and booting long running agents [2].

* Some users will require certain security measures be taken before a node
  can be recycled, such as securely erasing disks, which can be implemented
  using custom hardware managers in the Ironic Python Agent or with out of
  band systems that support it.

* The current PXE ramdisk would support a limited subset of cleaning
  steps, such as erase_devices(). Steps such as verifying the node's properties
  will require cooperation of the BMC, Ironic Python Agent, or additions to
  the current ramdisk.

Proposed change
===============

* The cleaning features will be added behind a config option, to ensure
  operators have the choice to disable the feature if it is unnecessary for
  their deployment. For example, some operators may want to disable cleaning
  on every request and only clean occasionally via ZAPPING.

* Add a decorator `@clean_step(priority)` to decorate steps that
  should be run as a part of CLEANING. priority is the order in which the
  step will be run. The function with the highest priority will run first,
  followed by the one with the second highest priority, etc. If priority is
  set to 0, the step will not be executed. The argument should be a config
  option, e.g. `priority=CONF.$interface.$stepname_priority` to
  give the operator more control over the order steps run in (if at all).

* Add a new function `get_clean_steps()` to the base Interface classes. The
  base implementation will get a list of functions decorated with
  `@clean_step`, determine which are enabled, and then return a list of
  dictionaries representing each step, sorted by priority.

* The return value of `get_clean_steps()` will be a list of dicts
  with the 3 keys: step, priority and interface, described below:

      * 'step': 'function_name',

      * 'priority': 'an int or float, used for sorting, described below',

      * 'interface': 'interface_name

  Only steps with a priority greater than 0 (enabled steps) will be returned.

* Add a new function `execute_clean_step(clean_step)` to the base Interfaces,
  which takes one of the dictionaries returned by `get_clean_steps()` as an
  arg, and execute the specified step.

* Create a new function in the conductor: `clean(task)` to run all
  enabled clean steps. It will get a list of all enabled
  steps and execute them by priority. The conductor will track the current
  step in a new field on the node called clean_step.

* In the event of a tie for priority,
  the tie breaker will be the interface implementing the function, in the order
  power, management, deploy interfaces. So if the power and deploy interface
  both implement a step with priority 10, power's step will be executed first,
  then the deploy interface's step.

* If there is a tie for priority within a single interface (an operator
  inadvertently sets two to the same priority), the conductor will fail
  to load that interface while starting up, and log errors about the
  overlapping priorities.

* Using CLEANING, CLEANED, and CLEANFAIL that will be added in the
  new state machine spec [1]. These states occur between DELETED and AVAILABLE.
  This will prevent Nova delete commands from taking hours.

* CLEANED will be used much like DELETED: generally as a target provision
  state. A node will be in CLEANED state after CLEANING completes and until the
  conductor gets a chance to move it to AVAILABLE.

* Nodes may be put into CLEANING via an API call (described below) only
  from MANAGED or CLEANFAIL states. MANAGED allows an operator to clean a node
  before it is available for scheduling. This ensures new nodes are at the same
  baseline as other, already added nodes.

* The ZAPPING API will allow nodes to go through a single or list of
  clean_steps from the MANAGED state. These will be operator driven steps via
  the API, as opposed to the automated CLEANING that occurs after tear_down
  described in this spec.

* Make the Nova Virt Driver look for CLEANING, CLEANED, and CLEANFAIL states
  in _wait_for_provision_state() so the node can be removed from a users list
  of active nodes more quickly. Failures to clean should not be
  errors for the user and need to be resolved by an operator.

* If a clean fails, the node will be put into CLEANFAIL state,
  have last_error set appropriately, and be put into maintenance.
  The node will not be powered off,
  as a power cycle could damage a node. The operator can then fix the node,
  and put the node's target_provision_state back to CLEANED via the API to
  retry cleaning or skip to AVAILABLE.

* CLEANING will not be performed on rebuilds.

Alternatives
------------

* The interfaces could implement this in tear_down only. It would be slower
  from a user perspective.

* Most of these actions could be taken during deploy. This would
  significantly lengthen the amount of time to deploy in some cases
  (especially with spinning disks)

Data model impact
-----------------

* node.clean_step will be added as a dict or None field to track which
  step is currently being performed on the node. This will give the operator
  more visibility into what a node is doing and allow conductor fail overs
  during CLEANING to be more simply implemented.

* If a cleaning step needs to store additional information, it should use
  node.driver_info. For example, the agent interface will store the IPA
  hardware manager version in driver_info, so it can detect changes and restart
  cleaning if a new hardware manager is deployed during a cleaning cycle.

REST API impact
---------------

* The API will be changed to prevent changing power state or provision state
  while the node is in a CLEANING state. A node in CLEANFAIL
  state may be powered on and off via the API, because the operator will
  likely need to restart the node to fix it.

* The API will allow users to put a node directly into cleaning
  provision_state with a POST, the same as how provision state is changed
  anywhere else in Ironic.
  This can be useful for verifying newly added nodes or if
  an operator wants to put a fleet of inactive servers into a known state. A
  node can only be put into CLEANING state from MANAGED or
  CLEANFAIL states.

* Nodes in CLEANFAIL may be put into CLEANING or AVAILABLE state,
  as determined by the operator.

* An API endpoint should be added to allow operators to see currently
  enabled clean steps and their ordering. This will be a GET endpoint
  at /nodes/<uuid>/cleaning/steps and will return the exact
  data noted above for `get_clean_steps()`, as a JSON document and ordered
  by priority.

* GET requests to the node's API
  (/nodes/<uuid>) and node detail API (/nodes/details) should return the
  current node.clean_step as well.

RPC API impact
--------------

Cleaning of a node will need to be available via RPC, so the API servers
can put a node into CLEANING from MANAGED or CLEANFAIL states.

At the end of a tear down, the conductor will RPC call() the do_node_clean()
method of the conductor.

As the states will first be added as no-ops in the new state machine spec,
upgrading won't be a problem.


Driver API impact
-----------------


* The BaseDriver will have a `get_clean_steps()` and
  `execute_clean_steps()` functions added and implemented.

  ..

  def get_clean_steps(task):
    """Return the clean steps this interface can perform on a node"""

    :param task: a task from TaskManager.
    :returns: a list of dictionaries as noted above

  ..

  def execute_clean_steps(task, step):
    """Execute the given clean step on the task.node"""

    :param task: a task from TaskManager.
    :param step: a step from get_clean_steps()
    :raises CleanStepFailed: if the step fails

* Testing will be similar to other driver interfaces and each interface will be
  expected to test their implementation thoroughly.

* Existing interfaces can choose to not implement the new API with no effect,
  as they will be added in the base classes.

Nova driver impact
------------------

* Nova driver will look for the clean states when determining if
  unprovisioning succeeded or not.

* If Nova is upgraded first, nothing will change. The driver will continue
  to be in the tear_down state until the node goes to AVAILABLE.

Security impact
---------------

* Security will be improved by adding erasing of disks [3].

* It should be noted in documentation that there are still attack vectors if
  baremetal nodes are given to untrusted users or if a baremetal node is
  compromised.

* If the API is called to set a node into a clean state,
  that node could be tied up for potentially hours. If run against enough
  nodes in a cluster by a bad actor, the cluster could run out of capacity
  quickly. These APIs by default require admin privileges. However, a user
  could provision and unprovision nodes quickly, leading to a denial of
  service. Quotas could mitigate this issue.

Other end user impact
---------------------

None

Scalability impact
------------------

None

Performance Impact
------------------

* There will be additional calls to the hardware to perform the
  cleaning steps. The steps could take hours,
  which will mean the time to recycle could be much higher than before.

* The node will be locked for the duration of the clean.

* Database calls will increase, because the state is saved after each
  cleaning step that requires a reboot or long running process, as well
  as saving the current clean_step before it begins execution of the step.

* Rebalances, in the worst case, will require the node to redo one step
  based on the cleaning_step. This
  could happen if a conductor dies while it owns a node that is doing a long
  running process. clean_steps should be implemented as idempotent
  actions, to avoid issues here.

Other deployer impact
---------------------

* Deployers will need to inspect which clean steps are being performed and
  adjust whether each step is performed and at what priority if the defaults
  don't work for their environment.

* If Ironic is updated first, nodes that are torn down may take additional
  time and will likely time out in unprovision. This would only happen if
  Ironic was updated before Nova, and a interface that implements clean
  which takes a large amount of time was enabled and used. This will need
  to be documented.

Developer impact
----------------

* Drivers will need to call any functions they deem necessary to
  clean a node, and possibly implement those functions. They may add
  config options to enable or disable those features.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  JoshNang

Other contributors:
  jroll
  JayF

Work Items
----------

* Add clean() to the conductor

* Add get_clean_steps() and execute_clean_step() to the
  BaseDriver interface.

* Add @clean_step() decorator

* Add API checks for clean states and allow "CLEANED" as a
  provision target state

* Add API end point /nodes/<uuid>/cleaning/steps

* Add support for erase_disks in PXE interface

* Add cleaning support to IPA

* Add Nova driver support

Dependencies
============

* Ironic State Machine: https://review.openstack.org/#/c/133828/. Both
  are attempting to add CLEANING/CLEANED/CLEANFAIL. If this is implemented
  without a new clean state, users will see a node in "deleting" state in Nova
  for potentially hours, eating up quota.

* Not required, but would be helpful: External event callback API would be
  helpful for the Agent deploy interface (and  probably others') implementation
  of clean: https://review.openstack.org/#/c/99770/.


Testing
=======

* Tempest will have to be adapted to support running a clean as part
  of its normal provision/unprovision tests.

* Drivers implementing cleaning will be expected to test their added
  features.


Upgrades and Backwards Compatibility
====================================

* The changes to the REST API to allow a node to go from MANAGED or CLEANFAIL
  to CLEANED will require the user to specify the new state:
  CLEANED. Therefore, it shouldn't break backwards compatibility. The
  only change existing users/tools may see is an extended period where nodes
  are unable to be powered off via the API.

Documentation Impact
====================

* There should be very clear documentation about how cleaning works, how the
  steps are ordered, what they do, and how operators can enable, disable, and
  reprioritize them. This is essential for operators to understand if they
  are going to use cleaning. The differences in between interfaces for cleaning
  will also need to be spelled out.

* The Ironic driver interface changes, the Nova driver support and changes to
  Ironic API will need to be documented.

* We should document the security problems that still exist, even with cleaning
  enabled.


References
==========

1: https://github.com/openstack/ironic-specs/blob/master/specs/kilo/new-ironic-state-machine.rst

2: https://review.openstack.org/#/c/102405/

3: https://bugs.launchpad.net/ironic/+bug/1174153
