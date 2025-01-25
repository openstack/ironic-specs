..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

====================================
Boot from Volume - Reference Drivers
====================================

https://bugs.launchpad.net/ironic/+bug/1559691

In order to support booting ironic nodes from a storage device that is
hosted and/or controlled remotely, such as via a SAN or cinder iSCSI target,
changes are required to ironic in order to help facilitate and enable drivers
to leverage the remote storage as a boot volume.

Problem description
===================

* Presently ironic has no support in the reference drivers to boot a
  node from a remote volume.

* Due to the lack of this support, users' capabilities and usability are
  limited. Providing this functionality allows deployments to leverage
  greater capabilities.

Boot from Volume scenarios
--------------------------

This specification is broken into multiple portions in order to facilitate
a phased implementation of support. While it would appear that these
changes should be limited to the boot and deployment interfaces, they
ultimately require substantial substrate changes to provide necessary
functionality.

As there is a large variety of potential connection methods and
configurations, the scenarios we have identified appear suitable for
implementation in a reference driver. We are primarily focused on the
use of cinder, but intend to make the storage substrate pluggable and
generic.

Not covered as part of this specification is handling of support for
MultiPath IO, sometimes referred to as MPIO. We feel this is largely
outside of Ironic's scope at this point in time.

Additionally not covered is the requirement to use UEFI HTTP boot support,
which was set forth during the `ironic mitaka midcycle`_. Using UEFI HTTP boot
would simply load the iPXE UEFI boot loader, and would thus be a redundant
capability compared with existing capabilities.

Below are various boot from volume scenarios. These scenarios are
intended to provide a clear definition of conditions and requirements.

Scenario 1 - iPXE boot from iSCSI volume
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

  Conditions:
    - Node boot defaults to network booting via iPXE controlled by the
      ironic conductor. This is similar to the PXE driver netboot option.
    - Metadata service use is expected as configuration drive
      support is not feasible at this time.
    - Configuration drive is not supported.
        - For context: This is a limitation as a result of the minimum
          new volume and new volume extension sizes in cinder. This may
          be a capability at a later point in time, but is out of scope
          for an initial implementation.
    - iPXE version sufficient to support boot from iSCSI target.
    - Operating system is already deployed to the intended iSCSI boot
      volume via external means.
    - Tenant network isolation is unsupported due to the need for iPXE boot.
        - Potentially in the future, a framework or proxy could be created to
          enable tenant network isolation, however that is considered out of
          scope at this time.
    - Node is configured by the operator with the
      ``node.properties['capabilities']`` setting of ``iscsi_boot``
      set to a value of ``true`` for node validation to succeed.
    - Node has a defined volume target with a ``boot_index``
      value of ``0`` in the volume_targets table.

  Requirements:
    - Storage driver interface
        - A storage driver/provider interface is needed in order to support
          recovery of systems in the event of a failure or change in hardware
          configuration.
    - iPXE template and generation logic changes.
    - Implementation of substrate logic in the deploy and PXE driver modules
      to appropriately handle booting a node in a boot from volume scenario.

Scenario 2 - iPXE boot from Fibre Channel over Ethernet (FCoE)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

  Conditions:
    - Node boot defaults to network booting via iPXE controlled by the
      ironic conductor. Similar to the PXE driver netboot option.
    - Metadata service use is expected.
    - Configuration drive is not supported.
    - Operating system is already deployed to the intended boot volume
      via external means.
    - Tenant network isolation is unsupported due to iPXE requirements.
    - Node is configured with the ``node.properties['capabilities']``
      setting of ``fiberchannel_boot`` set to a value of ``true``
      for node validation to succeed.
    - Node has a defined volume target with a ``boot_index``
      value of ``0`` in the volume_targets table.

  Requirements:
    - `Scenario 1 - iPXE boot from iSCSI volume`_ implemented
    - Additional logic for iPXE template generation in the FCoE use case

