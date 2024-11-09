..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

**********************
Lenovo XClarity Driver
**********************

https://bugs.launchpad.net/ironic/+bug/1702508

This specification proposes to add new interfaces that provide Ironic support
to Lenovo XClarity managed servers. Servers that are supported by XClarity
today are provided in the references at the end of this specification.

Problem description
===================

Lenovo servers use an IMM GUI which brings forth a unique way of managing the
nodes. The nodes need to be created, managed and operated by the XClarity
Administrator GUI tool and are identified by a unique host id.

In addition to managing the nodes using IPMI protocol, this specification
proposes to add hardware types and interfaces to manage Lenovo servers using
XClarity Administrator RESTful API. The REST API documentation for XClarity
is provided in the references at the end of the document. Benefits of using
XClarity over plain IPMI are: better user management, hardware monitoring and
hardware management.

Proposed change
===============
New power and management interfaces will be added as part of
this change.

The interfaces use RESTful API to communicate with XClarity Administrator.
The interfaces used are:

    * XClarity.XClarityPower for Power operations
    * XClarity.XClarityManagement for Management operations

The XClarity Administrator RESTful API provides various operations, like
controlling the power of nodes, retrieving firmware version and
Feature on Demand(FoD) enablement information, etc.

The multiple interfaces embed the client side code for communicating with
XClarity API via HTTP/HTTPS protocol, as a simple wrapper class. For all the
interfaces, an "xclarity-client" will to be imported. The xclarity-client is
available at https://pypi.python.org/simple/xclarity-client/.

* Power:

  This feature allows the user to turn the node on/off or reboot by using the
  power interface which will in turn call XClarity's REST API.

* Management:

  This feature allows the user to get and set the primary boot device of the
  Lenovo servers, and to get the supported boot devices.

Alternatives
------------
Use of the generic IPMI interfaces and pre-existing deploy interfaces is an
alternative especially in mixed configurations.

Data model impact
-----------------
None

RPC API impact
--------------
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

Driver API impact
-----------------
None

Nova driver impact
------------------
None

Security impact
---------------
Use of HTTPS for this interface, and verifying certificates is more secure
than IPMI-based interfaces.

Lenovo XClarity Administrator uses certificates to establish secure, trusted
communications between XClarity and its managed devices. By default, the
managed devices use XClarity-generated certificates. The user can choose to
let Lenovo XClarity Administrator manage certificates, or customize and
replace the server certificates. XClarity provides options for customizing
certificates depending on the user's requirements.

Other end user impact
---------------------
None

Scalability impact
------------------
There are some locking considerations when we are dealing with scale.
All locking is within a primary job/task framework which are profile
activation, firmware update, and OS deploy. A client will initiate a job
on an XClarity API endpoint, at which time it is locked from other jobs or
client actions until the job completes.

There is an additional mechanism used by Firmware Updates to prevent inventory
from refreshing from events, so commands are not sent to the IMM during the
update. A second level of locking is when a client attempts power actions, and
during the power request the endpoint is locked. This is generally very quick
though.

Performance Impact
------------------
Lenovo XClarity Administrator supports the management of up to 20 chassis with
compute nodes and a similar number of rack servers. An operator with a large
number of systems being managed by XClarity should expect reduced system
performance. Performance considerations have been provided in references at the
end of this specification.

Ramdisk impact
--------------
None

Other deployer impact
---------------------
The following driver_info fields are required while enrolling node into Ironic:

    * xclarity_address: XClarity Administrator IP-Address
    * xclarity_username: XClarity Administrator username
    * xclarity_password: XClarity Administrator password
    * xclarity_hostid: The host ID that is allocated by XClarity Administrator
      for each managed host.
    * xclarity_port(optional): The port used for establishing xClarity
      Administrator connection. Default is 443.

Developer impact
----------------
None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
    Hu Bian (hubian1@lenovo.com)

Other contributors:
    Jia Pei (jiapei2@lenovo.com)
    Haijun Mao (maohj2@lenovo.com)
    Finix Lei (leilei4@lenovo.com)
    Rushil Chugh (crushil)


Work Items
----------
* Add new XClarity hardware type, and adding new interfaces for Power
  and Management.

* Writing appropriate unit tests to provide test coverage for XClarity driver.

* Writing configuration documents.

* Third party CI-setup.

Dependencies
============
None

Testing
=======
* Unit tests will be implemented for new XClarity driver.

* Third party Continuous integration (CI) support will be added for Lenovo
  servers.

Upgrades and Backwards Compatibility
====================================
None

Documentation Impact
====================
* Updating Ironic documentation section `Enabling Drivers`
  with XClarity related instructions.

References
==========
* `XClarity Restful API introduction <http://flexsystem.lenovofiles.com/help/topic/com.lenovo.lxca_restapis.doc/lxca_rest_api_guide_v1.3.0.pdf>`_
* `XClarity Supported servers <http://flexsystem.lenovofiles.com/help/index.jsp?topic=%2Fcom.lenovo.lxca.doc%2Fplan_supportedhw.html>`_
* 'XClarity Performance considerations <http://flexsystem.lenovofiles.com/help/index.jsp?topic=%2Fcom.lenovo.lxca.doc%2Fplan_performconsiderations.html>'_
