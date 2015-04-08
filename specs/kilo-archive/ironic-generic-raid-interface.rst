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
available as part of zapping.

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
  applied in two steps during zapping: creating the root device and creating
  the rest of the RAID disks. This is required because certain drivers might
  not be able to propagate any root device hint. With an optional step between
  the zapping steps, the root device can be investigated with other methods
  (eg. using discoverd).

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
       ``CONF.raid.default_disk_type``. The default value of this config
       variable will be ``hdd``.
     - ``interface_type`` - ``sata`` or ``scsi`` or ``sas``. It has a default
       value of ``CONF.raid.default_interface_type``. The default value of this
       config variable will be ``sas``.
     - ``number_of_physical_disks`` - Integer, number of disks to use for the
       logical disk. Defaulted to minimum number of disks required for the
       particular RAID level.

     The above mentioned backing physical disk hints are defined by
     Ironic and every driver has to implement them.  The supported values and
     the default values for the above hints may be overridden the driver using
     the ``get_logical_disk_properties`` method.

     In addition to the above hints, drivers may define their own hints in the
     ``get_logical_disk_properties`` method.  For more details, refer the
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
    Only one of "Backing physical disk hints" or "Backing physical disks"
    need to be specified.  If both are specified, they need to be
    consistent with each other.  If they are not consistent, then the raid
    configuration will fail (because the appropriate backing physical disks
    could not be found).

  Some examples:
    Example 1::

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

    Example 2::

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





* New driver interface called ``RAIDInterface`` will be provided for RAID
  configuration for drivers. For more details, refer the Driver API impact
  section.

* New methods ``create_configuration`` and ``delete_configuration`` in
  ``RAIDInterface`` will be available as part of zapping.  The operator can
  choose to call them as part of zap steps.  The corresponding zap steps will
  be ``node.raid.create_configuration`` and ``node.raid.delete_configuration``.

* A new method ``update_raid_info`` will be available in the base class
  ``RAIDInterface``.  This method may be used by the driver implementation of
  ``create_configuration`` and ``delete_configuration`` to update
  the RAID information in the Node database. This will facilitate drivers to do
  the RAID configuration asynchronously.  This method will do the following:

  + Set ``node.driver_internal_info.current_raid_configuration`` to the value
    returned by the driver.
  + Set the respective part (root/non-root devices) of
    ``node.driver_internal_info.target_raid_configuration`` to ``None``. Update
    the ``last_updated_at`` timestamp in ``current_raid_configuration``.
  + The root device hint for the root volume will be updated in
    ``node.properties`` as per the root device hint `root device hint`_ and
    the size of root volume will be updated in ``node.properties.local_gb``.
    It's up to the driver to choose which root device hint it wants to specify.
  + The RAID level of the root volume will be updated as ``raid_level`` in
    ``node.properties.capabilities``.

* New REST APIs will be created for RAID configuration. For more details, refer
  to the REST API impact section.

* Four new options will be available in Ironic CLI for doing the RAID
  configuration.

  To set a new RAID configuration::

   $ ironic node-set-raid-configuration <node-uuid> --from-file raid_conf.json

  To get the RAID configuration::

   $ ironic node-get-raid-configuration <node-uuid>

  To get the physical disks available in RAID controllers::

   $ ironic node-get-raid-physical-disks <node-uuid>

  To get the properties that can be defined for each logical disk and their
  possible values::

   $ ironic node-get-raid-logical-disk-properties <node-uuid>



Alternatives
------------

* Operator can change the RAID configuration manually whenever required after
  putting the node to MANAGEABLE state. But this has to be done for each node.

* There needs to be only one API ``PUT /nodes/<uuid>/raid/configuration`` which
  can be used for both creating and deleting the configuration. For deletion,
  delete=True may be passed to the API.


Data model impact
-----------------

The following fields in the Node object will be updated:

* ``node.driver_internal_info.target_raid_configuration`` will store the
  pending RAID configuration to be applied during zapping.

* ``node.driver_internal_info.current_raid_configuration`` will store the
  last applied RAID configuration. This will also contain the timestamp of
  when this configuration was applied.

* ``node.properties.local_gb`` will be updated after applying RAID
  configuration to the size of the root volume.

* ``node.properties.root_device`` will be updated with the root device hint
  returned by the driver as prescribed in the `root device hint`_ spec.

REST API impact
---------------

Four new REST APIs will be introduced as part of this change.

