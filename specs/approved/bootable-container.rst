..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=========================================
Deployment of Bootable Containers (bootc)
=========================================

https://bugs.launchpad.net/ironic/+bug/2085801

While bootable containers are a relatively new concept, the overall concept
of a container is scoped to a filesystem from a higher level concept, a
container image. A container image itself is just a composite layering of
files in "tgz" files, ultimately creating an image.

While a "container" can take several different forms including one of a
generic image transport mechanism, the primary driver in this specification is
to enable efficient deployment sourced from a container registry in the form
of use where we utilize ``bootc`` to facilitate the deployment of a bootable
container.

Problem description
===================

Today, Ironic's "image" deployment options are limited, largely to just
disk images which represent a filesystem, or an entire block device layout with
multiple partitions. Respectively in community terms, these are referred to as
partition and whole-disk images.

These approaches are often called "tried and true" methods, as they represent
a relatively accurate composite, which requires standardized processes to
reconcile the contents. But these approaches have downsides as they require
complex and thus brittle process (bootloader setup), bootloader pointer
injection, and/or encoding whitespace and filesystem structural aspects
(like block device sizes) into images, which adds additional complexity.

This complexity can force multiple different types of images needing to be
maintained, but ultimately there are many different tradeoffs our users should
be empowered to make.

While the existing image format handling of Qcow2 format does handle whitespace
to an extent, it is not a solution to address all such issues. For example, our
bootloader installation modeling is built upon Grub/Grub2, which does not align
with the future of UniKernel Image (UKI) workloads which don't use bootloaders.
Similarly, whole disk images cannot be safely translated from a 512 byte block
size structure to a 4kB block structure on the fly and require the image
to be re-mastered as the structure and partitioning is distinctly different
with aspects like logical volumes.

This leaves the concept of going back to the files. Taking files, putting them
on disk, and letting the image do the needful through standard structure and
paths, for example the reality that for Linux workloads on x86_64 hosts,
the default artifact to boot is /boot/efi/EFI/BOOT/BOOTX64.EFI. A more modern
solution which shifts some of these burdens and challenges to an external tool
is to support the use of bootable containers through the bootc_ project.

Proposed change
===============

To facilitate the deployment of bootable containers, we need to consider the
overall model of usage. In most cases, one is not going to have a file on disk
which will represent an entire container, but instead the users are likely to
have a container registry which they are utilizing as a remote image store to
house their images.

Which means, if one looks at how bootable containers are used, it only makes
sense to speak in terms of a remote container registry, so we will just provide
a mechanism to download the container supplied via the
``instance_info\image_source`` parameter, and then execute
bootc-install-to-disk_ with a target disk uitlization size sufficient to allow
a configuration drive to be injected.

To facilitate this, we will craft a new ``deploy_interface`` called
``bootc`` which will based upon the ``CustomAgentDeploy``, with the
intent of booting the agent, and then utilizing the ``bootc`` tools through
additional support to be added to the agent, which would just trigger
installation process.

The installation process will take a model where the container is directly
downloaded from the container registry, bypassing involvement of
the ``image_download_source`` modeling which exists for the ``agent`` deploy
interface's logic.

With the container in memory on the host with the agent, the container can
then be launched, and the bootc-install-to-disk_ command is then invoked
allowing the image we are trying to deploy *also* being in charge of its
own installation. This is a requirement of the model while also shifting
the overall maintainer of the deployment logic from being Ironic in this
deployment interface's use case to the image itself. As such, this requires
bootc_ to be present in the requested container image.
To best secure this and to provide a means for operators to disable this
capability, this option is being exposed as its own streamlined deploy
interface, as opposed to adding further complexity to existing deployment
logic and workflow.

.. NOTE::
   An overall positive to this model of the container knows how to install
   itself, is ultimately that much of the logic is offloaded from Ironic,
   thus enabling more exotic images to also be deployed where the container
   just knows "what to do". Furthermore, support for deploying directly from
   a container allows operators to remove overall workflow steps or force
   awkward manual processes into the overall deployment sequence where one
   today must "prepare a disk image".

.. WARNING::
   An overall downside to this model is it *can* easily be slower than a
   pre-mastered disk image. In this model, we're shifting quite a bit of
   work to the "node being deployed", as part of the overall trade-off
   of capabilities.

Overall, this model is intended to focus on the use of UEFI, and still
support Ironic's model of use of configuration drives, while also enabling
some specific at-deploy options like root user authorized_keys injection
and LUKS encryption.

Alternatives
------------

We could "abstract" or hide much of the logic to facilitate this internally
in the agent which was originally proposed for this specification, however
upon reflection and review in line with another specification, change 933612_,
it seemed more logical to have a delineated interface and structural model as
if we attempted to support every modeling use case with a less specific model,
we would also open the door to having to ultimately support more complex
interactions and thus increase the risk of bugs resulting from this work.

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

"openstack baremetal" CLI
~~~~~~~~~~~~~~~~~~~~~~~~~

None

"openstacksdk"
~~~~~~~~~~~~~~

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

This change is largely anticipated to take place in the
``ironic-python-agent`` source code in the existing agent source code and
process.

Security impact
---------------

No additional known security impact at this time.

Other end user impact
---------------------

None

Scalability impact
------------------

None

Performance Impact
------------------

None

Other deployer impact
---------------------

This model does require loading the container into memory,
which might be problematic for larger container images.

Developer impact
----------------

This change may not be able to be tested with container images in upstream CI.
A middle ground will likely need to be identified by the community to
facilitate this testing in a realistic fashion.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Julia "TheJulia" Kreger

Work Items
----------

* Add an optional dependency of ``podman`` to the ironic-python-agent ramdisk
  to facilitate the download of the container and execution of the bootc
  utilities.

.. NOTE::
   The use of podman is largely considered as a hidden implementation detail,
   and may already be present in ramdisk images due to image URL work upon
   which this specification is dependent.

* Create a new interface method to download, execute, and install a container
  to disk.
* Add example deployment documentation.

Dependencies
============

* Podman
* OCI Container URL support as proposed in change 933612_,
  although no conductor side URL handling is likely since mirroring
  all architectures into a separate container registry would also
  be an inefficient operation because of additional image formats can result
  in quite a bit more data needing to be transferred. At a later point in time,
  the idea of such may become a distinct feature.

Testing
=======

We anticipate that this will require a separate CI job to utilize, or
might be able to be effectively driven via tempest in a combined CI job.
This might not have clarity until we have entered the implementation phase.

Upgrades and Backwards Compatibility
====================================

Not Applicable

Documentation Impact
====================

No negative impact is anticipated.

References
==========

* https://etherpad.opendev.org/p/ironic-ptg-october-2024

.. _bootc: https://github.com/containers/bootc
.. _using-bootc: https://docs.fedoraproject.org/en-US/bootc/bare-metal/#_using_bootc_install
.. _bootc-install-to-disk: https://containers.github.io/bootc/man/bootc-install-to-disk.html
.. _933612: https://review.opendev.org/c/openstack/ironic-specs/+/933612
