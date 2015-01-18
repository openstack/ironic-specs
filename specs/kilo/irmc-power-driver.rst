..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

============================
iRMC Power Driver for Ironic
============================

https://blueprints.launchpad.net/ironic/+spec/irmc-power-driver

The proposal presents the work required to add support for power
management features for FUJITSU PRIMERGY iRMC, integrated Remote
Management Controller, Drivers in Ironic.


Problem description
===================
FUJITSU PRIMERGY iRMC is a BMC from FUJITSU offering a remote system
management. This proposal adds the power management capabilities for
iRMC.

Proposed change
===============
Adding new iRMC Driver, namely pxe_irmc, to the list of available
drivers in Ironic and implementing the iRMC power module to interact
with ServerView Common Command Interface (SCCI) described in `FUJITSU Software ServerView Suite, Remote Management, iRMC S4 -   integrated Remote Management Controller <http://manuals.ts.fujitsu.com/file/11470/irmc-s4-ug-en.pdf>`_

iRMC supports WS-MAN, CIM, SMASH CLP, IPMI, SNMP, and etc. ServerView
Common Command Interface (SCCI), however, is chosen since it is the
most capable among them.

ServerView Common Command Interface (SCCI) uses
`python-scciclient package <https://pypi.python.org/pypi/python-scciclient>`_.


Alternatives
------------
Standard IPMI can be used for the power management.

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
Admin credentials will be stored unencrypted in the DB and they will
be visible in the driver_info field of the node when a node-show is
issued. But only the ironic admin user will have access to the Ironic
DB and node details.

Other end user impact
---------------------
The following driver_info fields are required:

* irmc_address: hostname or IP of iRMC
* irmc_username: username for iRMC with administrator privileges
* irmc_password: password for irmc_username
* irmc_port: port number of iRMC (optional)
* irmc_auth_method: authentication method for iRMC (optional)

The following parameters are added into newly created [irmc] section
in the ironic configuration file which is typically located at
/etc/ironic/ironic.conf.

* port: default value of iRMC (80 or 443) port number. The default
  value is 443.
* auth_method: default value of iRMC authentication method (basic or
  digest). The default value is basic.
* client_timeout: default timeout for SCCI operations. The default
  value is 60 seconds.

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

Primary assignee:
  Naohiro Tamura (naohirot)

Other contributors:
  None

Work Items
----------
* Add iRMC Driver (pxe_irmc)

* Implement iRMC power module for the iRMC Drivers

Dependencies
============
* This feature requires at least BX S4 or RX S8 generation of FUJITSU
  PRIMERGY servers.

* This feature requires `python-scciclient <https://pypi.python.org/pypi/python-scciclient>`_ library.
  This dependency will be checked on calling __init__() of iRMC driver.

Testing
=======
* Unit Tests with mocking `python-scciclient <https://pypi.python.org/pypi/python-scciclient>`_ library.

* Fujitsu plans Third-party CI Tests

Upgrades and Backwards Compatibility
====================================
None

Documentation Impact
====================
The required driver_info fields and [irmc] section parameters in the
ironic configuration file need be included in the documentation to
instruct operators how to use Ironic with iRMC.

References
==========
* `FUJITSU Software ServerView Suite, Remote Management, iRMC S4 -   integrated Remote Management Controller <http://manuals.ts.fujitsu.com/file/11470/irmc-s4-ug-en.pdf>`_

* `iRMC Virtual Media Deploy Driver for Ironic <https://github.com/openstack/ironic-specs/tree/master/specs/kilo/irmc-deploy-driver.rst>`_

* `iRMC Management Driver for Ironic <https://github.com/openstack/ironic-specs/tree/master/specs/kilo/irmc-management-driver.rst>`_

* `python-scciclient package <https://pypi.python.org/pypi/python-scciclient>`_

* `DRAC Power Driver for Ironic <https://github.com/openstack/ironic-specs/blob/master/specs/juno/drac-power-driver.rst>`_

* `iLO Power Driver for Ironic <https://github.com/openstack/ironic-specs/blob/master/specs/juno/ironic-ilo-power-driver.rst>`_
