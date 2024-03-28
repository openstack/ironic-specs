..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===============================
UEFI iSCSI Boot for iLO drivers
===============================

https://bugs.launchpad.net/ironic/+bug/1526861

HPE ProLiant Servers (Gen9 and beyond) supports UEFI iSCSI Boot through its
firmware. The proposed feature is to add support for this firmware based
booting of an iSCSI Cinder volume in UEFI mode for Ironic iLO drivers.

Problem description
===================

Currently, Ironic has ability to boot from Cinder volume. Moreover, this
support is to boot from an iSCSI volume using bootloaders like iPXE. It
doesn't provide any way to harness the feature of some servers which
inherently supports booting from an iSCSI volume using their firmware
capabilities. Hardware can be configured programmatically to boot from an
iSCSI volume through firmware.

Proposed change
===============

This change is based on the reference driver implementation guidelines
proposed by `Boot from Volume - Reference Drivers`_ spec to support booting
ironic nodes from a storage device that is hosted and/or controlled
remotely.
This change proposes two new methods for iLO drivers management interface;
namely ``set_iscsi_boot_target`` and ``clear_iscsi_boot_target``, which will
facilitate setting and clearing iSCSI target information using iLO
interfaces for UEFI iSCSI boot capable HPE Proliant servers.

The boot interface method ``prepare_instance()`` in ``ilo`` hardware type
will check if the instance requested boot mode is 'UEFI' and given volume is
bootable. If so, it will set the iSCSI target in the iLO and set boot device
to iSCSI target.

If the instance requested boot mode is 'BIOS' the behavior for the two boot
interfaces (``ilo-pxe`` and ``ilo-virtual-media``) will be as under:

* ``ilo-pxe`` : It will fallback to  iPXE to boot the volume.

* ``ilo-virtual-media``: It will throw the following error:
   ``virtual media cannot boot volume in bios.``

  The function definition for ``ilo-pxe`` boot interface with its pseudo-code
  will be as follows:

  .. code-block:: python

    class IloPXEBoot(pxe.PXEBoot):

      def prepare_instance(self, task):
        """Prepares the boot of instance.

        :param task: a task from TaskManager.
        :returns: None
        :raises: IloOperationError, if some operation on iLO failed.
        """
        if deploy_utils.is_iscsi_boot(task) and boot_mode == 'uefi':
          #Call the management interface
          task.driver.management.set_iscsi_boot_target(task)
          #Set boot device to 'ISCSIBOOT'
          deploy_utils.try_set_boot_device(task, boot_devices.ISCSIBOOT)

        else:
          #Let iPXE handle this
          super(IloPXEBoot, self).prepare_instance(task)

      def clean_up_instance(self, task):
        """Cleans up the boot of instance.

        :param task: a task from TaskManager.
        :returns: None
        :raises: IloOperationError, if some operation on iLO failed.
        """
        if deploy_utils.is_iscsi_boot(task) and boot_mode == 'uefi':
          #Call the management interface
          task.driver.management.clear_iscsi_boot_target(task)

        else:
          #Let iPXE handle this
          super(IloPXEBoot, self).clean_up_instance(task)

  The function definition for ``ilo-virtual-media`` boot interface with its
  pseudo-code will be as follows:

  .. code-block:: python

    class IloVirtualMediaBoot(base.BootInterface):

      def prepare_instance(self, task):
        """Prepares the boot of instance.

        :param task: a task from TaskManager.
        :returns: None
        :raises: IloOperationError, if some operation on iLO failed.
        """
        if deploy_utils.is_iscsi_boot(task) and boot_mode == 'uefi':
          #Call the management interface
          task.driver.management.set_iscsi_boot_target(task)
          #Set boot device to 'ISCSIBOOT'
          deploy_utils.try_set_boot_device(task, boot_devices.ISCSIBOOT)
          return

        elif deploy_utils.is_iscsi_boot(task) and boot_mode == 'bios':
          #Throw the error in bios boot mode
          msg = 'virtual media can not boot volume in bios mode.'
          raise exception.InstanceDeployFailure(msg)

        else:
          #Default code

      def clean_up_instance(self, task):
        """Cleans up the boot of instance.

        :param task: a task from TaskManager.
        :returns: None
        :raises: IloOperationError, if some operation on iLO failed.
        """
        if deploy_utils.is_iscsi_boot(task) and boot_mode == 'uefi':
          #Call the management interface
          task.driver.management.clear_iscsi_boot_target(task)
        else:
          #Fall to virtual media cleanup


Two new methods will be added in ``ilo`` drivers management interface
``ilo.management.IloManangement``:
* set_iscsi_boot_target() - To set iSCSI target information into iLO
* clear_iscsi_boot_target() - To clear iSCSI target information from iLO

New version of proliantutils library would be released that supports the
above mentioned methods.

  The function definition with its pseudo-code will be as follows:

  .. code-block:: python

    class IloManagement(base.ManagementInterface):

      def set_iscsi_boot_target(self, task):
        """Set iscsi boot volume target info from the node.

        :param task: a task from TaskManager.
        """
        #Proliants call to set iscsi target info

      def clear_iscsi_boot_target(self, task):
        """Clear iscsi boot volume target info from the node.

        :param task: a task from TaskManager.
        """
        #Library call to clear iscsi target info

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

None.

Ramdisk impact
--------------

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

Deployers will be able to configure server which support UEFI iSCSI boot with
this change. The workflow will be as follows:

* Operator configures the node with appropriate hardware type with boot
  interface and adds the capability ``iscsi_boot=true``  in
  ``node.properties['capabilities']`` (or it could be populated by
  inspection, but it's not part of this spec on how it gets populated).
* Operator creates a flavor with Compute capability ``iscsi_boot=true`` to
  request bare metal booting from Cinder volume.
* Tenant creates a Cinder volume.
* Tenant requests a bare metal instance to be booted up with a Cinder volume
  with the above mentioned flavor.
* Node having 'ilo-virtual-media' as boot interface with capability
  'iscsi_boot=true' should also have capability 'boot_mode' configured
  to 'uefi' only.
* Nova Ironic virt driver passes information about iSCSI volume to Ironic.
  For more information, refer ironic spec
  `Add volume connection information for Ironic nodes`_.

.. _`Add volume connection information for Ironic nodes`:  https://specs.openstack.org/openstack/ironic-specs/specs/9.0/volume-connection-information.html

Developer impact
----------------

None.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
    kesper
Other contributors:
    deray
    stendulker

Work Items
----------

* Need to add changes in ``ilo-pxe`` and ``ilo-virtual-media`` boot
  interfaces.

* Need to implement ``set_iscsi_boot_target`` and ``clear_iscsi_boot_target``
  in ``ilo`` management interface.

Dependencies
============
None.

Testing
=======

This feature would be tested using HPE iLO third-party CI.

Upgrades and Backwards Compatibility
====================================

None.

Documentation Impact
====================

iLO drivers documentation will be updated for this feature.

References
==========

* `Boot from Volume - Reference Drivers`_

.. _`add support in Ironic framework`: https://specs.openstack.org/openstack/ironic-specs/specs/approved/volume-connection-information.html
.. _`Boot from Volume - Reference Drivers`: https://specs.openstack.org/openstack/ironic-specs/specs/approved/boot-from-volume-reference-drivers.html
.. _`iLO UEFI Deployment Guide`: https://support.hpe.com/hpsc/doc/public/display?docId=c04565930
