..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===========================================
New driver interface for RAID configuration
===========================================

https://blueprints.launchpad.net/ironic/+spec/ironic-generic-raid-interface

The proposal presents the work required to create a new driver interface for
RAID configuration.  It also proposes a method to make RAID configuration
available as part of zapping or cleaning.

.. note::
  Even though RAID configuration fits into zapping, it can be used as part of
  cleaning as well.  Zapping and cleaning follow a similar mechanism (zap
  step is a clean step with priority of 0). It makes sense to do RAID
  configuration as part of cleaning for software RAID (where secure disk erase
  will also erase the software RAID configuration on the disk).  It's operators
  choice to decide whether RAID configuration should be part of zapping or
  cleaning and it will be configurable in the drivers implementing it.

Problem description
===================

* There is no support in Ironic currently to do RAID configuration.

* A specific set of tasks for this requires a separate interface on the
  drivers.  The new RAID interface will allow operators to specify RAID
  configuration for a node.  Different drivers may provide the same interface
  to the operator for RAID configuration.

Proposed change
===============

* After a node is enrolled and the basic hardware information is available,
  the operator can define a RAID configuration. This configuration will be
  applied during zapping or cleaning.

* The operator can convey the RAID configuration information to the Ironic
  driver through REST APIs or CLI as JSON data. The RAID configuration
  information will contain the properties for each logical disk and
  optionally hints to Ironic to find the desired backing physical disks for
  them.

  The properties can be split into 4 different types:

  #. Mandatory properties - These properties must be specified for each logical
     disk and have no default values.

     - ``size_gb`` - Size (Integer) of the logical disk to be created in GiB.
       ``MAX`` may be specified if the logical disk should use all of the
       space available on the backing physical disks.  This can be used only
       when backing physical disks are specified (see below).
     - ``raid_level`` - RAID level for the logical disk. Ironic will define the
       supported RAID levels as 0, 1, 2, 5, 6, 1+0, 5+0, 6+0. Drivers may
       override the values in the ``get_logical_disk_properties`` method in
       ``RAIDInterface``.

  #. Optional properties - These properties have default values and
     they may be overridden in the specification of any logical disk.

     - ``volume_name`` - Name of the volume. Should be unique within the Node.
       If not specified, volume name will be auto-generated.
     - ``is_root_volume`` - Set to ``true`` if this is the root volume. Can be
       used for only one of logical disk. The `root device hint`_ will be
       saved, if the driver is capable of retrieving it. This is ``false``
       by default.

  #. Backing physical disk hints - These hints are specified for each logical
     disk to let Ironic find the desired disks for RAID configuration. This is
     machine-independent information.  This serves the use-case where the
     operator doesn't want to provide individual details for each bare metal
     node.

     - ``share_physical_disks`` - Set to ``true`` if this logical disk can
       share physical disks with other logical disks.  It has default value
       of ``CONF.raid.share_physical_disks``. The default value of this config
       variable will be ``false``.
     - ``disk_type`` - ``hdd`` or ``ssd``. It has a default value of
       ``CONF.raid.disk_type``. The default value of this config
       variable will be ``hdd``.
     - ``interface_type`` - ``sata`` or ``scsi`` or ``sas``. It has a default
       value of ``CONF.raid.interface_type``. The default value of this
       config variable will be ``sas``.
     - ``number_of_physical_disks`` - Integer, number of disks to use for the
       logical disk. Defaulted to minimum number of disks required for the
       particular RAID level.

     The above mentioned backing physical disk hints are defined by
     Ironic and every driver has to implement them.  The supported values and
     the default values for the above hints may be overridden by the driver
     using the ``RAIDInterface.get_logical_disk_properties()`` method.

     In addition to the above hints, drivers may define their own hints in the
     ``get_logical_disk_properties`` method.  For more details, refer to the
     Driver API impact section. The possible use-cases for them might be:

     - Filter disks by particular vendors
     - Filter disks by models
     - Filter disks by firmware versions.

  #. Backing physical disks - These are the actual machine-dependent
     information.  This is suitable for environments where the operator wants
     to automate the selection of physical disks with a 3rd-party tool based
     on a wider range of attributes (eg. S.M.A.R.T. status, physical location).

     - ``controller`` - The name of the controller as read by the driver.
     - ``physical_disks`` - A list of physical disks to use as read by the
       driver.

     .. note::
       The values for these properties are hardware dependent.

  .. note::
    Only properties from "Backing physical disk hints" or
    "Backing physical disks" should be specified.  If both are specified,
    they should be consistent with each other.  If they are not consistent,
    then the raid configuration will fail (because the appropriate backing
    physical disks could not be found).

  Some examples:
    Example 1 (using backing physical disk hints)::

      {
        'logical_disks':
          [
            {
              'size_gb': 50,
              'raid_level': '1+0',
              'disk_type': 'hdd',
              'interface_type': 'sas',
              'volume_name': 'root_volume',
              'is_root_volume': 'true'
            },
            {
              'size_gb': 100,
              'number_of_physical_disks': 3,
              'raid_level': '5',
              'disk_type': 'hdd',
              'interface_type': 'sas'
              'volume_name': 'data_volume'
            }
          ]
      }

    Example 2 (using backing physical disks)::

      {
        'logical_disks':
          [
            {
              'size_gb': 50,
              'raid_level': '1+0',
              'controller': 'RAID.Integrated.1-1',
              'volume_name': 'root_volume',
              'is_root_volume': 'true'
              'physical_disks': [
                                 'Disk.Bay.0:Encl.Int.0-1:RAID.Integrated.1-1',
                                 'Disk.Bay.1:Encl.Int.0-1:RAID.Integrated.1-1'
                                ]
            },
            {
              'size_gb': 100,
              'raid_level': '5',
              'controller': 'RAID.Integrated.1-1',
              'volume_name': 'data_volume'
              'physical_disks': [
                                 'Disk.Bay.2:Encl.Int.0-1:RAID.Integrated.1-1',
                                 'Disk.Bay.3:Encl.Int.0-1:RAID.Integrated.1-1',
                                 'Disk.Bay.4:Encl.Int.0-1:RAID.Integrated.1-1'
                                ]
            }
          ]
      }


