..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Promote Ansible deploy interface to ironic
==========================================

https://blueprints.launchpad.net/ironic/+spec/ansible-deploy-driver

This spec presents a new deploy driver interface for provisioning nodes
via Ansible playbooks.

Problem description
===================

Sometime it may be required to treat (some) baremetal nodes more like pets
than cattle, providing per-node custom logic of deploy process.

Currently such customization in Ironic is not an easy task,
as developer/cloud administrator would have to do one or more of the following:

* Modify the code of Ironic deploy driver.
* Modify the code of Ironic Python Agent.
* Modify the code of ironic-lib.
* Rebuild IPA ramdisk.
* Upload new ramdisk to Glance or HTTP server(s).
* Update the nodes' info with new ramdisk.
* Update deploy driver on Ironic conductors.
* Restart conductors.

This problem can be partially solved in deploy driver based on external
templates for a configuration management tool.

Possible use cases and advantages:

* Custom actions with hardware at any stage of deploy process with vendor's
  utilities, in-band or out-of-band.
* Easy replace usage of one Linux utility with other for deploy.
* Deep tuning of deploy process.
* Changing behavior of deploy process without restart the conductors.
* Long life time of deploy ramdisk - vendor's utilities can be downloaded from
  external sources during deploy process.
* Separation of concerns - ironic manages the 'what' part,
  Ansible the 'how' part
* Allows BMs to be treated more like pets

Proposed change
===============

