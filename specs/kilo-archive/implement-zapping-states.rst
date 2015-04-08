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

* Operators may want to execute individual clean steps
  on nodes in MANAGEABLE state. This unfortunately means a lot of overlap
  with CLEANING states. One example is running verification of node.properties
  over a large group of nodes, but not wanting to wait hours for a full
  CLEANING.

* Many of these tasks will provide useful scheduling hints to Nova once
  hardware capabilities are introduced. Operators
  could use these scheduling hints to create flavors, such as a nova compute
  flavor that requires a node with RAID 1 for extra durability.

Proposed change
===============

* Modify the provision state API call which will allow a node in MANAGEABLE
  state to go to a ZAPPING state and perform a list of ZAPPING steps.

* Add zapping steps to drivers, using the @clean_step decorator with a default
  cleaning_priority of 0. This will ensure the step isn't run as part of the
  automated cleaning between DELETED and AVAILABLE that happens in CLEANING.

* The list of possible ZAPPING steps will be pulled from the list of functions
  decorated with @clean_step, which is documented in [1].

* Operators will be able to get a list of possible steps by querying
  /nodes/<uuid>/zapping/zap_steps. This will provide a superset of the
  states listed in /nodes/<uuid>/cleaning/clean_steps, which doesn't list
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

* The API will be changed to prevent changing power state or provision state
  while the node is in a ZAPPING state. A node in ZAPFAIL
  state may be powered off via the API, because the operator will likely need
  to restart the node to fix it.

* An API endpoint should be added to allow operators to see available
  zapping steps. This will be a GET endpoint
  at /nodes/<uuid>/zapping/steps and will return a combination of all
  cleaning steps and all zapping steps as a JSON document, with the format as
  follows::

    {
      // driver_interface_name is one of : 'power', 'management', 'deploy'
      // name is an opaque identifier used by the driver. Could be a driver
      // function name, could be some function in the agent.
      'step': 'driver_interface_name.name',
      // a list of required arguments as strings that must be included in
      // the PUT to the node's provision state API to move to ZAPPING
      'required_args': []

    }

* An example::

    {
      'step': 'management.configure_hardware_raid',
      'required_args': ['raid_level']

    }

* The API will allow users to put a node directly into zapping
  provision_state with a PUT from MANAGEABLE state,
  the same as how provision state is changed anywhere else in Ironic. The
  PUT will require an argument 'zap_steps', which will be a list of in the
  form::

    'zap_steps': [{
        'name': 'management.configure_hardware_raid',
        'raid_level': 10 // required kwarg
        ... // more required kwargs (if applicable)
      },
      {
        'name': 'deploy.erase_devices'
      }
    }]


  Only 'name' is required for all steps. Each step may require additional
  kwargs, as noted above.

* In the above example, hardware RAID 10 would be configured by the management
  driver, then all devices would be erased (in that order).

RPC API impact
--------------

None


Driver API impact
-----------------

This will use the existing changes in CLEANING for execute_clean_step()
and get_clean_steps().

Nova driver impact
------------------

None

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

* Add zap() to the conductor

* Add API checks for zap states and allow "ZAPPED" as a
  provision target state

Dependencies
============

* Implement Cleaning states [1]

* Implement Manageable [2]


Testing
=======

* Drivers implementing zapping will be expected to test their added
  features.


Upgrades and Backwards Compatibility
====================================

If the API is upgraded before the conductor, and the operator tries to
initiate zapping via a PUT, the API will be unable to complete the request.
If the conductor is upgraded first, there will be no way to call zap()
without the API.

Documentation Impact
====================

The overlap between cleaning and zapping should be clearly defined.


References
==========

1: https://review.openstack.org/#/c/102685/

2: https://review.openstack.org/#/c/150073/