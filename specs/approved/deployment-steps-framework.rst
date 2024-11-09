..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================
Deployment Steps Framework
==========================

https://storyboard.openstack.org/#!/story/1753128

There is a desire for ironic to support customizable and extendable deployment
steps, which would provide the ability to prepare bare metal nodes (servers)
that better match the needs of the users who will be using the nodes.

In order to support that, we propose refactoring the existing deployment
code in ironic into a deployment steps framework, similar to the cleaning
steps framework.

Problem description
===================

Presently, ironic provides a way to prepare nodes prior to them being made
available for deployment (see `state diagram`_). This is done via `cleaning`_.
However, it is not always possible, efficient, or effective to perform some of
these preparations without knowing the requirements of the users of the
nodes. In addition, there may be operations that should only be done once the
users' requirements are known.

For example, during `cleaning`_, a node could be configured for RAID.
However, this might not be the desired RAID configuration that the user of the
node wants. Since the user's desires are only known at deployment time, a
mechanism that allows for custom RAID configuration during deployment is
preferred.

Features like custom RAID configuration, BIOS configuration, and custom
kernel boot parameters are a few use cases that would benefit from a way
of defining deployment steps at deploy time, in ironic.

It makes sense to provide support for this via deployment steps. This would
be conceptually similar to the cleaning steps supported by ironic already.

Proposed change
===============

