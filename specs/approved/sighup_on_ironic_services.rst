..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=========================
SIGHUP on ironic services
=========================

https://bugs.launchpad.net/ironic/+bug/1585595

It is a common practice for daemons to use SIGHUP as a signal to reconfigure
a server by reloading configuration files (as mentioned in `Wikipedia`_).
This specification describes adding this feature to the ironic-conductor and
ironic-api services.

Problem description
===================

Issuing a SIGHUP signal (via, for example, ``kill -s 1 <process-id>``) to an
ironic (ironic-api and ironic-conductor) service causes the service to be
restarted.

It is a common practice for daemons to use SIGHUP as a signal to reconfigure
a server by reloading configuration files (as mentioned in `Wikipedia`_).
This specification describes how ironic will support SIGHUP, such that
select configuration options can be reloaded during runtime.

This is useful, for example, during a `rolling upgrade`_. After unpinning
(resetting the ``pin_release_version`` configuration option), SIGHUP could be
used to restart the services with the updated option value.

Another example is for operators to more easily enable or disable the debug
logging without having to stop and (re)start the services.

Note that SIGHUP is not supported on Windows.

Proposed change
===============

We will leverage code from these libraries:

* the `oslo.service library`_ provides support for services to handle this
  signal. We would change the ironic services so that they are `launched`_
  with ``restart_method='mutate'``. When the library code handles the SIGHUP
  signal, it gets any changes for mutable configuration options.
* The `oslo.config library`_ adds support for ``mutable`` configuration
  options.  Only mutable configuration options can be reloaded. A `mutable
  option note`_ ("Note: This option can be changed without restarting.")
  is added to the description of a mutable configuration option in the
  ironic.conf.sample file. It logs any changed mutable configuration options.
  It also logs a warning for any changed options that are not mutable.

With these changes, when a SIGHUP occurs, the service will reload with values
from the mutable options. A warning is logged for changes to any
immutable options.

Mutable configuration options
-----------------------------

Mutable configuration options that will be available are:

* options from other libraries. To date, the only mutable options that are used
  by the ironic services are from the oslo.log library:

  * ``[DEFAULT]/debug``
  * ``[DEFAULT]/log_config_append``

* ``[DEFAULT]/pin_release_version``

Other ironic configuration options can be made `mutable in the future`_; such
changes should have corresponding release notes. The belief is that most, if
not all, of the configuration options should be made mutable. However, that is
outside the scope of this specification -- which is to lay the groundwork
to make this possible with a small number of options. When mentioning that
ironic supports SIGHUP, operators might assume (incorrectly) that this applies
to all configuration options, so we should make other configuration options
available in a timely fashion.

The value of a mutable configuration option should not be cached; or at least,
if it is cached, the value must be updated upon a SIGHUP occurrence.

Alternatives
------------

Change the desired configuration option values, stop the service, and then
start it again.

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

"ironic" CLI
~~~~~~~~~~~~
None.

"openstack baremetal" CLI
~~~~~~~~~~~~~~~~~~~~~~~~~
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

Ramdisk impact
--------------

None.

Security impact
---------------

None.

Other end user impact
---------------------

The operator will be able to change certain configuration options and issue
a SIGHUP to have an ironic service restart using the changed option values.

Scalability impact
------------------

None.

Performance Impact
------------------

None.

Other deployer impact
---------------------

Among other things, this can be used for rolling upgrades.

Developer impact
----------------

None.

Implementation
==============

Assignee(s)
-----------

Primary assignee: rloo (Ruby Loo)

Work Items
----------

* change our services so they are launched with ``restart_method='mutate'``
* change the desired configuration options so that they are mutable
* make sure the mutable options are not cached, or if they are, make sure that
  they are updated appropriately with a SIGHUP occurrence

Dependencies
============

None.

Testing
=======

If we stop and restart a service in the e.g. multinode grenade testing,
we could change that and issue a SIGHUP instead.

Upgrades and Backwards Compatibility
====================================

Changing the value of mutable configuration options will now take effect when
a SIGHUP is issued. We need this to support rolling upgrades.

Documentation Impact
====================

The use of SIGHUP (in the context of ``[DEFAULT]/pin_release_version``) will
be documented as part of the rolling upgrade process.


References
==========

* `Wikipedia`_
* `oslo.service library`_
* `oslo.config library`_
* `rolling upgrade`_

.. _`Wikipedia`: https://en.wikipedia.org/wiki/SIGHUP
.. _`oslo.service library`: http://docs.openstack.org/developer/oslo.service/usage.html#signal-handling
.. _`rolling upgrade`: http://specs.openstack.org/openstack/ironic-specs/specs/approved/support-rolling-upgrade.html#rolling-upgrade-process
.. _`oslo.config library`: http://docs.openstack.org/developer/oslo.config/opts.html?highlight=mutable#option-definitions
.. _`mutable option note`: https://github.com/openstack/ironic/blob/ebfc4fe4c4c3910bf8b1229cb75259befa530877/etc/ironic/ironic.conf.sample#L383
.. _`launched`: https://docs.openstack.org/oslo.service/latest/reference/service.html#oslo_service.service.launch
.. _`mutable in the future`: https://bugs.launchpad.net/ironic/+bug/1713571
