..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===================================
Hardware that cannot be powered off
===================================

https://bugs.launchpad.net/ironic/+bug/2077432

Problem description
===================

Power off is a very fundamental action for bare-metal provisioning. Not only is
it available as an API primitive, Ironic also often uses a sequence of power
off and power on instead of a single reboot action. This happens for three
reasons:

* By waiting for the machine to power off first, we ensure that the power off
  request actually came through. Some IPMI implementation are notorious for
  ignoring power requests under certain conditions.

* Some actions require the machine to be off to work correctly or at all. For
  example, some hardware was reported to refuse to mount virtual media devices
  on a powered on machine.

* When multi-tenant networking is used, it's essentially to switch the
  networking with the machine powered off, otherwise the code running on it
  will be exposed to both networks (e.g. IPA will stay running on the tenant
  network).

Unfortunately, in some cases powering off a machine is not possible:

* Some implementations of the NC-SI_ technology suffer from a serious drawback:
  the NIC that is shared with the BMC is powered off whenever the machine is
  powered off. When that happens, it is no longer possible to power on the
  machine remotely.

* DPU's may not support the power off action at all, relying on the parent
  machine power state instead. They may support reboot/reset though.

While the second case is related to an emerging technology, the first case is
already seen in the wild and causes issues with the adoption of Ironic.

.. _NC-SI: https://en.wikipedia.org/wiki/NC-SI

Proposed change
===============

Add a new optional node flag ``disable_power_off``. When set to ``True``,
Ironic will avoid ever issuing an explicit power off request.  Specifically:

* All *power interfaces* will use an explicit reboot request (or fail if it's
  not available) even when normally they would use a power-off/power-on pair
  (e.g. ``redfish``). To detect the reboot, we'll insert a hardcoded sleep and
  then wait for the machine to be on.

* The ``tear_down_agent`` deploy step will no longer try to power off the
  machine. Instead, after collecting the ramdisk logs, it will issue the new
  ``lockdown`` IPA command to disable IPA (see `Ramdisk impact`_).

* The ``boot_instance`` deploy step will unconditionally use hard out-of-band
  reset instead of the in-band power off command. The previously issued
  ``lockdown`` command will ensure that the disk caches are flushed already.

* The ``tear_down_inband_cleaning`` function will issue a reboot request after
  de-configuring IPA via ``clean_up_ramdisk``. Same for
  ``tear_down_inband_service``.

* On deployment, cleaning, inspection or servicing failure, the machine will
  stay on with IPA running.

* Validation will fail for any requested deploy, clean or service steps that
  include an explicit power off command.

Downsides
---------

* The usage of ``disable_power_off`` opens up a potential vulnerability in the
  multi-tenant networking because IPA will be available on the tenant network
  for a short time. To mitigate this problem, a new *lockdown mode* will be
  introduced to IPA to ensure it's at least not operational any more - see
  `Ramdisk impact`_.

* Similarly, during cleaning the instance operating system will be switched
  to the cleaning network before IPA boots. We'll document this as a potential
  issue and add a new configuration option to enable the no-power-off mode
  together with the ``neutron`` interface.

* After ``tear_down_agent``, the machine will still be running. Any custom
  deploy steps or out-of-band actions that rely on the machine to be powered
  off after this step may fail.

* In case of IPMI, if the BMC ignores the reboot request, we'll still mark it
  as successful.

Alternatives
------------

Short of convincing the vendors to fix the NC-SI issue in hardware, I do not
see any alternatives. The NC-SI setup seems to be gaining popularity,
especially in *far edge* setups.

The first version of this specification suggested adding ``disable_power_off``
to ``driver_info`` instead of making it a first-class node field. I changed it
for two reasons: because of how many unrelated places in Ironic will need to
check this field and to provide an easy way to guard access to it via RBAC.

Data model impact
-----------------

None

State Machine Impact
--------------------

None

REST API impact
---------------

A new field will be possible to set on node creation and later on. The access
to it will be guarded by a new microversion and a new RBAC rule.

Client (CLI) impact
-------------------

"openstack baremetal" CLI
~~~~~~~~~~~~~~~~~~~~~~~~~

Expose the new field as ``--disable-power-off`` to the create/set commands.

"openstacksdk"
~~~~~~~~~~~~~~

Expose the new field on the Node object.

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

Add a new command ``lockdown`` that will prepare the machine for a hard reset
and make sure IPA is not practically usable on a running ramdisk. Namely:

* Issue ``sync`` and write 3 to ``/proc/sys/vm/drop_caches`` to flush Linux
  caches.
* For each device, issue ``blockdev --flushbufs <device>`` to flush any
  outstanding I/O operations.
* Stop the heartbeater thread and the API.
* Try to disable networking by running ``ip link set <interface> down`` for
  each network interface.

Security impact
---------------

See Downsides_ for security trade-offs that need to be made.

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

A new security parameter will be added:

``[neutron]allow_disabling_power_off`` (boolean, default ``False``)
    If ``False``, the validation of the ``neutron`` network interface will fail
    for nodes that have ``disable_power_off`` enabled. If set to ``True``, this
    feature will be usable together.

Developer impact
----------------

Authors of 3rd party power interfaces must take the new flag into account.
We'll give them a heads-up via release notes.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Dmitry Tantsur (dtantsur)

Other contributors:
  TBD

Work Items
----------

* Update all power interfaces to respect the new flag.
* Update the agent deploy steps to respect the new flag.

Dependencies
============

None

Testing
=======

It's possible to add a standalone job that tests the new mode of operation. We
could even modify sushy-tools to reject power-off calls, but using this
approach in the CI would require a new job, and we're trying to avoid new jobs.

Upgrades and Backwards Compatibility
====================================

No concerns

Documentation Impact
====================

Add a documentation page that lists the use cases and highlights the drawbacks.

References
==========
