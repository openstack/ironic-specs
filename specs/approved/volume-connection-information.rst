..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==================================================
Add volume connection information for Ironic nodes
==================================================

https://bugs.launchpad.net/ironic/+bug/1526231

This RFE introduces the changes in Ironic to support connecting
and booting instances from remote volumes.

Problem description
===================

When user starts bare metal instance with Cinder volume, Nova orchestrates
the communication with Cinder and Ironic. The work flow of the boot process is
as follows:

#. (Preparation) Administrator registers a node with initiator information.

#. User asks Cinder to create a boot volume.

#. User asks Nova to boot a node from the Cinder volume.

#. Nova calls Ironic to collect iSCSI/FC initiator information. Ironic
   collects initiator information and returns it to Nova.

#. Nova calls Cinder to attach the volume to the node. Cinder attaches the
   volume to the node and returns connection information which includes
   target information.

#. Nova passes the target information for the node to Ironic

#. Nova calls Ironic to spawn the instance. Ironic prepares the bare metal
   node to boot from the remote volume which is identified by target
   information and powers on the bare metal node.

In the work flow above, Nova calls Ironic to get/set initiator/target
information (4 and 6) and also administrator calls Ironic to set initiator
information (1) but currently Ironic has neither those information
nor APIs for them.

Proposed change
===============

* Add a new table named ``volume_connectors`` with the below fields:

  + id

    - Integer
    - PrimaryKeyConstraint

  + uuid

    - String(length=36)
    - UniqueConstraint

  + node_id

    - Integer
    - ForeignKeyConstraint('nodes.id')

  + created_at

    - DateTime

  + updated_at

    - DateTime

  + type (can have values "iqn", "ip", "mac", "wwnn", "wwpn", "net-id")

    - String(Length=32)
    - UniqueConstraint(type, connector_id)

  + connector_id

    - String(length=255)
    - UniqueConstraint(type, connector_id)

  + extra

    - Text

  .. note::
    Ironic should allow users to set IP and/or MAC address hardcorded into
    `connector_id` field because we can't put any assumptions on the storage
    network. It might be a Neutron network, or it might be a network that the
    OpenStack part of the deployment doesn't know about at all. It depends on
    deployment.

  .. note::
     `extra` field is text in the database but a dictionary (JSON-encoded
     dict) in the object

* Add a new table named ``volume_targets`` with the below fields:

  + id

    - Integer
    - PrimaryKeyConstraint

  + uuid

    - String(length=36)
    - UniqueConstraint

  + node_id

    - Integer
    - ForeignKeyConstraint('nodes.id')

  + created_at

    - DateTime

  + updated_at

    - DateTime

  + volume_type

    - String(length=64)

  + properties

    - Text

  + boot_index

    - Integer
    - UniqueConstraint(node_id, boot_index)
    - This is used for Ironic to distinguish the root volume. Similar to Nova,
      Ironic assumes volumes with boot index 0 are root device.
      (Nova associates a boot index with each block device and assumes volumes
      with boot index 0 are root volumes.)

  + volume_id

    - String(length=36)

  + extra

    - Text

  .. note::
     Ironic should clear the connected target information on node tear_down,
     just like it does for instance_info.

  .. note::
     `properties` and `extra` are text in the database but a dictionary
     (JSON-encoded dict) in the object

  .. note::
     The contents of the `properties` field depend on volume type. Reference
     information should be added in Bare Metal API document:

     For iSCSI example::

       {"auth_method": "CHAP",
        "auth_username": "XXX",
        "auth_password": "XXX",
        "target_iqn": "iqn.2010-10.com.example:vol-X",
        "target_portal": "192.168.0.123:3260",
        "volume_id": "12345678-...",
        "target_lun": 0,
        "access_mode": "rw",
        "target_discovered": false,
        "encrypted": false,
        "qos_specs": null}

     For iSCSI multipath example::

       {"auth_method": "CHAP",
        "auth_username": "XXX",
        "auth_password": "XXX",
        "target_iqns": ["iqn.2010-10.com.example:vol-X",
        "iqn.2010-10.com.example:vol-Y"],
        "target_portals": ["192.168.0.123:3260",
        "192.168.0.124:3260"],
        "volume_id": "12345678-...",
        "target_luns": [0, 1],
        "access_mode": "rw",
        "target_discovered": false,
        "encrypted": false,
        "qos_specs": null}

     For fibre channel example::

       {"device_path": "/dev/disk/by-path/pci-XXXX",
        "encrypted": false,
        "qos_specs": null,
        "target_lun": 1,
        "access_mode": "rw",
        "target_wwn": ["XXXX"]}

     REST API masks credential information such as `auth_username` and
     `auth_password` in iSCSI and iSCSI multipath examples in order to avoid
     security risk.

