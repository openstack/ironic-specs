..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Seamicro Serial Console
==========================================

https://blueprints.launchpad.net/ironic/+spec/seamicro-serial-console

This blueprint implements console driver -- "ShellinaboxConsole" which
support serial console access for Seamicro Fabric Compute system.

Problem description
===================

Currently there is no support to get the serial console for physical server
configured within the Seamicro Fabric Compute system.

Proposed change
===============
Implements a console driver -- "ShellinaboxConsole" -- that uses
telnet+shellinabox to connect to serial console of physical servers
configured within the Seamicro Fabric Compute system. SeaMicro System
provides telnet facility to connect to any of it's physical server's serial
console. Port to which we telnet depends on server-id. "server-id" here,
is what SeaMicro box refers to it's server and not ironic node's uuid.
We already have the required information (server-id) captured as part of
driver_info. Following are details,

* Use existing ironic/drivers/modules/console_utils module to start/stop
  shellinabox. IPMI driver already use shellinabox to access their serial
  console.

* Add seamicro_terminal_port property to CONSOLE_PROPERTIES. This is going
  to be port on which shellinabox listens locally.

* Add new class ShellinaboxConsole inherited from base.ConsoleInterface
  in ironic/drivers/modules/seamicro.py

* Implement the following methods in ShellinaboxConsole class.
    - ``validate()`` - Validate the Node console info.
          - param task : a task from TaskManager.
          - raises : InvalidParameterValue

    - ``start_console()`` - Start a remote console for the node.

    - ``stop_console()`` - Stop the remote console session for the node.

    - ``get_console()`` - Get the type and connection information about the
      console.

* Add self variable self.console in PXEAndSeaMicroDriver.


Alternatives
------------
None

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
The following which are already part of driver_info fields are required:
  * ``seamicro_api_endpoint`` - hostname or IP address of seamicro
  * ``seamicro_username`` - seamicro username
  * ``seamicro_password`` - seamicro password
  * ``seamicro_server_id`` - seamicro server id

Additionally one field need to be provided with driver_info
  * ``seamicro_terminal_port`` - node's UDP port to connect to. Only required
    for console access.

Developer impact
----------------
None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  harshada-kakad

Work Items
----------
Implement ``ShellinaboxConsole`` class inherited from
``base.ManagementInterface``.
Implement ``validate`` , ``start_console``, ``stop_console``, ``get_console``.


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
As part of this blueprint I would be documenting usage of this feature.

References
==========
None
