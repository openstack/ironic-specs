..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=============================
Exposing Hardware Capabilties
=============================

https://blueprints.launchpad.net/ironic/+spec/exposing-hardware-capabilities

Hardware can have a wide range of capabiltiies and potential configurations.
Ironic should expose these capabilities in a declarative way, and allow
deployers to configure custom Nova flavors that map to specific types of
hardware or hardware configurations. Ironic should then ensure these assertions
about the hardware are made valid during the deploy process.

For instance, a machine booted with capabilities ["vt:on", "turbo_mode:off"]
would have Ironic properly configure those tenant-specific BIOS settings
before deploying an image onto the node.

Problem description
===================

Deployers of Ironic currently must configure machines exactly as they would
like them to be configured when deployed to. For instance, a deployer who
wanted two different configurations of a given node to be mapped to two
different nova flavors, that deployer would have to split their capacity,
configure one half differently than the other, and manually add a capability
string to node.properties.capabilities diffierentiating them that Nova could
then schedule against.

Possible use cases include:

* Setting tenant-specific BIOS settings at deploy time
* Specifying desired firmware versions (and applying that firmware version) at
  deploy time
* Configuring boot mode (uefi vs bios) at deploy time
* Configuring a boot disk raid at deploy time
* Specifying extra hardware attributes (e.g., server model, secure boot, TPM)
  for Nova scheduling

Proposed change
===============

Nova scheduler would pass through the capabilities used to scheduled to a
node, then Ironic would use that information to configure the node as desired
in the flavor.
