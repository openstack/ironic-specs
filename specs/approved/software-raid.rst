..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=========================
Support for Software RAID
=========================

https://storyboard.openstack.org/#!/story/2004581

This spec proposes to add support for the configuration of software RAIDs.

In analogy to the way hardware RAIDs are currently set up, the RAID setup
shall be done as part of the cleaning ("clean-time software RAID"). Admin
Users define the target RAID config which will be applied whenever the
node is cleaned, i.e. before it becomes available for instance creation.

In order to allow the End User to provide details on how the software RAID
shall be configured, the RAID setup should eventually become part of the
deployment steps. Integrating this into the deployment steps framework,
however, is beyond the scope of this spec.


Problem description
===================

As it is hardware agnostic, flexible, reliable, and easy to use, software RAID
has become a popular choice to protect against disk device failures - also in
production setups. Large deployments, such as the ones at Oath or CERN, rely
on software RAID for their various services.

Ironic's current lack of support for such setups requires Deployers and Admins
to withdraw to workarounds in order to provide their End Users with physical
instances based on a software RAID configuration. These workarounds may require
to maintain an additional installation infrastructure which is then either
integrated into the installation process or requires the End User to re-install
a machine a second time after it has been already provisioned by Ironic to
eventually end up with the desired configuration of the disk devices. This
increases the complexity for Deployers and Admins, and can also lead to a
decrease of the End Users' satisfaction with the overall provisioning and
installation process.


Proposed change
===============

The proposal is to extend Ironic to support software RAID by:

* using a node's ``target_raid_config`` to specify the desired s/w RAID layout
  (with some restrictions, see below);
* adding support in the ``ironic-python-agent`` to understand a software
  RAID config as specified in a node's ``target_raid_config`` and be able to
  create and delete such configurations;
* allow the ``ironic-python-agent`` to consider s/w RAID devices for
  deployment, e.g. via root device hints (considering them at all is
  already addressed in [1]);
* adding support in Ironic and the ``ironic-python-agent`` to take the
  necessary steps to boot from a s/w RAID, e.g. installing the boot loader
  on the correct device(s).

Initially, only the following configurations will be supported for the
``target_raid_config`` as to be set by the Admin:

* a single RAID-1 spanning the available devices and serving as the deploy
  target device, or
* a RAID-1 serving as the deploy target device plus a RAID-N where the RAID
  level N is configurable by the Admin. N can be 0, 1, 5, 6, or 10.

The supported configurations have been limited to these two options in order
to avoid issues when booting from RAID devices. Having a (small) RAID-1 device
to boot from is a common approach when setting up more advanced RAID
configurations: a RAID-1 holder device can look like a standalone disk and does
not require the bootloader to have any knowledge or capabilities to understand
more complex RAID configurations.

In order to signal that a software RAID configuration is indeed desired (and
to protect from a situation where a software RAID is set up accidentally
when the configuration passed via the ``target_raid_config`` was meant for a
hardware RAID setup, for instance), the ``controller`` property of all of the
logical disks needs to be set to ``software``. Without this setting, the
software RAID code in the GenericHardwareManager of the IPA will ignore the
given ``target_raid_config``. If it is set on only one of the logical drives,
the validation code will raise an error.

The ``controller`` property set to ``software`` will also be used by the
conductor to identify a software RAID and trigger the required installation of
the bootloader. While whole-disk images are expected to come with a bootloader
configuration as part of the image, for software RAIDs in the current design
the image will not be at the start of a real disk, but inside the first
partition on top of a software RAID-1. The bootloader must hence be explicitly
installed onto the underlying holder disks, and this property will indicate
when to do this.

An example of a valid software RAID configuration would hence look like::

    {
        "logical_disks": [
            {
                "size_gb": 100,
                "raid_level": "1",
                "controller": "software"
            },
            {
                "size_gb": "MAX",
                "raid_level": "0",
                "controller": "software"
            }
        ]
    }

Support for more than one RAID-N, support for the selection of a subset of
drives to act as holder devices, support for simultaneous software and
hardware RAID devices as well as support to partition the created RAID-N
device are left for follow-up enhancements and beyond the scope of this
specification.

Also, there is currently no support for partition images, only whole disk
images are supported.

A first prototype very close to the proposal is available from [2][3][4].

Alternatives
------------

As mentioned above, the alternative is to use other methods to create s/w RAID
setups on physical nodes and integrate these out-of-band approaches into the
provisioning workflow of individual deployments. This increases complexity on
the Deployer/Admin side and can have a negative impact on the user experience
when creating physical instances which need to have a software RAID setup..


Data model impact
-----------------

None.


State Machine Impact
--------------------

None.


REST API impact
---------------

None.


Client (CLI) impact
-------------------

None.

"ironic" CLI
~~~~~~~~~~~~
None.

"openstack baremetal" CLI
~~~~~~~~~~~~~~~~~~~~~~~~~
None.

RPC API impact
--------------

None.

Driver API impact
-----------------

The proposed functionality could be consolidated into a new RAID interface.

Nova driver impact
------------------

None.

Ramdisk impact
--------------

The ``ironic-python-agent`` will need to be able to:
* setup and clean software RAID devices
* consider software RAID devices for deployment
* configure the holder devices of the RAID-1 device in a way they are bootable

This functionality could be consolidated in an additional RAID interface.

Security impact
---------------

None.

Other end user impact
---------------------

While the predefined RAID-1 ensures that a system should be able to boot,
End Users need to be aware that the kernel of the started image needs to
be able to understand software RAID devices.

Scalability impact
------------------

None.

Performance Impact
------------------

None.

Other deployer impact
---------------------

Deployers will need to be aware that the configuration and clean up of
the RAID-N devices is only done during cleaning, so any changes require
the node to be cleaned. Also, the config is not configurable by the End
User, but limited to admins (as the target_raid_config) is a node
property. All of this, however, already holds true for hardware RAID
configurations.

Developer impact
----------------

None.

Implementation
==============

An inital proof-of-concept is available from [2][3][4].

Assignee(s)
-----------

Primary assignee:
  None.

Other contributors:
  Arne.Wiebalck@cern.ch (arne_wiebalck)

Work Items
----------

This is to be defined once the overall idea is accepted and there's agreement
on a design.

Dependencies
============

None.

Testing
=======

TBD

Upgrades and Backwards Compatibility
====================================

None.

Documentation Impact
====================

Documentation on how to configure a software RAID along with the limitations
outlined in 'Deployer's Impact' need to be documented.

References
==========

[1] https://review.openstack.org/#/c/592639
[2] CERN Hardware Manager: https://github.com/cernops/cern-ironic-hardware-manager/commit/7f6d892ec4848a09000ed1f28f3137bf8ba917f0
[3] Patched Ironic Python Agent: https://github.com/cernops/ironic-python-agent/commit/bddac76c4d100af0103a6bc08b81dd71681a9c02
[4] Patched Ironic: https://github.com/cernops/ironic/commit/581e65f1d8986ac3e859678cb9aadd5a5b06ba60

