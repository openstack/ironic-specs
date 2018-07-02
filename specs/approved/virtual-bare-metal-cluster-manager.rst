..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==================================
Virtual Bare Metal Cluster Manager
==================================

`StoryBoard RFE <https://storyboard.openstack.org/#!/story/2003484>`__

Testing Ironic has always been challenging.  Bare metal compute resources are
expensive and inflexible.  The typical solution to this issue is to emulate
bare metal compute resources using virtual machines (VMs), allowing us to
improve the utilisation of test infrastructure, and test various scenarios
using general purpose test infrastructure.  Support for creating virtual bare
metal environments is available in DevStack, and also in Bifrost.  These are
used in OpenStack CI.  This specification covers creation of a new tool for
managing virtual bare metal clusters.

Problem description
===================

As Ironic and bare metal cloud use cases grow in popularity, it becomes
necessary to ensure that tooling is available for performing representative
tests.  The DevStack plugin and Bifrost playbooks are helpful, but not
applicable in every environment, as they pull in additional dependencies, and
are quite tied to the specifics of those environments.

In particular, testing of OpenStack deployment tools that make use of Ironic
such as Kayobe, Kolla Ansible and TripleO would benefit from a shared tool for
managing the configuration of virtual bare metal testing environments.

It would be desirable for the new tool to be extensible and support more
complex configuration in future - for example, networking configuration. Shell
script-based tools such as the DevStack plugin inherently risk becoming
monolithic with new feature additions. It is important that the new tool
supports more complex use cases without sacrificing its ease of use or
maintenance for simpler configurations.

User Stories
------------

* As an OpenStack developer, I want to be able to easily create a generic
  all-in-one virtual bare metal cluster at will, so that I can use it as a
  development environment.

* As an OpenStack developer, I want to be able to tear down my virtual cluster
  once I am finished with it, so that my system is brought back to a clean
  state.

* As an Ironic developer, I want to be able to create a virtual bare metal
  cluster to a particular specification of VMs and virtual networks, so that I
  can simulate a given system architecture for my own development.

* As an Ironic developer, I want to be able to reconfigure my virtual cluster,
  so that I can test changes in a variety of bare metal architectures.

* As a maintainer of a CI toolchain, I want there be a *de facto* virtual
  cluster management tool for CI jobs, so that I don't have to use a
  bespoke/non-extensible utility.

* As an Ironic developer, I want CI jobs to set up job environments with the
  same tool that I use to set up my development environment, so that I can
  easily reproduce the results of CI jobs on my own machine.

* As a systems deployer, I want to be able to perform bare metal scale testing
  locally/virtually, so I can diagnose scaling issues before deploying onto a
  real system.

Proposed change
===============

We propose to add a new tool for managing virtual bare metal clusters, named
*Tenks*. The scope of Tenks includes:

* Creation and deletion of VMs representing bare metal nodes

* Orchestration of tools used to emulate Baseboard Management Controllers
  (BMCs), e.g. `virtual BMC <https://github.com/openstack/virtualbmc>`__ and
  `sushy-tools <https://github.com/openstack/sushy-tools>`.

* Creation and deletion of virtual networks representing bare metal networks

Tenks will initially be targeted at the typical Libvirt/QEMU/KVM environment,
but in the typical OpenStack way, will be written in such a way as to allow
support for other virtualisation providers to be added in future.

N.B. Libvirt provides an `extremely extensive API
<https://libvirt.org/formatdomain.html>`__ for configuration of VM properties.
It is not Tenks' aim to expose anything but the smallest common subset of this.
This offers the advantages of easier cross-compatibility with multiple
virtualisation providers, and looser coupling to each of these. Tenks is
intended for development and testing purposes, rather than for fine-grained
tuning of virtual cluster configuration.

Once built, we propose to migrate the Ironic DevStack plugin and/or Bifrost
test playbooks to use Tenks.

The source code for Tenks is `available on GitHub
<https://github.com/stackhpc/tenks/>`__. A blog post about Tenks' initial
development can be found `on the StackHPC website
<https://www.stackhpc.com/tenks.html>`__. Documentation can be found on
`Read the Docs <https://tenks.readthedocs.io/>`__.

Etymological Side Note
----------------------

* Tenks

* ten-k-s

* 10-thousand-spoons

* Alanis Morissette - Ironic: lyrics L27

Name idea courtesy of mgoddard.

Proposed Implementation
------------------------

It is proposed to implement Tenks using Ansible. Ansible is a good fit for such
a tool because:

  * It provides a good platform upon which to write an idempotent application.
    Since Tenks will be configured declaratively, idempotence is important
    because it allows the system to be brought to the declared state regardless
    of its initial state (for example, if some of the declared VMs already
    exist).

  * It allows easy reference to pre-existing Ansible roles to help with
    configuration.

  * It encourages development of an opinioniated tool that can be easily
    configured as required. This means that Tenks' default Ansible
    configuration would be able to create a basic virtual bare metal cluster
    with minimal set-up required (due to Ansible role defaults), but any
    options can be overridden to customise the configuration as required,
    taking advantage of Ansible's variable precedence and scoping logic.

