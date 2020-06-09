..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

====================
In-band Deploy Steps
====================

https://storyboard.openstack.org/#!/story/2006963

Since the Rocky release, Ironic has had support for `deploy steps
<https://storyboard.openstack.org/#!/story/1753128>`__. These allow drivers to
customise the node deployment flow. Currently these steps are limited to out of
band execution - steps may not be executed on the node via IPA during
deployment. This spec proposes to support execution of in-band deploy steps, in
a similar manner to in-band cleaning steps.

Example use cases:

* Software RAID configuration during deployment
* In-band BIOS configuration during deployment


Problem description
===================

Ironic's deployment process has historically been quite rigid, not allowing for
much customisation outside of the scope of the supported features. This is
changing, starting with `deploy steps
<https://storyboard.openstack.org/#!/story/1753128>`__, drivers are able to
define custom tasks to perform during deployment using the pattern established
for cleaning. The `deploy templates
<https://storyboard.openstack.org/#!/story/1722275>`__ feature exposes these
deploy steps to users of nova via traits applied to flavors or images.

There are some limitations to deploy steps that we aim to address in this spec:

* deploy steps cannot be executed in-band (on the node, via IPA) during
  deployment

* deploy steps may only be executed before or after what we will refer to here
  as the 'mega step'

As we will see, these two issues are linked, since we must break apart the mega
step in order to support in-band deploy steps.

Mega step
---------

The 'mega step' starts with the node powered off and configured to boot on the
provisioning network. When it has finished, the image has been written to disk,
the boot device configured, and the node is plugged into the tenant network and
powered on. This covers a significant portion of the deployment process.

Use cases
---------

The following are some use cases for in-band deploy steps.

* as a user of ironic, I want a machine configured with a particular software
  RAID layout during deployment

* as a user of ironic, I want a machine configured with particular BIOS
  settings during deployment

* as a user of ironic, I want custom firmware installed during deployment

* as a user of ironic, I want to apply custom NIC configuration during
  deployment

And here are some for decomposing the mega step.

* as an ironic driver maintainer, I want to create a deploy step that executes
  with the node booted on the provisioning network

* as an ironic driver maintainer, I want to create a deploy step that executes
  after the image has been written to disk, while the node is attached to the
  provisioning network and powered on

Proposed change
===============

Mega step context
-----------------

The 'mega step' is actually a deploy step called ``deploy`` on the ``deploy``
interface. In order to understand how it will be changed, we must first
understand what it does and how it fits into the overall deployment flow.
Some details in the following will depend on the particular drivers and
configuration in use, but we will try to cover the most common usage.

We start our story in the ironic conductor, where a ``do_node_deploy`` RPC has
been received.

#. ``do_node_deploy`` RPC received:

   #. validation of ``power`` and ``deploy`` interfaces, traits, and deploy
      templates
   #. the node's provision state is set to ``deploying`` (or ``rebuilding`` if
      ``rebuild`` is ``True``)

#. execution continues in a new worker thread:

   #. config drive is built and stored, if using one
   #. the ``prepare`` method of the ``deploy`` interface is called
   #. deploy steps for execution are determined based on drivers and deploy
      templates, then stored in ``driver_internal_info.deploy_steps``
   #. trigger execution of the next deploy step

#. for each deploy step:

   #. update ``driver_internal_info.deploy_step_index`` to the index of the
      current step
   #. execute the deploy step

      #. if it returns ``DEPLOYWAIT``, this is an asynchronous step. Exit
         the worker thread and wait for a ``continue_node_deploy`` RPC
      #. if it returns ``None``, continue to execute the next deploy step

#. if all deploy steps complete:

   #. clean up ``driver_internal_info``
   #. start the node's console, if necessary
   #. the node's provision state is set to ``active``

Well that doesn't look too bad... until we realise there's some complexity and
asynchronism hidden in there.

Prepare
^^^^^^^

First of all, let's look at the ``prepare`` method of the ``deploy`` interface.
For the ``agent`` and ``iscsi`` deploy interfaces, this involves:

#. power off the node
#. remove tenant networks (for rebuild, when writing an image)
#. add provisioning network (when writing an image)
#. attach volumes
#. prepare ramdisk boot

So we know that if an image is to be written to the node, then after
``prepare``, the node will be ready to boot into the IPA ramdisk on the
provisioning network.

Continue node deploy RPC
^^^^^^^^^^^^^^^^^^^^^^^^

The next item to unpack here is asynchronous steps and the
``continue_node_deploy`` RPC. While waiting for execution of an asynchronous
step, the node's provision state is set to ``wait callback``. Completion of the
step is checked for either in the driver via a periodic task (the driver sets
``driver_internal_info.deployment_polling``), or in the heartbeat handler for
IPA. On completion, the ``continue_node_deploy`` RPC is triggered, and the node
returns to the ``deploying`` provision state.