* The RAID configuration information is stored as JSON in
  ``node.target_raid_config`` field. Operator can use the REST API (or CLI)
  to put a new value here at any time, which is compared to
  ``node.raid_config`` during zapping and cleaning, and driver may apply
  changes only in those stages. Refer REST API Impact section for more details.

* New driver interface called ``RAIDInterface`` will be provided for RAID
  configuration for drivers. For more details, refer to the Driver API impact
  section.

* New methods ``create_config`` and ``delete_config`` in
  ``RAIDInterface`` will be available as part of zapping.  The operator can
  choose to call them as part of zap steps.  The corresponding zap steps will
  be ``node.raid.create_config`` and ``node.raid.delete_config``.

* A new method ``update_raid_info`` will be available in the base class
  ``RAIDInterface``.  This method may be used by the driver implementation of
  ``create_config`` and ``delete_config`` to update
  the RAID information in the Node database. This will facilitate drivers to do
  the RAID configuration asynchronously.  This method will do the following:

  + Set ``node.raid_config`` to the value returned by the driver.
  + The root device hint for the root volume will be updated in
    ``node.properties`` (as per `root device hint`_) and
    the size of root volume will be updated in ``node.properties.local_gb``.
    It's up to the driver to choose which root device hint it wants to specify.
    Furthermore, it isn't even necessary for the driver to choose any
    root_device_hint.
  + The RAID level of the root volume will be updated as ``raid_level`` in
    ``node.properties.capabilities``.

* A new REST API will be created for retrieving the properties which may be
  specified as part of RAID configuration. For details, see the REST API Impact
  section below.

* REST API will be created to PUT RAID config, and a new REST resource added
  to retrieve the requested and actual RAID config.


Alternatives
------------

* Operator can change the RAID configuration manually whenever required after
  putting the node to MANAGEABLE state. But this has to be done for each node.


Data model impact
-----------------

The following fields in the Node object will be updated:

* A new database field, ``node.target_raid_config``, will store the pending
  RAID configuration to be applied during zapping or cleaning. This will be a
  JSON dictionary. This field will be read-only.

* A new database field, ``node.raid_config``, will store the last applied RAID
  configuration. This will also contain the timestamp of when this
  configuration was applied. This will be a JSON dictionary. This field will be
  read-only.

