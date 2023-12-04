..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

======================
Boot configuration API
======================

https://bugs.launchpad.net/ironic/+bug/2044561

Problem description
===================

Currently, an Ironic conductor generates various boot files (e.g. iPXE scripts)
in the public directory of the HTTP server associated with it. Then dynamic
DHCP configuration with Neutron is used to point a node at the right HTTP
server.

For standalone installations, the DHCP configuration is usually static. It
works well with a single conductor, but is not operational out-of-box in a
multi-conductor setup: a node simply does not know which HTTP server to boot
from.

Proposed change
===============

New API will be added to Ironic to serve boot configuration files, with iPXE
being the reference implementation. This approach will allow us to rely on
the existing hash ring to direct the request to the right conductor. See `REST
API impact`_ for further details.

This is how the boot process will work in the case of iPXE, standalone
Ironic and static DHCP configuration:

#. The Node's iPXE firmware initiates a new DHCP session.
#. The DHCP request reaches the Ironic's DHCP server (usually dnsmasq).
#. The DHCP server responds with an IP address and the catch-all boot script.
   This boot script will be located next to an arbitrary conductor, quite
   likely the one co-existing with the DHCP server.
#. The boot script will direct the iPXE firmware to the URL in the form of
   ``http://<IP>:6385/v1/boot/<MAC>/boot.ipxe`` where ``<IP>`` is the IP of any
   Ironic API instance (most likely the one co-existing with the HTTP server),
   ``<MAC>`` is the node's MAC address.
#. Ironic API will find the node by MAC and direct the request to the correct
   conductor.
#. The conductor responsible for the node returns the iPXE script.

Alternatives
------------

One proposed approach is to `enable coordination between conductors
<https://review.opendev.org/c/openstack/ironic-specs/+/873662>`_. While
potentially useful in more cases, that proposal has a JSON RPC multiplication
problem in a standalone setup.

The other approach to the problem is to introduce managed standalone DHCP. The
first step towards it has already been done: Ironic can manage its dnsmasq
server. In a multi-conductor setup, it may imply having several dnsmasq
instances on the same network, which is a potentially problematic setup. The
current implementation still requires some sort of coordination between
conductor or a periodic task to disable access to the DHCP servers of unrelated
conductors.

A much better, although also the most complex, option would be to use an
existing DHCP server with API access. One such server is `Kea
<https://www.isc.org/kea/>`_. The main problem: such a complex change may be
too much for Ironic right now. The contributors are spread thin already.
On top of that, I've been told that only paid addons give us what we need.

Data model impact
-----------------

None

State Machine Impact
--------------------

None

REST API impact
---------------

``GET /v1/boot/<MAC>/<NAME>``

``<MAC>``
  MAC address of any NIC of a node.
``<NAME>``
  Configuration name to request (e.g. ``boot.ipxe``).

The API will find the node by the MAC address, check its provision state and
call into the ``get_boot_config`` RPC on success. On failure, a generic HTTP
404 will be returned to avoid disclosing any further information.

.. note::
   The whole API branch ``/v1/boot`` will not be versioned since we don't
   expect firmware implementations to support extra headers or any sort of
   reasonable version negotiation.

Client (CLI) impact
-------------------

None. The API is not for end users.

"openstack baremetal" CLI
~~~~~~~~~~~~~~~~~~~~~~~~~

None

"openstacksdk"
~~~~~~~~~~~~~~

None

RPC API impact
--------------

.. code-block:: python

   def get_boot_config(self, context, node_id, name):
       """Request a boot configuration file."""

Driver API impact
-----------------

The ``boot`` interface will get a new call:

.. code-block:: python

   def get_boot_config(self, task, name):
       """Request a boot configuration file.

       :param task: a TaskManage instance with a shared lock.
       :param name: configuration name.
       :raises: NotFound if the configuration cannot be produced.
       """
       raise exception.UnsupportedDriverExtension(
           driver=task.node.driver, extension='get_boot_config')

A reference implementation will be added to the iPXE boot interface, supporting
a configuration called ``boot.ipxe`` - the iPXE script.

Nova driver impact
------------------

None

Ramdisk impact
--------------

None

Security impact
---------------

The new API will allow enumerating nodes in certain states by their MAC
addresses. Some information may potentially be exposed by the boot
configuration. The enumeration is already possible with the lookup API, and
the configuration can be leaked by the boot scripts in the HTTP server.
We will advise operators to limit access to the new API endpoints.

On top of that, the boot interface's ``validate`` will not be called to avoid
exposing information about the node fields.

Other end user impact
---------------------

None

Scalability impact
------------------

Serving boot scripts via the API is somewhat less efficient than from an HTTP
server. Operators concerned about the impact can opt into using the old
approach.

We will avoid using an exclusive lock or launching additional threads in
the implementation. The initial version will just read the existing files from
disk.

Performance Impact
------------------

None

Other deployer impact
---------------------

The feature will be configured with a few new options:

``[pxe]ipxe_use_boot_config_api = False``
    Enables the feature. If true, the generated root iPXE script
    (``boot.ipxe``) will contain links to the boot configuration API, not to
    the HTTP server.

``[pxe]ipxe_config_api_root_url = <None>``
    Specifies the root URL to use for links to the boot configuration API.
    An example use case is an Ironic deployment with TLS: iPXE does not support
    custom certificates without recompiling the firmware, so e.g. a proxy must
    be established instead.

``[api]restrict_boot_config = True``
    Instructs the API to be restricted to only nodes in ``* WAIT`` states.
    Operators using fast-track may want to set this to False.

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Dmitry Tantsur (dtantsur)

Work Items
----------

TODO

Dependencies
============

None

Testing
=======

We can switch Bifrost to the new API. It's highly likely that Metal3 will also
switch to it in the near future as we develop its HA story.

Upgrades and Backwards Compatibility
====================================

None.

Documentation Impact
====================

Installation guide may need to be adjusted.

References
==========