Mega step
^^^^^^^^^

The final piece here is the 'mega step' itself: the ``deploy`` method on the
``deploy`` interface.

#. reboot the node, wait for heartbeat (when writing an image)
#. on the first IPA heartbeat:

   #. write image to disk synchronously (``iscsi`` deploy interface)
   #. call IPA ``standby.prepare_image`` API, wait for heartbeats until
      complete (``direct`` deploy interface)

#. prepare instance to boot
#. power off the node
#. remove provisioning network
#. configure tenant networks
#. power on the node

At this point, any deploy steps with a lower priority than the mega step's
(100) will be executed. Care is required at this point however, since the node
is already attached to the tenant network and booting.

In-band cleaning steps
----------------------

Here is a quick overview of how in-band cleaning works for reference.

In-band cleaning starts by configuring the node on the provisioning network and
booting up the IPA ramdisk. On the first heartbeat, the list of in-band steps
is queried, combined with out-of-band steps and stored in
``driver_internal_info.clean_steps``.

In-band clean steps are advertised by the ``deploy`` interface, which overrides
the ``execute_clean_step`` method to execute them via the IPA API. In-band
clean steps are always asynchronous, with polling triggered via the IPA
heartbeat.

In-band clean steps may request that the node is rebooted after completion of
the step via a ``reboot_requested`` flag in their step definition. There is
some handling of the case where an IPA returns with a different version after
reboot. In this case automated cleaning is restarted, and manual cleaning is
aborted.

One final detail is the ability to define hooks that execute after completion
of an in-band cleaning step via the ``@post_clean_step_hook`` decorator.

Observations
------------

In order to gather a list of in-band deploy steps, we need to be able to
communicate with IPA. This is first possible at step 2 of the mega step.

We may wish to still allow execution of out-of-band deploy steps before IPA has
booted, to avoid unnecessary delays. An example here is BIOS or RAID
configuration on Dell iDRACs, which can require the node to be powered on for
the lifecycle controller to perform the configuration jobs. An additional boot
cycle adds significant delay to the deployment process. This would represent a
divergence in behaviour between deployment and cleaning.

When booting from a volume, there may be no image to write. Currently in that
case, IPA is not used. This would prevent the use of in-band deploy steps,
but booting up IPA just to gather a list of deploy steps would increase the
time required to boot from a volume.

The above description of deployment did not cover fast track deploys. This
feature allows a node that is already booted with an IPA ramdisk, e.g. from
discovery, to bypass the reboot in the mega step.

Proposed mega step decomposition
--------------------------------

The following describes the proposed decomposition of the 'mega step' into
separate steps.

#. ``deploy`` [100]:

   #. reboot the node, wait for heartbeat (when writing an image?)
   #. gather in-band deploy steps from the agent

#. ``write_image`` [80]:

   #. write image to disk synchronously (``iscsi`` deploy interface)
   #. in-band deploy step that does the equivalent of the
      ``standby.prepare_image`` IPA API and waits for completion of the write
      (``direct`` deploy interface)

#. ``prepare_instance_boot`` [60]:

   #. install bootloader (if needed)
   #. configure the boot interface

#. ``tear_down_agent`` [40]:

   #. power off the node
   #. remove provisioning network

#. ``boot_instance`` [20]:

   #. configure tenant networks
   #. power on the node

The useful priority ranges for inserting custom in-band steps are:

* 99 to 81: preparation before writing the image (e.g. software RAID).
* 79 to 61: modifications to the image before a bootloader is written
  (e.g. GRUB defaults changes).
* 59 to 41: modifications to the final instance (e.g. software configuration).

deploy
^^^^^^

*Priority: 100*

This deploy step will be largely unchanged from the current ``deploy`` step.
Changes will be necessary for fast track deploys, to skip the direct call to
``continue_deploy`` and rely on the new deploy steps. For boot from volume this
step currently performs the tenant network configuration, instance preparation
and reboot, however that can also be moved to the new steps.

write_image
^^^^^^^^^^^

*Priority: 80*

For the ``iscsi`` interface, the ``continue_deploy`` method will be split into
a ``write_image`` deploy step and the ``prepare_instance_boot``,
``remove_provisioning_network``, and ``boot_instance`` deploy steps.  This step
will be skipped when booting from a volume.

For the ``direct`` interface, this step will start as an out-of-band one,
will collect the necessary information, then switch into being executed in-band
by IPA. It will be equivalent to executing the existing
``standby.prepare_image`` command via the agent API, and will block until
the image has been written. This allows us to remove this special case of
command status polling. There will need to be a transition period to support
old IPA ramdisks that do not support in-band deploy steps.

