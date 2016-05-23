..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===============
Manual cleaning
===============

https://bugs.launchpad.net/ironic/+bug/1526290

Manual cleaning (as opposed to automated cleaning) encompasses all long
running, manual, destructive tasks an operator may want to perform either
between workloads, or before the first workload has been assigned to a node.

This feature had previously been called `"Zapping"
<https://review.openstack.org/#/c/185122/>`_ and this specification copies
a lot of the zapping specification. (Thank you Josh Gachnang!)


Problem description
===================

`Automated cleaning <http://specs.openstack.org/openstack/ironic-specs/specs/kilo-implemented/implement-cleaning-states.html>`_
has been available in ironic since the kilo cycle. It lets operators
choose which clean steps are automatically done prior to the first
time a node is deployed and each time after a node is released.

However, operators may want certain operations or tasks to only run on demand,
rather than in every clean cycle. Things like firmware updates, setting up new
RAID levels, or burning in nodes often need to be done before a user is given
a server, but take too long to reasonably do at deploy time.

Many of the above tasks could provide useful scheduling hints to nova once
hardware capabilities are introduced. Operators could use these scheduling
hints to create flavors, such as a nova compute flavor that requires a node
with RAID 1 for extra durability.


Proposed change
===============

Instead of adding new ZAP* states to the state machine to distinguish between
manual and automated cleaning, the existing CLEAN* states and cleaning
mechanism will be reused for both automated and manual cleaning.
The main differences will be:

* manual cleaning can only be initiated when a node is in the MANAGEABLE state.
  Once the manual cleaning is finished, the node will be put in the
  MANAGEABLE state again.

* operators will be able to initiate a manual clean via the modified API
  to set the nodes's provision state. Details are described in the
  `PUT .../states/provision <#put-v1-nodes-node-ident-states-provision>`_
  section below.

* A manual clean step might need some arguments to be specified. (This might
  be useful for future automated steps too.) To support this, the
  ironic.drivers.base.clean_step decorator will be modified to accept a list
  of arguments. (Default is None.) Each argument is a dictionary with:

  * 'name': <name of argument>
  * 'description': <description>. This should include possible values.
  * 'required': Boolean. True if this argument is required -- it must be
    specified in the manual clean request; false if it is optional.

* add clean steps to drivers that will only be used by manual cleaning. The
  mechanism for doing this exists already. Driver implementors only need to
  use the @clean_step decorator with a default cleaning priority of 0. This
  will ensure the step isn't run as part of the automated cleaning. The
  implementor can specify whether the step is abortable, and should also
  include any arguments that can be passed to the clean step.

* operators will be able to get a list of possible steps via an API. The
  `GET .../cleaning/steps <#get-nodes-node-ident-cleaning-steps>`_ section
  below provides more information.

* similar to executing automated clean steps, when the conductor attempts to
  execute a manual clean step, it will call execute_clean_step() on the driver
  responsible for that clean step.

* to avoid confusion, the 'clean_nodes' config will be renamed to
  'automated_clean_enable' since it only pertains to automated cleaning.
  The deprecation and deletion of the 'clean_nodes' config will follow
  ironic's normal deprecation process.

Alternatives
------------

* We could make manual clean steps and automated clean steps mutually
  exclusive with separate APIs and terminology and mechanisms to use, but
  conceptually, since they are all clean steps it is less confusing to
  provide a similar mechanism for both.

* We could have called 'manual clean' something else like 'zap' to avoid
  having to distinguish between 'manual' and 'automated' cleaning, but
  it seems more confusing to describe the differences between 'zap' and 'clean'
  and that confusion and complexity is apparent when trying to implement it
  that way.


Data model impact
-----------------

None.


State Machine Impact
--------------------

This:

* removes all mention of 'zap' and the ZAP* states from the `proposed
  state machine <http://specs.openstack.org/openstack/ironic-specs/specs/kilo-implemented/new-ironic-state-machine.html>`_

* adds two new transitions:

  * MANAGEABLE -> CLEANING via 'clean' verb, to start manual cleaning
  * CLEANING -> MANAGEABLE via 'manage' verb, to end a successful manual clean


