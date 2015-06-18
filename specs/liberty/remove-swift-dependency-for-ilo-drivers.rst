..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==================================================================
Make ilo drivers standalone in ironic by removing swift dependency
==================================================================

https://blueprints.launchpad.net/ironic/+spec/remove-swift-dependency-for-ilo-drivers

This spec proposes to remove hard dependency on swift for ilo
virtual media drivers.
There are standalone use-cases of Ironic (like bifrost) which are
capable of deploying nodes without requiring other Openstack services.
With this the ilo virtual media drivers can also
work standalone similar to other drivers in ironic.

Problem description
===================

Today the ilo drivers (iscsi_ilo and agent_ilo) require swift to host
the images like boot_iso (from which the instance boots)
and floppy images (used for passing parameters to deploy ramdisk).

Proposed change
===============

The ilo drivers (iscsi_ilo and agent_ilo) can use a web server to
host the images required. Swift would be used as a default backend
to host boot ISO and floppy images for these drivers.

* The automatic boot_iso created (as required by iscsi_ilo for booting up the
  instance) and floppy images (as required by both agent_ilo and iscsi_ilo for
  passing parameters to deploy ramdisk) during deploy process,
  will be hosted on swift or http web server as per the config variable under
  `[ilo]` in ironic.conf::

    use_http_web_server_for_images=True

  The default value would be `False` and will default to use swift.

* User needs to manually configure the webserver, and add the config options
  in ironic.conf under `deploy` as::

    http_server_root = /opt/stack/ironic/data/httpboot
    http_server_url = http://10.10.1.30/httpboot

  Since the same config variables exists under `[pxe]` and are required by
  ilo drivers to be able to run standalone, we can deprecate the same in
  `[pxe]` and move it under `[deploy]`. The above values to the config
  variables are just an example. They will continue to have the default
  value as the current config variables ``http_url`` and ``http_root``.

* To add the functionality of take_over() to ilo drivers. This is to enable
  a case when the conductor node goes down and other conductor takes over the
  baremetal. The take_over() will be implemented to do regenerate in following
  scenarios:

  - for wait_call_back state: implement regeneration of floppy images.

  - for active state : implement regeneration of boot ISO.


Alternatives
------------

None.

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

None.

Security impact
---------------

None.

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

The http web server configuration is out of scope of ironic but it should be
configured on every conductor node.
User needs to manually configure the web server, and add the config options
in ironic.conf under `deploy` as::

    http_server_root = /opt/stack/ironic/data/httpboot
    http_server_url = http://10.10.1.30/httpboot

Since the same config variables exists under `[pxe]` and is required by
ilo drivers to be able to run standalone, we can deprecate the same in `[pxe]`
and move it under `[deploy]`.

Developer impact
----------------

None.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  agarwalnisha1980

Work Items
----------

* To modify ipxe to use config variables from `[deploy]` section.

* To enable support for using webserver in ilo drivers.

* To implement take_over() for ilo_drivers for ``use_web_server=True``

Dependencies
============

None.

Testing
=======

* Mocked unit tests would be added.

* Functional tests would be done to ensure that the deploy works fine
  for ilo drivers with swift as backend or http webserver as backend.

Upgrades and Backwards Compatibility
====================================

The ilo drivers will continue to work with swift as backend.
The iPXE code will continue to work for config options in either of the
section.

Documentation Impact
====================

It is required to be documented.

References
==========

None.
