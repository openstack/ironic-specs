..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================
iPXE Dynamic Configuration
==========================

https://bugs.launchpad.net/ironic/+bug/1526275

This adds support for dynamically generating iPXE configuration
files when booting a node.

Problem description
===================

The current iPXE support depends on configuration files to be cached on
the disk. This creates a dependency between a given ``ironic-conductor``
and a given node (even without a conductor lock on a node) because that
``ironic-conductor`` is the only one able to boot that node. This also
makes take-over more complicated because the new ``ironic-conductor``
will need to regenerate the iPXE configuration files for the new nodes
it's now managing and update the DHCP server accordingly.

Proposed change
===============

The proposed implementation consists of creating a new ``Driver Vendor
Passthru`` method called ``ipxe_config`` that will dynamically generate
the iPXE configuration files for a given node UUID or mac address
depending on the node's provision state.

When Neutron is used with iPXE enabled, it will configure the DHCP server
to make a request to the ``Driver Vendor Passthru`` endpoint using the
node's UUID when booting a node, e.g::

  http://<Ironic API Address>:6385/v1/drivers/<driver_name>/vendor_passthru/ipxe_config?node_uuid=<node UUID>

Ironic will then check the ``provision_state`` of the node and
generate the iPXE configuration file for that state. Say, the node
``provision_state`` is DEPLOYING, we then will return an iPXE
configuration to boot the deploy ramdisk and kernel. If the node
``provision_state`` is ACTIVE, we then return an iPXE configuration
to boot from the image ramdisk and kernel (If local boot and/or full
disk image is not specified). For an unknown ``provision_state`` we just
return an iPXE configuration file that prints out an error explaining the
problem on the node's console log and a warning message in the Ironic log.

If an operator wants to have an external DHCP server (standalone version)
but still benefit from dynamically generated iPXE script files (instead
of using static files) it will be possible by making the same ``Driver
Vendor Passthru`` endpoint to support passing the MAC address of one of
the node's port as parameter, e.g::

  http://<Ironic API Address>:6385/v1/drivers/<driver_name>/vendor_passthru/ipxe_config?port_address=<port address>

When scripting iPXE allows `expanding variables
<http://ipxe.org/scripting#dynamic_scripts>`_ so that an operator can
create a single iPXE script pointing to the Ironic API (and expanding
the ``${mac}`` variable) when configuring their external DHCP server
allowing them to have dynamically generated iPXE configuration for their
environment even when Neutron is not used.

This work can get even more powerful when the images are set to boot from
``http`` [#]_, as then the iPXE drive won't need to save any state on
the disk. As a future work, it would be also possible to add support for
creating a ``Swift Temporary URL`` when booting images being served by
``Glance`` with a ``Swift`` storage backend.


Alternatives
------------

Continue doing what we are doing, generate the configuration files and
saving it to the disk.

Data model impact
-----------------

None

State Machine Impact
--------------------

None

REST API impact
---------------

A new ``Driver Vendor Passthru`` method called ``ipxe_config`` that
supports GET HTTP.

Client (CLI) impact
-------------------

None

RPC API impact
--------------

Currently the RPC method for ``vendor_passthru`` and
``driver_vendor_passthru`` returns a tuple with the return value and a
boolean indicating if the method is asynchronous. We will need another
flag to indicate if the value should be returned as a static file that
will be served by the Ironic API instead of a response body message.

Driver API impact
-----------------

None

Nova driver impact
------------------

None

Security impact
---------------

The new ``Vendor Passthru`` method endpoint needs to be part of the
public API, so that iPXE can get the configuration file from without
authentication. This is the same as the methods ``heartbeat`` or
``lookup`` for the agent driver [#]_.

Other end user impact
---------------------

None

Scalability impact
------------------

A stateless driver can scale better since it won't depend on any
information to be saved on the local conductor.

Performance Impact
------------------

None

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

* Create the new ``ipxe_config`` method for the PXEVendorPassthru interface.

* Change the PXE configuration options passed to the DHCP server to point
  to the ``v1/drivers/<driver
  name>/vendor_passthru/ipxe_config?node_uuid=<node UUID>`` endpoint in
  the Ironic API instead of pointing to the URL to download the boot.ipxe
  script (the script won't be need anymore and will be deleted).

* Extend the ``vendor_passthru`` and ``driver_vendor_passthru`` RPC
  methods to return a flag indicating whether the return value should
  be attached to the response object as a file or returned as a response
  message.

* Update the methods ``prepare_ramdisk`` and ``clean_up_ramdisk`` from
  the **IPXEBoot** interface to not attempt to create or delete the iPXE
  configuration files.


Dependencies
============

* `New boot interface
  <https://review.openstack.org/#/c/177726/6/specs/liberty/ipxe-dynamic-config.rst>`_:
  This spec is refactoring the boot logic out of the current Ironic
  ``deploy`` drivers into a new boot interface.


Testing
=======

Unittests will be added.

Upgrades and Backwards Compatibility
====================================

None

Documentation Impact
====================

The iPXE documentation will be updated to reflect the changes made by
this spec.

References
==========

.. [#] http://specs.openstack.org/openstack/ironic-specs/specs/kilo/non-glance-image-refs.html
.. [#] https://github.com/openstack/ironic/blob/master/ironic/api/config.py
