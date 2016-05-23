..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===========
SSH Console
===========

https://bugs.launchpad.net/ironic/+bug/1526305

This implements console driver -- "ShellinaboxConsole" which
supports console access for SSH driver (only for virsh virt_type).

Problem description
===================

Currently there is no support to get the console for virtual machines
in dev and test environments.

Proposed change
===============
Implements a console driver -- "ShellinaboxConsole" -- that uses
ssh+shellinabox to connect to console of virtual machines:

* Use existing ironic/drivers/modules/console_utils module to start/stop
  shellinabox.

* Add ssh_terminal_port property to CONSOLE_PROPERTIES. This is going
  to be port on which shellinabox listens locally.

* Add new class ShellinaboxConsole inherited from base.ConsoleInterface
  in ironic/drivers/modules/ssh.py

* Implement the following methods in ShellinaboxConsole class.
    - ``validate()`` - Validate the Node console info.
          - param task : a task from TaskManager.
          - raises : InvalidParameterValue.
          - raises : MissingParameterValue.

    - ``start_console()`` - Start a remote console for the node.

    - ``stop_console()`` - Stop the remote console session for the node.

    - ``get_console()`` - Get the type and connection information about the
      console.

* Add self variable self.console in PXEAndSSHDriver and AgentAndSSHDriver.


Alternatives
------------
None

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
The following which is already part of driver_info field is required:
  * ``ssh_address`` - IP address or hostname of the node to ssh into.
  * ``ssh_username`` - Username to authenticate as.
  * ``ssh_virt_type`` - Virtualization software to use; must be virsh.

Additionally one field need to be provided with driver_info
  * ``ssh_terminal_port`` - Port to connect to, only required for
    console access.

Developer impact
----------------
None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  niu-zglinux

Work Items
----------
Implement ``ShellinaboxConsole`` class inherited from
``base.ManagementInterface``.
Implement ``validate`` , ``start_console``, ``stop_console``, ``get_console``.
Add ability to enable pty console in devstack scripts, and leave
the log console by default in order not to affect the gate logs.


Dependencies
============
None

Testing
=======
Unit Testing will be added.

Upgrades and Backwards Compatibility
====================================
None

Documentation Impact
====================
None

References
==========
None
