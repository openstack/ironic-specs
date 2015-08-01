..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
DRAC Power Driver for Ironic
==========================================

https://blueprints.launchpad.net/ironic/+spec/drac-power-driver

The proposal presents the work required to add support for power management
features for Dell Remote Access Controller in Ironic.


Problem description
===================
Dell Remote Access Controller is an interface card from Dell offering a remote
system management. This proposal adds the power management capabilities for
DRAC.

Proposed change
===============
Adding a new DracDriver to the list of available drivers in Ironic and
implementing the DracPower module to interact with WS-Management API "(WS-Man)"
described in the ``DCIM Base Server and Physical Asset Profile`` using the
python binding of the OpenWSMAN library.

Alternatives
------------
There are other ways to interact with WS-Management endpoints but they are
wrappers around OpenWSMAN command-line client. These are:

* `Recite <http://en.community.dell.com/techcenter/systems-management/w/wiki/3757.recite-interactive-ws-man-scripting-environment.aspx>`_

* `Python WSMAN API <http://en.community.dell.com/techcenter/systems-management/w/wiki/3560.python-wsman-api-open-source.aspx>`_

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
Admin credentials will be stored unencrypted in the DB and they will be visible
in the driver_info field of the node when a node-show is issued.

Other end user impact
---------------------
The following driver_info fields are required:
  * drac_host: hostname or IP of the WS-Man endpoint
  * drac_port: port of the WS-Man endpoint (*default value is 443, assuming the
    user configured the endpoint in secure mode*)
  * drac_path: path of the WS-Man endpoint (*default value is '/wsman'*)
  * drac_protocol: protocol of the WS-Man endpoint (*default value is 'https',
    assuming the user configured the endpoint in secure mode*)
  * drac_username: username for the WS-Man endpoint
  * drac_password: password for the WS-Man endpoint

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
  ifarkas

Other contributors:
  None

Work Items
----------

* Add DracDriver

* Implement DracPower module for the DracDriver

Dependencies
============

* This feature depends on the python binding of the OpenWSMAN library. It's
  released under a simplified BSD licence and is available as a supported
  package in Ubuntu and Red Hat repositories.

* This feature requires 11th or 12th generation of Dell PowerEdge servers.

Testing
=======

* Unit tests

* 3rd-party CI: we would like to do it for this driver, but do not have
  sufficient hardware available at this time.

Documentation Impact
====================

The required driver_info properties need be included in the documentation to
instruct operators how to use Ironic with DRAC.

References
==========

* `OpenWSMAN library <http://openwsman.github.io/>`_

* `DCIM Base Server and Physical Asset Profile 1.0 <http://en.community.dell.com/techcenter/systems-management/w/wiki/3510.dcim-base-server-and-physical-asset-profile-1-0.aspx>`_
