..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=========================================================
The direct deploy interface provisioning with HTTP server
=========================================================

https://storyboard.openstack.org/#!/story/1598852

This spec proposes a mechanism to provision baremetal nodes by hosting custom
HTTP service as an image source provider to the ``direct`` deploy interface,
when the Image service is utilized.

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

* It has little benefit for a small cloud but takes more hardware resource.
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
otherwise it will be directly taken as ``image_url``. The two cases typically
represent using the Bare Metal service in the cloud or as a standalone
service, respectively.

The proposal introduces a new string option ``[agent]image_download_source``
to control which kind of image URL will be generated when the ``image_source``
is a glance image. Allowed values are ``swift`` and ``http``, defaults to
``swift``.

The process of the ``direct`` deploy interface on different configurations
is defined as:

* ``swift``: Keeps current logic, generates tempurl and update it to
  ``instance_info['image_url']``.

* ``http``: Downloads instance image via ``InstanceImageCache`` before node
  deployment, creates symbolic link to downloaded instance image in the
  directory accessible by local HTTP service, generates proper URL and updates
  it to ``instance_info['image_url']``.

The existing ``[deploy]http_root`` is reused for storing symbolic links to
downloaded instance images. A new string option ``[deploy]http_image_subdir``
is introduced to keep it isolated with iPXE related scripts. The default value
is ``agent_images``. The existing ``[deploy]http_url`` is reused to generate
instance image URLs.

The ``direct`` deploy interface will use the same instance cache for image
caching, the caching will be performed at ``AgentDeploy.deploy``. After an
instance image is cached, the ``direct`` deploy interface creates a symbolic
link at ``<http_root>/<http_image_subdir>`` to reference the instance image.
It will be ``/httpboot/agent_images/<node-uuid>`` if all goes to default.

The ``direct`` deploy interface generates URL for the instance image and
updates it to ``instance_info`` at ``AgentDeploy.prepare``. The corresponding
image URL will be ``<http_url>/<http_image_subdir>/<node-uuid>``. The symbolic
link will be removed at ``AgentDeploy.deploy`` when a node deploy is done, or
``AgentDeploy.clean_up`` when a node is teared down from the state
``deploy failed``.

Rule to convert image
---------------------

Currently the ``iscsi`` deploy interface will convert image to ``raw`` if
``[DEFAULT]force_raw_images`` is set to True.

While IPA treats instance image in two different ways:

* If the instance image format is ``raw``, ``stream_raw_images`` is True and
  image type is whole disk image, the image will be streamed into the target
  disk of the Bare Metal.
* Otherwise the image will be cached into memory before written to disk.

To avoid a raw image been cached into the memory of Bare Metal, the ``direct``
deploy interface will convert image to raw only if following criteria is met:

* ``[DEFAULT]force_raw_images`` is set to True,
* ``[agent]stream_raw_images`` is set to True,
* The instance image type is a whole disk image.

The ``direct`` deploy interface will recalculate MD5 checksum and update
necessary fields to ``instance_info`` if image conversion happened.

Cache sharing
-------------

``iscsi`` and ``direct`` deploy interface are sharing the same cache,
but apply different rule to whether the image should be converted to raw.
It leads to cache compatibility issue when both interface are in use.

As an example, suppose we deploy node A (using iscsi) with a partition image,
then deploy node B (use direct) with the same image. The image in the cache is
converted to raw, but according to the rule of ``direct`` deploy interface, it
assumes image will not be converted to raw, though it specifies ``force_raw``
to false to the image cache, due to cache hit, actually no image action will
be performed, this will leads to the situation that the ``direct`` deploy
interface actually provide a raw image but without MD5 recalculation.

Vice versa, if we reverse the order above, the ``iscsi`` deploy interface may
get a qcow with ``[DEFAULT]force_raw_images`` set to true, though it's
probably not an issue because populate_image will check image format before
writing. it's still not a consistent behavior.

To address the issue described above, this spec proposes to update
``ImageCache.fetch_image`` to take the input argument ``force_raw`` into
account for the master image file name:

* The master file name is not changed if ``force_raw`` is set to ``False``.
* The master file name will have ``.converted`` as file extension if
  ``force_raw`` is set to ``True``, e.g.::

    /var/lib/ironic/master_images/6e2c5132-db24-4e0d-b612-478c3539da1e.converted

Note that the ``.converted`` extension merely acts as an indicator that the
image downloaded has gone through the conversion logic. For a raw image in the
glance, the name of master image file still has ``.converted`` as long as
``force_raw`` argument passed in is True.


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
The expected space usage basically should be no more than ``iscsi`` deploy
interface.

IPA downloads instance image directly from the conductor node, which will
reduce traffic on the control plane network, by the cost of increasing traffic
on each conductor node. The consumption should be no more than ``iscsi`` deloy
interface.

Performance Impact
------------------

Depending on the hardware and image type, recalculating MD5 checksum for a raw
image could consume considerable amount of CPU/IO resources. If the
performance on ironic conductor node is in concern, please set
``[DEFAULT]force_raw_images`` to ``False`` (The option is ``True`` by default).

Other deployer impact
---------------------

When using this feature, an HTTP server should be set up and configured on
each ironic conductor node.

Each HTTP servers should be configured to follow symlinks for instance images
are accessible from external requests. Refer to ``FollowSymLinks`` if Apache
HTTP server is used, or ``disable_symlinks`` if Nginx HTTP server is used.

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  kaifeng

Other contributors:
  sambetts

Work Items
----------

* Promote instance cache to be a global cache, usable for other interfaces.
* Implement the proposed work for ``direct`` deploy interface, includes image
  caching, checksum recalculating, symlink management, etc.
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
``[deploy]http_image_subdir`` are introduced in this feature.

``[agent]image_download_source`` defaults to ``swift``, which should have no
impact on upgrades.

The change of the cache file naming could probably invalidate some cached
instance images after upgrades, they will be re-cached when used, images not
referenced will be cleaned up eventually. This will have no impact if caching
is disabled before upgrade.


Documentation Impact
====================

Update admin/interfaces/deploy.rst to describe the usage of this feature.

References
==========

None