- To create the RAID configuration for a node, run::

    PUT /nodes/<uuid>/raid/configuration

  This operation is idempotent. The operation will write the configuration
  to the ``node.driver_internal_info.target_raid_configuration`` and will be
  applied during the zapping step. The JSON data of the RAID configuration as
  mentioned above needs to be passed as data to this request. Updating the
  RAID configuration will be prevented if RAID configuration is in progress
  from the driver. This will also validate the target RAID configuration by
  calling ``validate_configuration`` method on the ``RAIDInterface``.

  .. note::
    This API doesn't actually do the RAID configuration.  It just stores the
    input for RAID configuration in the Ironic database.  The RAID
    configuration will be done as part of zapping.

  If the operation is success, then the API will return HTTP 202 (Accepted).
  If the operation failed, either because the driver doesn't support RAID
  configuration or validation of input failed, then the API will return HTTP
  400 (Bad Request).


- To GET the current RAID configuration::

    GET /nodes/<uuid>/raid/configuration

  This operation will return the current and target RAID configuration.

  Example 1: After putting a RAID configuration using ``PUT``::

    {
      'current': None
      'target':
        {
          'logical_disks':
            [
              {
                'size_gb': 50,
                'raid_level': '1',
                'volume_name': 'root_volume',
                'is_root_volume': 'true'
                'disk_type': 'hdd',
                'interface_type': 'sas',
              },
              {
                'size_gb': 100,
                'number_of_physical_disks': 3,
                'volume_name': 'data_volume'
                'raid_level': '5',
                'disk_type': 'hdd',
                'interface_type': 'sas'
              }
            ]
        }
    }


  Example 2: After the RAID configuration is applied as part of zapping::

    {
      'current':
        {
          'logical_disks':
            [
              {
                'size_gb': 50,
                'raid_level': '1',
                'share_physical_disks': False,
                'disk_type': 'hdd',
                'interface_type': 'sas',
                'number_of_physical_disks': 2,
                'volume_name': 'root_volume',
                'is_root_volume': 'true',
                'controller': 'Smart Array P822 in Slot 2',
                'physical_disks': [
                                   '5I:1:2',
                                   '5I:1:3'
                                  ]
                'root_device_hint': {
                                     'wwn': 600508B1001CE4ACF473EE9C826230FF'
                                    }
              },
              {
                'size_gb': 100,
                'number_of_physical_disks': 3,
                'raid_level': '5',
                'disk_type': 'hdd',
                'interface_type': 'sas',
                'number_of_physical_disks': 3,
                'volume_name': 'data_volume',
                'controller': 'Smart Array P822 in Slot 2',
                'physical_disks': [
                                   '5I:1:4',
                                   '5I:1:5',
                                   '5I:1:6'
                                  ]
              }
            ],
        }
        'target': None
    }

  If driver doesn't support RAID configuration, then the API will return HTTP
  400 (Bad Request). Otherwise the API will return HTTP 200 (OK).

- To GET the physical disks in various RAID controllers::

    GET /nodes/<uuid>/raid/physical_disks

      {
          'physical_disks':
            [
             {
              'controller': 'Smart Array P822 in Slot 2',
              'id': '5I:1:2',
              'disk_type': 'hdd',
              'interface_type': 'sas',
              'size_gb': 600,
              'vendor': 'HP',
              'model': 'EF0600FARNA',
              'firmware_version': 'HPD6',
              'state': 'active',
             },
             {
              'controller': 'Smart Array P822 in Slot 2',
              'id': '5I:1:3',
              'disk_type': 'hdd',
              'interface_type': 'sas',
              'size_gb': 600,
              'vendor': 'HP',
              'model': 'EF0600FARNA',
              'firmware_version': 'HPD6',
              'state': 'active',
             },
             {
              'controller': 'Smart Array P822 in Slot 2',
              'id': '5I:1:4',
              'disk_type': 'hdd',
              'interface_type': 'sas',
              'size_gb': 600,
              'vendor': 'HP',
              'model': 'EF0600FARNA',
              'firmware_version': 'HPD6',
              'state': 'active',
             },
             {
              'controller': 'Smart Array P822 in Slot 2',
              'id': '5I:1:5',
              'disk_type': 'hdd',
              'interface_type': 'sas',
              'size_gb': 600,
              'vendor': 'HP',
              'model': 'EF0600FARNA',
              'firmware_version': 'HPD6',
              'state': 'active',
             },
             {
              'controller': 'Smart Array P822 in Slot 2',
              'id': '5I:1:6',
              'disk_type': 'hdd',
              'interface_type': 'sas',
              'size_gb': 600,
              'vendor': 'HP',
              'model': 'EF0600FARNA',
              'firmware_version': 'HPD6',
              'state': 'active',
             },
             {
              'controller': 'Smart Array P822 in Slot 2',
              'id': '5I:1:7',
              'disk_type': 'hdd',
              'interface_type': 'sas',
              'size_gb': 600,
              'vendor': 'HP',
              'model': 'EF0600FARNA',
              'firmware_version': 'HPD6',
              'state': 'failed',
             },
            ]
          'last_updated': '2013-06-14 23:30:59'
      }

  If the driver doesn't support RAID configuration, then the API will return
  HTTP 400 (Bad Request). Otherwise the API will return HTTP 200 (OK).

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

  If the driver doesn't support RAID configuration, then the API will return
  HTTP 400 (Bad Request). Otherwise the API will return HTTP 200 (OK).

