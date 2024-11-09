..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=====================
VNC console
=====================

https://bugs.launchpad.net/ironic/+bug/1567629

In addition to a serial console, allow ironic nodes to be accessed through a
vnc console. This proposal presents the work required to create a new
driver interface for accessing graphical console of a node.


Problem description
===================

End users often have to troubleshoot their instances because they might
have broken their boot configuration or locked themselves out with a
firewall. Keyboard-Video-Mouse (KVM) access is often required for
troubleshooting these types of issues as serial access is not always
available or correctly configured. Also, KVM provides a better user
experience as compared to serial console.

Horizon's VNC console is not supported for the ironic
nodes provisioned by Nova. This spec intents to extend that to
graphical console via the novnc proxy.

The end user will be able to get workable vnc console url from baremetal
server:
switch console type on bm side to ``vnc``
``openstack baremetal node console enable``
``openstack console url show --novnc``

Proposed change
===============

* In order to support the handshake for VNC authentication we have to
  implement proxy service as a part of security isolation. During handshake
  ``vnc password`` is used. It is stored on ironic side in
  ``driver_info/vnc password`` and without proxy need to be provided to Nova.
  This password should be set by admin. More information about vnc password is
  in rfb protocol. With novncproxy Nova internals don't need internal details
  of the BMC network. Expected that this new service can be based on
  nova_novncproxy.

* for drac will be created a vnc driver based on ``base.ConsoleInterface``


Alternatives
------------

* Accept this limitation and only offer a serial console.

* We can configure kvm access including access to the bios via the
  serial proxy and shell in a box for nova provisioned ironic baremetal
  instances. This would require exposing credentials.

* Use out-of-band KVM access provided by administrator without Ironic support.

Data model impact
-----------------

None.


State Machine Impact
--------------------

None.


REST API impact
---------------

None.


Client (CLI) impact
-------------------

None.


RPC API impact
--------------

None.


Driver API impact
-----------------

None.


Nova driver impact
------------------

Nova impacts are fully described in the support of vnc console for ironic
spec in Nova.

Essentially, the Ironic virt driver will have to implement ``get_vnc_console``

As per policy in Nova, changes cannot land until ironic changes have landed.


Ramdisk impact
--------------

None.


Security impact
---------------

The VNC connection to the nodes are secured by a token generated while
creating the console in Nova. This bearer token is the only thing required
to connect to the novnc proxy, So the connection between user and novnc proxy
should be protected via ssl

Other end user impact
---------------------

None.


Scalability impact
------------------

None.


Performance Impact
------------------

None.


Other deployer impact
---------------------

additions to configs (idrac example):

``ironic-conductor/ironic.conf``:
enabled_console_interfaces = idrac-socat,ipmitool-socat, ``idrac-vnc``

``ironic-api/ironic.conf``:
enabled_console_interfaces = idrac-socat,ipmitool-socat, ``idrac-vnc``

Developer impact
----------------

None.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  * kirillgermanov

Other contributors:
  None.

Work Items
----------

* implement ``ironic-novncproxy`` service

* Introduce ``drac.DracWSManVNCConsole(base.ConsoleInterface)``

* Add usage description to documentation

Dependencies
============

https://review.opendev.org/c/openstack/nova-specs/+/863773


Testing
=======

* Unit tests


Upgrades and Backwards Compatibility
====================================

None.


Documentation Impact
====================

* Documentation will be updated.


References
==========

* https://review.opendev.org/c/openstack/nova-specs/+/863773

* https://stackoverflow.com/questions/16469487/vnc-des-authentication-algorithm

* https://review.opendev.org/c/openstack/ironic/+/860689 - gerrit review ironic

* https://review.opendev.org/c/openstack/nova/+/863177 - gerrit review nova

* https://datatracker.ietf.org/doc/html/rfc6143 - rfb protocol
