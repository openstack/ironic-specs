..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==================================================
Support NIC Firmware Updates in Firmware Interface
==================================================

https://bugs.launchpad.net/ironic/+bug/2107998

This spec proposes to extend the redfish firmware interface to support
NIC firmware updates.


Problem description
===================

A detailed description of the problem:

* As an operator using firmware updates via clean/service steps via firmware
  interface [0]_, I would like to be able to update the firmware of the NICs
  in addition to what is current supported (BIOS and BMC).

* For a major reworking of something existing it would describe the
  problems in that feature that are being addressed.


Proposed change
===============

Expand the current implementation of the ``RedfishFirmware`` to support NIC
firmware updates.

* Enhance sushy to support ``/redfish/v1/Chassis/<SystemID>/NetworkAdapters``,
  this resource is where we can find the information about the NIC and the
  firmware version.

* Update the ``RedfishFirmware`` interface to detect the NICs, execute the
  firmware update and collect the data.

* Use the ``Id`` from each ``NetworkAdapters/<NIC-X>`` in the component field,
  since we can have multiple cards it doesn't make sense to track them as
  ``nicX`` because it has no mapping to the resource.

NetworkAdapters resource examples:

- NIC.Integrated.1 https://paste.opendev.org/show/b8U2He23Yy3vxNc2zIUa/
- NIC.Slot.3 https://paste.opendev.org/show/bs3Qu9occVxZLzcTpG6Q/

Challenges
==========

One of the challenges is that we will have to deal with multiple NICs, that is
why in the proposed change we want to use the ``Id`` that comes from the
``NetworkAdapters/<NICX>``.

We will also have to deal with machines with multiple networks cards of the
same type, in one of the hardware I've tested, there was 2 network cards E810,
when doing the firmware update on it, both cards received the new version.

NetworkAdapters resource from each E810 cards:

- NIC.Slot.2 https://paste.opendev.org/show/biGgtah7Rm4FVH1Fe5SR/
- NIC.Slot.3 https://paste.opendev.org/show/bvCbyGRVPsOfUIptkU0o/

Alternatives
------------

Directlly update the NIC firmware via redfish call or via management UI.

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

"openstack baremetal" CLI
~~~~~~~~~~~~~~~~~~~~~~~~~

None

"openstacksdk"
~~~~~~~~~~~~~~

None

RPC API impact
--------------

None

Driver API impact
-----------------

Update the ``RedfishFirmware``  to handle NIC firmware updates.

* ``cache_firmware_information()`` - this method will will be updated to
  handle all NICs available that supports firmware update.

* The ``update()`` step will need to have a new validation for the name of the
  NICs, since we will be using the ``Id`` exposed via the ``NetworkAdapter``
  resource.

Nova driver impact
------------------

None

Ramdisk impact
--------------

None

Security impact
---------------

* The hardware may become unavailable during firmware updates.

Other end user impact
---------------------

None

Scalability impact
------------------

None

Performance Impact
------------------

* The NIC firmware update may extend the time required for manual cleaning or
  servicing on the nodes, this is because some cards may require a big amount
  of time, like Mellanox cards.


Other deployer impact
---------------------

* This change takes immediate effect after it's merged


Developer impact
----------------

* If the blueprint proposes a change to the driver API, discussion of how
  other drivers would implement the feature is required.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
*  <iurygregory, imelofer@redhat.com or iurygregory@gmail.com>


Work Items
----------

1. Update sushy to handle NetworkAdapters, current code [1]_ is under the
   wrong resource.

2. Release sushy with the new functionality.

3. Update Ironic code to handle nic firmware update in ``RedfishFirmware``.


Dependencies
============

* This feature is targeting only hardware that supports Redfish and have
  proper support to update NICs.

* Sushy needs to support NetworkAdapters.


Testing
=======

I have access to a set of hardware where I've manually tested update,
below you can find the list of hardware models and network cards.

Hardware Models
- Dell R640
- Dell PowerEdge XR8620t
- HPE DL380 Gen10
- HPE DL380 Gen10 Plus

Network cards
- Intel(R) Ethernet 25G 4P E810-XXV Adapter
- Intel(R) Ethernet 10GbE 4P X710 SFP+rNDC
- MLNX 25GbE 2P ConnectX4LX Adpt

I was able to update using ``SimpleUpdate`` in all hardware models, except
for the HPE DL380 Gen10.

.. NOTE::
   NIC firmware updates didn't work on the HPE DL380 Gen10, but it worked on
   the HPE DL380 Gen10 Plus.
   While checking the Updateable parameter in the ``FirmwareInventory``
   resource associated with the NICs, the ones on the Gen10 are set to false
   [2]_, while the one on Gen10 Plus is set to true.
   According to the Redfish spec the Updateable [3]_ indicate whether the
   image can be update by the the update service.


Upgrades and Backwards Compatibility
====================================

* backwards-compatibility: the bios and bmc updates will continue to work same
  way as before after upgrading to the new version.

* The NIC component information will only be added if it's available in the
  redfish resource.

* Add unit tests for the changes.


Documentation Impact
====================

Update the current documentation with the newer information about it.


References
==========

.. [0] Firmware Interface - https://github.com/openstack/ironic-specs/blob/master/specs/approved/firmware-interface.rst
.. [1] NetworkAdapter code - https://github.com/openstack/sushy/blob/master/sushy/resources/system/network/adapter.py
.. [2] HPE DL380 Gen10 Firmware Inventory - https://paste.opendev.org/show/bJru84IPdbKgdbBXwglc/
.. [3] Firmware Inventory Spec - https://www.dmtf.org/sites/default/files/standards/documents/DSP2062_1.0.0.pdf