This proposal is the first step in providing support for performing different
deployment operations based on the user's desires. (The `RFE to reconfigure
nodes on deploy using traits`_ is an example of a feature that depends on
this work.)

The proposed change is to implement a deployment steps (or ``deploy steps``)
framework that is very similar to the existing framework for automated and
manual `cleaning`_. (This was discussed and agreed upon in principle, at the
`OpenStack Dublin PTG`_.)

This change is internal to ironic. Users will not be able to affect the
deployment process any more than they can do today.

Conceptually, the clean steps model is a simple idea and operators are familiar
with it. Having similar deploy steps provides consistency and it will be easier
for operators to adopt, due to their familiarity with clean steps. It is also
powerful in that, at the end of the day (or year or two), a particular step
could be a clean step, a deploy step, or both.

This includes re-factoring of code to be used by both clean and deploy steps.

The existing deployment process will be implemented as a list of one (or more)
deploy steps.

What is a deploy step?
----------------------
Similar to clean steps, functions that are deploy steps will be decorated
with ``@deploy_step``, defined in ironic/drivers/base.py as follows::

 def deploy_step(priority, argsinfo=None):
    """Decorator for deployment steps.

    :param priority: an integer priority; used for determining the order in
        which the step is run in the deployment process. (See below,
        "When are deploy steps executed" for more details.)
    :param argsinfo: a dictionary of keyword arguments where key is the name of
        the argument and value is a dictionary as follows:

            ‘description’: <description>. Required. This should include
                           possible values.
            ‘required’: Boolean. Optional; default is False. True if this
                        argument is required.

An alternative is to have one decorator that allows specifying a function
to be a clean step and/or a deploy step, e.g.::

 @step(clean_priority=0, deploy_priority=0, argsinfo=None)

However, clean steps are abortable and deploy steps aren't (yet, see below),
and it is unclear whether other arguments might be added for the deploy step
decorator. Thus, it seems safer and simpler to have a separate decorator for
deploy steps.  (Having one decorator for both types of steps is left as a
future exercise.)

Although ironic allows cleaning to be aborted, ironic doesn't allow the
deployment to be aborted (although there is an `RFE to support abort in
deploy_wait`_). So it is outside the scope of this specification.

A deploy step can be implemented by any Interface, not just DeployInterface.

When are deploy steps executed?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Each deploy step has a priority; a non-negative integer. In this first phase,
the priorities will be hard-coded. There will be no way to turn off or change
these priorities.

The steps are executed from highest priority to lowest priority. Steps with
priorities of zero (0) are not executed. A step has to be finished, before the
next one is started.

Alternatives
------------

There may be other ways to provide support for customizable deployment
steps per user/instance, but there doesn't seem to be good reasons for
having a different design from that used for clean steps.

We could choose not to provide support for customized deploy steps on a per
user/instance basis. In that case, some of the current workarounds to overcome
this problem include:

* have groups of nodes configured in advance (using clean steps) for each
  required combination of configurations. This could lead to strange capacity
  planning issues.

* executing the desired configuration steps after each node is deployed.
  As these configuration steps are executed post-deploy, most of them need a
  reboot of the node, orchestration is needed to do these reboots properly,
  and this causes performance issues that are not acceptable in a production
  environment. This approach won't work for pre-deploy steps though, such as
  RAID for the boot disk.

* users can create their own images for each use case. But the limitation
  is that the number of images can grow exponentially, and that there is no
  ability to match a specific type of hardware with a specific image.

* use a customizable DeployInterface like the `ansible`_ deploy interface
  (although the `ansible`_ deploy interface is not recommended for production
  use). This may not be able to achieve the same level of access to the
  hardware or settings, to have the same effect.

Data model impact
-----------------

Similar to clean steps, a Node object will be updated with:

* a new ``deploy_step`` field: this is the current deploy step that is being
  executed or None if no steps have been executed yet. This will require an
  update to the DB.
* ``driver_internal_info['deploy_steps']``: the list of deploy steps to be
  executed.
* ``driver_internal_info['deploy_step_index']``: the index into the list of
  deploy steps (or None if no steps have been executed yet); this corresponds
  to node.deploy_step.

State Machine Impact
--------------------

No new state or transition will be added.

The state of the node will alternate from states.DEPLOYING (``deploying``) to
states.DEPLOYWAIT (``wait call-back``) for each asynchronous deploy step.

REST API impact
---------------

There will not be any new API methods.

GET /v1/nodes/*
~~~~~~~~~~~~~~~
The GET /v1/nodes/* requests that return information about nodes will
be modified to also return the node's ``deploy_step`` field and the
deploy-related information in the node's ``driver_internal_info`` field.

Similar to the ``clean_step`` field, the ``deploy_step`` field will be the
current deploy step being executed, or None if there is no deployment in
progress (or hasn't started yet).

If the deployment fails, the ``deploy_step`` field will show which step caused
the deployment to fail.

This change requires a new API version. For nodes that have not yet been
deployed using the deploy steps, the ``deploy_step`` field will be None, and
there won't be any deploy-related entries in the ``driver_internal_info``
field.

For older API versions, this ``deploy_step`` field will not be available,
although any deploy-related entries in the ``driver_internal_info`` field will
be shown.

Client (CLI) impact
-------------------
The only change (when the new API version is specified), is that the response
for a Node will include the new ``deploy_step`` field and during deployment,
the new deploy-step-related entries in the node's ``driver_internal_info``
field.

"ironic" CLI
~~~~~~~~~~~~
Even though this has been deprecated, responses will include the change
described above.

"openstack baremetal" CLI
~~~~~~~~~~~~~~~~~~~~~~~~~
Responses will include the change described above.

RPC API impact
--------------

None.

Driver API impact
-----------------

Similar to cleaning, these methods will be added to the
drivers.base.BaseInterface class::

    def get_deploy_steps(self, task):
        """Get a list of deploy steps this interface can perform on a node.

        :param task: a TaskManager object, useful for interfaces overriding this method
        :returns: a list of deploy step dictionaries
        """

    def execute_deploy_step(self, task, step):
        """Execute the deploy step on task.node.

        :param task: a TaskManager object
        :param step: The dictionary representing the step to execute
        :raises DeployStepFailed: if the step fails
        :returns: None if this method has completed synchronously, or
            states.DEPLOYWAIT if the step will continue to execute
            asynchronously.
        """

The actual deploy steps will be determined in the coding phase; we will start
with one big deploy step (to get the framework in) and then break that step up
into more steps -- determined by what makes sense given the existing code, and
the constraints (e.g. support for out-of-tree drivers, backwards compatibility
when a deploy step in release N is split into several steps in release N+1).

(This specification will be updated with the actual deploy steps, once that
is determined.)

Out-of-tree Interfaces
~~~~~~~~~~~~~~~~~~~~~~
Although the conductor will still support deployment the old way (without
deploy steps), this support will be deprecated and removed based on the
`standard deprecation policy
<https://governance.openstack.org/tc/reference/tags/assert_follows-standard-deprecation.html>`_.
(The deprecation period may be extended if there is a strong desire to do so
by the vendors; we're flexible.)

For out-of-tree interfaces that don't have deploy steps, the conductor will
emit (log) a deprecation warning, that the out-of-tree interface should be
updated to use deploy steps, and that all nodes that are being deployed
using the old way, need to be finished deploying, before an upgrade to the
release where there is no longer any more support for the old way.

Nova driver impact
------------------

None

Ramdisk impact
--------------

There should be no impact to the ramdisk (IPA).

In the future, when we allow configuration and specification of deploy steps
per node, we might provide support for collecting deploy steps from the
ramdisk, but that is out of scope for this first phase.

Security impact
---------------

None

Other end user impact
---------------------

None.

Scalability impact
------------------

None.

Performance Impact
------------------

None.

Other deployer impact
---------------------

None.

Developer impact
----------------

DeployInterfaces (and any other interfaces involved in the deployment process)
will need to be written with deploy steps in mind.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  * rloo (Ruby Loo)

Work Items
----------

Ironic:
  * Add support for deploy steps to base driver
  * rework the existing code into one or more deploy steps
  * Update the conductor to get the deploy steps and execute them

``python-ironicclient``:
  * Add support for node.deploy_step

Dependencies
============
None.

Testing
=======

* unit tests for all new code and changed behaviour
* CI jobs already test the deployment process; they should continue to work
  with these changes

Upgrades and Backwards Compatibility
====================================

* Old Interfaces will work with the new BaseInterface class because
  the code will cleanly fall back when an Interface does not support
  ``get_deploy_steps()``. A deprecation warning will be logged, and we will
  remove support for the old way according to the OpenStack policy for
  deprecations & removals.

* Likewise, an Interface implementation with ``get_deploy_steps()`` will work
  in an older version of Ironic.

* In a cold upgrade:

  * if the agent heartbeats and driver_internal_info['deploy_steps'] is empty,
    proceed the old way.
  * if a deployment is started by a conductor using deploy steps (new code),
    it means all the conductors are using the new code, so the deployment
    can continue on any conductor that supports the node

* In a rolling upgrade:

  * if the agent heartbeats and driver_internal_info['deploy_steps'] is empty,
    proceed the old way (similar to cold upgrade)
  * a new conductor will not use the deploy steps mechanism if it is pinned to
    the old release (via `pin_release_version` configuration option).
    if a deployment is started by a conductor using deploy steps (new code),
    it means that it is unpinned, and all the conductors are using the new
    code, so the deployment can continue on any conductor that supports the
    node.

Documentation Impact
====================

* api-ref: https://developer.openstack.org/api-ref/baremetal/ will be updated
  to include the new node.deploy_step field

References
==========

* `cleaning`_
* `OpenStack Dublin PTG`_ etherpad
* `RFE to reconfigure nodes on deploy using traits`_
* `RFE to support abort in deploy_wait`_
* `state diagram`_

.. _`cleaning`: https://docs.openstack.org/ironic/latest/admin/cleaning.html
.. _`OpenStack Dublin PTG`: https://etherpad.openstack.org/p/ironic-rocky-ptg-deploy-steps
.. _`RFE to reconfigure nodes on deploy using traits`: https://bugs.launchpad.net/ironic/+bug/1722275
.. _`RFE to support abort in deploy_wait`: https://bugs.launchpad.net/ironic/+bug/1498251
.. _`state diagram`: https://docs.openstack.org/ironic/latest/contributor/states.html
.. _`ansible`: https://docs.openstack.org/ironic/latest/admin/drivers/ansible.html
