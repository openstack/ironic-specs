..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

========================
Boot Interface in Ironic
========================

https://blueprints.launchpad.net/ironic/+spec/new-boot-interface

This spec talks about refactoring the boot logic out of the current Ironic
"deploy" drivers into a new boot interface.

Problem description
===================

Current we have a DeployInterface in Ironic.  All the current implementations
of this interface are responsible for two things:

* Booting the bare metal node - both deploy ramdisk and the deployed instance.
* Actual deployment of an image on a bare metal node.

These are two separate functions and therefore should be abstracted
separately. This makes it easy to mix and match various boot mechanisms (like
PXE, iPXE, virtual media) with various deploy mechanisms (iscsi deploy, agent
deploy and various other deploy mechanisms which may be possible like
deploying with torrent, multicast, etc in which discussions have been
initiated) without duplicating code.

Proposed change
===============

* A new ``BootInterface`` needs to be added.  The interface will recommend the
  following methods for the implementor::

   @six.add_metaclass(abc.ABCMeta)
   class BootInterface(object):
     """Interface for inspection-related actions."""

     @abc.abstractmethod
     def get_properties(self):
         """Return the properties of the interface.

         :returns: dictionary of <property name>:<property description>
        """

     @abc.abstractmethod
     def validate(self, task):
         """Validate the driver-specific info for booting.

         This method validates the driver-specific info for booting a ramdisk
         and an instance on the node.  If invalid, raises an exception;
         otherwise returns None.

         :param task: a task from TaskManager.
         :raises: InvalidParameterValue
         :raises: MissingParameterValue
         """

     @abc.abstractmethod
     def prepare_ramdisk(self, task, ramdisk_params):
         """Prepares the boot of Ironic ramdisk.

         This method prepares the boot of the deploy ramdisk after reading
         relevant information from the node's database.

         :param task: a task from TaskManager.
         :param ramdisk_params: the options to be passed to the ironic ramdisk.
             Different interfaces might want to boot the ramdisk in different
             ways by passing parameters to them.  For example,
             * When DIB ramdisk is booted to deploy a node, it takes the
               parameters iscsi_target_iqn, deployment_id, ironic_api_url, etc.
             * When Agent ramdisk is booted to deploy a node, it takes the
               parameters ipa-driver-name, ipa-api-url, root_device, etc.
             Other interfaces can make use of ramdisk_params to pass such
             information.  Different implementations of boot interface will
             have different ways of passing parameters to the ramdisk.
         """

     @abc.abstractmethod
     def clean_up_ramdisk(self, task):
         """Tears down the boot of Ironic ramdisk.

         This method tears down the boot of the deploy ramdisk after reading
         relevant information from the node's database.

         :param task: a task from TaskManager.
         """

     @abc.abstractmethod
     def prepare_instance(self, task):
         """Prepares the boot of instance.

         This method prepares the boot of the instance after reading
         relevant information from the node's database.

         :param task: a task from TaskManager.
         """

     @abc.abstractmethod
     def clean_up_instance(self, task):
         """Tears down the boot of instance.

         This method tears down the boot of the instance after reading
         relevant information from the node's database.

         :param task: a task from TaskManager.
         """

* The following new implementations of ``BootInterface`` will be created.

  + ``pxe.PXEBoot`` - Booting a bare metal node using PXE
  + ``ipxe.IPXEBoot`` - Booting a bare metal node using iPXE
  + ``ilo.boot.IloVirtualMediaBoot`` - Booting a bare metal node using iLO
    Virtual Media.

  .. note::
    Even though IPXEBoot and PXEBoot are in same deploy driver currently, the
    steps for preparing a bare metal to boot from PXE and iPXE are different
    (even though they share some common code).  We will refactor both of them
    as separate boot interfaces. The Kilo behaviour of using only either of
    PXE or iPXE at same time will be retained - drivers will instantiate
    pxe.PXEBoot or ipxe.IPXEBoot depending on CONF.pxe.ipxe_enabled.

