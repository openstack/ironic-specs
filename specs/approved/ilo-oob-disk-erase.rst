..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=======================================================================
Out-of-band disk-erase for Gen10 and above HPE Proliant Servers
=======================================================================

https://storyboard.openstack.org/#!/story/2004786

This specification proposes implementation of out-of-band disk-erase
for iLO5 managed HPE Proliant servers.

Problem description
===================

In the current scenario where disk-erase on HPE Proliant servers is
done only via inband cleaning, iLO5 based HPE Proliant Gen10 servers provide
support to perform out-of-band disk-erase which was not there in Gen9
and older servers. However, disk-erase request would be accepted by iLO only
when system boot completes POST. Hence disk-erase needs to be accompanied by
a reboot.

Proposed change
===============

This spec proposes to implement out-of-band disk-erase clean_step in hardware
type ``ilo5`` under new management interface ``Ilo5Management`` which would be
inherited from existing management interface ``IloManagement``.

List of changes required:

* The following would be the composition of the new management interface
  ``Ilo5Management``:

  + ``erase_devices`` - This will erase all disks on the baremetal node.

    - `erase_devices` will call proliantutils library method `do_disk_erase`
      to perform the operation in iLO. User can also choose between different
      erase pattern (ex. block, overwrite, crypto, zero) to perform the disk
      erase operation.

    - The reboot is required to initiate the disk erase. The actual disk
      erase operation would take time based on disk type and size.

Alternatives
------------

One can perform in-band disk-erase to achieve the same result. However,
The ramdisk to be used in such case should have proliant-tools element
that bundles 'ssacli' utility required for disk-erase operations as
part of the image.

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

Users need to configure two options to make use of OOB disk-erase on
HPE Proliant Gen10 servers.

* Configure the hardware type ``ilo5`` to ([DEFAULT]
  ``enabled_hardware_types``).

* Configure the new management interface ``ilo5`` to ([DEFAULT]
  ``enabled_management_interfaces``).


Developer impact
----------------
None


Implementation
==============

Assignee(s)
-----------

Primary assignee:
pareshsao

Work Items
----------

* Add a new management interface ``Ilo5Management`` to hardware type ``ilo5``
* Writing unit-test cases for the new OOB disk-erase interface.


Dependencies
============

Support for OOB disk-erase in proliantutils is under development and is yet to
be released.


Testing
=======

Unit test cases will be added. Will be tested in 3rd party CI setup.

Upgrades and Backwards Compatibility
====================================

None


Documentation Impact
====================

Need to update iLO driver documentation for new management interface.


References
==========

None
