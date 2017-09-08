..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Determinable supported boot device list
==========================================
https://blueprints.launchpad.net/ironic/+spec/supported-boot-device-list

This blueprint proposes to add the facility to return a determinable list
of supported boot devices that is specific to the node being queried.

Problem description
===================
Current driver interface get_supported_boot_devices() does not provide for
a means to access the node being queried, as a result a determinable list of
supported boot devices that are specific to this node cannot be calculated.

Example usage, if a node uses an architecture other than x86 e.g. SPARC, then
PXE boot is not supported, and therefore should not be contained in the
returned list. SPARC architecture supports WANBOOT and this should be returned.
However to determine this the node's property "cpu_arch" needs to be accessed.


Proposed change
===============
Add "task" parameter to get_supported_boot_devices() interface.

By providing a task parameter to the get_supported_boot_devices() interface a
driver can then access the node specific to this query e.g. task.node, and
from there can look at a nodes properties and correctly determine the
list of supported boot devices to return.

This change would be backwards compatible, using inspect to determine if
a specific driver as implemented the "task" parameter or not, and showing
a deprecation warning if "task" paramater has not been implemented.

This deprecation of get_suported_boot_devices() without task parameter will
be done in the next release, after which get_supported_boot_devices() without
the task parameter will not be supported.


Alternatives
------------
The only method to access the specific node for which a
get_supported_boot_devices request is being made is via passing in the task
argument.

Alternative 1:
Restrict all drivers to only be able to register nodes of a specific
architecture. Then the underlying driver API for get_supported_boot_devices()
would just assume that this node must be of a specific architecture and always
return a static list for that architecture.

This approach is limiting and would result in an unnecessary increase
in the number of drivers available for ironic, and a unnecessary potential
duplication of code.


Alternative 2:
Utilize set_boot_device(task, device), this method in most cases will validate
if a "device" is supported for this node. A task parameter is being passed in
here, and thus the node can be accessed to determine if "device" is supported
for this specific node. The issue here is that it would have to be called a
number of times to determine a list of supported devices, and each successful
call would result in an IPMI call to actually set the boot device for the node
which would be unacceptable and inefficient.

This approach is not complete and does not solve the scenario where
get_supported_boot_devices() is called via the ironic CLI. This would still
result in a potentially incorrect list of devices being returned to the user.


Alternative 3:
This is more of an addendum to the proposed solution. Add a new essential
property for a node called "supported_boot_devices". This property would be
populated during node inspection, and could then be queried to determine the
list of supported boot devices.

Access to the node however would still be required, so passing of the task
parameter to get_supported_boot_devices would still be required.


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
get_supported_device_list() is a member of the standard Management interface.

This change would effect all drivers but would be implemented so that it's
backward compatible, using inspect to determine if a driver supports the task
argument or not. If not a deprecation warning would be shown.

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
All in-tree driver and unit tests will be amended to include the new "task"
parameter. Out of tree drivers will see a depracation warning until they
implement the new "task" parameter.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  mattkeenan

Work Items
----------
  * Add "task" to get_supported_devices_list() in base driver
  * Add new management property definition to check if
    driver supports task parameter or not.
  * Update all in tree drivers adding task paramater
  * Update all unit tests affected by change

Dependencies
============
None

Testing
=======
Will update all affected unit tests

Upgrades and Backwards Compatibility
====================================
Backwards compatibility is achieved by using python's inspect module to
determine if a driver's get_supported_device_list() implementation includes
a "task" parameter or not. If not it will be called without the "task"
parameter and a deprecation warning will be shown.

Documentation Impact
====================
None

References
==========
Bug: https://bugs.launchpad.net/ironic/+bug/1391598
Review: https://review.openstack.org/#/c/188466
