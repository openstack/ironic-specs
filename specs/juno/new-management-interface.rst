..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==============================
New driver ManagementInterface
==============================

https://blueprints.launchpad.net/ironic/+spec/new-management-interface

This blueprint consolidates the work needed for the creation of a new
driver interface for management-like operations and a new REST API
resource to expose those methods.

Problem description
===================

Almost all Power Interfaces (except the SSH Power Interface) expose a
method to set the boot device on their Vendor Passthru interface, this
blueprint intends to promote this method to an official interface.

Setting the boot device doesn't fit into the current driver interfaces,
even if right now it's part of the Vendor Passthru of the Power Interfaces
it's not actually a power operation, so this blueprint will also include
the creation of a new interface called Management Interface where such
management operations can be exposed.

As noted in the first paragraph the SSH Power Interface doesn't expose
any method to set the boot device, so this is going to be implemented
as part of this blueprint. We need all drivers to adhere to the new
interface so that it's consistent.

As for the API changes, a new 'management' subresource will be added to
nodes resource of the REST API and will expose ways to get the supported
boot devices and set/get the boot device of a given node. In the future
more operations could be added to the management interface, for example:
get_sensor_data()[1], update_firmware(), get_firmware_list(), etc...

Proposed change
===============

* Create a new ManagementInterface which expose the methods:

  - validate() - To validate driver-specific management
    information. (E.g if the node has the right credentials already set)

  - set_boot_device() - To set the boot device for a specific node.

  - get_boot_device() - To get the current boot device of a specific node.

  - get_supported_boot_devices() - To get a list of the supported boot
    devices by that driver.

* Port the set_boot_device() method from the Vendor Passthru interface
  to the new interface.

* Add a ManagementInterface for ssh, and implement the set_boot_device()
  for it

* Create a new /nodes/<uuid>/management/boot_device subresource in the
  REST API to expose ways to the client to {set,get} the boot device for
  a node.

  - To set the boot device:

    PUT {'boot_device': 'pxe'}
        /nodes/<uuid>/management/boot_device[?persistent=<bool>]

    If the request was completed successfully HTTP 204 (No Content)
    is returned.

    If an invalid or not supported boot device parameter is passed it
    should return 400 (Bad Request).

    The "persistent" flag can be set to indicate whether the boot device
    changes should be applied for the next boot only or to all future
    boots. By default persistent will be False.

  - To get the current boot device:

    GET /nodes/<uuid>/management/boot_device

    Returns a dictionary with the boot device and if it's persistent or
    not. E.g:

    {'boot_device': 'pxe', 'persistent': True}

    If 'boot_device' is unknown the value of it will be None (The seamicro
    python library doesn't seem to expose a way to get the current boot
    device, only set it[3]).

    If 'persistent' is unknown the value of it will be None (The pyghmi
    method to  get the current boot device and doesn't indicate whether
    it's persistent or not[3]. For setting the boot device, it's possible
    to indicate whether it's persistent or not).

  - To get the supported boot devices:

    GET /nodes/<uuid>/management/boot_device/supported

    This will return a list of all supported boot devices (not the
    boot order).

* Update the Ironic client and library to support the new API resource.

Alternatives
------------

Continue to use the Vendor Passthru interface.

Data model impact
-----------------

None

REST API impact
---------------

* A new /nodes/<uuid>/management/boot_device subresource will be added
  to the API, requests to set or get the boot device for a node should
  go there so that methods like set_boot_device won't be exposed via the
  vendor_passthru anymore.

* The nodes/<uuid>/validate will include the management interface.

Driver API impact
-----------------

* The new ManagementInterface will be included in the standardized
  interfaces group.

* The ipmitool, ipminative, seamicro and ssh drivers are going to be
  updated to use this new interface.

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

* Create the new ManagementInterface base class.

* Port the set_boot_device() method from the Vendor Passthru interface
  of the ipmitool, ipminative, seamicro drivers to the new interface.

* Implement the missing methods on the ssh, ipmitool, ipminative,
  seamicro drivers.

* Implement the REST API to expose the new interface.

Dependencies
============

None

Testing
=======

* Unit tests will be added/updated to cover the changes.

* Tempest tests will be added to Ironic to ensure that the new
  /nodes/<uuid>/management/boot_device is working properly.

Documentation Impact
====================

The Architecture documentation should be updated to include the new
Management Interface.

References
==========

[1] https://github.com/openstack/ironic-specs/blob/master/specs/juno/send-data-to-ceilometer.rst
[2] https://github.com/seamicro/python-seamicroclient/blob/master/seamicroclient/v2/servers.py#L24
[3] https://github.com/stackforge/pyghmi/blob/master/pyghmi/ipmi/command.py#L123
