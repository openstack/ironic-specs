..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

======================================================
Support a new hardware type for Fujitsu PRIMEQUEST MMB
======================================================

https://storyboard.openstack.org/#!/story/1726271

This spec proposes adding a new hardware type that supports deployment of
servers managed by ManageMent Board(MMB) for Fujitsu PRIMEQUEST 3000 Series.
MMB is a system control unit that performs management tasks, including control
and monitoring in the cabinet, partition management, and system initialization.

Problem description
===================

Since PRIMEQUEST definitely differs from iRMC interface, Ironic cannot handle
Fujitsu PRIMEQUEST servers by using ``irmc`` hardware type at present.
Therefore, this spec proposes a new hardware type for MMB in order to handle
PRIMEQUEST by ironic. PRIMEQUEST has multiple partitions. Each partition works
as a physical server. That is, a partition relates an ironic node. In addition,
several partitions can be managed by one MMB. In order to control a specified
partition, the ironic node has to know its partition number.

Proposed change
===============

This spec proposes the ``fujitsu-mmb`` hardware type, implementing the Power,
Management and Console. The hardware type uses ssh library in order to connect
and execute commands into MMB.

Based on this premises, to be enrolled, the node MUST have the following
parameters:

driver_info

- (Required) **mmb_address**
    - IP address of the MMB to ssh into.
- (Required) **mmb_username**
    - Username to authenticate as.
- (Required) **mmb_partition**
    - Partition number to manage.
- **mmb_ssh_key_filename**:
    - Filename of optional private key(s) for authentication. If
      **mmb_ssh_password** is also specified, it will be used for unlocking
      the private key. It recommends to store at shared volume like NFS or
      CIFS.
- **mmb_ssh_password**
    - Password to use for authentication or for unlocking a private key. At
      least one of this or **mmb_ssh_key_filename** must be specified.
- **mmb_ssh_port**
    - Port on the node to connect to. Default is 22.

We'll define a new class:

- ``fujitsu_mmb.MMBHardware``

Following interfaces will be implemented:

- ``MMBPower``
- ``MMBManagement``
- ``MMBConsole``

``MMBPower``
    Ironic sets/synchronizes this interfaces.  After synchronization, this
    interface controls the power state of the nodes using MMB's command.

``MMBManagement``
    This interface allows the user to get and set the boot-order of a server
    hardware by executing the command on MMB.

``MMBConsole``
    This interface provides serial console view by executing the command on
    MMB.

This hardware type will support ``PXEBoot`` for boot and ``ISCSIDeploy``,
``AgentDeploy`` for deploy.

Alternatives
------------

None

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
None

Security impact
---------------

This hardware type retrieves following information.

* SSH private key filename
* SSH password for MMB

However, ironic only stores a filename of SSH private key into driver_info as
**mmb_ssh_key_filename**. SSH Key information doesn't include in REST API body.
Regarding SSH password, it will be hidden in REST API body like '***********'.


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
  y-furukawa-2

Other contributors:
  shiina-hironori

Work Items
----------

- Implement new ``fujitsu-mmb`` hardware type and interfaces.
- Implement unit-test cases for ``fujitsu-mmb`` hardware type and following
  interfaces.

    - MMBPower
    - MMBManagement
    - MMBConsole
- Write documents about ``fujitsu-mmb`` hardware type.

Dependencies
============

**python-pqclient**: In order to connect to MMB and execute commands for them.

Testing
=======

During next year, we'll add 3rd party CI for ``fujitsu-mmb`` hardware type.

Upgrades and Backwards Compatibility
====================================
None

Documentation Impact
====================

``Fujitsu MMB driver`` section will be included in Administrator's Guide.

References
==========

* Fujitsu PRIMEQUEST
  http://www.fujitsu.com/us/products/computing/servers/mission-critical/
* MMB
  http://manuals.ts.fujitsu.com/file/11627/CA92344-0541.pdf
* python-pqclient
  https://github.com/openstack/python-pqclient
