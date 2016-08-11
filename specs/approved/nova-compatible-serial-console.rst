..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==============================
Nova-compatible Serial Console
==============================

https://bugs.launchpad.net/ironic/+bug/1553083

This implements console interfaces using "socat" which provides nova-
compatible serial console capability.

Problem description
===================

Currently, ironic's only console interface is based on shellinabox,
which provides a stand-alone web console, and is not compatible with
nova-serialproxy.


Proposed change
===============

In order to address the problem of not having a serial console compatible with
nova, this spec proposes using a command line tool ``socat`` [#]_ in
conjunction with IPMI Serial-Over-Lan capabilities.
``socat`` is a command line based utility that establishes two bidirectional
byte streams and transfers data between them.
This application allows us to activate the ipmitool Serial-over-LAN
process and redirect it through a TCP connection which can then be consumed
by the ``nova-serialproxy`` service.

Each console (socat + ipmitool) will run on its own process on the same host
that the ironic-conductor which is currently managing that node is running.
``socat`` will run first, then it will execute ipmitool when it has connections
from ``nova-serialproxy``, and will work like a ``bridge`` between them.

Start/stop of an ironic-conductor process
-----------------------------------------

* When ironic-conductor starts, if console mode of the node is true, start
  socat also.

* When ironic-conductor stops, if console is started, stop it.

* About takeover work, we're planning:

  * When an ironic-conductor stops, console session will be stopped due to
    security reason. In this case, if there are other ironic-conductors,
    they takeover nodes and enables their console session again.
  * When ironic-conductor starts, if there are console enabled nodes, the
    ironic-conductor starts their console.

* Start/stop console will be implemented with subprocess.Popen.

* About start/stop socat, we're planning to implement a new console interface
  IPMISocatConsole and implement same methods as shellinabox classes.
  About this, discussed in: [#]_ .

* About reconnection, for example, in case of temporary network problem with
  using Horizon, "Closed" message will be shown. And socat itself
  supports session reconnect from client side, so that, when the network
  problem is resolved, users can try to reconnect.

Specify which of shellinabox or socat to use
--------------------------------------------

We're planning to specify which driver to use shellinabox or socat by setting
driver like ``pxe_ipmitool_socat`` or ``agent_ipmitool_socat``.
(Please see ``Other deployer impact`` section.)

Alternatives
------------

Creating a new service "ironic-xxx" instead of adding a new ConsoleInterface
to ``ironic-conductor`` . The upside of new service is that it can be scaled
independently, and has no implications on conductor failover. However
it will need its own HA model as well, and will be more work for developers
(API, DB, driver, ...).


Data model impact
-----------------

None


State Machine Impact
--------------------
None

REST API impact
---------------

The response body of "GET /v1/nodes/<UUID>/states/console" contains a
JSON object like below::

  {
    "console_enabled": true,
    "console_info": {
      "url": <url>,
      "type": <type>
    }
  }

In case of using socat instead of shellinabox,
<type> will be "socat" and <url> is like "tcp://<host>:<port>".


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

get_serial_console() will be implemented in ironic driver of Nova. It
returns a dictionary, similar to
nova.virt.libvirt.driver.LibvirtDriver.get_serial_console(). No other
impact for nova, and nova-serialproxy works well with the new one.
And also, nova has agreed to the nova side of the work [#]_.

Ramdisk impact
--------------

None

Security impact
---------------

The connection between nova-serialproxy and socat is TCP based, like
KVM. Socat supports OpenSSL connections, so we can improve the
security in the future.

Other end user impact
---------------------

None

Scalability impact
------------------

If a conductor can service 1000 nodes, and a process is created for a console
to each node, but it's the same scalability issue as shellinabox.

Performance Impact
------------------

None

Other deployer impact
---------------------

To use socat serial console, deployer needs to specify new driver.
For example, to use PXE + IPMItool + socat, specify ``pxe_ipmitool_socat``.
To use IPA + IPMItool + socat, specify ``agent_ipmitool_socat``.
To use existing shellinabox console, deployer doesn't need to change anything.
The new console interface ``IPMISocatConsole`` will be supported by two
new drivers: ``pxe_ipmitool_socat`` and ``agent_ipmitool_socat``.
After ``Driver composition reform`` [#]_ is implemented, this
feature will be available for a lot more drivers (or hardware types).

About configuration options, existing options ``terminal_pid_dir``,
``subprocess_checking_interval``, ``subprocess_timeout`` are available for
socat in the same way as shellinabox.
``terminal_cert_dir`` is not used in the case of socat because SSL is not
supported.
``terminal`` is not used in the case of socat because hard-coded ``socat`` is
used in the code, and absolute path is not needed because it's distro specific,
in Ubuntu for example it's ``/usr/bin/socat``, but it might be different in
other distros.

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:

  * Akira Yoshiyama <akirayoshiyama@gmail.com>

Other contributors:

  * Dao Cong Tien <tiendc@vn.fujitsu.com>
  * Nguyen Tuong Thanh <thanhnt@vn.fujitsu.com>
  * Cao Xuan Hoang<hoangcx@vn.fujitsu.com >
  * Hironori Shiina <shiina.hironori@jp.fujitsu.com>
  * Yuiko Takada Mori <y-mori@ti.jp.nec.com>

Work Items
----------

* Implement ``IPMISocatConsole`` and ``NativeIPMISocatConsole`` class
  inherited from ``base.ConsoleInterface``.


Dependencies
============

None

Testing
=======

Unit Testing will be added.

Upgrades and Backwards Compatibility
====================================

None

Documentation Impact
====================

Add configuration description to the install guide.

References
==========

.. [#] http://linux.die.net/man/1/socat
.. [#] https://review.openstack.org/#/c/293873/
.. [#] https://blueprints.launchpad.net/nova/+spec/ironic-serial-console-support
.. [#] https://review.openstack.org/#/c/188370/
