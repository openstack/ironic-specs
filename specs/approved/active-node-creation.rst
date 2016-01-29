..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

====================
Active Node Creation
====================

https://bugs.launchpad.net/ironic/+bug/1526315

This spec is intended to allow a slightly more permissive interaction with
the ironic API to allow an operator to migrate a hardware fleet to be managed
by ironic.

Problem description
===================

At present the ironic API explicitly sets the new state for nodes to the
beginning step in the ironic workflow.

As part of hardware fleet lifecycle management, an operator expects to
be able to migrate inventory and control systems for their hardware fleet
utilizing their existing inventory data and allocation records.
Ultimately this means that that an imported host MAY already be allocated
and unavailable for immediate allocation.

For an operator of multiple distinct OpenStack infrastructures, it is
reasonable to permit an operator to migrate running baremetal hosts from
one "system" to another "system" that are ultimately components in a
larger infrastructure, while not immediately reprovisioning hardware.

Proposed change
===============

Allow an API client to transition a node directly from the ``MANAGEABLE``
state to the ``ACTIVE`` state, bypassing actual deployment of the node.

* Creation of a new API provision_state verb of ``adopt`` that
  invokes the state transition of ``ADOPTING``.

* Creation of a new machine state transition of ``ADOPTING`` which is
  valid only in the ``MANAGEABLE`` state and allows an operator to directly
  move a node to ``active`` state. This transition would be dependent upon
  a successful interface validation. Failure of this transition shall move
  nodes to an ``ADOPTION_FAILED`` which will allow users to be able to
  identify nodes that failed adoption.

* Creation of a new machine state of ``ADOPTION_FAILED`` which a machine is
  set to upon the ``ADOPTING`` transition failing.  This state will allow a
  user to re-attempt ``ADOPTING`` via ``adopt``, or attempt to
  transition the node to the ``MANAGEABLE`` state via ``manage``.
  Additionally, the ``ADOPTION_FAILED`` state will be listed in the list
  of states that permit node deletion from the ironic database.

* API client update to provide CLI interface to invoke this feature.

* Creation of explicit documentation covering::

    - Use cases of the feature while explicitly predicating that proper
      operation requires node validation to succeed.
    - Explicitly detail that it is the operator's responsibility to
      define the node with all relevent appropriate configuration else
      the node could fail node state provision operations of ``rebuild``
      and ``delete``. Which would result in manual intervention being
      necessary.
    - Explain the basic mechanics of the use of the adoption feature
      to users in order to help convey the importance of the correct
      information being populated.

Alternatives
------------

The logical alternative is to remove restrictions in what an API client posts
to allow the caller to explicitly state or invoke a node to be created in
``ACTIVE`` state. As the community desires full functionality of the node to
exist upon being imported along with driver interface validation, the
implementation appears to lend itself to be implemented as a state
transition instead of pure API logic.

Alternatively, we could craft operator documentation to help assist operators
in directly loading nodes into the ironic database, coupled with the caveats
of doing so, and require that that documentation is updated in lock-step with
any database schema changes.

Data model impact
-----------------

None

State Machine Impact
--------------------

Implementation of a new state transition from ``MANAGEABLE`` state to
``ACTIVE`` state utilizing an intermediate state of ``ADOPTING`` which
takes the following actions.

1. Triggering the conductor node take_over logic.
2. Upon completion the node state is set to ``ACTIVE``.

Should a failure of take_over logic occur in the ``ADOPTING`` state,
the node will be returned to ``ADOPTION_FAILED`` state from which a user
will be able to retry the adoption operation or delete the node.

Addition of ``ADOPTION_FAILED`` into the ``DELETE_ALLOWED_STATES`` list.

REST API impact
---------------

Addition of a new state verb of ``adopt`` that triggers a transition to
``ADOPTING`` state. This verb will be unavailable for clients invoking
an insufficent API version.

The API micro-version will need to be incremented as a result of this change.

Client (CLI) impact
-------------------

Update of the ironicclient CLI to detail that ``adopt`` is a possible
provision state option.

Update of the ironicclient micro-version.

RPC API impact
--------------

None

Driver API impact
-----------------

None

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

Minimal API impact will exist for a user of this feature as the creation
of nodes in ``ACTIVE`` state will require multiple calls with the API by
any user attempting to leverage this feature.

Users performing bulk loads of hosts may find the multiple API calls
somewhat problematic from the standpoint of multiple API calls to create,
validate, and adopt a node, on top of API calls to poll the current state
of the node before proceeding to the next step.  Bulk loaders should also
be congnizant of their configurations as they potentially could result in
the conductors consuming disk space and network bandwidth if items need
to be staged on the conductor to support the node's normal operation.

Other deployer impact
---------------------

Allows for an easier adoption by managers of pre-existing hardware fleets.

There is the potential that a operator could define a hardware fleet with
bare minimal configuration to initially add the node to ironic. The result
of which means that an operator could conceivably and inadvertently act upon
a node when insufficent information is defined. This risk will be documented
as part of the resulting documentation in order to help highlight the risk
and help provide guidance on preventing such a possibility should a user
be attempting to adopt an inventory that is already "cloudy".

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  juliaashleykreger

Other contributors:
  None

Work Items
----------

* Conductor State Machine Changes
* API microversion and update and appropriate logic
* CLI node-set-provision-state option addition
* Documentation updates

Dependencies
============

None

Testing
=======

Addition of unit tests as well as tempest tests to explicitly test
the interface.

Upgrades and Backwards Compatibility
====================================

This feature will not be visible to older API clients via a the API
micro-version interface.

An older API client will receive the ``DEPLOYING`` as opposed to
``ADOPTING`` as this is the closest existing state representing the
current state of the node. Additionally the state of ``DEPLOYING`` will
prevent the nova API from considering the node as an available node for
deployment on to.

An older API client will receive the ``ERROR`` state for any node in
``ADOPTION_FAILED`` to allow for easy identification and deliniation of
a node that failed verification.

Documentation Impact
====================

Documentation will need to be updated to represent this new feature.

References
==========

None
