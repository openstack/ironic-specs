..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==================================================
Switch periodic tasks to the Futurist library
==================================================

https://bugs.launchpad.net/ironic/+bug/1526277

Futurist_ is a new Oslo library providing tools for writing asynchronous code.
This spec suggests switching our periodic task implementation to Futurist_ to
solve some long-standing problems.

Problem description
===================

The main problem with our current implementation is that we run all periodic
tasks in one thread. Any task that blocks for a while would block all other
tasks from executing, and it happens pretty often with tasks checking power
states via IPMI.

Switch to Futurist_ will allow executing all tasks in parallel.

Proposed change
===============

* Modify conductor to use Futurist_ library instead of implementation from
  oslo incubator.

  `Existing worker pool
  <https://github.com/openstack/ironic/blob/master/ironic/conductor/manager.py#L238>`_
  will be reused for periodic tasks. So, existing option ``workers_pool_size``
  will set maximum number of tasks to run in parallel at every moment of time.

* Switch all use cases of ``ironic.openstack.common.periodic_task`` to
  Futurist_ decorators, and drop this module.

* Switch ``ironic.drivers.base.driver_periodic_task`` to using Futurist_
  decorators internally and deprecate it.

Alternatives
------------

* We could fix existing implementation. That's not actually easier, as it
  requires essentially rewriting it.

Data model impact
-----------------

None

State Machine Impact
--------------------

None

REST API impact
---------------

None

Client (CLI) impact
-------------------

None

RPC API impact
--------------

None

Driver API impact
-----------------

* Old way of creating driver periodic tasks will be deprecated, drivers should
  eventually switch to using Futurist_ decorators.

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

* Overall positive impact on scalability expected, as every Ironic conductor
  will be able (at least theoretically) to manage more IPMI nodes.

Performance Impact
------------------

* A periodic tasks performance will no longer affect timing of other periodic
  tasks.

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
  Dmitry Tantsur (irc: dtantsur, lp: divius)

Work Items
----------

* Change conductor manager to use Futurist_

* Modify ``driver_periodic_task`` to use Futurist_ internally

Dependencies
============

The only big dependency is Futurist_ itself. At the moment of writing it
didn't see an official release yet, but is moving pretty fast and all required
code already landed in git master.

Testing
=======

Unit tests should already cover this functionality. Specific tests ensuring
parallelization will be added.

Upgrades and Backwards Compatibility
====================================

None

Documentation Impact
====================

Documentation of driver periodic tasks should be updated to mention Futurist_
instead of ad-hoc implementation.

References
==========

* `Futurist periodic task documentation
  <http://docs.openstack.org/developer/futurist/api.html#periodics>`_

.. _Futurist: https://github.com/openstack/futurist