This spec proposes such deploy interface based on Ansible [#]_ as configuration
management solution.
Effectively it uses ironic for its power, management and boot capabilities,
and shifts the logic of deployment itself to Ansible playbooks.

Such deploy interface is already implemented
and is available as part of ``ironic-staging-drivers`` project [#]_.
It can be used as possible deploy interface for ``ipmi`` hardware
(and possibly other hardware as well).
Therefore this spec is proposing promotion of the ``ansible`` deploy interface
for inclusion in the core ironic as one of available deploy interfaces.

Below is a short description of this deploy interface architecture
and current capabilities.
More information is available in the ``ironic-staging-drivers`` project
documentation at [#]_.

Use case
--------

This deploy interface is mostly suitable for 'undercloud'-like or
standalone ironic usage, where the operator of ironic service is usually the
'owner' of the images to be deployed and/or the deployed instances themselves.
It does however already include set of Ansible playbooks that try to mimic the
capabilities of the standard ``direct`` deploy interface of ironic
as close as possible.

This deploy interface is really useful when, during provisioning,
there is a need to perform some low-level system configuration
that would be hard to do in the already provisioned instance
(like placing the root partition on a LVM/software RAID)
or would require an extra reboot (like changing kernel parameters).

General overview
----------------

We chose Ansible for the following reason:

- open source (GPLv3 + parts as MIT), mature and popular enough,
  including OpenStack ecosystem itself
- written and extendable in Python, fits nicely in the OpenStack ecosystem
- configuration files are human-readable YAML
- agent-less by design, with minimal requirements on managed node,
  only Python and SSH server are required.

There are two ways to utilize Ansible from Python's program:
use Ansible Python API or run CLI utility with parameters.
Ansible Python API currently does mandatory fork of caller's process,
this behaviour is not suitable for Ironic conductor
(oslo.messaging does not allow forks at least).
Besides, Ansible licensing choice (GPLv3) prohibits usage of Ansible Python API
from ironic (Apache 2.0).
Therefore ``ansible-playbook`` CLI utility is used.

Each action (deploy, clean) is described by a single Ansible playbook
with roles, which is run as a whole during deployment,
or tag-wise during cleaning.
Control of cleaning steps is through Ansible tags
and auxiliary clean steps file.
The playbooks for actions can be set per-node, as is cleaning steps file.

The dreploy interface tries to reuse as much code from ironic as possible,
and interface-wise is quite similar to the ``direct`` deploy interface.

Currently this interface supports two modes for continuing deployment
or cleaning:

- having the deploy ramdisk calling back to ironic API’s heartbeat endpoint
  (default)
- polling the node until the ssh port is open as part of a playbook

We propose to remove the latter from the interface when moving it to ironic, as
support for it is not tested in gates, it decreases performance due to polling,
and in general makes code more complicated.

A custom Ansible callback plugin is used for logging. It can read the logging
configuration from ironic configuration file, and thus emit log entries for
Ansible events directly to the logging backend ironic is also using
(works best with journald backend).

Deploy
------

The interface prepares a set of parameters which are needed for deploy,
including access info for the node to be deployed.
It then executes the ``ansible-playbook`` script passing it all the collected
information, with node access info being used to register the node in Ansible
inventory at runtime.

Supported image types are whole-disk images and partition images with
"local" boot option, **"netboot" is currently not supported**.
Compressed images are downloaded to deploy ramdisk and converted to actual
disk device/partition, RAW images are streamed to the target directly.

Creating a configdrive partition is supported for both whole disk and
partition images, on both msdos and GPT labeled disks.

Root device hints are currently supported in their basic form only
(with exact matches, without oslo.utils operators), there are patches
to add full support on review.
If no root device hint is provided for the node, first device returned
as part of ``ansible_devices`` Ansible fact is used as root device
to create partitions on or write the whole disk image to.

Cleaning
--------
Cleaning procedure for Ansible deploy interface:

* Each cleaning step is a tag in the Ansible playbook file used for cleaning.
  Available steps, their priorities and corresponding tags are defined in a
  auxiliary cleaning steps configuration file.
* ``get_clean_steps()`` method returns a list of cleaning steps defined in
  mentioned configuration file.
* ``prepare_cleaning()`` method loads the same ramdisk as for deploying.
* ``execute_clean_step()`` method does synchronous execution of cleaning step
  via Ansible, executing only tasks with Ansible tags assigned
  to the cleaning step.

Default cleaning playbook provided with the interface supports
``erase_devices_metadata`` and ``erase_devices`` clean steps of ``direct``
deploy interface by executing shallow disk metadata cleanup
and shredding of disk devices respectively, honoring
priorities of those steps set in ironic's configuration file.

Alternatives
------------

Use a different deployment customization mechanism
or don't support the pet-like treatment.

The short rundown of main pros and cons of current ``ansible`` deploy interface
compared to already available and standard ``direct`` deploy interface:

- easier to extend for custom provision logic
- is not async
- does not support netboot

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

To support this new deploy interface the deploy ramdisk should include:

- a user with password-less sudo permissions - required
- running SSH server configured for access to this user via SSH keys - required
- Python interpreter (Python2 >= 2.6 or Python3 >=3.5)

  * currently tested with Python2 2.7 only
  * actual Python version required depends on Ansible version used
    and the version of Python interpreter that executes Ansible on
    ironic-conductor host
  * current Ansible support of Python3 on managed node is still
    considered experimental (and is not supported by Ansible 2.1.x at all)

- a software component that upon boot of the ramdisk will make
  a ``lookup`` API request to ironic API and make ``heartbeat`` requests
  afterwards

  * default choice for such component is IPA

- other system utilities used by deploy or clean playbooks

All or part of those (except the SSH server) can in principle be installed
at runtime through additional Ansible tasks in playbooks
(reducing the memory footprint and download/boot time of the deploy ramdisk),
but also can be provided with deploy ramdisk to shorten the provisioning time.

Re-using IPA as ``lookup`` and ``heartbeat`` ironic API client
makes it possible to have a unified deploy ramdisk for
``direct``, ``iscsi`` and ``ansible`` deploy interfaces.

The ``ironic-staging-drivers`` project includes a set of scripts to perform
a simple rebuild of TinyCore Linux based deploy ramdisk (TinyIPA),
as well as ``diskimage-builder`` element to build a suitable ramdisk with this
utility, basing it on ``ironic-agent`` element and thus also containing IPA.
Those will be promoted to the new ``openstack/ironic-python-agent-builder``
project [#]_.

Rebuild of CoreOS-based deploy ramdisk is currently not supported but such
support can be added in the future.


Security impact
---------------

Ansible communicates with remote machines over SSH. Deploy process is secure
if private SSH key is properly secured
(can be accessed only by the user running ironic-conductor service).

Other end user impact
---------------------

None

Scalability impact
------------------

The driver is not async and is blocking.
One conductor's worker thread per node being provisioned or cleaned
is required.
Most of the time the thread waits in blocking state for the completion
of ``ansible-playbook`` process.
Possible thread pool exhaustion must be accounted for when planning deployment
that allows usage of this deploy interface and configuring thread pool size
in ironic configuration file (``[conductor]workers_pool_size`` option).

There are ideas on how to make the driver async / not blocking,
those will be proposed in further specs/RFEs.


Performance Impact
------------------

We have conducted some tests to measure performance impact of running
multiple ``ansible-playbook`` processes on ironic-conductor host [#]_.

The results show that while there is indeed a performance overhead introduced
by using the ``ansible`` deploy interface, it is well within possibilities
of quite standard hardware - we were able to provision 50 and 100 nodes
concurrently via single ironic-conductor service using this deploy interface,
with total provisioning time similar to ``direct`` deploy interface.
Please see the blog post referenced above for mode details on test setup
and results.

Other deployer impact
---------------------

Config options
~~~~~~~~~~~~~~

these are defined in the ``[ansible]`` section of ironic configuration file

verbosity
    None, 0-4. Corresponds to number of 'v's passed to ``ansible-playbook``.
    Default (None) will pass 'vvvv' when global debug is enabled in ironic,
    and nothing otherwise.

ansible_playbook_script
    Full path to the ``ansible-playbook`` script. Useful mostly for
    testing environments when you e.g. run Ansible from source instead
    of installing it.
    Default (None) will search in ``$PATH`` of the user running
    ironic-conductor service.

playbooks_path
    Path to folder that contains all the Ansible-related files
    (Ansible inventory, deployment/cleaning playbooks, roles etc).
    Default is to use the playbooks provided with the package
    from where it is installed.

config_file_path
    Path to Ansible's config file. When set to None will use global system
    default (usually ``/etc/ansible/ansible.cfg``).
    Default is ``playbooks_path``/ansible.cfg

ansible_extra_args
    Extra arguments to pass to ``ansible-playbook`` on each invocation.
    Default is None.

default_username
    Name of the user to use for Ansible when connecting to the ramdisk
    over SSH. Default is 'ansible'.
    It may be overridden by per-node ``ansible_username`` option
    in node's ``driver_info`` field.

default_key_file
    Absolute path to the private SSH key file to use by Ansible by default
    when connecting to the ramdisk over SSH. If none is provided (default),
    Ansible will use the default SSH keys configured for the user running
    ironic-conductor service.
    Also note that private keys with password must be pre-loaded
    into ``ssh-agent``.
    It may be overridden by per-node ``ansible_key_file`` option
    in node's ``driver_info`` field.

default_deploy_playbook
    Path (relative to $playbooks_path or absolute) to the default
    playbook used for deployment. Default is 'deploy.yaml'.
    It may be overridden by per-node ``ansible_deploy_playbook`` option
    in node's ``driver_info`` field.

default_shutdown_playbook
    Path (relative to $playbooks_path or absolute) to the default
    playbook used for graceful in-band node shutdown.
    Default is 'shutdown.yaml'.
    It may be overridden by per-node ``ansible_shutdown_playbook`` option
    in node's ``driver_info`` field.

default_clean_playbook
    Path (relative to $playbooks_path or absolute) to the default
    playbook used for node cleaning.
    Default is 'clean.yaml'.
    It may be overridden by per-node ``ansible_clean_playbook`` option
    in node's ``driver_info`` field.

default_clean_steps_config
    Path (relative to $playbooks_path or absolute) to the default
    auxiliary cleaning steps file used during the node cleaning.
    Default is 'clean_steps.yaml'.
    It may be overridden by per-node ``ansible_clean_steps_config`` option
    in node's ``driver_info`` field.

extra_memory
    Memory (in MiB) consumed by the Ansible-related processes
    in the deploy ramdisk.
    Affects decision if the downloaded user image will fit into RAM
    of the node.
    Default is 10.

post_deploy_get_power_state_retries
    Number of times to retry getting power state to check if
    bare metal node has been powered off after a soft poweroff.
    Default is 6.

post_deploy_get_power_state_retry_interval
    Amount of time (in seconds) to wait between polling power state
    after triggering soft poweroff.
    Default is 5.

The last 3 options are effectively copies of similar options in ``[agent]``
section of configuration file.
We could use single option for (some of) those for all deploy interfaces
that make use of them,
especially if we rename/move them from ``[agent]`` section to a section with
more general name (like ``[deploy]``).


Per-node fields in driver_info
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

These parameters can be provided with driver_info, all are optional
and their default values can be set in the ironic configuration file:

ansible_username
    User name to use for Ansible to access the node (default is ``ansible``).

ansible_deploy_username
    Deprecated in favor of ``ansible_username``.

ansible_key_file
    Private SSH key used to access the node. If none is provided (default),
    Ansible will use the default SSH keys configured for the user running
    ironic-conductor service.
    Also note that private keys with password must be pre-loaded
    into ``ssh-agent``.

ansible_deploy_keyfile
    Deprecated in favor of ``ansible_key_file``.

ansible_deploy_playbook
    Name of the playbook file inside the ``playbooks_path`` folder
    to use when deploying this node.

ansible_shutdown_playbook
    Name of the playbook file inside the ``playbooks_path`` folder
    to use to gracefully shutdown the node in-band.

ansible_clean_playbook
    Name of the playbook file inside the ``playbooks_path`` folder
    to use when cleaning the node.

ansible_clean_steps_config
    Name of the YAML file inside the ``playbooks_path`` folder
    that holds description of cleaning steps used by this node,
    and defines playbook tags in ``ansible_clean_playbook`` file
    corresponding to each cleaning step.


Developer impact
----------------

Developers may use this deploy interface for drivers.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
    Pavlo Shchelokovskyy - pas-ha (IRC), pshchelo (Launchpad)

Other contributors:
    Yurii Zveryanskyy - yuriyz (IRC), yzveryanskyy (Launchpad)

Work Items
----------

* Copy ``ansible`` deploy interface from ``ironic-staging-drivers`` project

  + most changes would happen in imports of unit test modules

* Register the ``ansible`` deploy interface entrypoint,
  add it to the list of supported deploy interfaces for ``ipmi`` hardware type,
  do not enable it by default in the configuration file.
* Copy documentation.
* Copy the ``imagebuild`` scripts from ``ironic-staging-drivers`` project
  to the new ``ironic-python-agent-builder`` project

  + Install and use scripts from this new project in DevStack plugins
    and gate jobs

* Amend ironic's DevStack plugin to be able to set up nodes with this deploy
  interface.

  + Currently will require small rebuild of TinyIPA image
    during DevStack install.

* Copy and modify the
  ``gate-tempest-dsvm-ironic-staging-drivers-ansible-wholedisk-ubuntu-xenial-nv``
  gate job, enable it in non-voting mode on ironic project.


Dependencies
============

Ansible has to be installed on the host running ``ironic-conductor`` service.

This deploy interface was developed and tested with Ansible 2.1,
and targets Ansible >= 2.1
(with some intermediate versions being excluded as incompatible).
Currently the gate job testing this deploy interface passes
with latest released Ansible version (2.3.2.0 as of this writing).

Also see the `Ramdisk impact`_ section for changes necessary
to the deploy ramdisk.

Testing
=======

* Unit tests are already in place.
* CI testing is already in place

  + as this is a vendor-agnostic deploy interface, it can be tested
    with virtual hardware in DevStack on upstream gates
  + the job
    ``gate-tempest-dsvm-ironic-staging-drivers-ansible-wholedisk-ubuntu-xenial-nv``
    is already running in non-voting mode on all changes to
    ``ironic-staging-drivers`` project
  + it would have to be copied and modified after appropriate changes are made
    to ironic's DevStack plugin.

Upgrades and Backwards Compatibility
====================================

None.

Documentation Impact
====================

Documentation is already available and will have to be moved to ironic code
tree as well.

References
==========

.. [#] https://www.ansible.com/
.. [#] https://opendev.org/x/ironic-staging-drivers/
.. [#] http://ironic-staging-drivers.readthedocs.io/en/latest/drivers/ansible.html
.. [#] https://opendev.org/openstack/ironic-python-agent-builder/
.. [#] https://pshchelo.github.io/ansible-deploy-perf.html
