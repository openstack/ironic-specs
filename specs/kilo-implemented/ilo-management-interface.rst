..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=========================
iLO Management Interface
=========================

https://blueprints.launchpad.net/ironic/+spec/ilo-management-interface

This blueprint adds support to management Interface for HP ProLiant Servers
using iLO client python library.

Problem description
===================

Currently, IloManagement Interface used in IloVirtualMediaIscsiDriver,
IloVirtualMediaAgentDriver and PXEAndIloDriver uses IPMIManagement to support
management operations like ``get_boot_device``,
``get_supported_boot_devices``.

This leads to dependency of ipmitool on iLO servers.

Proposed change
===============

* Our proposed change is to do above operations using iLO for consistency,
  simplicity and correctness.

* Move existing IloManagement class from ilo/deploy.py to ilo/management.py.

* Change the existing IloManagement Class to inherit from
  base.ManagementInterface instead of ipmitool.IPMIManagement.

* Implement the following methods using iLO client python library.

    - ``validate()`` - To validate iLO driver specific information.
      (ilo_username, ilo_password, ilo_address)

    - ``get_boot_device()`` - To get the current boot device of a node with
      the indication whether it's persistent, or not.

    - ``get_supported_boot_devices()`` - To get a list of the supported boot
      devices of a node. The supported boot devices will be ``disk``, ``pxe``
      and ``cdrom``.

* Move ``set_boot_device()`` functionality to ManagementInterface and change
  the current invocations to manager_utils.node_set_boot_device().

* Implementation of ``get_sensors_data()`` is not in scope of current spec.
  It is proposed as part of the following blueprint-
  https://blueprints.launchpad.net/ironic/+spec/send-ilo-health-metrics-to-ceilometer


Alternatives
------------
Continue to use IPMI Interface to management operations.

Data model impact
-----------------
None

REST API impact
---------------
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
The following which are already part of driver_info fields are required:
  * ``ilo_address`` - hostname or IP address of the iLO.
  * ``ilo_username`` - the username for the iLO with administrator privileges.
  * ``ilo_password`` - the password for ``ilo_username``.
  * ``ilo_client_timeout`` - the timeout for iLO operations. The default value
    will be 60 seconds.
  * ``ilo_client_port`` - the port to be used by iLO client for
    iLO operations. The default value will be 443.


Developer impact
----------------
None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  anusha-iiitm

Work Items
----------
* Implement ``get_boot_device`` and ``get_supported_boot_devices``.
* Move ``set_boot_device()`` functionality from ilo/common.py to
  ilo/management.py.
* Change the current invocations of ``set_boot_device`` from
  ilo_common.set_boot_device() to  manager_utils.node_set_boot_device().

Dependencies
============
* Depends on ``proliantUtils`` library.
* Targeted for HP ProLiant servers with iLO4.

Testing
=======
* Unit tests will be added, mocking proliantutils library.

Upgrades and Backwards Compatibility
====================================
None

Documentation Impact
====================
None

References
==========
proliantutils library:

https://github.com/hpproliant/proliantutils

https://pypi.python.org/pypi/proliantutils
