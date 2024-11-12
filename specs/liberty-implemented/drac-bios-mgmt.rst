..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=================================================
DRAC vendor passthru for BIOS settings management
=================================================

https://blueprints.launchpad.net/ironic/+spec/drac-bios-mgmt

This spec will expose the vendor passthru methods needed to let
external services get, set, and commit changes to the BIOS
settings. This spec will assume that the external service knows
exactly what it is doing with the specific hardware it will manage,
and it will not attempt to standardize, normalize, or simplify the
exposed settings in any way beyond some minimal convenience measures
and what is needed to map between XML and JSON.


Problem description
===================

Tuning a server for a particular workload and power consumption
profile involves many different parameters to be tweaked, several of
which must be tuned at the level of the system firmware.  On Dell
systems, doing that out-of-band involves talking to the DRAC to have
it make changes on your behalf.


Proposed change
===============

To expose these changes, I propose to add 4 vendor passthrough methods
to the drac driver:

   - ``get_bios_config`` - Gather the current BIOS configuration of
     the system from the drac and return it.  This will return a JSON
     structure that contains the current BIOS configuration of the
     system.  It has no parameters.

   - ``set_bios_config`` - Queue up changes to the BIOS configuration for
     later committal. This will accept the same JSON data structure
     that ``get_bios_config`` returns.  It will raise an exception if
     any of the changed settings does not validate as a proper change,
     if you try to change a readonly setting, or if the changes cannot
     be queued up in the DRAC for some other reason.

   - ``commit_bios_config`` - Commit a set of queued up BIOS
     configuration changes, and schedules a system reboot if is needed
     to commit the changes.

   - ``abandon_bios_config`` - Abandon a set of queued up BIOS
     configuration changes.

For this spec, only changes that can be made though the `DCIM Bios and
Boot Management Profile <http://en.community.dell.com/techcenter/extras/m/white_papers/20440459>`_
will be considered, although there are many other BIOS and hardware
parameters that can be changed by the DRAC.


Alternatives
------------

Create a common BIOS interface which most vendors will agree to.  This
is a longer term solution which should replace or drive this
implementation in the future.

Data model impact
-----------------

None.

REST API impact
---------------

Four new API calls:

- ``get_bios_config`` - a GET method.  Takes no args, returns a blob
  of JSON that encapsulates the BIOS configuration parameters of the
  system.

- ``set_bios_config`` - a POST method.  Takes a blob of JSON that has
  the same format and settings returned by get_bios_config.  Returns
  the following status codes:

  * 200 if the set of proposed new parameters passed validation and
    was accepted for further processing.

  * 204 if the set of proposed new parameters passed validation, but
    did not actually change the BIOS configuration.

  * 409 if the set of proposed new parameters contains a parameter
    that cannot be set to the requested value, either because the
    parameter is read-only or the proposed new parameter is not valid.

  * 403 if there are already proposed changes in the process of being
    committed.

- ``commit_bios_config`` - a POST method.  Takes no args, commits the
  changes made by ``set_bios_config`` calls and schedules a system
  reboot to apply the changes if needed.  Returns the following status
  codes:

  * 202 if a commit job was created, and the system requires a reboot.

  * 200 if the settings were committed without needing a reboot.

  * 204 if there were no settings that needed to be committed.

  * 403 if there are already proposed changes in the process of being
    committed.

- ``abandon_bios_config`` - a POST method.  Takes no arguments, and
  abandons any changes made by ``set_bios_config`` calls that have not
  been committed by a ``commit_bios_config`` job.  Returns the
  following status codes

  * 200 if the proposed changes were successfully dequeued.

  * 204 if there were no proposed changes to dequeue

  * 403 if the proposed changes are already in the process of being
    committed.

RPC API impact
--------------

None

Driver API impact
-----------------

None

Nova driver impact
------------------

None for now.  If this spec gets generalized to other drivers, we will
need to figure out what (if any) capabilities should be exposed to Nova.

Security impact
---------------

It is quite possible to render a system unbootable through this API,
as it allows you to enable and disable a wide variety of hardware and
mess with the boot order indiscriminately.

Other end user impact
---------------------

None

Scalability impact
------------------

None

Performance Impact
------------------

None.

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
  victor-lowther

Work Items
----------

* Create and implement DracVendorPassthruBios class


Dependencies
============

* This feature depends on the python bindings of the OpenWSMAN library
  which we already use for the rest of the DRAC driver.

* This feature requires 11th or higher generations of Dell PowerEdge
  servers.

Testing
=======

* Unit tests

* 3rd-party CI:  I will try to implement it in parallel with
  implementing this driver, provided I can source sufficient internal
  resources and appropriate network connectivity.

Upgrades and Backwards Compatibility
====================================

None expected, and there should be no stability guarantee for this API.


Documentation Impact
====================

User documentation should mention this vendor passthrough API.


References
==========

`DCIM Bios and Boot Management Profile <http://en.community.dell.com/techcenter/extras/m/white_papers/20440459>`_
