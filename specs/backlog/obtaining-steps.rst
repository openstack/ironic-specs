..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===============
Obtaining Steps
===============

https://storyboard.openstack.org/#!/story/1719925

https://storyboard.openstack.org/#!/story/1715419

In Ironic, we have a concept of steps [1]_ to be executed to achieve a task
utilizing a blend of driver code running in the conductor and code operating
inside of the
`ironic-python-agent <https://opendev.org/openstack/ironic-python-agent>`_.

In order for this to be useful, we have to be able to raise the visibility of
what is available to be performed to the end user of the API. Presently users
are only able to rely upon documentation, and the state of the code including
modules that could be loaded in.

This issue is further compounded as the entire list of steps is a union
of information identified from the ``ironic-conductor`` process managing the
node and the ``ironic-python-agent`` process executing upon the node.

.. Note::
   This document is present in the backlog as there are implementation issues
   to this feature. Please see Gerrit change
   `606199 <https://review.opendev.org/#/c/606199/4>`_ for more information.

Problem description
===================

* API users presently have to rely upon documentation of steps to know
  what is available.

* Different steps may be available with different hardware managers.

* With the increasing use of the Deploy Steps [2]_ framework, new steps
  should be anticipated to be added with new releases of Ironic.

* The ``ironic-python-agent`` must be running to obtain a complete list
  of steps.

Proposed change
===============

In order to keep this solution relatively lightweight, there are four
fundamental changes that will be needed in order to facilitate visibility.

This doesn't seek to solve complete visibility by creating additional
processes, but instead seeks to provide tools to collect data,
with the limiting factor being we can only return the current available
information.

How to do it?
-------------

Step 1
~~~~~~

The initial step is to provide an API endpoint that returns the current
available list of steps visible for a node running in the conductor.
This would be an API endpoint, to a RPC method, to a conductor manager
method, which would then return the list of steps, while tolerating the
absence of ``ironic-python-agent``.

.. Note::
   The ironic community consensus is that this feature should cache steps
   and return those cached steps as available to the user.

Step 2
~~~~~~

Addition of a ``hold`` provision state verb and ``holding`` state.

.. Note::
   During a specific planning and discussion meeting to determine the path
   for a feature such as this, the ironic community reached a consensus on
   the call that a holding state would be useful, and could likely be
   implemented aside from the API functionality proposed in this backlog
   specification.

 +-----------------+-------------------+---------------------------------+
 | *Initial State* | *Temporary State* | *Possible next verbs*           |
 +-----------------+-------------------+---------------------------------+
 | manageable      | holding           | manage, clean, provide, active, |
 |                 |                   | inspect                         |
 +-----------------+-------------------+---------------------------------+
 | available       | holding           | active, manage, provide         |
 +-----------------+-------------------+---------------------------------+


With the invocation of the state:

* The machine is moved to the provisioning network.

.. Note::
   There is a slight issue with this transition in that to clean the node
   would realistically need to be on the cleaning network. Operationally
   changing the DHCP address is problematic as we have learned with the
   rescue feature.

* The deployment ramdisk is booted.
* The ``ironic-python-agent`` would then be left in a running
  state, allowed to heartbeat (or be polled), and the API
  endpoint added in the prior step would fetch a complete
  list of steps that can be executed upon.

Alternatives
------------

An alternative to this solution would be to provide an async API endpoint
to perform the steps detailed in step 2, and cache the data which could then
be retrieved by the user asynchronously. In this case, the user would have
to poll the API to determine if the cached information has been updated.

The conundrum is that this would have to be constrained by states, which
means we would still need to build state machine states around this to
represent the current operation to users.

Data model impact
-----------------

None

State Machine Impact
--------------------

As noted above, we would add a new hold verb, which would allow transition
back to the prior state. This ``hold`` verb would only be accessible from
the ``manageable`` and ``available`` states.

In this holding state, API users would be able to request logical next steps,
in-line with the present state, as detailed in the table above.

REST API impact
---------------

The node object returned would expose additional ``provision_state`` states,
however this is a known quantity with all state machine impacts.

An additional provision state target verb of ``hold`` to trigger the state
machine change.

An endpoint will be added on to enable an API user to return the list
of known steps via the RPC interface and the conductor, which will be
triggered as a GET request.

.. Note::
   Community consensus is that we should not be initiating a synchronous call
   to IPA to collect data, that we should instead return cached data and
   somehow trigger the cache to be updated.

Example::

   GET /v1/nodes/{node_ident}/steps[?type=(clean|deploy)]
   {
     [{"source": "conductor",
       "deploy": [
         {
           "interface": "deploy",
           "step": "deploy",
           "priority": 100,
         },
       ],
       "clean": [
         {
           "interface": "deploy",
           "step": "erase_devices",
           "reboot_requested": False,
           "priority": 10,
           "abortable": True,
         },
         {
           "interface": "bios",
           "step": "apply_configuration",
           "args": {....},
           "priority": 0,
         },
         {
           "interface": "raid",
           "step": "create_configuration",
           "args": {....},
           "priority": 0
         },
         {
           "interface": "raid"
           "step": "delete_configuration",
            "args": {....},
            "priority": 0
         }
       ]
     },
     {"source": "agent",
     ...
     }
     ]
   }

If a specific ``type`` is requested, then the request shall only return the
requested type of steps. If no type is defined, both sets will be returned
to the caller.

Normal response code: 200
Expected error codes::

  * 400 with malformed request
  * 503 upon conductor error

.. NOTE::
   API micro-version will be incremented in accordance with standard
   procedure.


Client (CLI) impact
-------------------

"ironic" CLI
~~~~~~~~~~~~
None

"openstack baremetal" CLI
~~~~~~~~~~~~~~~~~~~~~~~~~

An ``openstack baremetal node steps`` and ``openstack baremetal node hold``
commands will be added to facilitate returning the data exposed by this api.

RPC API impact
--------------

A new RPC method will need to be added called ``get_steps``
that will support a single argument to indicate what class of
steps are being requested by the API user.

Driver API impact
-----------------

None

Nova driver impact
------------------

None is required for this feature.

That being said, there is value to enable a node to be scheduled which is
being held for an available deployment. As such, it could be an optional
enhancement which could save quite a bit of time in a deployment process.
This could be enabled by allowing nova to consider a node in the ``holding``
state to be available for deployments by also evaluating the
``target_provision_state`` for nodes in ``holding``. It would be
fairly tight coupling, but a frequent ask is for faster deployments,
and it would be a route that we could take to enable such
functionality in terms of "holding for deployment".

Ramdisk impact
--------------

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
  Julia Kreger (TheJulia) <juliaashleykreger@gmail.com>

Other contributors:
  ?

Work Items
----------

* Implement API to retrieve a list of states.
* Implement State machine changes to allow an idle agent instance to return
  cleaning step data.
* Add API tests to ironic-tempest-plugin.
* Update state machine documentation.
* Add Admin documentation.
* Update CLI documentation.

Dependencies
============

None

Testing
=======

Basic API contract and state testing should be sufficient for this feature.

Upgrades and Backwards Compatibility
====================================

N/A, The existing rolling upgrades and RPC version pinning practice should
be more than sufficient to support this feature.

Documentation Impact
====================

Additional details will need to be added to the Admin guide.
State documentation will need to be updated.
Update client documentation for new state verb.

References
==========
.. [1] Manual cleaning - https://specs.openstack.org/openstack/ironic-specs/specs/5.0/manual-cleaning.html
.. [2] Deploy Steps - https://specs.openstack.org/openstack/ironic-specs/specs/11.1/deployment-steps-framework.html