REST API impact
---------------

PUT /v1/nodes/<node_ident>/states/provision
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This API will allow users to put a node directly into CLEANING
provision state from MANAGEABLE state via 'target': 'clean'.
The PUT will also require the argument 'clean_steps' to be specified. This
is an ordered list of clean steps, with a clean step being represented as a
dictionary encoded as JSON.

As an example::

  'clean_steps': [{
      'interface': 'raid'
      'step': 'create_configuration',
      'args': {'create_nonroot_volumes': False, // optional keyword argument
               ... }               // more keyword arguments (if applicable)
    },
    {
      'interface': 'deploy'
      'step': 'erase_devices'
    }
  ]

In the above example, the driver's RAID interface would configure hardware
RAID without non-root volumes, and then all devices would be erased
(in that order).

A clean step is represented by a dictionary (JSON), in the form::

  {
      'interface': <interface>,
      'step': <name of clean step>,
      'args': {<arg1>: <value1>, ..., <argn>: <valuen>}
  }

The 'interface' and 'step' keys are required for all steps. If a step
takes additional keyword arguments, the 'args' key may be specified. It
is a dictionary of keyword arguments, with each keyword-argument entry being
<name>: <value>.

If any step is missing a required keyword argument, no manual cleaning will be
performed and the node will be put in CLEANFAIL provision state with an
appropriate error message.

If, during the cleaning process, a clean step determines that it has incorrect
keyword arguments, all earlier steps will be performed and then the node will
be put in CLEANFAIL provision state with an appropriate error message.

A new API version is needed to support this.


GET /nodes/<node_ident>/cleaning/steps
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We had planned on having an API endpoint to allow operators to see the
clean steps for an automated cleaning. That proposed API had been
GET /nodes/<node_ident>/cleaning/clean_steps, but it hasn't been
implemented yet.

With the introduction of manual cleaning, instead of
GET /nodes/<node_ident>/cleaning/clean_steps, this proposes replacing that
with the API endpoint GET /nodes/<node_ident>/cleaning/steps. By default, it
will return all available clean steps (with priorities of zero and non-zero),
for both manual and automated cleaning.

An optional field 'min_priority' can be specified to filter for clean
steps with priorities equal to or above the specified minimum value.
For example, to only get clean steps for automated cleaning (not manual)::

    GET http://127.0.0.1:6385/v1/nodes/my-awesome-node/cleaning/steps?min_priority=1

The response to this request would be a list of clean steps sorted in
decreasing priorities, formatted as follows::

  [{
    // 'interface': is one of 'power', 'management', 'deploy', 'raid'.
    // 'step': is an opaque identifier used by the driver. Could be a driver
    //         function name or some function in the agent.
    // 'priority': is the priority used for determining when to execute
    //             the step; larger values have higher priority.
    // 'abortable': True if cleaning can be aborted during execution of this
    //              step; False otherwise.
    'interface': 'interface',
    'step': 'step',
    'priority': Integer,
    'abortable': Boolean

    // 'args': a list of keyword arguments that may be included in the
    //         'PUT /v1/nodes/NNNN/states/provision' request when doing
    //         a manual clean. An argument is a dictionary with:
    //           - 'name': <name of argument>
    //           - 'description': <description>
    //           - 'required': Boolean. True if required; false if optional
    'args': []
   },
   ... more steps ...
  ]

An example with a single step::

  [{
    'interface': 'raid',
    'step': 'create_configuration',
    'args': [{'name':'create_root_volume',
              'description':'Set to True (the default) to create root volume
                             specified in the node's target_raid_config. False
                             prevents the root volume from being created.',
              'required':False},
             {'name':'create_nonroot_volumes',
              'description':'Set to True (the default) to create non-root
                             volumes that may be specified in the node's
                             target_raid_config. False prevents non-root
                             volumes from being created.',
              'required':False}]
    'priority': 0,
    'abortable': True
  }]