* Add REST APIs end points to get/set values on them. For details see REST API
  Impact section.

  + /v1/volume/connectors
  + /v1/volume/targets
  + /v1/nodes/<node_uuid or name>/volume/connectors
  + /v1/nodes/<node_uuid or name>/volume/targets

* Add new capability flags in ``node.properties['capabilities']``. These flags
  show whether or not the node can boot from volume with each backend. If it
  can boot from volume, we should set the flag to true.

  + iscsi_boot
  + fibre_channel_boot

  .. note::
    This should be set to true if the bare metal node supports booting from
    that specific volume.  It might be populated manually by operator or by
    inspection, but that is not in the scope of this spec.

  .. note::
     In the future, Ironic will provide driver capabilities information.
     Nova can use that information to choose appropriate node.

* If a list of targets are specified, it's up to the driver handling the deploy
  to take care of this.  For multi-pathing, Ironic driver, bare metal hardware
  and the operating system should support it.  If Ironic driver and bare metal
  hardware supports it, but instance operating system doesn't understand it,
  then it might lead to failure in booting the instance or corrupting the
  information in the Cinder volume.

* Information which is stored in volume_connector and volume_target tables
  are used in drivers in order to boot the node from volume. Changes for
  reference driver, driver interfaces are described in the spec [4]_.


Alternatives
------------

* Saving connector information in a new node attribute like
  volume_initiator_info. This change has less impact on current code and API
  but proposed one has more benefits such as better integrity check, faster
  query from db and easier to store information related to a particular
  connector.

* Saving target information in a new node attribute like volume_target_info.
  This change has less impact on current code and API but proposed one has
  more benefits such as better integrity check, faster query from db and
  easier to store information related to a particular target.

* Saving target information in instance_info along with other instance related
  information. This seems to be straightforward because basically target
  volume information is related to the instance. In this case,
  ``node.instance_info`` is nested to store target information. This makes it
  difficult for users to manipulate target information, and for a driver to
  validate it. On the other hand, current approach can avoid nesting
  instance_info and so it's easier to use those information. Note, ironic
  clears the target connection information on the node tear_down.

* Not implement storage of target and initiator information, which ultimately
  would not improve user experience and require manual post-deployment
  configuration for out-of-band control. For in-band use, Nova ironic driver
  can manage initiator information and it is proposed by jroll [2]_.

Data model impact
-----------------

* Add new type of object ``VolumeConnector`` in objects/volume_connector.py. It
  inherits IronicObject class. The new object will have the following fields:

  + ``id``
  + ``uuid``
  + ``node_id``
  + ``type``
  + ``connector_id``
  + ``extra``
  + ``created_at`` (defined in IronicObject class)
  + ``updated_at`` (defined in IronicObject class)

* Add new type of object ``VolumeTarget`` in objects/volume_target.py. It
  inherits IronicObject class. The new object will have the following fields:

  + ``id``
  + ``uuid``
  + ``node_id``
  + ``volume_type``
  + ``properties``
  + ``boot_index``
  + ``volume_id``
  + ``extra``
  + ``created_at`` (defined in IronicObject class)
  + ``updated_at`` (defined in IronicObject class)


State Machine Impact
--------------------

None.

REST API impact
---------------

Six new REST API endpoints will be introduced with this change.

