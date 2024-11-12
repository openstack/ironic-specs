..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

========
HTTPBoot
========

https://bugs.launchpad.net/ironic/+bug/2032380

A long sought after feature in Ironic is to boot a node from a single
HTTP URL. Except, there is more than one flavor of this functionality.

A first flavor is very virtual media like where we ask the Baseboard
management controller to boot the machine from a URL. The exact details
are vendor specific, but in essence UEFI firmware boots the OS from the
URL.

The second flavor is very similar to PXE booting using DHCP, however the
primary difference is through the use of a vendor class of "HTTPClient" is
utilized instead of "PXEClient". The funny thing, IPv6 network boot
requires the same DHCP response in the form of a URL for the bootfile-url.

The reason to note both is they are both *very* similar, and both can
be tested in our CI at this point. Previously we deferred implementation
of the DHCP path because a lack of ability to test that in CI, but that
is no longer a constraint of late 2023.

Implementing both would be relatively easy and very beneficial for the
operator ecosystem, while also allowing for the navigation of the security
and NAT incompatibility issues which exist with TFTP.

Problem description
===================

Infrastructure operators need reliable, and relatively secure means of
conveying bootloaders and initial artifacts to remote machines.

Ironic's historical answer has been to utilize virtual media.

But not all hardware supports virtual media, and emulating a block device
is not exactly the simplest thing once you boot an operating system. A helpful
aspect with UEFI and the evolution of systems is now we have facilities in
Baseboard management controllers and even UEFI base firmware support
retrieving initial boot payload from a remote system using HTTP(s).

Proposed change
===============

Given the similarity, it makes sense to implement support for both
the BMC oriented path and the DHCP oriented path as part of single effort.

The greater benefit for implementing the DHCP oriented path is we can also
extend this functionality to our downstream consumers with minimal effort.

BMC Path
--------

* Update sushy-tools to support mapping cals to utilize a HTTP next boot
  URL to the virtual media driver code. Functionally this is similar, as
  there appears to be no means to inject the hint to boot from the URL
  into libvirt.
* Update sushy to support requesting to boot a node from a HTTP URL.
* Create a new ``redfish-http-url`` boot interface, named ``RedfishHTTPBoot``
  BootInterface class based upon the underlying class
  ``RedfishVirtualMediaBoot``. In this class, replace ``_insert_vmedia``,
  and ``_eject_vmedia`` class. In essence these methods would perform the
  needful calls to the BMC to perform actions such as setting
  ``BootSourceOverrideEnabled`` to "Once", ``BootSourceOverrideMode`` to
  "UEFI", ``BootSourceOverrideTarget`` to "UefiHttp", and finally
  ``HttpBootUri`` to the ISO file we wish to boot.

Constraints:

* Limited to UEFI.

.. Note::
   We may wish to retool some of the internals of the RedfishVirtualMediaBoot
   class for our implementation sanity.

.. Note::
   This interface with the BMCs is modeled around use of an ISO image as
   a boot source, where as the DHCP path is modeled upon a bootloader, much
   like iPXE.

DHCP Path
---------

* Determine if we need to modify the ``neutron-dhcp-agent``.
* Create an ``httpboot`` BootInterface based upon the existing ``pxe``
  interface code base, and wire through a flag which is set by the PXE
  utils invocation of the DHCP code base, to signal the use of an HTTP(S)
  URL to the conductor. Specifically it would take the form of a flag on the
  pxe_utils method ``prepare_instance_pxe_config`` which would be supplied to
  the ``dhcp_options_for_instance`` method call in the same file. Likely as
  simple as ``pxe_base`` looking for a feature flag on the BootInterface
  class.

.. Note::
   We may wish to make an iPXE specific version of the boot interface as well,
   which is *also* already handled by a capabilities feature flag.
   A separation would enable Grub and iPXE use concurrently.

Alternatives
------------

We could limit scope, but there really are not any alternatives, and both
paths provide a great deal of functionality and benefit to users of Ironic.

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

"openstack baremetal" CLI
~~~~~~~~~~~~~~~~~~~~~~~~~

None, this is entirely a server side capability/configuration.

"openstacksdk"
~~~~~~~~~~~~~~

None, this is entirely a server side capability/configuration.

RPC API impact
--------------

None

Driver API impact
-----------------

No changes to the Driver API are anticipated, although this change functionally
proposes two or three different BootInterfaces to be created.

Nova driver impact
------------------

None

Ramdisk impact
--------------

None. Booting the ramdisk would take the existing code paths with slight
deviation where applicable for each driver case.

Security impact
---------------

The overall security posture of deployments could improve with these
capabilities. Specifically UEFI firmware can boot an ISO or first stage
bootloader over HTTPS.

Other end user impact
---------------------

None

Scalability impact
------------------

None anticipated.

Performance Impact
------------------

None anticipated.

Other deployer impact
---------------------

Deployers interested in using this functionality will have expanded
operational and security capabilities which are in-line with established
interfaces and data models in Ironic.

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Julia (TheJulia) Kreger <juliaashleykreger@gmail.com>

Other contributors:
  Volunteers welcome!

Work Items
----------

* Add support to sushy and sushy-tools for the URL boot operation.
* Add support to pxe_utils logic to generate a URL boot response
  payload, and set that based upon a driver feature/capability flag.
* Compose lots of documentation.
* Create tempest suite to exercise both modes of boot operations.

Dependencies
============

*IF* we need to apply DHCP server configuration, similar to PXE/IPXE,
chain loading attributes, then we will need to engage the Neutron developers.

Testing
=======

The ideal path would be to create a single integration suite test in the
ironic-tempest-plugin to set a node to utilize both interfaces, and toggle
the nodes through a clean step, which would prove the interfaces work as
we expect.

Upgrades and Backwards Compatibility
====================================

No issues are anticipated here.

Documentation Impact
====================

We will likely need to compose more documentation than code in every
case of these interface.

References
==========

* https://www.dmtf.org/sites/default/files/standards/documents/DSP2053_2022.3.pdf
* https://bugs.launchpad.net/ironic/+bug/2032380
* https://en.opensuse.org/UEFI_HTTPBoot_Server_Setup

