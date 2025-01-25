..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===================================================
Dynamic allocation of nodes for the OneView drivers
===================================================

https://bugs.launchpad.net/ironic/+bug/1541096

This spec proposes a change in the way the OneView drivers allocate nodes. The
new model will allocate resources in OneView only at boot time, avoiding that
idle hardware in Ironic is still blocked from OneView's users perspective.

In this spec, the following terms will be used to refer to OneView resources:

- Server Hardware (SH): corresponds to a physical server. A Server Hardware
  can have only one Server Profile applied at a time.

- Server Profile (SP): representation of hardware configuration, such as
  network configuration, boot settings, firmware version, as well as features
  configurable through BIOS.

- Server Profile Template (SPT): template used to define a reference
  configuration of a set of Server Profiles.

Problem description
===================

The current version of the OneView drivers consider what we call
``pre-allocation`` of nodes. This means that when a node is registered in
Ironic, there must be a Server Profile applied to the Server Hardware
represented by the given node.

In OneView, when a Server Hardware has a Server Profile applied to it,
the understanding is that such hardware is being used.

The problem with ``pre-allocation`` is that even when a node is ``available``
in Ironic and, therefore, there is no instance associated to it, the
resource in OneView is considered to be allocated. This means that no other
OneView user can use and control this resource.

Therefore, in an environment shared by Ironic and OneView users, to simply
allocate a pool of Server Hardware items to Ironic, for which we do not know
when they are going to be used, will result in hardware reserved but not in
use, which from many perspectives, specially for OneView users, is
undesirable.

The ability to dynamically allocate nodes is currently missing from the set of
OneView drivers. By adding this feature, the drivers will be able to have
OneView resources allocated to Ironic only at boot time. Thus, this will
enable the hardware pool to be actually shared among OneView and Ironic users.

Proposed change
===============

In order to support dynamic allocation of nodes, some steps in the process
of validating and deploying an OneView node need to be changed.

A node will be considered to be free for Ironic when (1) there is no Server
Profile applied to the Server Hardware the node represents, or (2) there is
a Server Profile applied, but this Server Profile is consistent with what
is registered in Ironic's node data structure. This means that the Server
Profile's URI is equal to the value of the field ``applied_server_profile_uri``
in the ``driver_info`` namespace of the given node in Ironic.

Therefore, the following rules define the ownership of the node:

- SH without server_profile
  - Free
- SH.server_profile == node.driver_info.applied_server_profile_uri
  - Used by Ironic
- SH.server_profile != node.driver_info.applied_server_profile_uri
  - Used by OneView

When following this approach, a Server Profile is no longer required to
validate a node. The ``validate`` methods of the ``Power`` and ``Management``
interfaces of the driver must be changed.

In the proposed model, if a node is not free for Ironic (i.e., it is being
used by OneView) the validation will fail. However, as we expect nodes that
are used by OneView to be moved to ``manageable`` and be cleaned before being
made available again in Ironic, if the ``target_provision_state`` of a node is
``manageable``, then this check will be skipped.

A node free for Ironic can be claimed by a OneView user at any moment. In that
case, the node would still appear to be ``available`` in Ironic. To settle this
case, a driver periodic task will be issued to detect nodes in use by OneView
users and set them to ``manageable`` state and put into maintenance mode with a
proper maintenance reason message. As soon as the node is freed by the OneView
user, another driver periodic task will remove the maintenance mode and
``provide`` the node back into available. This is necessary to ensure the node
is cleaned before being provided to an Ironic user.

If such node is scheduled for deployment prior to the execution of the periodic
task, it will go to the ``deploy failed`` state and enter the cleaning process,
that should fail since the node is in use by a OneView user. Nova scheduler
will be able to pick a different node. A third periodic task will then be
responsible to detect such failures and move the node back to ``manageable``
state and set maintenance mode until freed.