- ``/v1/volume/connectors``

  + To set the volume connector (initiator) information::

      POST /v1/volume/connectors

    with the body containing the JSON description of the volume connector.
    It will return 201 on success, 400 if some required attributes are missing
    or having invalid value OR 409 if an entry already exists for the same
    volume connector.

  + To get information about all volume connectors::

      GET /v1/volume/connectors

    This operation will return a list of dictionaries. It contains information
    about all volume connectors::

      {
          "volume_connectors":[
              {
                  "connector_id": "<wwpn>",
                  "links": [ ... ],
                  "type": "wwpn",
                  "uuid": "<uuid>",
              },
              {
                  "connector_id": "<wwpn>",
                  "links": [ ... ],
                  ...
              },
              ...
          ]
      }

    This will return 200 on success

    This operation can take parameters like ``type``, ``container_id``,
    ``limit``, ``marker``, ``sort_dir``, and ``fields``.

  + To get detail information about all volume connectors::

      GET /v1/volume/connectors/detail

    The operation will return a list of dictionaries. It contains detailed
    information about all volume connectors::

      {
          "volume_connectors":[
              {
                  "connector_id": "<wwpn>",
                  "created_at": "<created_date>",
                  "extra": {},
                  "links": [ ... ],
                  "node_uuid": "<node_uuid>",
                  "type": "wwpn",
                  "updated_at": "<updated_date>",
                  "uuid": "<uuid>",
              },
              {
                  "connector_id": "<wwpn>",
                  "created_at": "<created_date>",
                  ...
              },
              ...
          ]
      }

    It will return 200 on success.

    This operation can take parameters like ``type``, ``container_id``,
    ``limit``, ``marker``, and ``sort_dir``.

  + It should be possible to pass ``node`` as a parameter which can be a node
    name or a node UUID to get all volume connectors for that particular node::

      GET /v1/volume/connectors?node=<node_uuid or name>
      GET /v1/volume/connectors/detail?node=<node_uuid or name>

    It will return 200 on success or 404 if the node is not found.

- ``/v1/volume/connectors/<volume_connector_uuid>``

  + To get detail information about a particular volume connector::

      GET /v1/volume/connectors/<volume_connector_uuid>

    This will return 200 on success or 404 if volume connector is not found.

  + To update a particular volume connector::

      PATCH /v1/volume/connectors/<volume_connector_uuid>

    This will return 200 and the representation of the updated resource on
    success and 404 if volume connector is not found.

  .. note::
    Updating connector information when the node is in POWER_ON or REBOOT
    state is blocked. It means that users need to make sure the node is in
    POWER_OFF state before updating connector information. When connector
    information is updated, driver should update node configuration.

  + To delete volume connector::

      DELETE /v1/volume/connectors/<volume_connector_uuid>

    It will return 204 on success or 404 if volume connector is not found or
    400 if the node is not in POWER_OFF state.

- ``/v1/nodes/<node_uuid or name>/volume/connectors``

  + To get all the volume connectors information for a node::

      GET ``/v1/nodes/<node_uuid or name>/volume/connectors``

- ``/v1/volume/targets``

  + To set the volume target information::

      POST /v1/volume/targets

    with the body containing the JSON description of the volume target.
    It will return 201 on success, 400 if some required attributes are missing
    or having invalid value OR 409 if an entry already exists for the same
    volume target.

  + To get information about all volume targets::

      GET /v1/volume/targets

    This operation will return a list of dictionaries. It contains information
    about all volume targets::

      {
          "volume_targets":[
              {
                  "boot_index", "<boot_index>",
                  "links": [ ... ],
                  "uuid": "<uuid>",
                  "volume_id": "<volume_id>"
                  "volume_type": "<volume_target_type>",
              },
              {
                  "boot_index", "<boot_index>",
                  "links": [ ... ],
                  ...
              },
              ...
          ]
      }

    This will return 200 on success.

    This operation can take parameters like ``boot_index``, ``volume_id``,
    ``volume_type``, ``limit``, ``marker``, ``sort_dir``, and ``fields``.

  + To get details information about all volume targets::

      GET /v1/volume/targets/detail

    The operation will return a list of dictionaries. It contains detailed
    information about all volume targets::

      {
          "volume_targets":[
              {
                  "boot_index": "<boot_index>",
                  "created_at": "<created_date>",
                  "extra": {},
                  "links": [ ... ],
                  "node_uuid": "<node_uuid>",
                  "properties" : { "<target_information>" },
                  "updated_at": "<updated_date>",
                  "uuid": "<uuid>",
                  "volume_id": "<volume_id>",
                  "volume_type": "<volume_target_type>",
              },
              {
                  "boot_index": "<boot_index>",
                  "created_at": "<created_date>",
                  ...
              },
              ...
          ]
      }

    It will return 200 on success.

    This operation can take parameters like ``boot_index``, ``volume_id``,
    ``volume_type``, ``limit``, ``marker``, and ``sort_dir``.

    .. Note::
       `properties` may include credential information. This API will
       mask it to avoid security risk.

  + It should be possible to pass ``node`` as a parameter which can be a node
    name or a node UUID to get all volume targets for that particular node::

      GET /v1/volume/targets?node=<node_uuid or name>
      GET /v1/volume/targets/detail?node=<node_uuid or name>

    It will return 200 on success or 404 if the node is not found.