* The code for the above implementations of ``BootInterface`` will be taken
  from ``pxe.PXEDeploy``, ``agent.AgentDeploy``,
  ``ilo.IloVirtualMediaIscsiDeploy`` and ``ilo.IloVirtualMediaAgentDeploy``.
  These implementations of ``DeployInterface`` will be freed of any logic
  dealing with booting of bare metal node.

* ``pxe.PXEDeploy`` will be refactored into ``pxe.PXEBoot`` and
  ``iscsi_deploy.ISCSIDeploy``.

* Each driver will mention what is the ``BootInterface`` implementation that it
  wishes to instantiate.  For example, the ``pxe_ipmitool`` driver will look
  like the following::

    class PXEAndIPMIToolDriver(base.BaseDriver):
      """PXE + IPMITool driver"""

      def __init__(self):
        self.power = ipmitool.IPMIPower()
        self.console = ipmitool.IPMIShellinaboxConsole()
        self.boot = pxe.PXEBoot()
        self.deploy = iscsi_deploy.ISCSIDeploy()
        self.management = ipmitool.IPMIManagement()
        self.vendor = pxe.VendorPassthru()
        self.inspect = discoverd.DiscoverdInspect.create_if_enabled(
            'PXEAndIPMIToolDriver')


.. note::

  It might make sense to rename the drivers to include the boot interface as
  well as deploy interface after this is implemented.  As such, this requires
  a better thought out process to rename the drivers, address issues of
  backward compatibility, etc. Hence it is out of scope of this spec.  That
  can be addressed later after this is implemented.

Alternatives
------------
We can continue to keep the boot and deploy logic together but this will
lead to code duplications and unnecessary refactorings when additional deploy
mechanisms and boot mechanisms are added in the future.

Data model impact
-----------------
None.

State Machine Impact
--------------------
None.

REST API impact
---------------
None.

RPC API impact
--------------
None.

Client (CLI) impact
-------------------
None.

Driver API impact
-----------------
This adds the a new ``BootInterface`` (as described above) which driver
writers may use with the deploy drivers.  ``BootInterface`` is not a
mandatory interface.

Nova driver impact
------------------
None.

Security impact
---------------
None.

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
New driver developers adding new deploy mechanisms in Ironic will be
encouraged to separate boot and deploy logic so that it can reused easily.

Implementation
==============

Assignee(s)
-----------
rameshg87

Work Items
----------
* Add new boot interface
* Create ``pxe.PXEBoot``, ``ipxe.IPXEBoot`` and refactor ``pxe.PXEDeploy``
  into ``iscsi_deploy.ISCSIDeploy`` to make use of these boot interfaces.
* Refactor ``agent.AgentDeploy`` to use new ``pxe.PXEBoot`` and
  ``ipxe.IPXEBoot`` (Yes, we are adding iPXE support for agent deploy).
* Create ``ilo.boot.IloVirtualMediaBoot``, and refactor
  ``IloVirtualMediaIscsiDriver``, ``IloVirtualMediaAgentDriver`` to make
  use of the new boot interface.

Dependencies
============
None.

Testing
=======
Unit tests will be updated for the new interfaces.  Since this change doesn't
add any new functionality, the current upstream CI testing should be enough.

Upgrades and Backwards Compatibility
====================================
This doesn't break out-of-tree deploy drivers.  Still it will be possible
to implement deploy drivers for provisioning bare metal nodes without a boot
interface- i.e without separate boot and deploy interfaces. This is because
the conductor will still be using all the published interfaces of
``DeployInterface`` for deploying a bare metal node.

This change proposes the addition of new optional boot interface which can be
used as a helper for ``DeployInterface`` and refactors all upstream deploy
drivers to follow this logic.

Documentation Impact
====================
Changes to the existing interface will be documented.  Also, new developer
documentation will be updated to encourage splitting deploy logic into separate
boot and deploy interfaces.

References
==========
Not according to this spec, but a POC how it will look like:
* https://review.openstack.org/#/c/166512/
* https://review.openstack.org/#/c/166513/
* https://review.openstack.org/#/c/166521/