* ``node.properties.local_gb`` will be updated after applying RAID
  configuration to the size of the root volume.

* ``node.properties.root_device`` will be updated with the root device hint
  returned by the driver as prescribed in the `root device hint`_ spec.

* A new capability ``raid_level`` will be added in
  ``node.properties.capabilities``. This will contain the RAID level of the
  root volume.


State Machine Impact
--------------------
None.

REST API impact
---------------

Two new REST API endpoints will be introduced as part of this change.

- To GET the RAID properties that can be defined and their possible values::

    GET /drivers/<driver>/raid/logical_disk_properties

  The operation will return the properties and a textual description of the
  possible values for each property::

    {
     'raid_level': 'RAID level for the logical disk. Supported values are
                    0, 1, 2, 5, 6, 1+0, 5+0, 6+0. Required.',
     'size_gb': 'Size of the logical disk in GiB. Required.',
     'disk_type': 'Disk Type. Supported values are `hdd` or `sdd`. Optional',
     .
     .
     .
     .
    }

- To set the target RAID configuration, a user will::

    PUT /v1/nodes/NNNN/states/raid

  with a BODY containing the JSON description of the RAID config.

  If accepted by the driver, this information will be stored in the
  ``node.target_raid_config`` field and exposed in the same manner as the power
  and provision states. In other words, it may be retrieved either within the
  detailed view of a ``node``, or by either of the following::

    GET /v1/nodes/NNNN
    GET /v1/nodes/NNNN/states

  .. note::
    It might also make sense to have GET /v1/nodes/NNNN/states/raid, but for
    maintaining consistency with power and provision, we allow only
    GET /v1/nodes/NNNN and GET /v1/nodes/NNNN/states.

If the driver doesn't support RAID configuration, then both API calls will
return HTTP 404 (Not Found). Otherwise the API will return HTTP 200 (OK).


Client (CLI) impact
-------------------

A new option will be available in Ironic CLI for getting the properties which
may be specified as part of the RAID configuration::

   $ ironic node-raid-logical-disk-properties <node-uuid>


A new method will be added to set the target RAID properties

RPC API impact
--------------

One new RPC API will be created.

- ``get_raid_logical_disk_properties`` - This method will be called in
  ``GET /drivers/<driver>/raid/logical_disk_properties``.

Driver API impact
-----------------

A new ``RAIDInterface`` will be available for the drivers to allow them to
implement RAID configuration.  It will have the following methods:

  - ``create_config()`` - The driver implementation of the method
    has to read the request RAID configuration from ``node.target_raid_config``
    and create the RAID configuration on the bare metal. The driver
    implementations should throw error if ``node.target_raid_config``
    is not set.  The driver must ensure ``update_raid_info`` is called at the
    end of the process updating the ``raid_config``. The implementation detail
    is up to the driver depending on the synchronicity/asynchronicity of the
    operation.

    The ``raid_config`` will include the following:

    + For each logical disk (in addition to the input passed):

      * ``controller`` - The name of the controller used for the logical disk
        as read by the driver.
      * ``physical_disks`` - A list containing the identifier for the
        physical disks used for the logical disk as read by the driver.
      * ``root_device_hint`` - A dictionary containing the root device hint to
        be used by Ironic to find the disk to which image is to be deployed.
        It's up to the driver to determine which root device hint it wants to
        provide.

    + A list of all the physical disks on the system with the following
      details:

      * ``controller`` - RAID controller for the physical disk.
      * ``id`` - ID for the physical disk as read the driver
      * ``disk_type`` - ``hdd`` or ``ssd``
      * ``interface_type`` - ``sas`` or ``sata`` or ``scsi``
      * ``size_gb``
      * ``state`` - State field states the current status of the physical disk.
        It can be one of:

        - ``active`` if disk is part of an array
        - ``ready`` if disk is ready to be part of a volume
        - ``failed`` if disk has encountered some error
        - ``hotspare`` if disk is hotspare and part of some array
        - ``offline`` if disk is not available for raid due to some other
          reason, but not failed
        - ``non_raid`` if disk is not part of raid and is directly visible


      The above details may be used for backing physical disk hints for later
      raid configurations.

      .. note::
        For a newly enrolled node or a node in which raid configuration was
        never done, the information about physical disks and controllers can
        be populated by hardware introspection. This is not in the scope of
        this spec.


    The function definition will be as follows::

      def create_config(task, create_only_root_volume=False,
                        create_only_nonroot_volumes=False):
          """Create RAID configuration on the node.

          This method creates the RAID configuration as read from
          node.target_raid_config.  This method
          by default will create all logical disks.

          :param task: TaskManager object containing the node.
          :param create_only_root_volume: This specifies whether to create
              only the root volume.
          :param create_only_nonroot_volumes: This specifies to create only
              non-root volumes.
          """

  - ``delete_config`` - To delete the RAID configuration. This
    method doesn't have an input and doesn't return anything.

    The function definition will be as follows::

      def delete_config(task):
          """Delete RAID configuration on the node.

          :param task: TaskManager object containing the node.
          """

  - ``validate`` - To validate a RAID configuration. This will be called
    while validating the driver interfaces. This will read the target RAID
    configuration from node.properties.target_raid_config.

    The function definition will be as follows::

      def validate(task):
          """Validates the given RAID configuration.

          :param task: TaskManager object containing the node.
          :raises: InvalidParameterValue, if RAID configuration is invalid.
          :raises: MissingParameterValue, if RAID configuration has some
              missing parameters.
          """

  - ``get_logical_disk_properties`` - To get the RAID properties that are
    defined by the driver.

    The function definition will be as follows::

      def get_logical_disk_properties(task):
          """Gets the RAID properties defined by the driver.

          :param task: TaskManager object containing the node.
          :returns: A dictionary of properties and a textual description.
          """