If the driver interface cannot synchronously get the list of clean steps,
for example, because a remote agent is used to determine available clean
steps, then the driver MUST cache the list of clean steps from the most
recent execution of said agent and return that. In the absence of such data,
the driver MAY raise an error, which should be translated by the API service
into:

  * an HTTP 202

  * a new (we created this) HTTP header 'Retry-Request-After', indicating
    to the client how long in seconds the client should wait to retry. A '-1'
    indicates that it is unknown how long to wait. This might happen for
    example when the request is made when a node is in ENROLL state. At this
    point it is unknown when the remote agent will be available on the node
    for querying.

  * a body with a message indicating that the data are not available yet.

If the driver interface can synchronously return the clean steps without
relying on the hardware or a remote agent, it SHOULD do so, though it
MAY also rely on the aforementioned caching mechanism.

A new API version is needed to support this.


Client (CLI) impact
-------------------

ironic node-set-provision-state
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A new argument called 'clean-steps' will be added to the
node-set-provision-state CLI. Its value is a JSON file which is read and the
contents passed to the API. Thus, the file has the same format as what is
passed to the API for clean steps.

If the input file is specified as '-', the CLI will read in from stdin, to
allow piping in the clean steps. Using '-' to signify stdin is common in Unix
utilities.

The 'clean-steps' argument is required if the requested provision state
target/verb is "clean". Otherwise, specifying it is considered an error.

ironic node-get-clean-steps
~~~~~~~~~~~~~~~~~~~~~~~~~~~

A new node-get-clean-steps API will be added as follows::

    ironic node-get-clean-steps [--min_priority <priority>] <node>

    <node>: name or UUID of the node
    --min-priority <priority>: optional minimum priority; default is 0 for all clean steps

If successful, it will return a list of clean steps. If the response from the
corresponding REST API request is an HTTP 202, it will return the message from
that response body (that the data are not available) along with a suggestion to
retry the request again.


RPC API impact
--------------

Add do_node_clean() (as a call()) to the RPC API and bump the RPC API version.


Driver API impact
-----------------

None


Nova driver impact
------------------

None


Ramdisk impact
--------------

N/A

.. NOTE: This section was not present at the time this spec was approved.

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
  rloo (taking over from JoshNang who has left ironic)

Other contributors:
  JoshNang (who started this)


Work Items
----------

* Make the changes (as described above) to the state machine

* Bump API microversion to allow manual cleaning and implement the changes
  to PUT /v1/nodes/(node_ident)/states/provision API (as described above)

* Modify the cleaning flow to allow manual cleaning

* Change execute_clean_steps and get_clean_steps in any asynchronous driver
  to cache clean steps and return cached clean steps whenever possible.

* Allow APIs to return a Retry-Request-After HTTP header and empty response, in
  response to a certain exception from drivers.


Dependencies
============

* get_clean_steps API: https://review.openstack.org/#/c/159322


Testing
=======

* Drivers implementing manual cleaning will be expected to test their added
  features.


Upgrades and Backwards Compatibility
====================================

None


Documentation Impact
====================

The documentation will be updated to describe or clarify automated cleaning and
manual cleaning and how to configure ironic to do one or both of them:

 * http://docs.openstack.org/developer/ironic/deploy/install-guide.html

 * http://docs.openstack.org/developer/ironic/deploy/cleaning.html

 * http://docs.openstack.org/developer/ironic/webapi/v1.html will be
   updated to reflect the API version that supports manual cleaning


References
==========

Automated cleaning specification: http://specs.openstack.org/openstack/ironic-specs/specs/kilo-implemented/implement-cleaning-states.html

State machine specification: http://specs.openstack.org/openstack/ironic-specs/specs/kilo-implemented/new-ironic-state-machine.html

Zapping related patches:

*  Launchpad blueprint: https://blueprints.launchpad.net/ironic/+spec/implement-zapping-states

* specification patches:
    * https://review.openstack.org/#/c/185122/
    * https://review.openstack.org/#/c/209207/

* code patches:
    * https://review.openstack.org/#/c/221949/
    * https://review.openstack.org/#/c/221989/
    * https://review.openstack.org/#/c/223295/
    * https://review.openstack.org/#/c/223311/
