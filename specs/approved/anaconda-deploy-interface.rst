..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=========================
Anaconda deploy interface
=========================

https://storyboard.openstack.org/#!/story/2007839



Problem description
===================

We would like Ironic to provide the following features (described in more
detail later in this spec):

- Create LVM logical volumes, volume groups, and physical volumes
- Create MD raid arrays
- Create Linux filesystems
- Generate Linux fstab files based on created Linux filesystems

Support for creating LVM and MD structures has significant usefulness in when
provisioning Nodes with multiple physical storage devices.

Use-cases include:

- A user wants to use a LVM or MD feature
- A user wants to create a Linux filesystem on any block device created during
  provisioning
- A user wants an fstab with entries for all filesystems created by the Ironic
  deploy interface

While Ironic supports creation of custom MD raid arrays using deploy templates,
it could lead to an explosion of flavors [1]_.

Proposed change
===============

This spec suggests implementing these block device provisioning features by
creating a new "anaconda deploy interface" using `Anaconda`_. The "anaconda
deploy interface" allows a user to select one of a set of pre-defined Kickstart
configurations [2]_.

The primary advantage of this approach is in allowing customization of the
deployed operating system with all features offered by `Kickstart commands`_.

.. _`Anaconda`: https://fedoraproject.org/wiki/Anaconda
.. _`Kickstart commands`: https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/8/html/performing_an_advanced_rhel_installation/kickstart-commands-and-options-reference_installing-rhel-as-an-experienced-user

This spec is interested in the following Anaconda features. In most cases, each
feature described has a 1:1 relationship with a Kickstart command:

.. list-table::
   :header-rows: 1
   :stub-columns: 1

   * - Feature
     - Ironic
     - Anaconda
   * - Zeroize GPT/MBR structures
     - yes
     - yes
   * - Create a partition in GPT/MBR
     - yes
     - yes
   * - Install a bootloader (GRUB)
     - yes
     - yes
   * - Create a LVM logical volume
     - no
     - yes
   * - Create a LVM volume group
     - no
     - yes
   * - Create a LVM physical volume
     - no
     - yes
   * - Create a MD raid array
     - limited
     - yes
   * - Create filesystems specified by the user
     - no
     - yes
   * - fstab entry generator
     - no
     - yes

As shown, there are several block device-related features supported by this
spec.

In addition, there are some desired pseudo-features, for example "LVM physical
volume on MD raid array" that are accomplished by the user providing sequences
of (imperative) Kickstart commands that effectively implement this.

Deploying a node with ``Anaconda`` deploy driver involves solving following
problems:

1. Identifying the correct Anaconda version to use with the OS image.
2. Getting user-provided kickstart file to the Anaconda runtime.
3. The Operator/User generating an OS image with necessary tools in a format
   supported by Anaconda.
4. Passing correct kernel cmdline arguments to Anaconda by generating them
   in PXE boot driver.
5. Sending status back to Ironic API when the deployment starts/ends or
   crashes.
6. Handling cleaning when 'Anaconda deploy driver' is used.

Scope
-----

The scope of the Anaconda deploy interface is limited to

* CentOS/RHEL >= 7 and Fedora >=31
* Anaconda will be used to deploy the OS image.
* Support both UEFI and Legacy BIOS mode.


Matching the OS image with correct anaconda version
---------------------------------------------------

Anaconda is a two stage installer where the ramdisk is considered stage1.
Once stage1 is loaded, it tries to download stage2 of the installer over the
network. Stage2 is a squashfs [3]_ image and the location of stage2 can be
specified using ``inst.stage2`` kernel command line argument.

    ``inst.stage2=http://<address>:<port>/httproot/<node-uuid>/squashfs.img``

To deploy the OS using anaconda, apart from the OS image,kernel,ramdisk(stage1)
and anaconda squashfs(stage2) images are required. All these artifacts should
be uploaded to glance and associated with the OS image by the operator.

.. code:: bash

    openstack image create --disk-format raw --container-format compressed \
        --file path/to/os_image.tar.bz2 \
        --property kernel_id=$MY_VMLINUZ_UUID \
        --property ramdisk_id=$MY_INITRD_UUID \
        --property stage2_id=$MY_ANACONDA_SQUASHFS_UUID \
        --property os_distro=RHEL \
        --property os_version=7 centos-7-base \
        --property ks_template=glance://uuid``