After performing the RAID configuration (create or delete), the drivers
may call ``update_raid_info`` with the ``raid_config``. The
details about the method has been described above. The definition of the
method will look like below::

  def update_raid_info(task, raid_config):
      "Updates the necessary fields of the node after RAID configuration.

      This method updates the current RAID configuration in
      node.properties.raid_config.  If root device hint was passed,
      it will update node.properties.local_gb, node.properties.root_device_hint
      and node.properties.capabilities['raid_level'].

      :param task: TaskManager object containing the node.
      :param raid_config: The current RAID configuration on the bare metal
          node.
      """





Nova driver impact
------------------

None.

Security impact
---------------

None.

Other end user impact
---------------------

Users from Nova may choose the desired RAID level for the root volume by
using compute capabilities. For example::

  nova flavor-key ironic-test set capabilities:raid_level="1+0"

Scalability impact
------------------

None.

Performance Impact
------------------

RAID configuration may extend the time required for zapping or cleaning on the
nodes, but this is important for performance and reliability reasons.

Other deployer impact
---------------------

Operator can make use of ``node.raid.create_config`` and
``node.raid.delete_config`` as zap or clean tasks for doing RAID management.

Developer impact
----------------

Developers may implement the ``RAIDInterface`` for respective drivers.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  rameshg87

Other contributors:
  ifarkas

Work Items
----------

+ Create REST API endpoints for RAID configuration.
+ Create ``RAIDInterface`` and create a fake implementation of
  ``RAIDInterface``.
+ Implement ``update_raid_info`` in ``RAIDInterface``.
+ Implement Ironic CLI changes.
+ Write unit tests.

Dependencies
============

* Root device hints - http://specs.openstack.org/openstack/ironic-specs/specs/kilo/root-device-hints.html
* Zapping of nodes - https://review.openstack.org/#/c/140826/

Testing
=======

* Unit tests will be added for the code.  A fake implementation of the
  ``RAIDInterface`` will be provided for testing purpose and this can be run
  as part of zapping.

* Tempest API coverage will be added, using the fake driver above.

* Each driver is responsible for providing the third party CI for testing the
  RAID configuration.


Upgrades and Backwards Compatibility
====================================

None.


Documentation Impact
====================

Documentation will be provided on how to configure a node for RAID.

References
==========

.. _`root device hint`: http://specs.openstack.org/openstack/ironic-specs/specs/kilo/root-device-hints.html

Other references:

* New Ironic provisioner state machine: http://specs.openstack.org/openstack/ironic-specs/specs/kilo/new-ironic-state-machine.html

* Support Zapping of Nodes: https://review.openstack.org/#/c/140826/
