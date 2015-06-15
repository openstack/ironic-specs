..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==================================================
Add "enroll" state to the state machine
==================================================

https://blueprints.launchpad.net/ironic/+spec/enroll-node-state

This blueprint introduces a new state called ``enroll``, which we previously
agreed to introduce in the `new state machine`_ spec.

Problem description
===================

Currently nodes on creation are put into ``available`` state, which is designed
as a replacement for ``NOSTATE``. Such nodes will instantly be available
to Nova for deployment, provided they have all the required properties.

However, the new state machine lets the operator perform inspection on a node
and zapping of a node. The state machine allows for them to be done before a
node reaches the ``available`` state.

Even worse, the cleaning feature introduced in Kilo cycle should also
happen before a node becomes ``available``.

Proposed change
===============

* Add a new state ``enroll``, from which a node can transition into the
  ``manageable`` state by an action called ``manage``.

* ``manage`` transition will cause power and management interfaces to be
  validated on the node. Also an attempt will be made to get the power state on
  a node to actually verify the supplied power credentials.

  On success, the node will go to the ``manageable`` state. On failure, it will
  go back to the ``enroll`` state and ``last_error`` will be set.

* Disable the sync_power_state for nodes in the ``enroll`` state, as nodes in
  this state are not expected to have valid power credentials.

* Introduce a new API microversion, making newly created nodes appear in the
  ``enroll`` state instead of the ``available`` state.

  After that the client-server interaction will be the following:

  - new client (with new API version) + new server: nodes appear
    in the ``enroll`` state.

  - new client + old server: client gets a response from the server stating
    that node is in ``available`` (or ``none``) state. Client issues a warning
    to the user.

  - old client (or new client with old API version) + new server:
    due to versioning the node will appear in ``available`` (or ``none``)
    state.

* Document that we are going to make a breaking move to the ``enroll`` state by
  default.

* Update DevStack gate to explicitly request the new microversion and fix the
  tests.

* Release a new version of ``ironicclient`` defaulting to this new
  microversion. Clearly document this breaking change in upgrade notes.

Alternatives
------------

We can ask people to manually move nodes to the ``manageable`` state before
inspection or zapping. We also won't validate power and management interfaces.

Data model impact
-----------------

None

State Machine Impact
--------------------

* ``enroll`` becomes a valid node state with transitions to:

  * ``verifying`` via ``manage`` action

* ``verifying`` becomes a valid transient node state with transitions to:

  * ``manageable`` on ``done``

  * ``enroll`` on ``fail`` and ``last_error`` will be set.

REST API impact
---------------

* Add new API microversion. When it is declared by client, node creation API
  should default to creating nodes in the ``enroll`` state.

Client (CLI) impact
-------------------

* New release of client will be issued defaulting to the new microversion
  (and breaking many flows).

RPC API impact
--------------

None

Driver API impact
-----------------

None

Nova driver impact
------------------

* Double check that Nova driver won't use nodes in ``enroll`` state

* Sync ``nova/virt/ironic/ironic_states.py`` for the sake of consistency

No functionality impact expected.

Security impact
---------------

None expected

Other end user impact
---------------------

With the new microversion, nodes will appear in the ``enroll`` state. Two more
steps should be taken to make them available for deploy: ``manage`` and
``provide``. Cleaning will happen, if enabled.

Scalability impact
------------------

None

Performance Impact
------------------

None

Other deployer impact
---------------------

See `Upgrades and Backwards Compatibility`_.

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Dmitry Tantsur, IRC: dtantsur, LP: divius

Other contributors:
  None

Work Items
----------

* Create new states and transitions

* Introduce new microversion with node defaulting to ``enroll`` on creation

* Make sure our tests do not break (fix devstack etc)

* Default ironicclient to the new microversion

Dependencies
============

None

Testing
=======

* Tempest tests should be modified to test ``enroll`` state.

Upgrades and Backwards Compatibility
====================================

* Change is backwards compatible, while it's not the default in ironicclient.

* Once new microversion is the default in ironicclient, it will break existing
  flows, when explicit microversion is not in use.

Documentation Impact
====================

* Working with the new state and the transition should be documented

* Upgrade notes should be updated

References
==========

.. _new state machine: http://specs.openstack.org/openstack/ironic-specs/specs/kilo/new-ironic-state-machine.html