This is a departure from how direct deploy interface works where the kernel_id
and ramdisk_id are either in configuration file or set in driver_info. IPA is
distro agnostic, Anaconda is not. There is no single Anaconda installer version
that is compatible with all major versions of CentOS. Each major version of
CentOS has its own version of anaconda installer. For this reason we require
the operator to associate correct PXE kernel, PXE ramdisk and Anaconda squashfs
with the OS image as properties in Glance. The Anaconda deploy interface shall
validate the image properties and make sure that all required properties are
set before the deployment.

Kickstart templates
-------------------

Anaconda installer needs a kickstart file to deploy an operating system
non-interactively. The kickstart file is used to automate the deployment of the
operating system. The default kickstart template when not modified by the
operator should automatically partition the available disks using the autopart
mechanism [4]_ and deploy the OS. The default kickstart file template will be
named default_kickstart.template and referenced by the configuration option
``default_ks_template`` in ironic.conf under ``[kickstart]`` section.

Example default kickstart template:

.. code::

    lang en_US
    keyboard us
    timezone America/Los_Angeles --isUtc
    #platform x86, AMD64, or Intel EM64T
    text
    install
    cmdline
    reboot
    selinux --enforcing
    firewall --enabled
    firstboot --disabled
    auth --passalgo=sha512 --useshadow


    bootloader --location=mbr --append="rhgb quiet crashkernel=auto"
    zerombr
    clearpart --all --initlabel
    autopart

All kickstart templates will be automatically appended with following mandatory
sections during deployment

.. code::

    # Downloading and installing OS image using liveimg section is mandatory
    liveimg --url={{ liveimg_url }}

    # Following %pre, %onerror and %trackback sections are mandatory
    %pre
    /usr/bin/curl -X PUT -H 'Content-Type: application/json' -H 'Accept: application/json' -d '{.."agent_status": "start"}' http(s)://host:port/v1/heartbeat/{{node_ident}
    %end

    %onerror
    /usr/bin/curl -X PUT -H 'Content-Type: application/json' -H 'Accept: application/json' -d '{"agent_status": "Error: Deploying using anaconda. Check console for more information."}' http(s)://host:port/v1/heartbeat/{{node_ident}
    %end

    %traceback
    /usr/bin/curl -X PUT -H 'Content-Type: application/json' -H 'Accept: application/json' -d '{.."agent_status": "Error: Anaconda crashed unexpectedly."}' http(s)://host:port/v1/heartbeat/{{node_ident}
    %end

    # Sending callback after the installation is mandatory
    %post
    /usr/bin/curl -X PUT -H 'Content-Type: application/json' -H 'Accept: application/json' -d '{.."agent_status": "success"}' http(s)://host:port/v1/heartbeat/{{node_ident}
    %end

Multiple %pre, %post, %traceback and %error  sections can exist in a kickstart
file. These sections will be processed and executed in the order they are
encountered [5]_.

Custom kickstart templates should be uploaded to glance or hosted in a
webserver accessible by the conductor or on the conductor's filesystem.

The operator can set the kickstart file using URI formats ``glance://<uuid>``
or ``http(s)://host:port/path/ks.cfg`` or ``file://path/to/ks.cfg``

If the API user decides to store the kickstart file in glance they can do so
by running the following command

.. code:: bash

    openstack image create --file ks.cfg --container-format bare \
        --disk-format raw custom_kickstart_template


Users can specify a specific kickstart template for a node via the node's
instance_info field, with key 'ks_template'. For example:

.. code:: bash

    openstack baremetal node set $NODE_UUID \
        --instance_info ks_template=glance://uuid

    or

    openstack baremetal node set $NODE_UUID \
        --instance_info ks_template=http(s)://port:host/path/ks.cfg

    or

    openstack baremetal node set $NODE_UUID \
        --instance_info ks_template=file://path/to/ks.cfg

The user can also associate a kickstart template with an OS image(image_source)
in glance. The template specified in the instance_info will take precedence
followed by ``ks_template`` property on the OS image. Finally if
``ks_template`` property is not present in both instance_info and OS image then
the default kickstart template specified in the configuration file will be
used.

The custom kickstart template will be downloaded and stored in
httproot/<node-uuid>/ks.cfg. Where as ``httproot`` is defined in ``http_root``
configuration item under ``[deploy]`` section of ``ironic.conf`` configuration
file. Once the custom kickstart template is downloaded it will be validated
against ``os_distro`` and ``os_version``

    ``ksvalidator -v RHEL7 ks.cfg``

os_distro and os_version are properties of image_source(The OS image). The API
user is required to set os_distro and os_version. If there is no os_distro or
os_version set on the image_source, the kickstart file will be validated
against ``DEVEL`` version of kickstart syntax. See ``ksvalidator -l`` for list
of supported kickstart versions [6]_.

