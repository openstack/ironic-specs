..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==============================
Wake-On-Lan (WOL) power driver
==============================

https://blueprints.launchpad.net/ironic/+spec/wol-power-driver

This blueprint adds support for Wake-On-Lan (WOL) power interface
in Ironic.

Problem description
===================

Wake-On-Lan is a standard that allows a computer to be powered on by a
network message. This is widely available and doesn't require any fancy
hardware to work with. This is useful for users that want to try Ironic
with real bare metal instead of virtual machines and only have some old
PCs around.

Proposed change
===============

The proposed implementation consists of a driver power interface
implementation that will create and send Wake-On-Lan magic packets for
each port (MAC addresses) registered on the node resource in Ironic.

It's important to note that Wake-On-Lan is only capable of powering
**on** the machine. After the machine is unprovisioned it needs to
powered off manually.

Driver properties that can be specified by the user::
  **wol_host**: Broadcast IP address to send the magic packets. Defaults
  to ``255.255.255.255``.

  **wol_port**: Destination port to send the magic packets; defaults to
  ``9``.

When powering **off** is called we are just going to log a message
saying the operation isn't supported by the driver and require manual
intervention to be performed.

When **reboot**  is called the driver will try to power **on** the
machine.

When getting the power state of the node, the driver will rely on whatever
is in the Ironic database and return it, since we don't have any reliable
way of knowing the current power state of the machine.

Alternatives
------------

A alternative would be relying on some external mechanism to power control
the nodes. Such as ``iBoot`` which Ironic already have a driver for. But
for that the user will need to spend some money (~200 USD) to buy an
``iBoot`` device.

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

Security impact
---------------

This spec only covers the bits of sending a magic packet **without**
the ``SecureOn`` feature.

``SecureOn`` allows a client to append a password to the magic packet so
NICs that support the feature will check prior to powering on the machine
and if the MAC address + password are correct only then the system is
awake . This is good against ``brute force attacks``, but will be left
for future work.

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

None

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  lucasagomes

Other contributors:
  None

Work Items
----------

* Write the Wake-On-Lan power interface
* Write unittests

Dependencies
============

None

Testing
=======

Unittests will be added as part of the work.

Upgrades and Backwards Compatibility
====================================

None

Documentation Impact
====================

The driver should be documented under
http://docs.openstack.org/developer/ironic/index.html. The documentation
will also be clear about the use of this driver, this is a testing driver
and not meant for production use.

References
==========

* Wake-On-Lan: http://en.wikipedia.org/wiki/Wake-on-LAN
