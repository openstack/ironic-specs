..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

================================================
In-band cleaning support in iSCSI deploy drivers
================================================

https://bugs.launchpad.net/ironic/+bug/1526405

Current deploy drivers that make use of iSCSI don't support in-band
cleaning.  We need to make these drivers support in-band cleaning operations
as well.

Problem description
===================

Drivers that do iSCSI based deployment don't support in-band cleaning today.
Hence in-band cleaning steps like disk erase, in-band RAID configuration, etc
cannot be performed on these nodes which are registered with these drivers.

The following drivers (omitting the testing drivers) do iSCSI based deployment
today:

* pxe_{ipmitool,ipminative,seamicro,iboot,ilo,
       drac,snmp,irmc,amt,msftocs,ucs,wol}
* iscsi_ilo
* iscsi_irmc

Proposed change
===============

* Deprecate the opt ``CONF.agent.agent_erase_devices_priority`` and move that
  to ``CONF.deploy.agent_erase_devices_priority``.

* Add the following methods to iscsi_deploy.ISCSIDeploy (these methods will do
  the same things as what AgentDeploy does today)

  + ``prepare_cleaning`` - This method will create the Neutron cleaning ports
    for each of the Ironic ports and will call ``self.boot`` to prepare for
    booting the ramdisk and return ``states.CLEANWAIT``. The method definition
    will be as follows::

        def prepare_cleaning(self, task):
            """Boot into the agent to prepare for cleaning.

            :param task: a TaskManager object containing the node
            :raises NodeCleaningFailure: if the previous cleaning ports cannot
                be removed or if new cleaning ports cannot be created
            :returns: states.CLEANWAIT to signify an asynchronous prepare
            """

  + ``tear_down_cleaning`` - This method will delete the cleaning ports created
    for the Ironic ports and will call ``self.boot`` to clean up the ramdisk
    boot.  It will return None.  The method definition will be as follows::

        def tear_down_cleaning(self, task):
            """Cleans up the environment after cleaning.

            :param task: a TaskManager object containing the node
            :raises NodeCleaningFailure: if the cleaning ports cannot be
                removed
            """

  + ``execute_clean_step`` - This method will call
    ``deploy_utils.agent_execute_clean_step``.  The method definition will be
    as follows::

        def execute_clean_step(self, task, step):
            """Execute a clean step asynchronously on the agent.

            :param task: a TaskManager object containing the node
            :param step: a clean step dictionary to execute
            :raises: NodeCleaningFailure if the agent does not return a command
                status
            :returns: states.CLEANWAIT to signify the step will be completed
                async
            """

  + ``get_clean_steps`` - This method will call
    ``deploy_utils.agent_get_clean_steps`` to get the cleaning steps from the
    agent ramdisk.  It will also reassign the cleaning priority to disk erase.

    This will return an empty list if bash ramdisk is used.  It will be
    detected by checking if ``agent_url`` is present in node's
    driver_internal_info.

    The method definition will be as follows::

        def get_clean_steps(self, task):
            """Get the list of clean steps from the agent.

            :param task: a TaskManager object containing the node
            :returns: A list of clean step dictionaries. Returns an
                empty list if bash ramdisk is used.
        """

* For deployers who have been using DIB ramdisk, the node will be stuck i
  n ``states.CLEANWAIT`` when they try to do cleaning.  This is because
  DIB ramdisk doesn't heartbeat like agent ramdisk.  Hence, such deployers
  might face the issue with nodes moving to ``states.CLEANFAIL``
  as node enters cleaning.  To overcome this problem, the following
  will be done:

  + Send the bash ramdisk parameters (deploy_key, iscsi_target_iqn, etc) while
    booting the deploy ramdisk for cleaning. It will enable bash ramdisk to
    invoke pass_deploy_info vendor passthru.

  + If node is in CLEANWAIT in pass_deploy_info vendor passthru, then we set
    the clean steps for the node and ask conductor to resume cleaning.

  + We also skip validation for pass_deploy_info vendor passthru if node is
    in CLEANWAIT state.


Alternatives
------------

None.

Data model impact
-----------------

None.

State Machine Impact
--------------------

None.

REST API impact
---------------

None.

Client (CLI) impact
-------------------

None.

RPC API impact
--------------

None.

Driver API impact
-----------------

None.

Nova driver impact
------------------

None.

Security impact
---------------

Drivers using ``iscsi_deploy.ISCSIDeploy`` will do in-band disk erase which
will be a security benifit for tenants.

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

None.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  rameshg87

Work Items
----------

* Add new methods the ``iscsi_deploy.ISCSIDeploy`` for in-band cleaning.
* Modify pass_deploy_info to make it ready when it is invoked during
  cleaning.


Dependencies
============

* Completion of work for deploy-boot interface separation [2] to enable in-band
  cleaning for all drivers.

Testing
=======

Unit tests will be added.


Upgrades and Backwards Compatibility
====================================

None.

Documentation Impact
====================

The new CONF option and it's impact will be documented.


References
==========

[1] http://specs.openstack.org/openstack/ironic-specs/specs/approved/deprecate-bash-ramdisk.html
[2] https://blueprints.launchpad.net/ironic/+spec/new-boot-interface