- ``/v1/volume/targets/<volume_target_uuid>``

  + To get detailed information about a particular volume target::

      GET /v1/volume/targets/<volume_target_uuid>

    This will return 200 on success or 404 if volume target is not found.

  + To update a particular volume target::

      PATCH /v1/volume/targets/<volume_target_uuid>

    This will return 200 and the representation of the updated resource on
    success, 404 if volume target is not found or 400 if the node is not
    POWER_OFF state.

  .. note::
     Updating target information when the node is in POWER_ON or REBOOT state
     is blocked. It means that users need to make sure the node is in
     POWER_OFF state before updating target information. When target
     information is updated, driver should update node configuration.

  + To delete volume target::

      DELETE /v1/volume/targets/<volume_target_uuid>

    It will return 204 on success, 404 if volume target is not found or
    400 if the node is not in POWER_OFF state.

- ``/v1/nodes/<node_uuid or name>/volume/targets``

  + To get all the volume targets information for a node::

      GET ``/v1/nodes/<node_uuid or name>/volume/targets``

- ``/v1/nodes/<node_uuid or name>/volume/targets``

  + To get all the volume targets information for a node::

      GET ``/v1/nodes/<node_uuid or name>/volume/targets``

The endpoint ``GET /v1/nodes/detail`` will provide the volume connectors and
targets information for the node with links to them. Also, the endpoint
``GET /v1/nodes/<node_uuid or name>`` will provide the volume connectors and
targets information for the specified node.

For the above REST API changes, micro version will be bumped and 406 will be
raised if newer endpoints are accessed with a lesser micro version.

Client (CLI) impact
-------------------

* A new ``VolumeConnectorManager`` will be added to ``ironicclient`` to get/set
  connector information for the node.  Also the CLI will be modified as
  follows::

    ironic volume-connector-create --node <node> --type <type>
                                   --connector_id <connector_id>
                                   [-e <key=value>] [-u <uuid>]
    ironic volume-connector-delete <uuid> [<uuid>]
    ironic volume-connector-list [--detail] [--type <type>]
                                 [--connector_id <connector_id>]
                                 [--limit <limit>] [--marker <uuid>]
                                 [--sort-key <field>] [--sort-dir <direction>]
                                 [--fields <field> [<field> ...]]
    ironic volume-connector-show [--fields <field> [<field> ...]] <uuid>
    ironic volume-connector-update <uuid> <op> <path=value> [<path=value> ...]

    ironic node-volume-connector-list [--detail] [--limit <limit>]
                                      [--marker <uuid>] [--sort-key <field>]
                                      [--sort-dir <direction>]
                                      [--fields <field> [<field> ...]]
                                      <node>

