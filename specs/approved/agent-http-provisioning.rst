..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=========================================================
The direct deploy interface provisioning with HTTP server
=========================================================

https://storyboard.openstack.org/#!/story/1598852

This spec proposes a mechanism to provision baremetal nodes by hosting custom
HTTP service as an image source provider to ``direct`` deploy interface, when
the Image service is utilized.

Problem description
===================

Currently the ``direct`` deploy interface requires an unauthenticated image
source link, so that the agent running at ramdisk can download the image from
provided link and deploy it to the hard disk.

In a typical deployment, user images are managed by the Image service and in
most cases, access is controlled by the Identity service. The ``direct``
deploy interface relies on the Object Storage service to generate an
unauthenticated URL which is accessible for a period (i.e. tempurl).

The problem is the Object Storage service is not always adopted in a
deployment due to various reasons, and itself imposes restrictions on
deployment. E.g.:

* It profits low for a small cloud but takes more hardware resource.
* It requires baremetal nodes to have access to control plane network, which
  is a restriction to network topology.
* It requires the Image service be configured with a backend of swift, which
  may conflicts with original one.

As there is no mechanism or means for ironic to leverage a local HTTP server
to provide temporary image file for IPA to facilitate a node deployment, this
proposal is to offer an alternative by providing such support.

Proposed change
===============

An HTTP server on the ironic conductor node is required for this feature to
work.

Currently there are two scenarios, if the ``instance_info['image_source']``
indicates it's a glance image, the ``direct`` deploy interface generates
tempurl via glance client, and stores it to ``instance_info['image_url']``,
otherwise it will be used directly as ``image_url``. Typically the two
cases represent using the Bare Metal service in the cloud or as a standalone
service, respectively.

Introduces a new string option ``[agent]image_download_source`` to control
which kind of image URL will be generated when the ``image_source`` is a
glance image. Allowed values are ``swift`` and ``http``, defaults to ``swift``.

The process of the ``direct`` deploy interface on different configurations
is defined as:

* ``swift``: keeps current logic, generates tempurl and update it to
  ``instance_info['image_url']``.

* ``http``: downloads instance image via ``ImageCache`` before node
  deployment, makes the cached image accessible by local HTTP service,
  generates proper URL and updates it to ``instance_info['image_url']``.

The existing ``[deploy]http_root`` and ``[deploy]http_url`` are reused for
storing instance image symlinks and generating instance image URLs. A new
string option ``[deploy]http_image_path`` is introduced to keep it isolated
with iPXE related scripts. The default value is ``agent_images``.

The ``direct`` deploy interface will use the same instance cache for image
caching, this will be performed at ``AgentDeploy.deploy``. After an instance
image is cached, the ``direct`` deploy interface creates a soft symlink at
``<http_root>/<http_image_path>`` to reference the instance image. It will be
``/httpboot/agent_images/<node-uuid>`` if all goes to default.

The ``direct`` deploy interface generates URL for the instance image and
updates it to ``instance_info`` at ``AgentDeploy.prepare``. The corresponding
image URL will be ``<http_url>/<http_image_path>/<node-uuid>``. If
``[DEFAULT]force_raw_images`` is set to true, checksum will be recalculated
and updated as well. It is highly encouraged to set it false for better
performance.

The symbolic link will be removed at ``AgentDeploy.deploy`` when a node deploy
is done, or ``AgentDeploy.clean_up`` when a node is teared down from the state
``deploy failed``.

Alternatives
------------

Another implementation approach
`Support all glance backends in the agent <https://storyboard.openstack.org/#!/story/1526241>`_
is to support IPA directly downloading instance image from glance, the
deployment restriction of this approach is the same as agent today, baremetal
has to access glance at provisioning network. But it can address the
dependency issue on glance backend, thus can be a further work.

Instead of supporting HTTP provisioning from the ``direct`` deploy interface,
it can also be implemented as a new deploy interface, ``direct-http`` for
example.

Data model impact
-----------------

None

State Machine Impact
--------------------

None.

REST API impact
---------------

None

Client (CLI) impact
-------------------

None.

"ironic" CLI
~~~~~~~~~~~~

"openstack baremetal" CLI
~~~~~~~~~~~~~~~~~~~~~~~~~

RPC API impact
--------------

None.

Driver API impact
-----------------

None.

Nova driver impact
------------------

None

Ramdisk impact
--------------

None

Security impact
---------------

Providing HTTP service on ironic conductor node will expose accessible port
thus can be a security impact. There are several ways to improve security:

#. Bind the port to the network interface dedicated to provisioning networks.
#. Configure firewall to prevent access from source IP addresses other than
   the provisioning networks.

There might be other ways, but that's beyond the scope of this spec.

To allow HTTP server accessing instance image in the cache directory, the
file-creation mask of user for ironic conductor service should be configured
to be accessible by the user of HTTP service. Most systems use 022 or 002 as
the default umask, it should be sufficienth. There would be a security impact
if it's not the case.

Other end user impact
---------------------

None

Scalability impact
------------------

Instance images will be cached on the ironic conductor node once the
``[agent]image_download_source`` is set to ``http``, it will cost more
disk space if the conductor node is using ``direct`` deploy interface before.
The expected space usage basically should be the same with ``iscsi``
deploy interface.

IPA downloads instance image directly from the conductor node, which will
reduce traffic on the control plane network, by the cost of increasing traffic
on each conductor node. Substantially the consumption should be equivalent
with the ``iscsi`` deploy interface if ``[DEFAULT]force_raw_images`` is set to
true.

Performance Impact
------------------

None

Other deployer impact
---------------------

When using this feature, an HTTP server should be set up and configured on
each ironic conductor node.

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  kaifeng

Work Items
----------

* Promote instance cache to be a global cache, usable for other interfaces.
* Implement the proposed work for ``direct`` deploy interface, includes image
  caching, checksum recalculating, symlink mangement, etc.
* Update documents.

Dependencies
============

None

Testing
=======

This feature will be covered by unit test.


Upgrades and Backwards Compatibility
====================================

Two new options ``[agent]image_download_source`` and
``[deploy]http_image_path`` are introduced in this feature.

``[agent]image_download_source`` defaults to ``swift``, which should have no
impact on upgrades.

Documentation Impact
====================

Update admin/interfaces/deploy.rst to describe the usage of this feature.

References
==========

None