Scenario 3 - Boot via hardware Host Bus Adapter (HBA) to volume
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

  Scenario involves boot to a local volume, however, the volume is expected
  to be pre-populated with a bootable operating system. No volume deployment
  operation is expected.

  This scenario is based upon the expectation that the environment and
  the node's firmware settings are such that it is capable of booting
  directly to a presented volume via the HBA once powered on.

  Conditions:
    - Metadata service use is expected.
    - Configuration drive support is unavailable.
    - Node boot defaults to block storage device.
    - Tenant network isolation is supported as this scenario does
      not require iPXE booting for normal operation of the host.
    - Operating system is already deployed to the intended boot volume
      via external means.
    - Infrastructure and HBA BIOS configuration is such that the node will
      boot to what is expected to be the Logical Unit Number (LUN)
      offered as the boot volume.
    - Node is configured with the ``node.properties['capabilities']``
      setting of ``hba_boot`` set to a value of ``true`` for node
      validation to succeed.
    - Node has a defined volume target with a ``boot_index``
      value of ``0``.

  Requirements:
    - Creation of driver deploy method functionality that under normal
      circumstances performs a no-op, and defaults the next boot state
      to local disk when the user requests a node to be deployed.

Scenario 4 - Boot via Host Bus Adapter (HBA) to volume with image deployment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

  Scenario involves boot to a local volume where the volume needs to
  be written out by Ironic's mechanisms.

  Conditions:
    - Metadata service is not required.
    - Configuration drive is supportable.
    - Node boots to block storage device.
    - Tenant network isolation is supported as this scenario does
      not require iPXE booting for normal operation of the host.
    - Infrastructure and HBA BIOS configuration is such that the node will
      boot to what is expected to be the LUN offered as the boot volume.
    - Node is configured with the ``node.properties['capabilities']``
      setting of ``hba_boot`` set to a value of ``true``.
    - Node is configured with the ``node.instance_info['force_deployment']``
      parameter set to ``true``.

  Requirements:
    - This method is expected to be essentially identical to the scenario
      defined in
      `Scenario 3 - Boot via hardware Host Bus Adapter (HBA) to volume`_,
      however via the inclusion of default logic that only invokes deploy
      phase when explicitly requested for boot from a volume.

Scenario 5 - iPXE boot to NFS root volume
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

  Scenario involves use of a kernel and ramdisk image hosted by the
  conductor host in order to enable the node to boot via iPXE with
  sufficient command line parameters to enable the root volume to
  attach during the boot sequence.

  This is a logical progression given that users have indicated that they
  have enabled similar boot functionality downstream.

  Conditions:
    - Metadata service use expected.
    - Configuration drive support is unavailable.
    - Node boot defaults to iPXE.
    - Node boot utilizes kernel and ramdisk hosted by the conductor.
    - Operating System is already deployed to the intended boot volume
      via external means.
    - Tenant network isolation is unsupported due to iPXE need.
    - Node is configured with ``node.properties['capabilities']`` setting of
      ``nfs_boot`` set to a value of true coupled with an ``instance_info``
      setting of ``nfs_root`` which provides nfs root connection information.
    - Kernel and ramdisk utilized support the
      `nfsroot kernel command line option`_.

Potential future capabilities
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

  These are some additional items that it might make sense to develop
  later on after reference driver implementation has been completed,
  however these are out of scope of the existing specification.

     * Boot the agent from a remote volume to facilitate a deployment.
     * Creation of a deployment framework to allow IPA to potentially
       apply HBA settings.
     * Multipath IO configuration handling and potentially passing.
     * Configuration drives support.
     * Support for tenant network isolation boot scenarios.

Proposed change
===============