Some changes in the cleaning process must also be considered. In order to
clean a node, a Server Profile needs to be assigned to it. Considering that,
if a node has no Server Profile applied to it, a new temporary one will be
created based on the Server Profile Template of this node, and applied to such
hardware for cleaning purposes. If there is a Server Profile already applied to
the node, it will be reused. After the cleaning is complete, in both cases,
such Server Profile will be removed.

From a technical perspective, the ``iscsi_pxe_oneview`` and
``agent_pxe_oneview`` drivers will now implement:

- oneview.deploy.OneViewIscsiDeploy
- oneview.deploy.OneViewAgentDeploy

Both interfaces will override three methods:

- ``prepare_cleaning``:

If the node is in use by OneView, an exception will be raised and the node
goes to the ``clean failed`` state. Otherwise, cleaning steps will be performed
and additional actions taken according to the following:

    - If there is no Server Profile assigned to the node's Server Hardware:
        - Server Profile will be created according to the Server Profile
          Template of the node;
        - Such Server Profile will be applied to the Server Hardware the
          node represents;
        - ``applied_server_profile_uri`` field will be added to the
          ``driver_info`` namespace of the node;

- ``tear_down_cleaning``:

If the node is in use by Ironic, the following actions will be taken:

  - ``applied_server_profile_uri`` field will be deleted from the
    ``driver_info`` namespace of the node;
  - Server Profile will be removed from the Server Hardware the node
    represents;

- ``prepare``:

If the node is in use by OneView, an exception will be raised and the node
goes to a ``deploy failed`` state. Otherwise, additional actions will be taken
as follows:

  - Server Profile is applied to the Server Hardware represented by the node.
    The information required to perform such task will be recovered from the
    Server Profile Template indicated in the ``server_profile_template_uri``
    inside the ``properties/capabilities`` namespace of the node.
  - ``applied_server_profile_uri`` field will be added to the
    ``driver_info`` namespace of the node;

The interfaces will also implement three new driver periodic tasks:

- ``_periodic_check_nodes_taken_by_oneview``:

This driver periodic task will check for nodes that were taken by OneView users
while the node is in available state and set the node to maintenance mode with
an appropriate maintenance reason message and move the node to ``manageable``
state.

- ``_periodic_check_nodes_freed_by_oneview``:

This driver periodic task will be responsible to poll the nodes that are in
maintenance mode and on ``manageable`` state to check if the Server Profile was
removed, indicating that the node was freed by the OneView user. If so, it'll
``provide`` the node, that will pass through the cleaning process and become
available to be provisioned.

- ``_periodic_check_nodes_taken_on_cleanfail``

This last driver periodic task will take care of nodes that would be caught on
a race condition between OneView and a deploy by Ironic. In such cases, the
validation will fail, throwing the node on ``deploy fail`` and, afterwards on
``clean fail``. This task will set the node to maintenance mode with a proper
reason message and move it to ``manageable`` state, from where the second task
can rescue the node as soon as the Server Profile is removed.

A new configuration will be created on ``[oneview]`` section to allow operators
to manage the interval in which the periodic tasks will run::

    [oneview]
    ...
    periodic_check_interval=300


Alternatives
------------

Today, there is no other way to enable dynamic allocation of nodes with the
OneView drivers.

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

"ironic" CLI
~~~~~~~~~~~~
None

"openstack baremetal" CLI
~~~~~~~~~~~~~~~~~~~~~~~~~
None

RPC API impact
--------------
None

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

When a machine previously in use by an OneView user is released, its disks are
not erased in the process since OneView does not perform such cleaning tasks.
This means that once a node is released, some remaining data from its previous
user can be available for Ironic. To prevent this leftover data from being
exposed to Ironic users, the driver will move these machines to ``manageable``
state through its periodic tasks, where Ironic will require them to go through
cleaning before being made ``available`` again. Note that if the cleaning
feature is disabled in Ironic, OneView users are responsible for manually erase
such disks prior to releasing the hardware.