The OS_DISTRO should be one of 'RHEL' and OS_VERSION should be either '7' or
'8'.

The kickstart file is passed to anaconda installer using the kernel cmdline
argument ``inst.ks``

    ``inst.ks=http(s)://<address>:<port>/httproot/<node-uuid>/ks.cfg``


Kernel command line arguments
-----------------------------

Two important kernel command line arguments are required for the anaconda
installer to work.

    1. ``inst.stage2``
    2. ``inst.ks``

Both of these kernel command line arguments will be appended to ``pxe_options``
dictionary. A function similar to get_volume_pxe_options() will be added to
pxe_utils to facilitate this.

OS image format
---------------

While Anaconda supports installing individual RPM packages from a remote
server, the deployment driver will only support installation of disk image
formats described by liveimg [7]_. liveimg accepts tarballs, squashfs images
and any mountable disk images. Users can generate squashfs images and tarballs.


Deployment status
-----------------

Anaconda installer doesn't know how to talk to Ironic APIs. However we can have
%pre and %post sections of kickstart file make API calls to Ironic. The ramdisk
will use heartbeat API to talk to the Ironic API. The %pre %onerror,
%traceback, and %post sections will be populated with ``curl`` calls to
heartbeat API when conductor renders the kickstart template.

The %pre and %post sections of kickstart files are executed in order they are
encountered by anaconda.

At the start of the installation following status will be sent using %pre
section of the kickstart file from anaconda ramdisk to lookup

POST {'callback_url':  '', 'agent_token': <token>,  'agent_version': '', \
      'agent_status': 'start'} \
        http(s)://<address>:<port>/v1/heartbeat/{{node_ident}}

On receiving the 'start' status from anaconda ramdisk, the conductor will
set driver_internal_info['agent_status'] = 'start'

At the end of the OS installation %post section will be used to send following
message back to Ironic

POST {'callback_url': '', 'agent_token': <token>, 'agent_version': '',
      'agent_status': 'success'} \
        http(s)://<address>:<port>/v1/heartbeat/{{node_ident}}

On receiving the 'success' the conductor will move the Ironic node to
'active' state depending on the current state and set
driver_internal_info['agent_status'] = 'success'

If there are errors during installation we will capture those error using
%onerror [8]_ and %traceback [9]_ sections of kickstart file, then send the
'error' status to Ironic

POST {'callback_url': '', 'agent_token': <token>, 'agent_version': '', \
      'agent_status': 'Error: <msg>'} \
        http(s)://<address>:<port>/v1/heartbeat/{{node_ident}}

On receiving the 'Error' status the conductor will set the provision_state of
Ironic node to 'deploy_failed' depending on the current status of the node
and set the last_error field of the Ironic node.

There will be no calls to /v1/lookup API from ramdisk. The agent token will
be generated when the kickstart file is rendered. Agent token will be embedded
in the kickstart file for the heartbeat ``curl`` call to use. The driver avoids
calls to lookup API because it is difficult to read and extract agent token
using scripts in the ramdisk.


Cleaning
--------
The ``PXEAnacondaDeploy`` driver will inherit from ``AgentBaseMixin`` interface
and ``DeployInterface`` similar to ``PXERamdiskDeploy`` driver. This implies
that the cleaning will be done by the agent Driver not by the Anaconda deploy
driver.

During deployment the ``PXEAnacondaDeploy`` driver  will use the properties
associated with the ``image_source`` to figure out the deploy_kernel and
deploy_ramdisk. However during cleaning it will use the
driver_info['deploy_kernel'] and driver_info['deploy_ramdisk'] fields to
determine the cleaning kernel and ramdisk. This mean the driver_info deploy_*
fields should refer to IPA kernel/ramdisk. This change is likely to be a point
of confusion.


Alternatives
------------

The Anaconda deployment driver is specific to Red Hat based distributions. This
deployment driver won't support distributions not supported by Anaconda. For
example ubuntu is not supported by this deploy driver. A similar driver can be
implemented to support ubuntu using preseed [10]_ files.

Another alternative is to define a generic partition configuration format and
use that configuration instead of kickstart file. This new generic partition
configuration will be validated by the conductor and sent to
Ironic python agent during deployment. IPA will read the generic partition
configuration and use libraries like blivet [11]_ to partition/format the
disks. With this approach the deploy driver isn't tied to a specific
distribution or vendor. We explored this approach but we found it to be too
complex and reinventing lot of things the distribution installers already do.