In order to support an initial feature set, i.e. Scenarios 1-4,
for boot from volume, we propose the following:

  - Implementation of a basic capability concept via a helper method that
    will allow a driver/provider capability to be checked by another portion
    of the code base, returning false if the capabilities definition
    is missing. Example:

     .. code-block:: python

         utils.check_capability(
             task.driver.boot.capabilities, 'iscsi_volume_boot')
         utils.check_compatibility(
             task.driver.deploy.capabilities, 'iscsi_volume_deploy')

    This would be implemented via a list of capability 'tags' to
    each main level interface class, as required in order to guard
    against invalid configurations.

  - Implementation of logic in the existing reference driver deploy
    validate methods to fail the validation of any node that has volume
    storage configured when the driver that a node is configured with
    lacks any such support as identified by the previously noted
    capability interface.
    This is to help ensure that such nodes are not accidentally
    provisioned with erroneous user expectations.

  - Updating of the ``agent.AgentDeploy`` and ``iscsi_deploy.ISCSIDeploy``
    driver logic to support skipping deployment of a node if a storage
    interface provider is defined, volume information exists for the volume,
    and the volume has an index of ``0`` indicating it is the boot volume.
    In essence, this means that if the node is defined to boot from a
    remote volume, that the driver.deploy.deploy method should immediately
    return DEPLOYDONE as any network booting configuration, if applicable,
    would have to be written out via driver.deploy.prepare method.
    Example:

     .. code-block:: python

         if (task.node.storage_interface is not None and
                 not task.driver.storage.should_write_image(task)):

    Additionally, validation logic will need to be updated in the deploy
    drivers to pass specific checks of instance_info fields that do not apply
    with the case of booting from a volume.

  - Creation of a storage provider interface:
     - Similar in composition to the network provider interface, where a
       default will result in a provider interface that performs
       ``no-op`` behavior, while exposing an empty set of storage
       capabilities.
     - A node level ``storage_interface`` setting with default value,
       similar to the `Add network interface to base driver class`_
       change, to define if a node is to utilize the storage interface along
       with the provider that is to be utilized.
       This is intended to align with the
       `Driver composition reform specification`_.
     - Initial and reference storage driver to be based upon cinder,
       leveraging ``python-cinderclient`` for the REST API interface,
       to support the following fundamental operations detailed below.

         - ``detach_volumes`` - Initially implemented to enumerate
           through known attached volumes and remove the storage
           attachments.
         - ``attach_volumes`` - Initially implemented to enumerate
           through known configured volumes and issue storage
           attachment requests. In the case of the cinder driver,
           we will reserve the volumes in our configuration, initialize
           connections to the volumes meanwhile supplying current initiator
           configuration, then trigger the cinder volume attach call to update
           the database configuration. Additionally, we will update the volume
           metadata to allow for easy user identification of volumes that are
           used for ironic nodes by recording information to allow for
           reconciliation of nodes that are powered off with detached volume.
         - ``validate`` - Initially implemented to validate that sufficient
           configuration is present in the configuration to allow for the
           functionality to operate. This validation will be skipped if no
           volumes are defined.
         - ``should_write_image`` - Provides an interface to allow the other
           components to ask the storage driver if the image should be
           written to disk. This allows all of the logic to be housed with
           the storage interface.

  - Updating of the ``pxe.PXEBoot`` driver logic to support the creation of
    the appropriate iPXE configurations for booting from the various boot
    scenarios if the ``volume_target`` information is defined, iPXE is
    enabled, and a storage provider is available.

  - Updating of the ``pxe.PXEBoot`` validate interface to leverage a helper
    method when a storage provider and boot volume is defined in the
    node configuration, to validate that the capabilities, initiator
    configuration, and volume configuration are in alignment for the
    specified volume/path type.  Note that the bulk of this logic should
    reside in a ``deploy_utils`` method that can be re-used by other
    drivers moving forward.

  - Updating of the conductor ``utils.node_power_action`` logic to
    enable the storage provider (defined by the node.storage_interface
    setting) to be called to permit volume attachment and detachment
    for the node and thus update any storage configuration if necessary.

  - Addition of a helper method that sets and returns, if not already
    set, the node.instance_info's boot_option parameter based upon the
    hardware configuration, and supplied volume configuration information,
    enabling matching and identification of what the next appropriate step
    is for each scenario.

  - Updating of the conductor ``_do_node_tear_down`` method to call the
    storage provider detach_volumes method and purge volume information
    if not already implemented.

        - At the beginning and completion of the storage detachment
          interaction, a notification shall be generated to allow
          visibility into if the process is successfully completed.

  - Updating the iPXE template logic to support the creation of
    the various file formats required for Scenarios 1, 2, 5.  See:
    `IPXE sanhook command`_, `IPXE san connection URLs`_ and
    `nfsroot kernel command line option`_.

As previously noted, each scenario will be submitted separately as
incremental additions to ironic.

In order to support scenario 4, the deploy driver will need to
understand how to deploy to a system with such configuration.

  - Updating of the deploy driver to enable the logic added for scenarios 1-3
    to be bypassed using a ``force_deployment`` parameter which should be
    removed from the node's instance_info prior to the node reaching the
    active state. This, in effect, would cause ironic to support a deployment
    operation when the supplied volume information is normally expected to
    have a valid Operating System and boot loader already in place.

  - Agent will need to be informed of the desired volume for the boot volume,
    and, if supplied to the target, connection information. The appropriate
    information should be passed in using `Root device hints`_, specifically
    setting a WWN or volume serial number if available.