Other end user impact
---------------------
None

Scalability impact
------------------
None

Performance Impact
------------------

In most cases, applying a Server Profile in OneView takes less than 2
minutes.

In the few cases it can take longer, e.g. in firmware upgrades, the user
must configure timeouts accordingly. Documentation will be provided on how
to do it.

The performance impact of the periodic tasks on Ironic conductor will be
proportional to the number of nodes being managed since they'll poll nodes in
OneView to check if nodes were taken/returned by OneView users. We'll minimize
that impact by polling only nodes on specific known states as said previously
on this spec. Yet, the ``periodic_check_interval`` can be adjusted according to
OneView usage behavior and the number of nodes enrolled to reach an optimized
performance of the conductor.

Other deployer impact
---------------------

After this change is merged, the way the OneView drivers allocate nodes
will be different. Deployers should be aware that:

- For existing nodes hosting instances, the ``applied_server_profile_uri``
  field must be added to the ``driver_info`` namespace of the node.
- Nodes that had a Server Profile assigned to them but were not actually
  in use (according to the ``pre-allocation`` model), can have their Server
  Profiles removed and still be available in Ironic.

In order to ease this process, a migration tool will be provided. Check
``Upgrades and Backwards Compatibility`` for more details.

Developer impact
----------------
None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  liliars

Other contributors:
  sinval
  thiagop
  gabriel-bezerra
  marcusrafael
  nicodemos
  caiobo

Work Items
----------

- Implement oneview.deploy.OneViewIscsiDeploy
- Implement oneview.deploy.OneViewAgentDeploy
- Override ``prepare``, ``prepare_cleaning``, ``tear_down_cleaning`` methods
  for both interfaces
- Implement the driver periodic tasks to deal with nodes taken by OneView users
- Write tests for such scenarios
- Document these changes

Dependencies
============

- python-oneviewclient version will be bumped

Testing
=======

- Unit-tests will be implemented for the changes;
- The OneView third party CI will be used to provide a suitable test
  environment for tests involving a OneView appliance and specific hardware;

Upgrades and Backwards Compatibility
====================================

As said in ``Other deployer impact`` section of this spec, to migrate nodes
that are in use with the ``pre-allocation`` model, one should add the field
``applied_server_profile_uri`` to the ``driver_info`` namespace of the node.
Nodes that are on ``available`` state needs to have their Server Profiles
removed. To ease this upgrade process on running deployments of Ironic, a
migration tool will be provided and properly referenced in the driver's
documentation.

Operators might have to increase the value of ``workers_pool_size`` and
``periodic_max_workers`` settings to allow to increase the greethread pool size
and allow more than one parallel task to deal with nodes taken/returned on each
periodic task as the pool of nodes on OneView increases.

Deprecation policy for ``pre-allocation``:

* Newton:

  * Both pre-allocation and dynamic allocation will be supported
  * Flag to indicate whether dynamic allocation is enabled in driver_info
  * Driver defaults to pre-allocation in case the flag is missing
  * Script provided to ease migration process.
  * Deprecate ``pre-allocation`` feature in the driver code.

* Ocata:

  * Both pre-allocation and dynamic allocation will continue to be supported
    (due to deprecation process)

* P:

  * Drop support of ``pre-allocation``
  * Flag ignored.

Documentation Impact
====================

OneView drivers documentation will be updated accordingly. Some topics to be
addressed are as follow:

- Definition of the new dynamic allocation model;
- Addition of fields in the node;
- Information regarding the migration process from the ``pre-allocation`` model
- New configuration options and possible improvements;

References
==========

OneView page
    http://www8.hp.com/ie/en/business-solutions/converged-systems/oneview.html
OneView 2.0 REST API Reference
    http://h17007.www1.hp.com/docs/enterprise/servers/oneview2.0/cic-rest/en/content/
python-oneviewclient
    https://pypi.org/project/python-oneviewclient
