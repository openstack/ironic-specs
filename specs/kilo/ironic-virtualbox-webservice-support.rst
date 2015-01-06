..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=============================================
Add support for VirtualBox through WebService
=============================================

https://blueprints.launchpad.net/ironic/+spec/ironic-virtualbox-webservice-support

This change proposes to add ``PowerInterface`` and ``ManagementInterface``
of VirtualBox for testing purposes through VirtualBox WebService.

Problem description
===================

Some developers run Windows as the operating system on their development
machines. Such developers may use a linux VM running in VirtualBox as their
cloud controller.  There is no way for the developers to do testing of Ironic
on their laptop using VMs in the same VirtualBox Windows host (with
hardware-assisted virtualization) as bare metal nodes.  Developers may choose
to run kvm/qemu inside their VirtualBox VM but nested virtualization is really
slow (as there is no hardware assistance).

Currently, Ironic has support for using a VirtualBox VM as a bare metal target
and do provisioning on it. It works by connecting via SSH into the VirtualBox
host and running commands using VBoxManage. This works well if you have
VirtualBox installed on a Linux box. But when VirtualBox is installed on a
Windows box, configuring and getting SSH to work with VBoxManage is a
difficult (if not impossible) due to following reasons:

* Windows doesn't come with native SSH support and one needs
  to use some third-party software to enable SSH support on Windows.
* Even after configuring SSH, VBoxManage doesn't work remotely due to how
  Windows manages user accounts - the native Windows user account is
  different from the corresponding SSH user account, and VBoxManage doesn't
  work properly when done with SSH user account.
* Even after tweaking policies of VirtualBox application, the remote VBoxManage
  and VBoxSvc don't sync each other properly and often results in a crash.

Proposed change
===============

* VirtualBox comes with a very friendly WebService to manage the VMs remotely.
  This works by talking to a WebService running on the VirtualBox host using
  SOAP.

* A new python library named ``pyremotevbox`` will be written and will be
  available separately in Github and PyPI. Currently it is hosted in `Github`_.

* Write a new implementation of ``PowerInterface`` and ``ManagementInterface``
  named ``VirtualBoxPowerInterface`` and ``VirtualBoxManagementInterface``
  which uses the new python library to manage VirtualBox VMs.

* Create new drivers ``pxe_vbox``, ``agent_vbox`` for deploying on Virtualbox
  VMs. Also create a ``fake_vbox`` driver for testing purposes with fake
  deploy.


Alternatives
------------

Developers using Windows can continue to use nested virtualization
but it is really slow. Also getting SSH to work with Windows for VBoxManage
is very difficult and buggy.

Data model impact
-----------------

None.

REST API impact
---------------

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

None. This is used only on developer's own systems for testing purposes.

Other end user impact
---------------------

None.

Scalability impact
------------------

None.

Performance Impact
------------------

Developers running Windows will find it very fast to deploy on VMs run with
hardware-assisted virtualization rather than nested virtualization.

Other deployer impact
---------------------

The following driver_info fields are required:

* ``vbox_address`` - hostname or IP address of the VirtualBox host.
* ``vbox_username`` - the username for the VirtualBox host.
* ``vbox_password`` - the password for ``vbox_username``
* ``vbox_port`` - the port to be used by VirtualBox Web Service.  The default
  value will be 18083.
* ``vbox_vmname`` - the name of the VM in VirtualBox acting as bare metal.

Developer impact
----------------

None.

Implementation
==============

Assignee(s)
-----------

rameshg87

Work Items
----------

* Add VirtualBoxPowerInterface.
* Add VirtualBoxManagementInterface

Dependencies
============

* Depends on pyremotevbox library which is being developed. This library
  will be available in Github and PyPI for developers to install on their
  laptop and will have Apache license.


Testing
=======

Unit tests will be added.


Upgrades and Backwards Compatibility
====================================

None.


Documentation Impact
====================

How to use the changes with Windows VirtualBox will be documented in Ironic
wiki.


References
==========

None

.. _`Github`: https://github.com/rameshg87/pyremotevbox
