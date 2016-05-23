..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

======================
Add InfiniBand Support
======================

https://bugs.launchpad.net/ironic/+bug/1532534

Today, Ironic supports Ethernet interfaces for Hardware inspection and
PXE boot. Ironic should have the ability to inspect and PXE boot over
InfiniBand network as well.


Problem description
===================

* Hardware inspection for InfiniBand - A InfiniBand GUID is similar in concept
  to a MAC address because it consists of a 24-bit manufacturer’s prefix and
  a 40-bit device identifier (64 bits total).

* PXE Boot over InfiniBand - To allow DHCP over IPoIB interface the DHCP client
  must send the client-id with a unique identifying value for the
  client. The value is consist of the vendor prefix 12 bytes and GUID 8 bytes.
  Today ironic doesn't send update the neutron port with client-id option.

Proposed change
===============

* Hardware inspection for InfiniBand -  In order to use InfiniBand with PXE
  you have to flash the NIC with a vendor specific firmware. The vendor
  firmware defined the conversion of GUID to "InfiniBand MAC" (48 bits).
  To resource complicity of the change, the ironic address will contain the
  "InfiniBand MAC".

* PXE/iPXE Boot over InfiniBand changes:
  To allow DHCP over InfiniBand we need the following:

  1. The dhcp-server must use the BROADCAST flag in the dhcp-server.
     This already support in neutron-dhcp-agent by config file.

  #. Updating the ironic port extra attribute to contains the InfiniBand
     port client-id extra e.g::

        {
            'client-id':
            'ff:00:00:00:00:00:02:00:00:02:c9:00:00:02:c9:03:00:00:10:39'
        }

     The client-id update can be done manually or with IPA and
     ironic-inspector.

  #. The neutron port that represent the ironic port should be updated
     with client-id option in the extra_dhcp_opts attribute.
     The client-id consists of a vendor prefix and the port GUID.
     The client id for Mellanox ConnectX Family Devices is
     consists of a prefix (ff:00:00:00:00:00:02:00:00:02:c9:00) and
     8 byte port GUID. The prefix in the client-id is vendor specific.

  #. The PXE MAC file name consists of the <Hardware Type>-<MAC>.
     For InfiniBand the hardware Type is 20 and the mac is the
     InfiniBand truncate GUID.

  #. The iPXE MAC file name consists of the <MAC>.
     For InfiniBand the MAC is the InfiniBand truncate GUID.

Other projects changes:

   * ironic-python-agent changes:

     1. Update the ironic agent to calculate the InfiniBand truncate GUID
        and the Client ID.
     #. Update coreos  and tinyipa with ib_ipoib driver.

   * ironic-inspector changes:

     1. Update the ironic-inspector to update port.extra with client-id

   * diskimage-builder changes:

     1. Update the mellanox element to load ib_ipoib driver.

Alternatives
------------

* Extend the ironic port to support GUID which is 8 bytes and
  calculate the client-id in the ironic code from the GUID.
  This will require updating the ironic model and API.
  This will require updating the nova ironic driver to truncate
  the GUID to MAC.


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

"ironic" CLI
~~~~~~~~~~~~
None

"openstack baremetal" CLI
~~~~~~~~~~~~~~~~~~~~~~~~~
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

When using IPA, the deployer needs IPA that provides
the InfiniBand MAC and client-id.

Developer impact
----------------

None


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  moshele

Other contributors:
  None

Work Items
----------

* Add Client-ID option to the neutron port to allow DHCP.
* Update the generation of the iPXE/PXE file.
* Update documentation.


Dependencies
============

None


Testing
=======

* Adding unit tests.
* Adding Third-party CI which will test Mellanox hardware.


Upgrades and Backwards Compatibility
====================================

None


Documentation Impact
====================

* We will update the ironic documentation on how to allow
  pxe boot from IPoIB.


References
==========

* http://www.syslinux.org/wiki/index.php/PXELINUX
* https://tools.ietf.org/html/rfc4392
* http://www.mellanox.com/related-docs/prod_software/Mellanox_FlexBoot_User_Manual_v2.3.pdf