RPC API impact
--------------

Three new RPC APIs will be created. They will have the corresponding methods
defined in the conductor for handling their functionalities.

- ``create_raid_configuration`` - This method will be called in
  ``PUT /nodes/<uuid>/raid/configuration``.

- ``get_raid_configuration`` - This method will be called in
  ``GET /nodes/<uuid>/raid/configuration`` and
  ``GET /nodes/<uuid>/raid/physical_disks``.

- ``get_raid_logical_disk_properties`` - This method will be called in
  ``GET /drivers/<driver>/raid/logical_disk_properties``.

Driver API impact
-----------------

A new ``RAIDInterface`` will be available for the drivers to allow them to
implement RAID configuration.  There will be two methods in the interface:

  - ``create_configuration()`` - The driver implementation of the method
    has to read the request RAID configuration from
    ``node.driver_internal_info.target_raid_configuration`` and
    create to RAID configuration on the bare metal. The driver must
    ensure ``update_raid_info`` is called at the end of the process updating
    the ``current_raid_configuration``. The implementation detail is up to the
    driver depending on the synchronicity/asynchronicity of the operation.

    The ``current_raid_configuration`` will include the following:

    + For each logical disk (on top of the input passed):

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

      def create_configuration(task,
                               create_only_root_volume=False,
                               create_only_nonroot_volumes=False):
          """Create RAID configuration on the node.

          This method creates the RAID configuration as read from
          node.driver_internal_info.target_raid_configuration.  This method
          by default will create all logical disks.

          :param task: TaskManager object containing the node.
          :param create_only_root_volume: This specifies whether to create
              only the root volume.
          :param create_only_nonroot_volumes: This specifies to create only
              non-root volumes.
          """

  - ``delete_configuration`` - To delete the RAID configuration. This
    method doesn't have an input and doesn't return anything.

    The function definition will be as follows::

      def delete_configuration(task):
          """Delete RAID configuration on the node.

          :param task: TaskManager object containing the node.
          """

  - ``validate_configuration`` - To validate a RAID configuration. This is
    called during the ``PUT`` operation in the API.

    The function definition will be as follows::

      def validate_configuration(task, raid_config):
          """Validates the given RAID configuration.

          :param task: TaskManager object containing the node.
          :param raid_config: The RAID configuration to be validated.
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
may call ``update_raid_info`` with the ``current_raid_configuration``. The
details about the method has been described above.


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

RAID configuration may extend the time required for zapping on the nodes, but
this is important for performance and reliability reasons.

Other deployer impact
---------------------

Operator can make use of ``node.raid.create_configuration`` and
``node.raid.delete_configuration`` as zap tasks for doing RAID management.

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

* Root device hints - https://github.com/openstack/ironic-specs/blob/master/specs/kilo/root-device-hints.rst
* Zapping of nodes - https://github.com/openstack/ironic-specs/blob/master/specs/kilo/implement-zapping-states.rst

Testing
=======

* Unit tests will be added for the code.  A fake implementation of the
  ``RAIDInterface`` will be provided for testing purpose and this can be run
  as part of zapping.

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

.. _`root device hint`: https://github.com/openstack/ironic-specs/blob/master/specs/kilo/root-device-hints.rst

Other references:

* New Ironic provisioner state machine: https://github.com/openstack/ironic-specs/blob/master/specs/kilo/new-ironic-state-machine.rst

* Support Zapping of Nodes: https://github.com/openstack/ironic-specs/blob/master/specs/kilo/implement-zapping-states.rst
