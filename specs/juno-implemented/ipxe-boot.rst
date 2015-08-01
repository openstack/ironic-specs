..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=========
iPXE boot
=========

https://blueprints.launchpad.net/ironic/+spec/ipxe-boot

This blueprint presents the work needed to add support for iPXE in Ironic.

Problem description
===================

As the size of our deploy ramdisk would continue to increase (Ironic
Python Agent) we need a more reliable way to transfer such data via
the network without relying on TFTP. The problem with TFTP is that it's
unreliable and any transmission error will result consequently in boot
problems (The first T in TFTP stands for trivial).

Proposed change
===============

By adding support for iPXE we would have the ability to transfer data
through HTTP which is a reliable protocol.

* New config options:
    - ipxe_enabled: Whether iPXE is enabled or not.
    - ipxe_boot_script: The path to the main iPXE script file.
    - http_server: The IP address of the HTTP server.
    - http_root: The HTTP root path.

* When generating the PXE configuration file the kernel and initrd
  parameters should contain the HTTP URL for the files and not the TFTP
  path.

* All the configuration files, ramdisks and kernels will now be put in
  the HTTP directory instead of the TFTP directory.

* The pxe_bootfile_name config option should point to the iPXE image
  (undionly.kpxe).

* A configuration template for iPXE.

* The pxe_config_template config option should point to the iPXE
  configuration template.

* An iPXE script file (ipxe_boot_script config option) which is the
  file fetched by the client after it has loaded the iPXE image, and from
  there the script will load the MAC-specific iPXE configuration file for
  that request.

* When passing the DHCP boot options to Neutron we also have to pass
  the HTTP link pointing to the iPXE script file.

It's important to note that Ironic is not responsible for managing the
HTTP server, just like the TFTP server, it should be configured and
running on the Node that ironic-conductor was deployed.

Another important note is that the iPXE image (undionly.kpxe) used for
chainloading is sent to the clients via TFTP, so we still need a TFTP
server up and running, this is the only TFTP transaction in the whole
process, once the client has loaded iPXE, everything happens over HTTP.

Alternatives
------------

Continue to use the standard PXE and rely on the TFTP protocol to transfer
the data.

Data model impact
-----------------

None

REST API impact
---------------

None

Driver API impact
-----------------

None

Nova driver impact
------------------

None

Security impact
---------------

While not part of work proposed by this spec, iPXE supports using the
HTTPS protocol which allows encrypting all communication with the HTTP
server, this patch can be considered a plumbing work for that to be
implemented in the future.

Other end user impact
---------------------

To enable iPXE users would have to set the http_root, http_server
and ipxe_enabled configuration options along with the tftp_root and
tftp_server options.

Scalability impact
------------------

As a future work, we can add support to be able to fetch images and
configuration files directly from Glance or Swift since those are
already scalable.

Performance Impact
------------------

TFTP can be extremely slow, so fetching data over HTTP can improve the
speed of transferring the images from the conductor to the Node being
booted.

Other deployer impact
---------------------

New config options:
    - ipxe_enabled: Whether iPXE is enabled or not.
    - ipxe_boot_script: The path to the main iPXE script file.
    - http_server: The IP address of the HTTP server.
    - http_root: The HTTP root path.

By default iPXE will be disabled and so should not change anything on the
current flow to deploy/configure Ironic. In the future since we are moving
towards having the Ironic Python Agent to be the standard provisioning
method, we might want to enable iPXE by default as part of that effort.

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  lucasagomes

Other contributors:
  None

Work Items
----------

See the "Proposed change" section.


Dependencies
============

A HTTP server up and running.

Testing
=======

* Unit tests.

* Add support to DevStack to be able to configure Ironic to use iPXE.

Documentation Impact
====================

Documentation should be modified to instruct operators about how to
enable and configure Ironic to use iPXE.

References
==========

None
