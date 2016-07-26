..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Bare Metal Trust Using Intel TXT
==========================================

https://bugs.launchpad.net/ironic/+bug/1526280

This uses Intel TXT[4], which builds a chain of trust rooted in
special purpose hardware called Trusted Platform Module (TPM)[3] and measures
the BIOS, boot loader, Option ROM and the Kernel/Ramdisk, to determine
whether a bare metal node deployed by Ironic may be trusted.

Problem description
===================
The bare metal tenant has the ability to introduce rootkits and other malware
on the host. Prior to releasing the host to a new tenant, it is prudent to
ensure the machine is in a known good state.

Using Intel TXT[4], the TPM[3], Trusted Boot[1], and remote authentication[2],
it is possible to confirm that the BIOS, boot loader, Option ROM, and the
Kernel/Ramdisk are all in a known good state.

Proposed change
===============
Add a new boot mode, trusted boot:

* Read value "capabilities:trusted_boot" from flavor. Pass boolean value
  "trusted_boot" to ironic.drivers.modules.deploy_utils.switch_pxe_config().
  Switch to "trusted_boot" section.

* Add a new section "trusted_boot" in PXE Configuration. It will make
  use of mboot.c32 which supports multiple loading. It loads TBOOT first.
  TBOOT will measure Kernel/Ramdisk before loading them.
  PXE config template::

    label trusted_boot
    kernel mboot
    append tboot.gz --- {{pxe_options.aki_path}} root={{ ROOT }} ro text
    {{ pxe_options.pxe_append_params|default("", true) }} intel_iommu=on
    --- {{pxe_options.ari_path}}


Alternatives
------------
Secure Boot[5] is used for the same purpose. The main difference is secure boot
will verify the signature before executing while trusted boot uses a hardware
root of trust and can be configured to verify each component before executing
or execute all components and capture "measurements" (aka extended hash
computations) for post verification. So if a node is changed, trusted boot will
still boot it up but give a warning to users. Secure boot will not boot it up
at all.

They are complementary, both making the cloud more secure. It is recommended to
boot nodes with secure boot under uefi and boot nodes with trusted boot under
legacy BIOS. The next step is to combine them together but that is out of the
scope of this spec.

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
Will pass the extra_spec "capabilities:trusted_boot=True" to Ironic

Ramdisk impact
--------------

N/A

.. NOTE: This section was not present at the time this spec was approved.

Security impact
---------------
Increased confidence in bare metal nodes being free of rootkits and other
malware. Intel TXT and TPM are leveraged.

Other end user impact
---------------------
None

Scalability impact
------------------
Our experiments indicate handling concurrent attestation requests is linear
in the number of requests. Attestation occurs on the node release path,
and thus is not latency sensitive.

Performance Impact
------------------
There is an extra attestation step during trusted boot which spends several
seconds. But for bare metal trust no dynamic attestation requests are
entertained. So this is a non-issue.

Other deployer impact
---------------------
* Create a special flavor with 'capabilities:trusted_boot=True'

* Set ``trusted_boot``:``True`` as capability in node.properties.

* Additionally two items need to be provided with tftpboot/httpboot folder
    - "mboot.c32" - Support multiple loading from /usr/lib/syslinux/mboot.c32
    - "tboot.gz"  - a pre-kernel module to do measurement.

* Set up each machine, enable Intel TXT, VT-x and VT-d and take ownership
  of the TPM, reboots, and captures the platform configuration register (PCR)
  values. This is to create the whitelist values that will be registered in
  the attestation service at initialization time.

* Set up an OAT-Server and create the whitelist with all known types of
  hardwares from previous step.

* Create customized images with OAT-Client.

* Run a customized script to verify the trust state of nodes when creating
  instances.

Developer impact
----------------
None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  tan-lin-good

Work Items
----------
  * Add trusted_boot section to pxe_config.template
  * Support trusted_boot flag and switch to trusted_boot.
  * A dib element to create customized images.

Dependencies
============
  * TBOOT[1]
  * OAT[2]
  * Hardware Support: TPM and Intel TXT


Testing
=======
Will add unit tests.
Planning on adding third party hardware CI testing.

Upgrades and Backwards Compatibility
====================================
None.
Backwards compatibility is achieved by not requesting "trusted"
bare metal. Custom tenant images are accommodated by deploying an initial
standard image that has the OAT client embedded. Today Fedora releases come
bundled with the OAT client. This solution approach, while increasing the
number of boots preserves us from having to doctor the tenant image by way
of injecting the OAT client into the same, or requiring that bare metal
users provide images with an OAT client included.

Documentation Impact
====================
Will document usage and benefits.
Here is a doc for the technical detail of Bare metal trust:
https://wiki.openstack.org/wiki/Bare-metal-trust

References
==========
1. http://sourceforge.net/projects/tboot/
2. https://github.com/OpenAttestation/OpenAttestation
3. http://en.wikipedia.org/wiki/Trusted_Platform_Module
4. http://en.wikipedia.org/wiki/Trusted_Execution_Technology
5. https://review.openstack.org/#/c/135228/
6. http://docs.openstack.org/admin-guide-cloud/compute-security.html#trusted-compute-pools
