..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

============================
Collect system logs from IPA
============================

https://bugs.launchpad.net/ironic/+bug/1587143

This spec adds support for retrieving the deployment system logs from IPA.

Problem description
===================

We currently have no mechanism to automatically retrieve the system
logs from the IPA deploy ramdisk. Having access to the logs may be
very useful, especially when troubleshooting a deployment failure.
Currently, there are a few ways to get access to the logs in the ramdisk,
but they are manual, and sometimes it is not desirable to enable them
in production. The following points describe two of them:

#. Have a console session enabled for the node being deployed.

   While this works, it's tricky because the operator needs to figure
   out which node was picked by the scheduler and enable the console
   for it. Also, not all drivers have console support.

#. Disable powering off a node upon a deployment failure.

   Operators could `disable powering off a node upon a deployment
   failure <https://review.openstack.org/#/c/259119>`_ but this has
   some implications:

   a. It does not work in conjunction with Nova. When the instance
      fails to be provisioned nova will invoke destroy() and the Ironic
      virt driver will then force a power off on that node.

   b. Leaving the nodes powered on after the failure is not desirable
      in some deployments.


Proposed change
===============

The proposed implementation consists in having Ironic retrieve the
system logs from the deploy ramdisk (IPA) via its API and then upload
it to Swift or save it on the local file-system of that conductor (for
standalone-mode users).

Changes in IPA
--------------

A new ``log`` extension will be added to IPA. This extension will
introduce a new synchronous command called ``collect_system_logs``. By
invoking this command IPA will then tar, gzip and base64 encode the
system logs and return the resulting string to the caller.

Since we do support different base OSs for IPA (e.g Tiny Core Linux,
Fedora, Debian) we need different ways to find the logs depending on the
system. This spec proposes two ways that should be enough for most of
the distros today:

#. For distributions using ``systemd``, all system logs are available via
   ``journald``. IPA will then invoke the ``journalctl`` command and
   get the logs from there.

#. For other distributions, this spec proposes retaining all the logs
   from */var/log* and the output of the ``dmesg`` command.

The logs from all distributions independent of the init system, will
also contain the output of the following commands files: ``ps``, ``df``,
and ``iptables``.

Changes in Ironic
-----------------

New configuration options will be added to Ironic under the ``[agent]``
group:

#. ``deploy_logs_collect`` (string): Whether Ironic should collect the
   deployment logs or not. Valid options are: "always", "on_failure" or
   "never". Defaults to "on_failure".

#. ``deploy_logs_storage_backend`` (string): The name of the storage
   backend where the response file will be stored. One of the two:
   "local" or "swift". Defaults to "local".

#. ``deploy_logs_local_path`` (string): The path to the directory
   where the logs should be stored, used when the
   ``deploy_logs_storage_backend`` is configured to **local**. Defaults to
   ``/var/log/ironic/deploy``.

#. ``deploy_logs_swift_container`` (string): The name of the Swift
   container to store the logs, used when the
   ``deploy_logs_storage_backend`` is configured to **swift**. Defaults
   to *ironic_deploy_logs_container*.

#. ``deploy_logs_swift_days_to_expire`` (integer):
   Number of days before a log object is `marked as expired in Swift
   <http://docs.openstack.org/developer/swift/overview_expiring_objects.html>`_.
   If None, the logs will be kept forever or until manually deleted. Used
   when the ``deploy_logs_storage_backend`` is configured to **swift**.
   Defaults to *30 days*.

.. note::
   When storing the logs in the local file-system Ironic won't be
   responsible for deleting the logs after a certain time. It's up to
   the operator to configure an external job to do it, if wanted.


Depending on the value of the ``deploy_logs_collect`` Ironic will
invoke ``log.collect_system_logs`` as part of the deployment of the
node (right before powering it off or rebooting). For example, if
``deploy_logs_collect`` is set to **always** Ironic will collect the logs
independently of the deployment being a success or a failure; if it is set
to **on_failure** Ironic will collect the logs upon a deployment failure;
if it is set to **never**, Ironic never collect the deployment logs.

When the logs are collected, Ironic should decode the base64 encoded
tar.gz file and store it according to the ``deploy_logs_storage_backend``
configuration. All log objects will be named with the following pattern:
*<node-uuid>[_<instance-uuid>]_<timestamp yyyy-mm-dd-hh:mm:ss>.tar.gz*. Note
that, ``instance_uuid`` is not a required field for deploying a node when
Ironic is configured to be used in **standalone** mode so, if present
it will be appended to the name.

When using Swift, operators can associate the objects in the container
with the nodes in Ironic and search for the logs of a specific node
using the ``prefix`` parameter, for example:

.. code-block:: bash

  $ swift list ironic_deploy_logs_container -p 5e9258c4-cfda-40b6-86e2-e192f523d668
  5e9258c4-cfda-40b6-86e2-e192f523d668_0c1e1a65-6af0-4cb7-a16e-8f9a45144b47_2016-05-31_22:05:59
  5e9258c4-cfda-40b6-86e2-e192f523d668_db87f2c5-7a9a-48c2-9a76-604287257c1b_2016-05-31_22:07:25

.. note::

  This implementation requires the network to be setup correctly,
  otherwise Ironic will not be able to contact the IPA API.  When
  debugging such problems, the only action possible is to look at the
  consoles of the nodes to see some logs. This method has some caveats:
  see the `Problem description`_ for more information.

.. note::

  Neither Ironic or IPA will be responsible for sanitizing any logs
  before storing them. First because this spec is limited to collecting
  logs from the deployment only and at this point the tenant won't have
  used the node yet. Second, the services generating the logs should be
  responsible for masking secrets in their logs (like we do in Ironic),
  if not, it should be considered a bug.


Alternatives
------------

Since we already provide ways of doing that via accessing the console
or disabling the powering off the nodes on failures, there are few
alternatives left for this work.

The current proposed solution could be extended to fit more use cases
beyond what this spec proposes. For example, instead of uploading it to
Swift or storing it in the local file-system, Ironic could upload it to
a HTTP/FTP server.

As briefly described at `Changes in IPA`_ the method to collect the logs
could be extended to include more logs and output of different commands
that are useful for troubleshooting.

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

Security impact
---------------

None.

As a note, credentials **are not** passed from Ironic to the deploy
ramdisk. The ``ironic-conductor`` service, which already holds the Swift
credentials, is the one responsible for uploading the logs to Swift.

Other end user impact
---------------------

None

Scalability impact
------------------

None

Performance Impact
------------------

The node will stay a little longer in the ``deploying`` provision state
while IPA is collecting the logs, if enabled.

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
  lucasagomes <lucasagomes@gmail.com>

Other contributors:


Work Items
----------

* Add the new ``log`` extension and ``collect_system_logs`` method in IPA.

* Add the new configuration options described in the `Changes in Ironic`_
  section.

* Invoke the new ``log.collect_system_logs`` method in IPA as part
  of the deployment and store the response file according to the
  ``deploy_logs_storage_backend`` configuration option (if enabled).


Dependencies
============

None

Testing
=======

Unittests will be added.

Upgrades and Backwards Compatibility
====================================

None.

As a note, when using an old IPA ramdisk which does not support the new
``log.collect_system_logs`` command Ironic should handle such exception
and log a warning message to the operator if ``deploy_logs_collect``
is set to **always** or **on_failure**.

Documentation Impact
====================

Documentation will be provided about how to configure Ironic to collect
the system logs from the deploy ramdisk.

References
==========

None.