* A new ``VolumeTargetManager`` will be added to ``ironicclient`` to get/set
  target information for the node.  Also the CLI will be modified as
  follows::

    ironic volume-target-create --node <node> --volume_type <volume_type>
                                --volume_id <volume_id>
                                [--properties <key=value>]
                                [--boot_index <boot_index>]
                                [-e <key=value>] [-u <uuid>]
    ironic volume-target-delete <uuid> [<uuid>]
    ironic volume-target-list [--detail] [--volume_type <volume_type>]
                              [--volume_id <volume_id>]
                              [--boot_index <boot_index>] [--limit <limit>]
                              [--marker <uuid>] [--sort-key <field>]
                              [--sort-dir <direction>]
                              [--fields <field> [<field> ...]]
    ironic volume-target-show [--fields <field> [<field> ...]] <uuid>
    ironic volume-target-update <uuid> <op> <path=value> [<path=value> ...]

    ironic node-volume-target-list [--detail] [--limit <limit>]
                                   [--marker <uuid>] [--sort-key <field>]
                                   [--sort-dir <direction>]
                                   <node>

* New objects, ``CreateBaremetalVolumeConnector``,
  ``DeleteBaremetalVolumeConnector``, ``ListBaremetalVolumeConnector``,
  ``SetBaremetalVolumeConnector``, ``ShowBaremetalVolumeConnector``,
  and ``UnsetBaremetalVolumeConnector`` will be added to ``openstackclient``
  plugin to get/set connector information for the node. Also the CLI will be
  modified as follows::

    openstack baremetal volume connector create [-h]
                                                [-f {json,shell,table,value,yaml}]
                                                [-c COLUMN]
                                                [--max-width <integer>]
                                                [--noindent] [--prefix PREFIX]
                                                --node <node_uuid> --type <type>
                                                --connector_id <connector_id>
                                                [--extra <key=value>]
                                                [--uuid <uuid>]
    openstack baremetal volume connector delete [-h] <connector> [<connector>]
    openstack baremetal volume connector list [-h]
                                              [-f {json,shell,table,value,yaml}]
                                              [-c COLUMN]
                                              [--max-width <integer>]
                                              [--noindent]
                                              [--quote {all,minimal,none,nonnumeric}]
                                              [--limit <limit>]
                                              [--marker <uuid>]
                                              [--sort <key>[:<direction>]]
                                              [--long | fields <field [field] ...>]
    openstack baremetal volume connector set [-h] [--node <node>]
                                             [--type <type>]
                                             [--connector_id <connector_id>]
                                             [--extra <key=value>] <connector>
    openstack baremetal volume connector show [-h]
                                              [-f {json,shell,table,value,yaml}]
                                              [-c COLUMN]
                                              [--max-width <integer>]
                                              [--noindent] [--prefix PREFIX]
                                              [--fields <field> [<field> ...]]
                                              <connector>
    openstack baremetal volume connector unset [-h] [--extra <key>] <connector>

* New objects, ``CreateBaremetalVolumeTarget``,
  ``DeleteBaremetalVolumeTarget``, ``ListBaremetalVolumeTarget``,
  ``SetBaremetalVolumeTarget``, ``ShowBaremetalVolumeTarget``, and
  ``UnsetBaremetalVolumeTarget`` will be added to ``openstackclient`` plugin
  to get/set target information for the node. Also the CLI will be modified
  as follows::


    openstack baremetal volume target create [-h]
                                             [-f {json,shell,table,value,yaml}]
                                             [-c COLUMN] [--max-width <integer>]
                                             [--noindent] [--prefix PREFIX]
                                             --node <node_uuid> --type <type>
                                             --volume_id <volume_id>
                                             [--properties <key=value>]
                                             [--boot_index <boot_index>]
                                             [--extra <key=value>]
                                             [--uuid <uuid>]
    openstack baremetal volume target delete [-h] <target> [<target>]
    openstack baremetal volume target list [-h]
                                           [-f {json,shell,table,value,yaml}]
                                           [-c COLUMN] [--max-width <integer>]
                                           [--noindent]
                                           [--quote {all,minimal,none,nonnumeric}]
                                           [--limit <limit>] [--marker <uuid>]
                                           [--sort <key>[:<direction>]]
                                           [--long | fields <field [field] ...>]
    openstack baremetal volume target set [-h] [--node <node>] [--type <type>]
                                          [--volume_id <volume_id>]
                                          [--properties <key=value>]
                                          [--boot_index <boot_index>]
                                          [--extra <key=value>] <target>
    openstack baremetal volume target show [-h]
                                           [-f {json,shell,table,value,yaml}]
                                           [-c COLUMN] [--max-width <integer>]
                                           [--noindent] [--prefix PREFIX]
                                           [--fields <field> [<field> ...]]
                                           <target>
    openstack baremetal volume target unset [-h]
                                            [--properties <key>]
                                            [--boot_index] [--extra <key>]
                                            <target>