In order to support scenario 5:
  - Scenario 3 must be implemented.  This is anticipated to largely be
    an alternative path in the iPXE template where the previously defined
    settings cause the on-disk PXE booting template to boot the node from
    the NFS root.

Later potential improvements above and beyond this initial specification:
  - Creation of logic to allow Ironic users to leverage the storage provider
    to request a volume for their node.  Such functionality would require
    ironic to deploy the OS image, and should be covered by a separate
    specification.

Alternatives
------------

An alternative could be to simply not develop this functionality and to
encourage downstream consumers to independently develop similar tooling
to meet their specific environment's needs. That being said, both options
are unappealing from the standpoint of wishing to grow and enhance
ironic.

Data model impact
-----------------

A ``storage_interface`` field will be added to the node object which will
be mapped to the appropriate storage driver.

State Machine Impact
--------------------

None

REST API impact
---------------

As the node storage driver will be selectable by the operator,
it will need to be concealed from older API clients, which will
necessitate a microversion update once the functionality is present
in the API.

Client (CLI) impact
-------------------

"ironic" CLI
~~~~~~~~~~~~

None. All expected CLI updates are expected to be part of the
specification covering information storage,
`Add volume connection information for Ironic nodes`_.

"openstack baremetal" CLI
~~~~~~~~~~~~~~~~~~~~~~~~~

None

RPC API impact
--------------

None

Driver API impact
-----------------

The first change is the introduction of a list of supported advanced driver
features defined by the deploy and boot driver classes, known as capabilities,
that allow for other driver components to become aware of what functionality
is present in a neighboring driver interface/composition.

The second change is the introduction of a new ``storage_interface`` that will
be mapped to a selectable storage driver of the available storage drivers.

Within this storage interface, new methods will be defined to support
expected storage operations.  Below are the methods that are anticipated
to be added and publicly available from drivers::

    def attach_volumes(self, task):
    """Informs the storage subsystem to detach all volumes for the node."""

    def detach_volumes(self, task):
    """Informs the storage subsystem to detach all volumes for the node."""

    def validate(self, task):
    """Validate that the storage driver has appropriate configuration."""

    def should_write_image(self, task):
    """Determines if deploy should perform the image write-out."""

Nova driver impact
------------------

Impact to the nova driver is covered in a separate specification
`Nova Specs - Ironic - Boot from Cinder volume`_. As the driver will
be available as an opt-in change, we expect no negative impact
on behavior.

Ramdisk impact
--------------

While we should be able to derive the intended root volume and pass
an appropriate root hint if necessary in order to facilitate a deployment
as part of
`Scenario 4 - Boot via Host Bus Adapter (HBA) to volume with image deployment`_
, the IPA ramdisk should likely have functionality added in the form of a
HardwareManager in order to support MutliPath IO.  That being said MPIO
is out of scope for this specification.

Security impact
---------------

Overall, the storage driver, in this case, cinder, will need to utilize
credentials that are already populated in the configuration for keystone
to connect to cinder to obtain and update mapping information for volumes.

Scenarios 1-2 and 5 are designed such that the tenant machine is able to
reach the various services being offered up by whatever the volume driver
is set to leverage over the node's default network configuration. As a
result of the need to network boot, the flat network topology is required
along with access controls such that the nodes are able to reach the
services storage volumes.

The more secure alternative are the drivers representing scenarios 3 and 4
as this configuration ultimately requires a separate storage infrastructure.
This case will allow for tenant network isolation of deployed nodes.

Other end user impact
---------------------

This functionality may require additional knowledge to be conveyed to
the ironic-webclient and ironic-ui sub-projects, however that will need
to be assessed at the time of implementation as they are under active
development.

Scalability impact
------------------

This is a feature that would be opted into use by an operator.  In the
case where it is active, additional calls to the backend storage
interface may have a performance impact depending upon architecture
of the deployment.

Performance Impact
------------------

For each node under ironic's care that we believe has volumes, we need to
query storage manager, presumably cinder based on this implementation, and
attach/detach volumes during intentional user drive power operations. This
may extend the call to power-on a node after deployment, or potentially
prevent power-up if the attachment cannot be made.

Other deployer impact
---------------------

Deployers wishing to use these drivers will naturally need to add the
``cinder`` storage interface to the ``enable_storage_interfaces`` list.

