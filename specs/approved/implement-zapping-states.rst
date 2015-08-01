..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Implement Zapping States
==========================================

https://blueprints.launchpad.net/ironic/+spec/implement-zapping-states

Zapping encompasses all long running, destructive tasks an operator may
want to take either between workloads, or before the first workload has been
assigned to a node.


Problem description
===================

* Operators need some long running work done on nodes before they can be
  successfully provisioned.

* Things like firmware updates, setting up new RAID levels, or burning in
  nodes often need to be done before a user is given a server, but take
  too long to reasonably do at deploy time.

* Operators may want certain clean steps to only run on demand, rather than
  every clean cycle. One example is a burn in test before nodes are made
  AVAILABLE. By making clean_steps a subset of all possible zap steps,
  operators can choose which steps will be run on every clean cycle, and
  which will only be initiated by the operator.

* Many of these tasks will provide useful scheduling hints to Nova once
  hardware capabilities are introduced. Operators
  could use these scheduling hints to create flavors, such as a nova compute
  flavor that requires a node with RAID 1 for extra durability.

Proposed change
===============

* Modify the provision state API call which will allow a node in MANAGEABLE
  state to go to a ZAPPING state and perform a list of specified ZAPPING steps.
  These will be provided to the API as a list of dictionaries encoded as JSON.

* Add zapping steps to drivers, using the @clean_step decorator with a default
  cleaning_priority of 0. This will ensure the step isn't run as part of the
  automated cleaning between DELETED and AVAILABLE that happens in CLEANING.

* The list of possible ZAPPING steps will be pulled from the list of functions
  decorated with @clean_step, which is documented in [1].

* Operators will be able to get a list of possible steps by querying
  /nodes/<node_ident>/cleaning/all_steps. This will provide a superset of the
  states listed in /nodes/<node_ident>/cleaning/clean_steps, which doesn't list
  clean_steps with a cleaning_priority of 0.

* When the conductor attempts to execute a zap step, it will call
  execute_clean_step() on the driver responsible for that zap step.

Alternatives
------------

* We could make zap steps and clean steps mutually exclusive, simplifying
  some of the API and possible confusion, but limiting zapping and requiring
  a second, nearly identical API for executing individual CLEANING states or
  duplicating cleaning steps as zap and clean steps. Nearly any step that
  can be executed on demand via ZAPPING can be argued to be a necessary step
  in CLEANING to provide a consistent platform. For example, if you use
  ZAPPING to set up a RAID 10 on the node, you may want to ensure a clean
  RAID 10 is presented to every client, and therefore would need to check
  and possibly rebuild the RAID 10 in CLEANING. The same can be said for
  firmware upgrade (tenants can change firmwares), etc.

Data model impact
-----------------

None

REST API impact
---------------

GET /nodes/<node_ident>/cleaning/all_steps

* An API endpoint should be added to allow operators to see available
  zapping steps. This will be similar to
  /nodes/<node_ident>/cleaning/clean_steps, but will return all cleaning and
  zapping steps, with the format as follows::

    [{
      // 'interface' is one of : 'power', 'management', 'deploy'
      // 'step' is an opaque identifier used by the driver. Could be a driver
      // function name, could be some function in the agent.
      // 'cleaning_priority' is priority the step would be run at in cleaning.
      'interface': 'interface',
      'step': 'step',
      'cleaning_priority': some_integer,
      // a list of required arguments as strings that must be included in
      // the PUT to the node's provision state API to move to ZAPPING
      'required_args': []
    },
    ... more steps ...
    ]


* An example with a single step::

    [{
      'interface': 'management',
      'step': 'configure_hardware_raid',
      'required_args': ['raid_level']
      'cleaning_priority': 0,
    }]



* If the driver interface can not synchronously get the list of clean steps
  (eg, because a remote agent is used to determine available cleaning steps),
  then the driver MUST cache the list of clean steps from the most recent
  execution of said agent and return that. In the absence of such data, the
  driver MAY raise an error, which should be translated by the API service into
  an HTTP RETRY with an indication to the client as to when to retry using a
  Retry-After HTTP header. If the driver interface can synchronously return the
  cleaning steps, without relying on the hardware or a remote agent, it SHOULD
  do so, though it MAY also rely on the aforementioned caching mechanism.

PUT /v1/nodes/<node_ident>/states/provision

* The API will allow users to put a node directly into zapping
  provision_state with a PUT from MANAGEABLE state,
  the same as how provision state is changed anywhere else in Ironic. On top
  of the normal 'target_state': 'zap' , the PUT will require an argument
  'zap_steps', which will be a list in the form::

    'zap_steps': [{
        'interface': 'management'
        'step': 'configure_hardware_raid',
        'raid_level': 10 // required kwarg
        ... // more required kwargs (if applicable)
      },
      {
        'interface': 'deploy'
        'step': 'erase_devices'
      }
    }]


  Only 'interface' and 'step' are required for all steps. Each step may
  require additional kwargs, as noted above. The steps will be executed in the
  order provided. If any step is missing a kwarg or has incorrect kwargs, the
  node will go to ZAPFAIL with an appropriate error message.

* In the above example, hardware RAID 10 would be configured by the management
  driver, then all devices would be erased (in that order).

* The API will be changed to prevent changing power state or provision state
  while the node is in a ZAPPING state. A node in ZAPFAIL
  state may have its power state changed via the API, because the operator will
  likely need to restart the node to fix it.

State Machine Impact
--------------------

Implement/add the following parts of the state machine:

* MANAGEABLE -> ZAPPING (zap)

* ZAPPING -> MANAGEABLE (done)

* ZAPPING -> ZAPFAIL (fail)

* add ZAPFAIL -> ZAPPING (zap)

* add ZAPFAIL -> MANAGEABLE (manage)

Add 'zap' to states.VERBS.

Client (CLI) impact
-------------------

* Add an argument to the node-set-provision-state CLI called
  '--zap-steps' that takes a single argument: a JSON file to read and pass to
  the API, which has the same format as what is passed to the API for zapping.
  If the input file is specified as '-', the CLI will read in from stdin, to
  allow piping in the zap steps. Using '-' to signify stdin is common in Unix
  utilities. '--zap-steps' will on be required if the requested provision state
  is "zap", otherwise, it not allowed.

RPC API impact
--------------

Add do_node_clean to the RPC API, remove cleaning from the
do_provisioning_action RPC API call, and use this same call for zapping.
This should provide the cleanest API.

Driver API impact
-----------------

None

Nova driver impact
------------------

states.py should be synced to the Nova driver, so Nova is aware of zap* states.

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
  JoshNang

Work Items
----------

* Add API checks for zap states and allow "zap" as a
  provision target action, which will trigger the manageable -> zapping
  transition or zapfail -> zapping transition.

* Bump API microversion to add zapping states and "zap" verb.

* Modify the cleaning flow to allow zapping

* Change execute_clean_steps and get_clean_steps in any asynchronous driver
  to cache clean/zap steps and return cached clean/zap steps whenever possible.

* Allow APIs to return a Retry-After HTTP header and empty response, in
  response to a certain exception from drivers.

Dependencies
============

* get_clean_steps API https://review.openstack.org/#/c/159322


Testing
=======

* Drivers implementing zapping will be expected to test their added
  features.


Upgrades and Backwards Compatibility
====================================

None

Documentation Impact
====================

The overlap between cleaning and zapping should be clearly defined.


References
==========

1: https://review.openstack.org/#/c/102685/

2: https://review.openstack.org/#/c/150073/
