..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===========================
iLO Power Driver for Ironic
===========================

https://blueprints.launchpad.net/ironic/+spec/ironic-ilo-power-driver

This proposal adds the ability to manage power control for HP ProLiant servers
via iLO using iLO client python library.

Problem description
===================
The HP iLO subsystem is a standard component of HP ProLiant servers that
simplifies initial server setup, server health monitoring, power and thermal
optimization, and remote server administration. Our proposed Ironic IloDriver
will expose these capabilities in OpenStack to manage HP Proliant servers.

This proposal covers support for power management interfaces using iLO.

Proposed change
===============
To add a new IloPower() module which will conform to base.PowerInterface.
This module uses iLO credentials (ilo_address, ilo_username, ilo_password),
specified in driver_info property of the node to connect to target iLO.
It makes use of iLO client in proliantUtils library to talk to iLO.

HP iLO also supports more advanced power management features for monitoring
and power capping.  We would like to add support for these advanced vendor
specific features later on.

*NOTE*: Even though iLO uses SSL over port 443 for communication, ssh key based
authentication is not supported for RIBCL communication. iLO username/password
will need to be provided for talking to iLO.


Alternatives
------------
IPMI standard specification can be used for the power management.  But adding
a new power module allows the solution to be consistent with other future iLO
drivers for deploy, management in using a single iLO interface to do the
operations.

There is no functional benefit as of now in choosing this module over IPMI.


Data model impact
-----------------
None

REST API impact
---------------
None

Driver API impact
-----------------
None

Nova driver impact
------------------
None

Security impact
---------------
iLO admin credentials will be stored unencrypted in the Ironic DB.  This will
also be visible with the driver_info of the node when a node-show is issued.
But only the ironic admin user will have access to the Ironic DB and node
details.

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
  * ``ilo_address`` - hostname or IP address of the iLO.
  * ``ilo_username`` - the username for the iLO with administrator privileges.
  * ``ilo_password`` - the password for ``ilo_username``
  * ``ilo_client_timeout`` - the timeout for iLO operations. The default value
    will be 60 seconds.
  * ``ilo_client_port`` - the port to be used by iLO client for iLO operations.
    The default value will be 443.


Developer impact
----------------
None

Implementation
==============
Assignee(s)
-----------
Primary assignee:
  Ramakrishnan G (rameshg87)

Other contributors:
  Anusha Ramineni (anusha_08)

Work Items
----------
Implement a new power module, IloPower, conforming to base.PowerInterface.

Dependencies
============
*  This feature is targeted for HP ProLiant servers with iLO4 and above.
   This power module might work with older version of iLO (like iLO3), but this
   will not be officially tested by the iLO driver team.
*  Depends on proliantutils library.

Testing
=======
Unit tests will be added, mocking proliantutils library.

Tempest tests will be considered later when more advanced module of IloDriver
like deploy are available in the ironic tree.

Documentation Impact
====================
The required driver_info properties need be included in the documentation to
instruct operators how to use iLO Driver with Ironic.

References
==========
proliantutils library:
https://github.com/hpproliant/proliantutils
https://pypi.python.org/pypi/proliantutils

HP iLO4 User Guide:
http://h20628.www2.hp.com/km-ext/kmcsdirect/emr_na-c03334051-10.pdf

HP Power Capping and HP Dynamic Power Capping
http://bit.ly/1m8sbEi