A default storage configuration driver will be set to ``noop`` which will
prevent any storage related code from being invoked until the operator
explicitly chooses to enable this support.

Based on the proposed driver configuration, we can expect two additional
sections in the conductor configuration file:
::

  [DEFAULT]
  enabled_storage_interfaces = <None> # Defaults to none and is a list of the
  available drivers.

  [cinder]
  url = http://api.address:port
  url_timeout = 30
  retries = 3
  auth_strategy = <noauth|keystone>
  toggle_attachments_with_power = true

Developer impact
----------------

This will increase the overall complexity and set of capabilities that
ironic offers. Driver developers wishing to implement driver specific
functionality should expect certain substrate operations to occur,
and attempt to leverage the substrate set forth in this specification and
the `Add volume connection information for Ironic nodes`_ specification.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  juliaashleykreger

Other contributors:
  blakec
  shiina-hironori

Work Items
----------

The breakdown of the proposed changes, when combined with the underlying
scenarios helps convey the varying work items.  That being said, this
functionality will take some time to land.

Dependencies
============

Logic will need to be implemented in IPA to handle the scenario when no disks
are detected. ``cleaning`` and ``inspection`` operations should be able to be
executed upon hardware nodes that have no local disk storage.

Additionally in IPA, as a soft dependency, logic MAY be required to better
handle directly attached volume selection when multipathing is present.
This will require its own specification or well-defined and validated plan
as IPA cannot expect OS multipathing support to handle MPIO scenarios in all
cases, or to even be present.

Implementation of `Add volume connection information for Ironic nodes`_.
This specification should not be entirely dependent upon the implementation
of the `Nova Specs - Ironic - Boot from Cinder volume`_ specification.

A soft dependency exists for the `Driver composition reform specification`_ in
that these two efforts are anticipated to be worked in parallel, and this
implementation effort should appropriately incorporate functionality as the
functionality for the `Driver composition reform specification`_ begins to
become available.

Testing
=======

The level of full stack functional and integration tests is a topic that
requires further discussion in the ironic community. An initial case for a
gate test could be where an ironic deployment boots from a Cinder volume,
which a tempest test could orchestrate.

Scenarios 3 and 4 are the most difficult to test as they have detached
infrastructure expectations outside of our direct control. However, we may
find that the base overlay is sufficient to test with unit tests due to
what will ultimately be significant underlying common paths.

Upgrades and Backwards Compatibility
====================================

As this feature set is being created as a new set of capabilities within the
reference drivers and their capability, no compatibility issues are expected
as the API field additions related to this specification will be hidden from
an API client that does not request the appropriate API version.

A database migration step will be added to create the ``storage_interface``
node database field. The initial value for this field will be None, and
there will be no implied default set as an operator must choose to enable
a storage interface in their environment.

Documentation Impact
====================

Documentation will need to be updated detailing the new driver and the related
use scenarios so an operator can comprehend what options the driver(s) provide
and how they can fit into their use cases. Additional caveats regarding long
term network booting of hosts should be explicitly stated as part of this
work.

It is expected that this specification will be further refined during
development of this functionality in order to raise and document any new
findings at a technical level.

References
==========

Relevant specifications:
  - `Add volume connection information for Ironic nodes`_
  - `Nova Specs - Ironic - Boot from Cinder volume`_
Mitaka midcycle etherpad:
  - `ironic mitaka midcycle`_

.. _`IPXE sanhook command`: http://ipxe.org/cmd/sanhook
.. _`IPXE san connection URLs`: http://ipxe.org/sanuri
.. _`Driver composition reform specification`: https://specs.openstack.org/openstack/ironic-specs/specs/not-implemented/driver-composition-reform.html
.. _`Add network interface to base driver class`: https://review.opendev.org/#/c/285852/
.. _`Add volume connection information for Ironic nodes`: https://specs.openstack.org/openstack/ironic-specs/specs/not-implemented/volume-connection-information.html
.. _`Nova Specs - Ironic - Boot from Cinder volume`: https://review.opendev.org/#/c/311696/
.. _`ironic mitaka midcycle`: https://etherpad.openstack.org/p/ironic-mitaka-midcycle
.. _`nfsroot kernel command line option`: https://www.kernel.org/doc/Documentation/filesystems/nfs/nfsroot.txt
.. _`Root device hints`: https://specs.openstack.org/openstack/ironic-specs/specs/kilo-implemented/root-device-hints.html
