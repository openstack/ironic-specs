..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==================================================
New driver in Ironic for OneView
==================================================

https://bugs.launchpad.net/ironic/+bug/1526406

This spec proposes adding a new driver that supports deployment of servers
managed by OneView. OneView is an Integrated Infrastructure Systems Management
Software developed by HP.

In this spec, *Server Hardware* is the label used on OneView to denote a
physical server.


Problem description
===================

Currently Ironic does not have integration with any Infrastructure Management
System. Nowadays, being able to use hardware from these systems inventory to
provision a baremetal instance is a manual/time consuming task that would
require pre-configuration of each server. OneView eases this configuration
workload.

This spec proposes a new Ironic OneView driver that will promote integration
with the HP OneView Management System. The proposed driver will provide
automatic inventory management with OneView, allowing Ironic to borrow
non-dedicated servers from OneViews's inventory to provision baremetal
instances with minimal common pre-configuration, set through OneView's *Server
Profile Templates* (SPT).

In order to use a Server Hardware managed by OneView, one needs to assign it a
*Server Profile*, prior to the enrollment of the node, in order to configure
the hardware to be used (select/update firmware, enable NIC's, setup the
network connections on them, BIOS/UEFI settings, initialize storage and so on).
The cloud administrator can take advantage of such a resource to configure the
server's NIC to use the Ironic provision network on the fly as needed, along
with other options that could allow optimal performance.

Proposed change
===============

This spec proposes the `pxe_oneview` and `agent_oneview` drivers, implementing
the Power, Management and, in the case of the Agent driver, Vendor interfaces.

The driver uses `python-oneviewclient` in order to handle the communication
between the driver and OneView for, e.g., getting information about a resource,
turning a server hardware on and off, and handling the configuration of a
server profile.

Server profiles are based on SPT's, which have information to configure the
hardware NIC to join a flat network, initialize the server storage and other
configuration options used by Ironic like boot_type and boot_order. The SPT
can also hold specific configuration options to improve the hardware
performance for Ironic, like Advanced Memory Protection, USB boot, enable
Virtualization Technology and HyperThreading, change the thermal configuration
and so on. Based on this premises, to be enrolled, the node MUST have
the following parameters:

- driver_info
    - server_hardware_uri: URI of the Server Hardware on OneView
    - server_profile_template_uri: URI for the Server Profile Template used to
      create the Server Profile of the node. This will be used on the future to
      change the Server Profile of the node on a zapping task.
- properties/capabilities
    - server_hardware_type_uri: URI for the Server Hardware Type on OneView,
      for scheduling purposes if one wants to deploy on specific hardware
      determined on the flavor.
    - enclosure_group_uri: URI for the Enclosure Group on OneView, for
      scheduling purposes if one wants to deploy on specific enclosure
      determined on the flavor.

The driver implements:

- oneview.power.OneViewPower
- oneview.management.OneViewManagement
- oneview.vendor.AgentVendorInterface

Power Interface:
    The `*_oneview` driver's Power Interface controls and synchronizes the
    power state of the nodes using OneView's REST API. The validate() method on
    this interface will check the required parameters and if the node already
    has a server profile associated.

Management Interface:
    The `*_oneview` driver's Management Interface allows the user to get and
    set the boot-order of a server hardware by modifying the server profile
    assigned to the server hardware. If no server profile is assigned yet
    to an instance, an exception will be thrown since the boot order of a
    server managed by OneView can only be modified through a server profile.
    The validate() method on this interface will also check the required
    parameters and if the node already has a server profile associated.

Agent Vendor Interface:
    The `agent_oneview` interface modifies the way `reboot_to_instance` method
    sets the boot device since OneView doesn't allow such a change with the
    machine powered on.

This driver reuses PXEBoot for boot and ISCSIDeploy/AgentDeploy for deploy.

To be deployed using the `*_oneview` driver, the node's Server Profile MUST be
applied to the server hardware the node represents. This Server Profile MUST
connect the 1st NIC of the node to Ironic's provision network.

Alternatives
------------
We could use the already existing drivers (such as pxe_ipmitool, pxe_ilo,
iscsi_ilo or even agent_ilo) to launch instances managed by OneView. But then:
- We would lose the capability to manage these instances through OneView;
- If the node is being managed by OneView, without a Server Profile, and
deployed with other driver, another user can claim it by applying a Server
Profile and thus Ironic would lose control of the server;
- Without using OneView, the task of maintaining configuration consistency
between the Server Hardware items is manual, boring and time consuming.

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
The connection with OneView is by default secure using TLS with certificate
authentication, but the user can allow insecure connections by setting to
True the allow_insecure_connections field in the configuration file.

Other end user impact
---------------------
None

Scalability impact
------------------
The driver gets some data using `python-oneviewclient` through OneView's REST
API which is an external service. The calls are simple, but considering a large
amount of Server Hardware items a small increase in network traffic can happen.

Performance Impact
------------------
None

Other deployer impact
---------------------
The following parameters are required in the newly created [oneview] section on
ironic.conf:

- manager_url: OneView Manager url
- username: User account with admin/server-profile access privilege in OneView
- password: User account password in OneView
- allow_insecure_connections: Allow connections to OneView without a
  certificate signed by a trusted CA. Its default value is False.
- tls_cacert_file: The path to the certificate of a trusted CA to be used to
  verify the OneView certificate when insecure connections are not allowed
- max_polling_attempts: Max connection attempts to check changes on OneView

Developer impact
----------------
None

Implementation
==============

Assignee(s)
-----------
Primary assignee:
  thiagop

Other contributors:
  albertoffb
  caiobo
  diegolp
  liliars
  sinval
  afaranha

Work Items
----------

- Implement new `iscsi_pxe_oneview` and `agent_pxe_oneview` drivers.
- Implement unit-test cases for `*_oneview` driver.
- Write configuration documents.

Dependencies
============
* The driver requires `python-oneviewclient package <https://pypi.org/project/python-oneviewclient>`_.

Testing
=======
Unit-tests will be implemented for the new drivers. A third party CI will be
used in the future to provide a suitable test environment for tests involving
an OneView appliance.

Upgrades and Backwards Compatibility
====================================
None

Documentation Impact
====================
The required parameters on the node and `[oneview]` section of `ironic.conf`
will be included in the documentation to instruct operators how to use Ironic
with OneView.

References
==========
OneView Page
    http://www8.hp.com/ie/en/business-solutions/converged-systems/oneview.html
OneView REST API Reference
    http://h17007.www1.hp.com/docs/enterprise/servers/oneviewhelp/oneviewRESTAPI/content/images/api/index.html
python-oneviewclient
    https://pypi.org/project/python-oneviewclient
