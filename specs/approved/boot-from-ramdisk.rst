..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===================
Boot from a Ramdisk
===================

https://storyboard.openstack.org/#!/story/1753842

While Ironic, by its very operational nature supports booting from a ramdisk,
we do not empower or enable operators who wish to utilize instances that boot
from ramdisks.

In the use cases desired, these are often ephemeral instances, with no actual
back-end storage. That being said, we of course can't forget cleaning and other
mechanisms that help provide improved value for Ironic in a deployment.

Most of these cases are where an operator is sufficiently knowledgeable  to
construct a ramdisk and kernel image that can be explicitly booted from
RAM. Such cases are common in High Performance Computing environments where
instances may need to be quickly deployed, or are functionally disk-less
in order to remove a point of failure.

Problem description
===================

* Operators desire fully ephemeral instances that essentially operate
  in RAM only. This allows compute-local disks to be dedicated to ephemeral
  storage, or to be omitted from the machine entirely.

* Large scale cluster computing practices have long used prepared
  kernel/ramdisk images in order to help facilitate the stand-up
  and operation of their environments.

* Ironic has _some_ of the support required. We do something somewhat
  similar with boot from volume, and if we ever support RBD booting,
  we would functionally require this exact feature. What delineates
  this from the Boot from Volume iPXE chain loading scenarios and
  virtual media based booting from a remote volume, is that Boot
  from Volume scenarios are ultimately reliant upon back-end block
  storage, which is not always needed or desired for all cases.

Proposed change
===============

We propose to build a ``ramdisk`` deploy interface built upon our
existing ramdisk code and facilities. This would allow us to have a
jump start on working functionality and help us better identify where
refactoring must be required.

The ``ramdisk`` deployment driver interface would be an opt-in interface
which focuses on supporting ramdisk booting cases.

The ``ramdisk`` deployment driver would also loop in the agent interface
classes, in order to minimize complexity and allow for cleaning workflow
and related code to remain in one location.

Mechanism wise, if the ``ramdisk`` deployment interface is set:

* The instance can boot based upon any provided
  instance ``kernel`` and ``ramdisk`` as part of
  the requested "glance" image to be deployed.
  Effectively any image contents would be ignored.

* The instance ``boot_option`` will be ignored by the
  ramdisk interface, and will be explicitly set to ``ramdisk``.
  If otherwise set, the interface logs a warning.

* The same ``kernel`` and ``ramdisk`` parameters that are used
  for a "glance" image based deployment could be re-used to contain
  a URL.

  * In the future, ironic should consider extending the accepted URL
    format to include ``nfs://${server_ip}{$path}{$file}``, which
    would enable direct boot to NFS hosted kernel and ramdisk.
    This would not consist of ``nfsroot`` scenarios. This document
    does not require that is performed, but the Boot from Volume
    specification does explicitly state that could be a scenario
    implemented.

  * An additional consideration could also be to support direct
    specification of a path to chain-load to.

* Users must explicitly allow TFTP and/or HTTP iPXE endpoint access for
  booting the baremetal nodes. Typically deployments do not allow tenant
  networks to access to these endpoints.

* Configuration drives would be ignored by ironic, and users would be
  advised to make use of the metadata service. Deployments with a
  configuration drive will explicitly result in an warning being logged
  by the conductor.

  * Operators who directly deploy nodes using ironic may need to pass
    additional kernel command line arguments to the node being "deployed"
    via a ramdisk. In this case, a ``/instance_info/ramdisk_kernel_arguments``
    field will be accepted to allow those operators to pass information to the
    instance.

Building this functionality would allow us to also quickly adapt the
support to enable Ceph RBD based booting as well as ramdisk booting
to an NFS share serving as the root device. Both are features some
operators have expressed desire for. Ceph RBD support would need to
be in the underlying ``pxe`` boot interface, as the ramdisk interface
overlays the ``pxe`` interface. Support for Ceph RBD or NFS based
booting, from ``volume target`` information, would be a future
enhancement.

Alternatives
------------

We could consider building logic to handle and support this into the standard
deployment workflow, however given this is a sufficient and specialized use
case, that it might be completely unnecessary as it would not be used in most
cases.

Data model impact
-----------------

None.

State Machine Impact
--------------------

None. Deployment would consist of setting the boot configuration and then
powering on the network node.

REST API impact
---------------

None

Client (CLI) impact
-------------------

"ironic" CLI
~~~~~~~~~~~~

None

"openstack baremetal" CLI
~~~~~~~~~~~~~~~~~~~~~~~~~

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

None

Security impact
---------------

No additional security impact is expected aside from a deployment scenario
being able to be setup by an operator where it may be necessary to keep the
deployed kernel/ramdisk potentially for an elongated period of time.

Ironic already does this with instances that are netboot.

Other end user impact
---------------------

Operators which choose to use this feature may wish to put in place
specialized network controls to facilitate the machines network booting.

Each deployment and case will be different, and without post-implementation
information, we will be unable to determine if there is a standard that can
be derived.

Scalability impact
------------------

No scalability impact anticipated.

Performance Impact
------------------

No substantial performance impact anticipated, although if the feature
gains popularity... takeover naturally takes longer.

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
  Julia Kreger (TheJulia)

Other contributors:
  None

Work Items
----------

* Create deploy interface
* Create tempest test for said ramdisk deploy interface.
* Create user documentation.

Dependencies
============

Testing
=======

This seems like a feature that could be easily tested via a tempest scenario
if the driver is available. No additional testing should be required.

Upgrades and Backwards Compatibility
====================================

None

Documentation Impact
====================

Documentation will need to be updated to support this effort.

References
==========

None