RPC API impact
--------------

Four new rpcapi method ``update_volume_connector``,
``destroy_volume_connector``, ``update_volume_target``, and
``destroy_volume_target`` will be added.

* ``update_volume_connector``

  This method takes context and volume connector object as input and returns
  updated volume connector object.

* ``destroy_volume_connector``

  This method takes context and volume connector object as input.

* ``update_volume_target``

  This method takes context and volume target object as input and returns
  updated volume target object.

* ``destroy_volume_target``

  This method takes context and volume target object as input.

Driver API impact
-----------------

None.

Nova driver impact
------------------

When spawning a new instance, Nova Ironic virt driver queries Ironic
(through API) to find out the volume connector information. It passes the
volume connector information to Cinder which returns the target information.
This is then passed down to Ironic. Detailed information about Nova Ironic
driver can be found in the spec [5]_.

Ramdisk impact
--------------

None

Security impact
---------------

None.

.. note::
   As for FC zoning, Cinder takes care of it [6]_.


Other end user impact
---------------------

None.

Scalability impact
------------------

None.

Performance Impact
------------------

This may extend the time required for nova boot/delete, but it's not a big
impact and it's important for enterprise users.

Other deployer impact
---------------------

* If administrators want to provide boot from volume feature, they need to
  fill out following initiator information before activating the node.

  + iSCSI:

    - ip
    - iqn
    - mac

      .. note::
       ip may be omitted when Neutron is used to manage the storage network.


  + FC:

    - wwnn
    - wwpn

  Administrators need to set the node.properties['capabilities']
  (iscsi_boot and/or fibre_channel_boot) true.

  It's better if inspection automatically collects and registers them.
  For example, in the case of a node with FC-HBA, inspection(in-band) can
  get wwnn and wwpn from sysfs like following::

    # cat /sys/class/scsi_host/host*/device/fc_host/host*/node_name
    # cat /sys/class/scsi_host/host*/device/fc_host/host*/port_name

* If users want to boot a node from volume in Ironic standalone mode, they
  need additional tooling to leverage this functionality. For example, that
  tool needs to do something like:

  - Get initiator information from Ironic
  - Call the storage management tool with initiator information to create a
    new volume (maybe from template) and attach it to the initiator
  - Get target information from storage management tool
  - Put target information into Ironic

Developer impact
----------------

Driver developers can consume the information mentioned above to write
boot from volume support in their driver. The details about reference driver
and driver interface specs are described in [4].

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  satoru-moriya-br

Other contributors:
  rameshg87

Work Items
----------

* Create new table named volume_connectors and volume_targets
* Create new DB API methods
* Create new Object named VolumeConnector and VolumeTarget
* Create new RPC API methods
* Create new REST API endpoints
* Document the changes
* Enhance inspector to register connector information if available
* Enhance Client(CLI) to get/set connector and target information
* Enhance Nova-Ironic driver to support boot from volume with these APIs

Dependencies
============

None

Testing
=======

* Unit tests will be added/updated to cover the changes.

* Tempest tests will be added to Ironic to ensure that the following newly
  added API endpoints work correctly.

Upgrades and Backwards Compatibility
====================================

Add a migration script for database.

Documentation Impact
====================

Documentations such as Installation guide and api-ref will be updated to
explain the newly added fields and end points.

* Installation guide:

  http://docs.openstack.org/developer/ironic/deploy/install-guide.html

* api-ref documentation:

  http://developer.openstack.org/api-ref/baremetal/index.html

References
==========

.. [2] https://review.opendev.org/#/c/184652/
.. [4] https://review.opendev.org/#/c/294995
.. [5] https://review.opendev.org/#/c/211101/
.. [6] http://docs.openstack.org/mitaka/config-reference/block-storage/fc-zoning.html
