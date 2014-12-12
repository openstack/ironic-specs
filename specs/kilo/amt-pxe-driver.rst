..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
AMT PXE Driver
==========================================

https://blueprints.launchpad.net/ironic/+spec/amt-pxe-driver

This blueprint implements a new driver -- "PXEAndAMTDriver" which
supports deployment for AMT/vPro system on Desktops.

Problem description
===================

Currently there is no support with Ironic to do deployment for Desktops
within AMT/vPro system. This BP will extend Ironic to Desktop area.

Proposed change
===============
Implement a new driver -- "PXEAndAMTDriver" -- that uses
amt to control the power of nodes with AMT System and uses
pxe to deliver the image to nodes. Following are details,

* Add new class PXEAndAMTDriver inherited from base.BaseDriver
  in ironic/drivers/pxe.py

* Add new class AMTPower inherited from base.PowerInterface
  in ironic/drivers/modules/amt/power.py

  - ``validate()`` - Validate the node driver info

  - ``get_power_state()`` - Get the power state from the node

  - ``set_power_state()`` - Set the power state of the node,
    such as power on/off

  - ``reboot()`` - reboot the node

* Add new class AMTMangement inherited from base.ManagementInterface
  in ironic/drivers/modules/amt/management.py

  - ``validate()`` - Validate the node driver info

  - ``ensure_next_boot_device()`` - ensure the next boot device of the node

    .. note::
        AMT/vPro only accept the first boot device and ignore the rest
        if we send multiple _set_boot_device_order requests to AMT nodes.
        For example, when the user set boot device twice, the node will
        boot with the first one. So AMT driver only save amt_boot_device
        into DB via set_boot_device() and send the request to the node via
        ensure_next_boot_device() before set the node power on.
        So that AMT driver can support users to set boot device multiple times
        like other drivers.

  - ``set_boot_device()`` - Set the boot device of the node.

    .. note::
        As AMT/vPro doesnt support set boot device persistent in BM node
        like BMC, it only set boot device for one time. So AMT driver call
        ensure_next_boot_device() between every power cycle if boot device
        is persistent.
        AMT driver saves amt_boot_device/amt_boot_persistent into
        node.driver_internal_info, which will be read by
        ensure_next_boot_device().

  - ``get_boot_device()`` - Get the boot device of the node

* Add a condition to enable AMT driver to call ensure_next_boot_device in
  pxe._continue_deploy

   .. note::
        During PXE deploy processing, after finish dd, the target machine will
        reboot by ramdisk rather than Ironic. AMT Driver has to call
        ensure_next_boot_device again in _continue_deploy().

Alternatives
------------
* Save amt_boot_device and amt_boot_persistent in:
    * "driver_info" but user will aware the change of boot device and
      could be different from his input.

    * "extra" but not for use from inside Ironic.

Data model impact
-----------------
None

REST API impact
---------------
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
The following driver_info fields are required:

* amt_address: hostname or IP of AMT node
* amt_password: password used for connect to AMT node
* amt_username: username used for connect to AMT node
* amt_protocol: protocol used for connect to AMT node (optional)

The following parameters are added into newly created [amt] section
in ironic.conf.

* protocol: default value of AMT (http/https) protocol. The default
  value is http
* max_retry: default retries for AMT power operations. The default
  value is 3 times.
* action_wait: default seconds for driver to wait for retries. The default
  value is 10 seconds.

Developer impact
----------------
None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  tan-lin-good

Work Items
----------
Implement ``PXEAndAMTDriver`` class inherited from
``base.BaseDriver``.

Implement ``AMTPower`` class inherited from ``base.PowerInterface``

Implement ``AMTManagement`` class inherited from
``base.managementInterface``


Dependencies
============
openwsman-python package

    .. note::
        AMT deprecated SOAP (amttool) support after the latest version 9.0.
        http://en.wikipedia.org/wiki/Intel_AMT_versions
        "Intel AMT 9.0 — SOAP(EOI) protocol removed."
        So AMT only support WS-MAN protocol (openwsman) now.
        The solution with openwsman works for AMT 7.0/8.0/9.0.
        AMT 7.0 is released in 2010, so most PCs with vPro are involved.

Testing
=======
Will add Unit Testing.

Upgrades and Backwards Compatibility
====================================
None

Documentation Impact
====================
Will document the usage of this driver.

References
==========
None