Dependent on the size that Tenks grows to, it will probably be necessary to
write an OpenStack-like CLI to wrap around the Ansible plays.

Multi-Stage Process
^^^^^^^^^^^^^^^^^^^

* Host setup:

    * Installing and configuring the relevant software on each host:

        * Open vSwitch (containerised?)

        * Virtualisation tookit (e.g. Libvirt/QEMU/KVM)

        * Virtual platform management toolkit: Virtual BMC for IPMI at the
          moment. Scope for extension to include other tools in future (e.g.
          VirtualPDU for SNMP, sushy-tools for Redfish).

        * LVM - set up storage pools for VM volumes

    * Networking setup:

        * Creation of bridges for each physical network, and connection to
          physical interfaces.

* VM configuration:

    * Schedule requests of different VM specifications to the most appropriate
      BM hypervisor. The scheduling algorithm could initially be naïve (or
      even random), and could be iteratively improved. Tenks could even be
      configured to prioritise certain scheduling heuristics more or less.

    * Create the specified VMs through the virtualisation provider.

    * Attach the VMs' NICs to the relevant bridges, based on the physical
      networks they were configured to be connected to.

    * Register each VM with a platform management tool suitable for its driver
      (e.g. Virtual BMC for IPMI).

* VM enrolment (these steps are optional if introspection is to be used):

    * Enrol each VM with Ironic, using a specified deployment
      ramdisk and kernel.

    * Set any additional properties on the node. This could include
      boot-from-volume details, capabilities and boot mode (for boot modes
      supported by Tenks).

    * Set any traits on the node.

    * Create a port in Ironic for each of the VMs' NICs.

    * Make Ironic nodes available for deployment.

* Post-deployment:

    * Create Nova flavors as required. These can specify node traits that are
      either desired or forbidden.

Tenks should also support a 'tear-down' mode which would clean up all created
resources and restore the system (more or less) to its initial state.

Configuration
^^^^^^^^^^^^^

A declarative configuration style would be appropriate to describe the virtual
infrastructure provisioned by Tenks. This could include:

  * Host inventory. Tenks will need a list of bare metal hypervisors, i.e.
    hosts of virtual machines simulating bare metal nodes.  Could use an
    Ansible inventory for this.

  * Physical networks. Tenks would be configured with a list of physical
    networks that are shared by all hosts in the inventory. A per-host mapping
    of physical networks to source interfaces/bridges would be required. Tenks
    would create a bridge for each physical network on each host.

  * Desired virtual bare metal VM configuration. Tenks would be configured with
    'flavours' of VM, and a count of how many VMs of each flavour to create.
    Flavours would ideally be agnostic of virtualisation provider, but should
    have the following properties:

      * Physical networks. A virtual NIC would be added to the VM for each
        physical network, and the NICs would be plugged into the respective
        bridge on the hypervisor.

      * Generic VM attributes. These would include number of CPUs and amount
        of RAM.

      * Volumes to be attached to the VM. Creation of blank volumes and
        volumes from existing images should be supported, in addition to use
        of existing volumes.

    These properties could be used to influence VM placement during
    scheduling. Initial flavour mappings for the Libvirt provider may be
    facilitated using the `StackHPC libvirt-vm Ansible role
    <https://galaxy.ansible.com/stackhpc/libvirt-vm>`__ as an interface.

Alternatives
------------

* Continue using specific tools in each environment

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

None

Ramdisk impact
--------------

None

Security impact
---------------

None

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

None

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Will Miller: willm@stackhpc.com

Other contributors:

Work Items
----------

- Develop proof-of-concept Ansible playbooks

- Flesh out Tenks to include more advanced features, for example:

    - Tear-down of clusters

    - Improved scheduling heuristics

    - Reconfiguration of clusters without need for tear-down

    - Providers other than Libvirt

    - Command-line interface

    - Tests (unit, functional, integration) as necessary

- Manual testing of Tenks with various environments/configurations

- Submit Tenks to PyPI (if the extent of Python code requires this)

- Adapt CI pipelines to use Tenks for ephemeral cluster management

Dependencies
============

None

Testing
=======

TODO


Upgrades and Backwards Compatibility
====================================

None

Documentation Impact
====================

TODO


References
==========

* `DevStack bare metal network simulation split (abandoned)
  <https://review.openstack.org/#/c/509844>`__
* `Sam Betts libvirt bare metal simulation
  <https://github.com/Tehsmash/libvirt-baremetal-simulation>`__
* `QuintupleO: OpenStack virtual bare metal
  <https://github.com/cybertron/openstack-virtual-baremetal>`__