prepare_instance_boot
^^^^^^^^^^^^^^^^^^^^^

*Priority: 60*

This will be largely equivalent to the ``prepare_instance_to_boot`` method of
the ``AgentDeployMixin``.

tear_down_agent
^^^^^^^^^^^^^^^

*Priority: 40*

In this step, the node will be powered off, and the provisioning networks
removed.

boot_instance
^^^^^^^^^^^^^

*Priority: 20*

In this step, the node will be added to the tenant networks and powered on.

Agent heartbeat handler
^^^^^^^^^^^^^^^^^^^^^^^

The ``heartbeat`` method of the ``HeartbeatMixin`` currently provides an
extension of the logic of the ``deploy`` step. This includes calling
``continue_deploy`` on the first heartbeat, and ``reboot_to_instance`` when the
deployment is finished. This logic will be unnecessary with these methods as
deploy steps, but will remain in place for a period for backwards
compatibility. Drivers will advertise support for decomposed deploy steps by
returning ``True`` from a method called ``has_decomposed_deploy_steps``.

Proposed in-band deploy step support
------------------------------------

In-band deploy steps will be handled in a similar way to in-band cleaning
steps, with some differences:

* out-of-band deploy steps with a priority greater than 100 may be executed
  before the node has booted up
* the ``deploy`` interface may provide both in-band and out-of-band deploy
  steps
* there is no equivalent of manual cleaning
* IPA version mismatch will lead to termination of deployment

In-band deploy steps must have a priority between 76 and 99 to ensure they
execute after ``deploy`` and before ``remove_provisioning_network``.

In-band deploy steps will be driven through the agent's heartbeat mechanism.
The first heartbeat will query the in-band steps, combine them with out-of-band
steps and store them in ``driver_internal_info.deploy_steps``.

In-band deploy steps are advertised by the ``deploy`` interface, which
will override the ``get_deploy_steps`` method to query the steps from IPA, and
the ``execute_deploy_step`` method to execute them via the IPA API.  This will
be slightly different from clean steps, to support execution of out-of-band
steps on the ``deploy`` interface. In-band deploy steps are always
asynchronous, with polling triggered via the IPA heartbeat.

In-band deploy steps may request that the node is rebooted after completion of
the step via a ``reboot_requested`` flag in their step definition. In the case
where an IPA returns with a different version after reboot, deployment will be
terminated.

Post-deploy step hooks will be supported via a ``@post_deploy_step_hook``
decorator, for example to set a node's RAID configuration field.

The IPA ramdisk will be modified to add a new ``deploy`` extension. This will
be very similar to the existing ``clean`` extension. Hardware managers should
implement a ``get_deploy_steps`` method that should work in a similar way to
the existing ``get_clean_steps`` method.

Alternatives
------------

* Deny execution of out-of-band deploy steps before IPA has booted.
  See Observations for details.
* Allow in-band steps for boot from volume. These could be made available via
  an optional deploy step that boots up the node on the provisioning network.

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

There will be no changes to the driver API, but there will be changes to the
``AgentDeployMixin`` class used by all in-tree drivers and potentially
out-of-tree drivers. These changes will be backwards compatible, with a
transition period for out-of-tree drivers to switch to the new decomposed step
model (advertised by returning ``True`` from ``has_decomposed_deploy_steps``).

Nova driver impact
------------------

None

Ramdisk impact
--------------

Changes to the IPA ramdisk are discussed above. Backward compatibility will be
provided by ignoring a missing ``deploy`` extension.

Security impact
---------------

In-band deploy steps will have additional access to the node by the nature of
executing directly on it. These steps and the IPA ramdisk are under the control
of the operator, who will need to take action to ensure that they do not
introduce any security issues.

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

Primary assignees:
  Mark Goddard (mgoddard)
  Arne Wiebalck (arne_wiebalck)

Work Items
----------

* Decompose core deploy step
* Advertise & execute in-band steps via IPA
* Collect & execute in-band steps from IPA
* Update documentation

Dependencies
============

* `Deploy steps (implemented)
  <https://specs.openstack.org/openstack/ironic-specs/specs/approved/deployment-steps-framework.html>`__

* `Deploy templates (implemented)
  <https://specs.openstack.org/openstack/ironic-specs/specs/approved/deploy-templates.html>`__

Testing
=======

Ideally tempest tests will be added to cover execution of in-band deploy steps.
Software RAID configuration is a reasonable candidate for this as the resulting
configuration could be verified.


Upgrades and Backwards Compatibility
====================================

This has been discussed elsewhere.


Documentation Impact
====================

The deploy steps documentation will be updated, in particular covering the new
flow and the required priorities of user steps.


References
==========

None
