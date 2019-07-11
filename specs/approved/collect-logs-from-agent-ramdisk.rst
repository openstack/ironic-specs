..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===============================
Collect logs from agent ramdisk
===============================

https://bugs.launchpad.net/ironic/+bug/1587143

This spec adds support for retrieving the deployment system logs from
agent ramdisk.

Problem description
===================

Currently we do not have any documented mechanism to automatically retrieve
the system logs from Bootstrap. Having access to agent ramdisk logs may be
highly required especially after deployment failure. Collecting logs on
remote server is common deployment thing. There are a lot of proprietary,
opensource, standardized technologies that solve this task. Lets walk
through linux natively supported:

#. Syslog: is the standardized protocol for message logging, described in
   `RFC. <https://tools.ietf.org/html/rfc5424>`_ All distros supports
   syslog in different implementations ``rsyslogd``, ``syslogd``,
   ``syslog-ng``

#. Systemd `journal-remote <https://fedoraproject.org/wiki/Changes/Remote_Journal_Logging>`_:
   systemd tool to send/receive journal messages over the network.


Proposed change
===============

The proposed implementations is about adding documentation that helps
Operators to build agent ramdisk with collecting logs feature. On top of
syslog and systemd journal-remote technologies.


Changes in IPA
--------------

A new kernel parameter is added ``use_syslog``.

#. ``use_syslog`` (Boolean): Whether IPA should send the
   logs to syslog or not. Defaults to "False".

Changes in Ironic
-----------------

New pxe_append parameters are added ``use_syslog`` and ``syslog_server``
in ``[agent]`` section.

#. ``use_syslog`` boolean): Whether IPA should send the
   logs to syslog or not. Defaults to "False".

#. ``syslog_server`` (string): IP address or DNS name of syslog server
   to send system logs to. Defaults to "IP address of ironic-conductor node."
   The variable may be used to configure ``rsyslogd`` or ``syslog`` or any
   other syslog server implementation.

Changes in agent ramdisk
------------------------

Bootstrap should support remote logging via syslog/systemd. All agent ramdisk
changes are related to logging tool configuration (rsyslogd, syslogd,
journal-remote). The logging service should be started right after
networking service to make sure that we send all logs from OpenStack services.
On ``Collector`` side (ironic-conductor) we receive messages from
``Originator`` (agent ramdisk) and place the according to local rules.
It may be directory on the
filesystem: /var/log/remote/ironic/<node_uuid>/<log_filename>


Alternatives
------------

Implement logs collecting mechanism in Ironic and IPA as it described in
https://review.opendev.org/323511


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

Support will be added to ramdisk build tools, such as ``diskimage-builder``
and image building scripts under IPA repository to build ramdisks with remote
logging support.

Security impact
---------------

None.

Other end user impact
---------------------

None.

Scalability impact
------------------

None

Performance Impact
------------------

None

Other deployer impact
---------------------

Deployer chooses which mechanism for collecting logs should be used.
General changes to agent ramdisk described at `Changes in agent ramdisk`_

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  lucasagomes <lucasagomes@gmail.com>
  vsaienko <vsaienko@mirantis.com>

Other contributors:


Work Items
----------

* Add documentation that describes how to configure ``Collector`` on
  ironic-conductor, and ``Originator`` in ironic agent ramdisk on top of
  rsyslogd or syslogd or journal-remote.

* Add an examples of building most popular images (coreos, tinyipa) with
  syslog support. New ``dib`` element will be added as well.

* Integrate configuring ``Collector`` on devstack host.


Dependencies
============

None

Testing
=======

Collecting logs from agent ramdisk will be configured on gate jobs. The
directory with logs from agent ramdisk will be archived and available in the
jobs artefacts.

Upgrades and Backwards Compatibility
====================================

None.

Documentation Impact
====================

Documentation will be provided about how to configure syslog ``Collector``
to receive and store logs from ``Originator``.

References
==========

None.