The kickstart file is either uploaded to glance or hosted in a webserver in
current proposal. Alternatively we can add a new field named ``kickstart`` to
``nodes`` table which accepts raw kickstart file

.. code:: bash

    openstack baremetal rebuild --kickstart path/to/ks.cfg <node-uuid>

Data model impact
-----------------

None

State Machine Impact
--------------------

None

REST API impact
---------------

Add an optional field ``agent_status`` to v1/heartbeat API, which can be used
to receive deployment status from the anaconda deploy driver.

    POST {.. 'agent_status': <status>} /v1/heartbeat/{{node_ident}}

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

RPC API needs to be updated to handle the new ``agent_status`` in heartbeat
API.

Driver API impact
-----------------

None

Nova driver impact
------------------

There is no impact to nova's Ironic driver at this time.

Ramdisk impact
--------------

There is no impact to Ironic-python-agent.


Security impact
---------------

The ``heartbeat`` method implemented by the driver has to be
unauthenticated so that anaconda can POST to the status API without a token.
An attacker could potentially cause targeted denial of service attack by
sending invalid/incorrect status to Ironic nodes since the API is
unauthenticated. This issue is mitigated by mandatory agent token verification.

Other end user impact
---------------------

An OS image that can be deployed via liveimg kickstart command should be
uploaded to glance along with relevant anaconda installer's PXE kernel,
ramdisk and squashfs image. The PXE kernel,ramdisk and squashfs need to be
associated with the OS image.

.. code:: bash

    openstack image set IMG-ID --property kernel_id=$MY_VMLINUZ_UUID \
        --property ramdisk_id=$MY_INITRD_UUID --property \
        squashfs_id=$MY_ANACONDA_SQUASHFS_UUID

The end user can make use of their custom kickstart templates during deployment
by working with the Operator. The Operator can set the instance_info
``ks_template`` key with the path of user provided kickstart template. The
kickstart template can be in glance ``glance://uuid``, webserver
``http(s)://host:port/path/ks.cfg`` or on the filesystem
``file://etc/ironic/ks.cfg`` of the conductor.

.. code:: bash

    openstack baremetal node set $NODE_UUID --instance_info ks_template=<TMPL>

Scalability impact
------------------

None

Performance Impact
------------------

None

Other deployer impact
---------------------

The operator has to set default kickstart template under ``[kickstart]``
section of Ironic configuration file.

.. code::

      [kickstart]
      default_ks_template=$Ironic_CONF_DIR/kickstart/default_ks.template

The ``kickstart`` deploy interface must be set on the node
.. code:: bash

    openstack baremetal node set <NODE> --deploy-interface kickstart

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  zer0c00l, sagarun@gmail.com

Work Items
----------

1. Definition of default kickstart template and configuration items related
   to kickstart deploy template.

2. Implementation of core deploy driver that fetches artifacts from glance,
   generates PXE configuration files, renders kickstart templates into httproot

3. A CI job to test the anaconda deploy driver

4. Documentation for operators and users

Dependencies
============

None

Testing
=======

* This driver should be testable in gate. Enhancements might be needed to gate
  to get this working.

* Devstack support will be added for this driver so that it can be tested
  easily.


Upgrades and Backwards Compatibility
====================================

None

Documentation Impact
====================

Clear operator and user documentation need to be added on kickstart deploy
interface and how to make use of it.

References
==========

.. [1] https://specs.openstack.org/openstack/ironic-specs/specs/approved/deploy-templates.html#current-limitations
.. [2] https://pykickstart.readthedocs.io/en/latest/kickstart-docs.html
.. [3] https://en.wikipedia.org/wiki/SquashFS
.. [4] https://pykickstart.readthedocs.io/en/latest/kickstart-docs.html#autopart
.. [5] https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/7/html/installation_guide/sect-kickstart-syntax#sect-kickstart-preinstall
.. [6] https://pypi.org/project/pykickstart/
.. [7] https://pykickstart.readthedocs.io/en/latest/kickstart-docs.html#liveimg
.. [8] https://pykickstart.readthedocs.io/en/latest/kickstart-docs.html#chapter-7-handling-errors
.. [9] https://pykickstart.readthedocs.io/en/latest/kickstart-docs.html#chapter-8-handling-tracebacks
.. [10] https://wiki.debian.org/DebianInstaller/Preseed
.. [11] https://pypi.org/project/blivet/
.. https://etherpad.opendev.org/p/ironic-disk-partitioning-2020
