..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==================================================
Ironic Neutron Integration
==================================================

https://bugs.launchpad.net/ironic/+bug/1526403
https://bugs.launchpad.net/ironic/+bug/1618754

The current Ironic implementation only supports flat networks. For isolation
of tenant networks Ironic should be able to pass information to Neutron to
allow for provisioning of the baremetal server onto the tenant network.


Problem description
===================

Ironic currently provisions servers only on flat networks hence providing no
network isolation between tenants. Ironic should allow end users to utilize
a baremetal instance in the same isolated (e.g. VLAN, VXLAN) networks as
their virtual machines are.

In order to provide the required network isolation, Ironic should be able to
provide the requisite connectivity information (using LLDP) to the Neutron
ML2 plugin to allow drivers to provision the top-of-rack (ToR) switch for the
baremetal server.

Ironic also poses new challenges for Neutron, for example, the concepts of
link aggregation and multiple networks per node. This spec covers the concept
of link aggregation where multiple interfaces on the bare metal server connect
to switch ports of a single LAG and belong to the same network. However,this
spec does not cover:

* the case of trunked ports belonging to multiple networks - this will need a
  separate spec and implementation in Neutron, see `vlan-aware-vms
  <https://blueprints.launchpad.net/neutron/+spec/vlan-aware-vms>`_.

* the case where the bare metal server has multiple interfaces that belong to
  different networks.  This may require the capability to specify which NICs
  belong to which network. It is in scope but the method of deciding which
  interface gets which network will be decided elsewhere.

Proposed change
===============

When nodes are enrolled/introspected in Ironic, local link (e.g. LLDP)
information should be recorded for each port. The option
of creating a portgroup to specify an aggregation of said ports should be
made available.

Ironic should then send the local link information to Neutron in the form of a
port binding profile. For each portgroup, the port binding profile will
contain a list of the local link information for each port in that portgroup.
For each port not belonging to a portgroup, the port binding profile will
contain only the local link information for that particular port. Therefore
the length of the list of local link information can be used by Neutron to
determine whether to plumb the network for a single port or for a portgroup
(in the case of a portgroup there may be additional switch configurations
necessary to manage the associated LAG).  Each port binding profile sent to
the Neutron port create API will result in the creation of a single Neutron
port. In this way, each portgroup can represent a LAG for which all member
switch ports will belong to the same network and to the same network segment.

The node should first be placed on a provisioning network and then onto the
tenant network as specified in the network-provider spec [1]_. To help
facilitate this there will be a variable stored in the binding profile to
record whether a port binding has been requested. This will allow Ironic to
defer binding until Ironic is able to populate the extra information that is
required by Neutron.

Note also, there will be no support for PXE booting after deploy (i.e. local
disk installation only). The reason for this is because the nodes will not be
able to PXE boot if they cannot reach the TFTP server. Local boot will
need to be used for any node deployed outside of the provisioning network.
Instance netboot should not be permitted when this feature is used. This
limitation could be addressed if routing was set up from every tenant network
to the TFTP server or if Ironic would work with a TFTP server per tenant
network, but these options are out of scope in this spec.

.. note::
  It may be possible for virtual media drivers to support both netboot and
  localboot when provisioning/tenant networks are isolated.  This is because
  virtual media drivers boot the bare metal using out of band means using BMC
  and hence bare metal server's NICs don't require to access Ironic conductor
  when booting the instance.


A supportive ML2 driver can then use the information supplied to provision the
port.

The Ironic port object will be updated with a new local_link_connection field
dict supplying the following values:

* switch_id
* port_id
* switch_info

These fields are in string format. The information could be gathered by using
LLDP based on the LLDP TLV counterparts of chassis_id, port_id and
system_name, although it is not strictly required to populate these fields
with LLDP values. For example, the switch_id field is used to identify a
switch and could be an LLDP based MAC address or an OpenFlow based
datapath_id. The switch_info field could be used to distinguish different
switch models or some other vendor specific identifier. The switch_id and
port_id fields are required and the switch_info field can be optionally
populated.  The key point is that Ironic and Neutron should share the same
understanding of this information in order to connect the Ironic instance to
the appropriate Neutron network.

To facilitate link aggregation a new portgroup object will be created. In
addition to the base object it will have the following fields:

* id
* uuid
* name
* node_id
* address
* mode
* properties
* extra
* internal_info
* standalone_ports_supported

The ``address`` field represents the MAC address for bonded NICs of the bare
metal server. It is optional, as its value is highly dependent on the instance
OS. In case of using ironic through nova, the ``address`` gets populated by
whatever value is generated by neutron for the VIF's address representing this
portgroup, if there is one. This happens during every VIF attach call.
In case of standalone mode, it can be always ``None``, as it should be
configured on the instance through the configdrive.

The ``mode`` field is used to specify the bond mode. If not provided in the
portgroup creation request, its default value is determined by the
``[DEFAULT]default_portgroup_mode`` configuration option, which in turn has a
default value of ``active-backup``. For a portgroup that was created in an
older API version, this configuration value will be used as the value for that
portgroup's mode. ``active-backup`` is chosen as the default because this mode
does not require any additional configuration on the switch side.

The ``properties`` field is a dictionary that can contain any parameters
needed to configure the portgroup.

For additional information about ``mode`` and ``properties`` fields' contents,
see `linux kernel bonding documentation <https://www.kernel.org/doc/Documentation/networking/bonding.txt>`_.

The ``extra`` field can be used to hold any additional information
that operators or developers want to store in the portgroup.

The ``internal_info`` field is used to store internal metadata. This field is
read-only.

The ``standalone_ports_supported`` indicates whether ports that are members of
this portgroup can be used as stand-alone ports.

The Ironic port object will then have the following fields added to support
new functionality:

* local_link_connection
* portgroup_id
* pxe_enabled

If there are multiple pxe_enabled ports or portgroups, dhcpboot options
will be set for all portgroups and all pxe_enabled ports not belonging to any
portgroup.


The following port binding related information needs to be passed to Neutron:

+------------------------+--------------------------------------------------+
| Field Name             | Description                                      |
+========================+==================================================+
| vnic_type              | Type of the profile ('baremetal' in this case).  |
|                        | This would allow at least basic filtering for    |
|                        | Ironic ports by ML2 drivers.                     |
+------------------------+--------------------------------------------------+
| local_link_information | A list of local link connection information      |
|                        | either from all Ironic ports in a particular     |
|                        | portgroup or from a single Ironic port not       |
|                        | belonging to any portgroup.                      |
+------------------------+--------------------------------------------------+
| host_id                | This should be set to the Ironic node uuid.      |
+------------------------+--------------------------------------------------+

A JSON example to describe the structure is::

 {
   "port": {
     <all other fields>,
     "vnic_type": "baremetal",
     "host_id": <Ironic node UUID>,
     "binding:profile": {
       "local_link_information": [
         {
           "switch_id": xxx,
           "port_id": xxx,
           "switch_info": zzz,
           <optional more information>
         },
         {
           "switch_id": xxx,
           "port_id": yyy,
           "switch_info": zzz,
           <optional more information>
         }
       ]
       <some more profile fields>
     }
   }
 }



Alternatives
------------

The current model of prescribing flat networks could be maintained with the
same flat network being used for everything.  This is not so much an
alternative to the proposal in this spec, but rather staying with the existing
solution.



Data model impact
-----------------

The proposed change will be to add the following fields to the port object
with their data type and default value for migrations:

+-----------------------+--------------+-----------------+
| Field Name            | Field Type   | Migration Value |
+=======================+==============+=================+
| local_link_connection | dict_or_none | None            |
+-----------------------+--------------+-----------------+
| portgroup_id          | int_or_none  | None            |
+-----------------------+--------------+-----------------+
| pxe_enabled           | bool         | True            |
+-----------------------+--------------+-----------------+

All existing ports will have ``pxe_enabled`` set to ``true`` so that the
current behavior is not changed. The portgroup relationship is a 1:n
relationship with the port.

The portgroup object is proposed with the following fields and data types:

+----------------------------+-------------------------+
| Field Name                 | Field Type              |
+============================+=========================+
| id                         | int                     |
+----------------------------+-------------------------+
| uuid                       | str                     |
+----------------------------+-------------------------+
| name                       | str_or_none             |
+----------------------------+-------------------------+
| node_id                    | int_or_none             |
+----------------------------+-------------------------+
| address                    | str_or_none             |
+----------------------------+-------------------------+
| mode                       | str_or_none             |
+----------------------------+-------------------------+
| properties                 | dict_or_none            |
+----------------------------+-------------------------+
| extra                      | dict_or_none            |
+----------------------------+-------------------------+
| internal_info              | dict_or_none            |
+----------------------------+-------------------------+
| standalone_ports_supported | bool                    |
+----------------------------+-------------------------+
| created_at                 | datetime_or_str_or_none |
+----------------------------+-------------------------+
| updated_at                 | datetime_or_str_or_none |
+----------------------------+-------------------------+

.. note::
  While ``mode`` attribute of the portgroup object has type str_or_none, its
  value can not be ``None``, unless the database was changed manually. It
  gets populated either during the database migration, or during portgroup
  creation (if not specified explicitly). In both cases it is set to the
  ``[DEFAULT]default_portgroup_mode`` configuration option value.

State Machine Impact
--------------------

The state machine will not be directly impacted, however, changes to the new
portgroup object and additions of portgroups will only be allowed when a
node is in a particular set of states.

Change to port membership of a portgroup can be made when the node
is in a MANAGEABLE/INSPECTING/ENROLL state.  Any port updates that update
local_link_connection or pxe_enabled can only be made when the node is in
a MANAGEABLE/INSPECTING/ENROLL state. The reason for limiting to these states
is because updating these new port attributes should result in an update of
local_link_information in the binding_profile, which would trigger an update
in Neutron. It might be safest to only allow this when the node is not in a
state where uninterrupted connectivity is expected. These limitations will
also ensure that Neutron port updates should only happen during a state
change and not automatically with any port-update call.

REST API impact
---------------

The following port API methods will be affected:

* ``/v1/ports``

  * Retrieve a list of ports.

  * Method type GET.

  * The http response code(s) are unchanged.
    An additional reason for the 404 error http response code would be if the
    portgroup resource is specified but is not found.

  * New parameter can be included:

      * ``portgroup (uuid_or_name)`` - UUID or logical name
        of a portgroup to only get ports for that portgroup.

  * Body:

      * None

  * Response:

      * JSON schema definition of Port


* ``/v1/ports/(port_uuid)``

  * Retrieve information about the given port.

  * Method type GET.

  * The http response code(s) are unchanged.

  * Parameter:

      * ``port_uuid (uuid)`` - UUID of the port.

  * Body:

      * None

  * Response:

      * JSON schema definition of Port



* ``/v1/ports``

  * Create a new port.

  * Method type POST.

  * The http response code(s) are unchanged.

  * Parameter:

      * None

  * Body:

      * JSON schema definition of Port

  * Response:

      * JSON schema definition of Port


* ``/v1/ports/(port_uuid)``

  * Update an existing port.

  * Method type PATCH.

  * The http response code(s) are unchanged.

  * Parameter:

      * ``port_uuid (uuid)`` - UUID of the port.

  * Body:

      * JSON schema definition of PortPatch

  * Response:

      * JSON schema definition of Port


* JSON schema definition of Port (data sample):

::

  {
    "address": "fe:54:00:77:07:d9",
    "created_at": "2015-05-12T10:00:00.529243+00:00",
    "extra": {
      "foo": "bar",
    },
    "links": [
      {
        "href": "http://localhost:6385/v1/ports/
         1004e542-2f9f-4d9b-b8b9-5b719fa6613f",
        "rel": "self"
      },
      {
        "href": "http://localhost:6385/ports/
         1004e542-2f9f-4d9b-b8b9-5b719fa6613f",
        "rel": "bookmark"
      }
    ],
    "node_uuid": "e7a6f1e2-7176-4fe8-b8e9-ed71c77d74dd",
    "updated_at": "2015-05-15T09:04:12.011844+00:00",
    "uuid": "1004e542-2f9f-4d9b-b8b9-5b719fa6613f",
    "local_link_connection": {
      "swwitch_id": "0a:1b:2c:3d:4e:5f",
      "port_id": "Ethernet3/1",
      "switch_info": "switch1",
    },
    "portgroup_uuid": "6eb02b44-18a3-4659-8c0b-8d2802581ae4",
    "pxe_enabled": true
  }


* JSON schema definition of PortPatch would be a subset of JSON schema of
  Port.


The following API methods will be added in support of the new portgroup
model:

* ``/v1/portgroups``

  * Retrieve a list of portgroups.

  * Method type GET.

  * Normal http response code will be 200.

  * Expected error http response code(s):

      * 400 for bad query or malformed syntax (e.g. if address is not
        mac-address format)
      * 404 for resource (e.g. node) not found

  * Parameters:

       * ``node (uuid_or_name)`` - UUID or name of a node, to only get
         portgroups for that node.

       * ``address (macaddress)`` - MAC address of a portgroup, to only
         get portgroup which has this MAC address.

       * ``marker (uuid)`` - pagination marker for large data sets.

       * ``limit (int)`` - maximum number of resources to return in a single
         result.

       * ``sort_key (unicode)`` - column to sort results by. Default: id.

       * ``sort_dir (unicode)`` - direction to sort. "asc" or "desc".
         Default: asc.

  * Body:

      * None

  * Response:

      * JSON schema definition of PortgroupCollection


* ``/v1/portgroups/(portgroup_ident)``

  * Retrieve information about the given portgroup.

  * Method type GET.

  * Normal http response code will be 200.

  * Expected error http response code(s):

      * 400 for bad query or malformed syntax
      * 404 for resource (e.g. portgroup) not found

  * Parameters:

      * ``portgroup_ident (uuid_or_name)`` - UUID or logical name of a
        portgroup.

  * Body:

      * None

  * Response:

      * JSON schema definition of Portgroup


* ``/v1/portgroups``

  * Create a new portgroup.

  * Method type POST.

  * Normal http response code will be 201.

  * Expected error http response code(s):

      * 400 for bad query or malformed syntax
      * 409 for resource conflict (e.g. if portgroup name already exists
        because the name should be unique)

  * Parameters:

      * None

  * Body:

      * JSON schema definition of Portgroup

  * Response:

      * JSON schema definition of Portgroup


* ``/v1/portgroups/(portgroup_ident)``

  * Delete a portgroup.

  * Method type DELETE.

  * Normal http response code will be 204.

  * Expected error http response code(s):

      * 400 for bad query or malformed syntax
      * 404 for resource (e.g. portgroup) not found

  * Parameters:

      * ``portgroup_ident (uuid_or_name)`` - UUID or logical name of a
        portgroup.

  * Body:

      * None

  * Response:

      * N/A


* ``/v1/portgroups/(portgroup_ident)``

  * Update an existing portgroup.

  * Method type PATCH.

  * Normal http response code will be 200.

  * Expected error http response code(s):

      * 400 for bad query or malformed syntax
      * 404 for resource (e.g. portgroup) not found
      * 409 for resource conflict (e.g. if portgroup name already exists
        because the name should be unique)

  * Parameters:

      * ``portgroup_ident (uuid_or_name)`` - UUID or logical name of a
        portgroup.

  * Body:

      * JSON schema definition of PortgroupPatch

  * Response:

      * JSON schema definition of Portgroup


* ``/v1/portgroups/detail``

  * Retrieve a list of portgroups with detail.
    The additional 'detail' option would return all fields, whereas
    without it only a subset of fields would be returned, namely uuid and
    address.

  * Method type GET.

  * Normal http response code will be 200.

  * Expected error http response code(s):

      * 400 for bad query or malformed syntax
      * 404 for resource (e.g. node) not found

  * Parameters:

       * ``node (uuid_or_name)`` - UUID or name of a node, to only get
         portgroups for that node.

       * ``address (macaddress)`` - MAC address of a portgroup, to only
         get portgroup which has this MAC address.

       * ``marker (uuid)`` - pagination marker for large data sets.

       * ``limit (int)`` - maximum number of resources to return in a single
         result.

       * ``sort_key (unicode)`` - column to sort results by. Default: id.

       * ``sort_dir (unicode)`` - direction to sort. "asc" or "desc".
         Default: asc.

  * Body:

      * None

  * Response:

      * JSON schema definition of PortgroupCollection with detail.


* ``/v1/nodes/(node_ident)/portgroups``

  * Retrieve a list of portgroups for node.

  * Method type GET.

  * Normal http response code will be 200.

  * Expected error http response code(s):

      * 400 for bad query or malformed syntax
      * 404 for resource (e.g. node) not found

  * Parameters:

      * ``node_ident (uuid_or_name)`` - UUID or logical name of a
        node.

  * Body:

      * None

  * Response:

      * JSON schema definition of PortgroupCollection.

* ``/v1/nodes/(node_ident)/portgroups/detail``

  * Retrieve a list of portgroups with detail for node.

  * Method type GET.

  * Normal http response code will be 200.

  * Expected error http response code(s):

      * 400 for bad query or malformed syntax
      * 404 for resource (e.g. node) not found

  * Parameters:

      * ``node_ident (uuid_or_name)`` - UUID or logical name of a
        node.

  * Body:

      * None

  * Response:

      * JSON schema definition of PortgroupCollection with detail.

* ``/v1/portgroups/(portgroup_ident)/ports``

  * Retrieve a list of ports for portgroup.

  * Method type GET.

  * Normal http response code will be 200.

  * Expected error http response code(s):

      * 400 for bad query or malformed syntax
      * 404 for resource (e.g. portgroup) not found

  * Parameters:

      * ``portgroup_ident (uuid_or_name)`` - UUID or logical name of a
        portgroup.

  * Body:

      * None

  * Response:

      * JSON schema definition of PortCollection.

* ``/v1/portgroups/(portgroup_ident)/ports/detail``

  * Retrieve a list of ports with detail for portgroup.

  * Method type GET.

  * Normal http response code will be 200.

  * Expected error http response code(s):

      * 400 for bad query or malformed syntax
      * 404 for resource (e.g. portgroup) not found

  * Parameters:

      * ``portgroup_ident (uuid_or_name)`` - UUID or logical name of a
        portgroup.

  * Body:

      * None

  * Response:

      * JSON schema definition of PortCollection with detail.

* JSON schema definition of Portgroup (data sample):

::

  {
    "address": "fe:54:00:77:07:d9",
    "created_at": "2015-05-12T10:10:00.529243+00:00",
    "extra": {
      "foo": "bar",
    },
    "internal_info": {},
    "links": [
      {
        "href": "http://localhost:6385/v1/portgroups/
        6eb02b44-18a3-4659-8c0b-8d2802581ae4",
        "rel": "self"
      },
      {
        "href": "http://localhost:6385/portgroups/
        6eb02b44-18a3-4659-8c0b-8d2802581ae4",
        "rel": "bookmark"
      }
    ],
    "mode": "802.3ad",
    "name": "node1_portgroup1",
    "node_uuid": "e7a6f1e2-7176-4fe8-b8e9-ed71c77d74dd",
    "ports": [
      {
        "href": "http://127.0.0.1:6385/v1/portgroups/
        6eb02b44-18a3-4659-8c0b-8d2802581ae4/ports",
        "rel": "self"
      },
      {
        "href": "http://127.0.0.1:6385/portgroups/
        6eb02b44-18a3-4659-8c0b-8d2802581ae4/ports",
        "rel": "bookmark"
      }
    ],
    "properties": {
      "bond_xmit_hash_policy": "layer3+4",
      "bond_miimon": 100
    },
    "standalone_ports_supported": true,
    "updated_at": "2015-05-15T09:04:12.011844+00:00",
    "uuid": "6eb02b44-18a3-4659-8c0b-8d2802581ae4"
  }

* JSON schema definition of PortgroupCollection:

::

  {
    "portgroups": [
        {
            "address": "fe:54:00:77:07:d9",
            "links": [
                {
                    "href": "http://localhost:6385/v1/portgroups/
                    6eb02b44-18a3-4659-8c0b-8d2802581ae4",
                    "rel": "self"
                },
                {
                    "href": "http://localhost:6385/portgroups/
                    6eb02b44-18a3-4659-8c0b-8d2802581ae4",
                    "rel": "bookmark"
                }
            ],
            "name": "node1_portgroup1",
            "uuid": "6eb02b44-18a3-4659-8c0b-8d2802581ae4"
        }
    ]
  }

* JSON schema definition of PortgroupCollection with detail:

::

  {
    "portgroups": [
      {
        "address": "fe:54:00:77:07:d9",
        "created_at": "2016-08-18T22:28:48.165105+00:00",
        "extra": {},
        "internal_info": {},
        "links": [
          {
            "href": "http://127.0.0.1:6385/v1/portgroups/
            6eb02b44-18a3-4659-8c0b-8d2802581ae4",
            "rel": "self"
          },
          {
            "href": "http://127.0.0.1:6385/portgroups/
            6eb02b44-18a3-4659-8c0b-8d2802581ae4",
            "rel": "bookmark"
          }
        ],
        "mode": "802.3ad",
        "name": "node1_portgroup1",
        "node_uuid": "e7a6f1e2-7176-4fe8-b8e9-ed71c77d74dd",
        "ports": [
          {
            "href": "http://127.0.0.1:6385/v1/portgroups/
            6eb02b44-18a3-4659-8c0b-8d2802581ae4/ports",
            "rel": "self"
          },
          {
            "href": "http://127.0.0.1:6385/portgroups/
            6eb02b44-18a3-4659-8c0b-8d2802581ae4/ports",
            "rel": "bookmark"
          }
        ],
        "properties": {
          "bond_xmit_hash_policy": "layer3+4",
          "bond_miimon": 100
        },
        "standalone_ports_supported": true,
        "updated_at": "2016-11-04T17:46:09+00:00",
        "uuid": "6eb02b44-18a3-4659-8c0b-8d2802581ae4"
      }
    ]
  }

* JSON schema definition of PortgroupPatch would be a subset of JSON schema
  of Portgroup.


Does the API microversion need to increment?

*  Yes.

Example use case including typical API samples for both data supplied
by the caller and the response.

*  Example of port create.

     * Data supplied:

     ::

        {
          "address": "fe:54:00:77:07:d9",
          "node_uuid": "e7a6f1e2-7176-4fe8-b8e9-ed71c77d74dd",
          "local_link_connection": {
            "switch_id": "0a:1b:2c:3d:4e:5f",
            "port_id": "Ethernet3/1",
            "switch_info": "switch1",
            },
          "pxe_enabled": true
        }

     * Response 201 with body:

     ::

        {
          "address": "fe:54:00:77:07:d9",
          "node_uuid": "e7a6f1e2-7176-4fe8-b8e9-ed71c77d74dd",
          "local_link_connection": {
            "switch_id": "0a:1b:2c:3d:4e:5f",
            "port_id": "Ethernet3/1",
            "switch_info": "switch1",
            },
          "pxe_enabled": true
          "created_at": "2015-05-12T10:00:00.529243+00:00",
          "extra": {
          },
          "links": [
            {
              "href": "http://localhost:6385/v1/ports/
               1004e542-2f9f-4d9b-b8b9-5b719fa6613f",
              "rel": "self"
            },
            {
              "href": "http://localhost:6385/ports/
               1004e542-2f9f-4d9b-b8b9-5b719fa6613f",
              "rel": "bookmark"
            }
          ],
          "updated_at": null,
          "uuid": "1004e542-2f9f-4d9b-b8b9-5b719fa6613f",
          "portgroup_uuid": null,
        }

*  Example of portgroup create.

     * Data supplied:

     ::

        {
          "address": "fe:54:00:77:07:d9",
          "node_uuid": "e7a6f1e2-7176-4fe8-b8e9-ed71c77d74dd",
          "standalone_ports_supported": true,
          "name": "node1_portgroup1"
        }

     * Response 201 with body:

     ::

        {
          "address": "fe:54:00:77:07:d9",
          "node_uuid": "e7a6f1e2-7176-4fe8-b8e9-ed71c77d74dd",
          "name": "node1_portgroup1"
          "created_at": "2015-05-12T10:10:00.529243+00:00",
          "extra": {
          },
          "internal_info": {},
          "links": [
            {
              "href": "http://localhost:6385/v1/portgroups/
               6eb02b44-18a3-4659-8c0b-8d2802581ae4",
              "rel": "self"
            },
            {
              "href": "http://localhost:6385/portgroups/
               6eb02b44-18a3-4659-8c0b-8d2802581ae4",
              "rel": "bookmark"
            }
          ],
          "mode": null,
          "ports": [
            {
              "href": "http://127.0.0.1:6385/v1/portgroups/
              6eb02b44-18a3-4659-8c0b-8d2802581ae4/ports",
              "rel": "self"
            },
            {
              "href": "http://127.0.0.1:6385/portgroups/
              6eb02b44-18a3-4659-8c0b-8d2802581ae4/ports",
              "rel": "bookmark"
            }
          ],
          "properties": {},
          "standalone_ports_supported": true,
          "updated_at": null,
          "uuid": "6eb02b44-18a3-4659-8c0b-8d2802581ae4",
        }

*  Example of port update.

     * Parameter "port_uuid"="1004e542-2f9f-4d9b-b8b9-5b719fa6613f"

     * Data supplied (JSON PATCH syntax where "op" can be add/replace/delete):

     ::

        [{"path": "/portgroup_uuid", "value":
          "6eb02b44-18a3-4659-8c0b-8d2802581ae4", "op": "add"}]

     * Response 200 with body:

     ::

        {
          "address": "fe:54:00:77:07:d9",
          "node_uuid": "e7a6f1e2-7176-4fe8-b8e9-ed71c77d74dd",
          "local_link_connection": {
            "switch_id": "0a:1b:2c:3d:4e:5f",
            "port_id": "Ethernet3/1",
            "switch_info": "switch1",
            },
          "pxe_enabled": true
          "created_at": "2015-05-12T10:00:00.529243+00:00",
          "extra": {
          },
          "links": [
            {
              "href": "http://localhost:6385/v1/ports/
               1004e542-2f9f-4d9b-b8b9-5b719fa6613f",
              "rel": "self"
            },
            {
              "href": "http://localhost:6385/ports/
               1004e542-2f9f-4d9b-b8b9-5b719fa6613f",
              "rel": "bookmark"
            }
          ],
          "updated_at": "2015-05-12T10:20:00.529243+00:00",
          "uuid": "1004e542-2f9f-4d9b-b8b9-5b719fa6613f",
          "portgroup_uuid": "6eb02b44-18a3-4659-8c0b-8d2802581ae4",
        }

     * Note that the port update API should support updating the portgroup_id
       of the port object.
       This will allow operators to migrate existing deployments.

*  Example of port list.

     * Parameter "node_uuid"="e7a6f1e2-7176-4fe8-b8e9-ed71c77d74dd"

     * Response 200 with body:

     ::

        {"ports": [
          {
          "address": "fe:54:00:77:07:d9",
          "links": [
            {
              "href": "http://localhost:6385/v1/ports/
               1004e542-2f9f-4d9b-b8b9-5b719fa6613f",
              "rel": "self"
            },
            {
              "href": "http://localhost:6385/ports/
               1004e542-2f9f-4d9b-b8b9-5b719fa6613f",
              "rel": "bookmark"
            }
          ],
          "uuid": "1004e542-2f9f-4d9b-b8b9-5b719fa6613f",
          "portgroup_uuid": "6eb02b44-18a3-4659-8c0b-8d2802581ae4",
          }
        ]}

     * Note that portgroup_uuid is now returned in the response.


Discuss any policy changes, and discuss what things a deployer needs to
think about when defining their policy.

* Ironic has an admin-only policy so policy definitions should not be a
  concern.

* A deployer should be aware of the capabilities of the particular ML2 driver
  for supporting use of the new local_link_information that will be passed to
  it via the binding_profile.

Is a corresponding change in the client library and CLI necessary?

*  The client library and CLI should be updated to support the new APIs.

Is this change discoverable by clients? Not all clients will upgrade at the
same time, so this change must work with older clients without breaking them.

*  The changes to the API will be backward-compatible so older clients will
   still continue to work as-is.

Client (CLI) impact
-------------------

The python-ironicclient and OSC would need updated to support the new
portgroups APIs.

In the commands below, ``<portgroup>`` means that this placeholder can contain
both portgroup UUID or name. ``<portgroup_uuid>`` can contain only portgroup
UUID.

Example usage of the new methods:

  * For ports, the CLI would support port creation with new optional
    parameters specifying the new port attributes (local_link_connection,
    portgroup_id and pxe_enabled) and would also support update of these
    attributes. As examples:

    "ironic" CLI:

        * ironic port-create -a <address> -n <node> [-e <key=value>]
          [--local-link-connection <key=value>]
          [--portgroup <portgroup>] [--pxe-enabled <boolean>]

        * ironic port-update <port_uuid> add portgroup_uuid=<portgroup_uuid>
          --local-link-connection <key=value> --pxe-enabled <boolean>

    "openstack baremetal" CLI:

        * openstack baremetal port create --node <node>
          [--local-link-connection <key=value>] [--port-group <portgroup>]
          [--pxe-enabled <boolean>] <address>

        * openstack baremetal port set [--port-group <portgroup>]
          [--local-link-connection <key=value>] [--pxe-enabled <boolean>]
          <port>

        * openstack baremetal port list [--address <mac-address>]
          [--node <node> | --port-group <portgroup>]


  * For portgroups, the CLI would support the following new methods:

    "ironic" CLI:

        * ironic portgroup-create --node <node> [--address <mac-address>]
          [--name <portgroupname>] [-e <key=value>]
          [--standalone-ports-supported <boolean>] [-m <mode>]
          [-p <key=value>]

        * ironic portgroup-delete <portgroup> [<portgroup> ...]

        * ironic portgroup-list [--detail | --fields <field> [<field> ...]]
          [--node <node>] [--address <mac-address>] [--limit <limit>]
          [--marker <portgroup_uuid>] [--sort-key <field>]
          [--sort-dir <direction>]

        * ironic portgroup-port-list
          [--detail | --fields <field> [<field> ...]]
          [--limit <limit>] [--marker <portgroup_uuid>] [--sort-key <field>]
          [--sort-dir <direction>] <portgroup>

        * ironic portgroup-show [--address] [--fields <field> [<field> ...]]
          <id>

            * <id> is the UUID or name of the portgroup (or MAC address if
              --address is specified)

        * ironic portgroup-update <portgroup> <op> <path=value>
          [<path=value> ... ]

            * <op> is add, remove or replace.

            * <path=value> is the attribute to add, remove or replace. Can be
              specified multiple times. For 'remove' only <path> is necessary.

        * Note: Even though the ironic CLI includes 'ironic node-port-list',
          we are NOT going to provide a corresponding
          'ironic node-portgroup-list'. Rather, the list of portgroups
          of a node will be available via ironic portgroup-list --node.

    "openstack baremetal" CLI:

        * openstack baremetal port group create --node <uuid> [--name <name>]
          [--extra <key=value>]
          [--support-standalone-ports | --unsupport-standalone-ports]
          [--mode <mode>] [--properties <key=value>]
          [--address <mac-address>]

        * openstack baremetal port group delete <portgroup> [<portgroup> ...]

        * openstack baremetal port group list [--marker <portgroup>]
          [--address <mac-address>] [--node <node>]
          [--sort <key>[:<direction>]]
          [--long | --fields <field> [<field> ...]]

        * openstack baremetal port group show [--address]
          [--fields <field> [<field> ...]] <id>

          * <id> is the UUID or name of the portgroup (or MAC address if
            --address is specified)

        * openstack baremetal port group set [--address <mac-address>]
          [--name <name>] [--node <node>] [--extra <key=value>]
          [--support-standalone-ports | --unsupport-standalone-ports]
          [--mode <mode>] [--properties <key=value>]
          <portgroup>

        * openstack baremetal port group unset [--address] [--name]
          [--extra <key>] [--properties key] <portgroup>


    * To add ports to a portgroup, the portgroup should first
      be created and then port_update or port create called.

The python-ironicclient would also need the Port detailed resource extended
to include the new port attributes.

RPC API impact
--------------

No impact on existing API calls.

New RPC API calls would be needed:

  * update_portgroup
  * destroy_portgroup

These new API calls will use call(). As for the existing API call for
update_port, the new API call for update_portgroup should request an update
for DHCP if the address field is updated.


To roll this change out to an existing deployment, the ironic-conductor should
be upgraded before the ironic-api.


Driver API impact
-----------------

The NeutronDHCPApi class in ``ironic/dhcp/neutron`` updates Neutron ports
with DHCP options.  The vifs are obtained in ``ironic/common/network`` by
extracting ``vif_port_id`` from the ``extra`` attributes of Ironic ports.
This method should be updated if vifs are bound to portgroups as well as
ports.

The complementary network-provider spec [1]_ provides
details regarding the workflow of the network flip and the point at which
the binding profile will be passed to Neutron to bind the port.



Nova driver impact
------------------

As this work depends on the attach/detach interface work [2]_, the only thing
that needs to be changed to fully support portgroups is configdrive
generation.

Nova will call into ironic to get the list of ports of each portgroup that has
a VIF associated with it, along with portgroup ``mode`` and ``properties``
fields (see `Data model impact`_ section), and update the network metadata
with the needed information. When the contents of the ``properties``
dictionary gets passed to the config drive builder in nova, we will ensure
that ``bond_`` prefix is prepended to all key names, so that these keys are
not ignored by cloud-init when reading the config drive.

Ramdisk impact
--------------

N/A

.. NOTE: This section was not present at the time this spec was approved.

Security impact
---------------

The new REST API calls for portgroups should not be usable by the end user.
Only operators and administrators should be able to manage portgroups and
local_link_connection data of ports, because these settings are used to
configure the network. This is satisfied because Ironic is an admin-only API,
so there should be no security impact.



Other end user impact
---------------------

Using the binding profile to enable flipping between provisioning and tenant
networks means there will be no support for PXE booting after deploy (i.e.
local disk installation only). How to allow operators to deploy instances
using either net-boot or local boot using the same Ironic conductor should be
discussed in the complementary network-provider spec [1]_.

Scalability impact
------------------

There will be more API calls made to Ironic in order to create and use
portgroups but impact on scalability should be negligible.



Performance Impact
------------------

None.

Other deployer impact
---------------------

New database columns are added to the port table and a new database table
portgroup is introduced, so this will require a database migration.

Deployers will need to deploy an ML2 mechanism driver that supports connecting
baremetal resources to Neutron networks.

If using Nova, deployers will need to deploy a version of Nova that supports
this feature.

Deployers may want to set the ``[DEFAULT]default_portgroup_mode`` configuration
option to match their environment. Its default value is ``active-backup``.

Deployers should be aware that automated upgrade or migration for
already-provisioned nodes is not supported.  Deployers should follow this
recommendation for upgrading a node in an existing deployment to use this
new feature:

* Upgrade the OpenStack services.

* Move node into the MANAGEABLE state.

* Update node driver field (see the network-provider spec [1]_).

* Create Ironic portgroups.

* Update Ironic port membership to portgroups.

* Update Ironic ports with local_link_connection data.

* Move node into the AVAILABLE state.



Developer impact
----------------

Neutron ML2 mechanism drivers should support this feature by using the data
passed in binding profile to dynamically configure relevant ports and
port-channels on the relevant switch(es).


Implementation
==============

Assignee(s)
-----------

* laura-moore

* yhvh (Will Stevenson)

* bertiefulton

* sukhdev-8

* vsaienko

* vdrok

Work Items
----------

* Extend port table.

* Create the new portgroup table.

* Implement extension to port APIs.

* Implement the new portgroup APIs.

* Implement the extension to the RPC API.

* Implement the changes to the Nova driver to get and use the binding profile.

* Implement the changes needed to get vifs for updating Neutron port DHCP
  options.

* Implement tests for the new functionality.

* Implement updates to the python-ironicclient.

* Update documentation.


Dependencies
============

Network flip is dependent on the network-provider spec [1]_.

Nova `changes <https://blueprints.launchpad.net/nova/+spec/ironic-portgroups-support>`_
are dependent on attach/detach interfaces work [2]_.

VLAN provisioning on switch(es) is dependent on ML2 driver functionality
being developed to support this feature.


Testing
=======

Existing default behaviour will be tested in the gate by default.

New tests will need to be written to test the new APIs and database
updates.

Simulation of connecting real hardware to real switches for testing
purposes is described in the network-provider spec [1]_.


Upgrades and Backwards Compatibility
====================================

Default behavior is the current behavior, so this change should be fully
backwards compatible.


Documentation Impact
====================

This feature will be fully documented.


References
==========

.. [1] http://specs.openstack.org/openstack/ironic-specs/specs/6.1/network-provider.html

.. [2] http://specs.openstack.org/openstack/ironic-specs/specs/approved/interface-attach-detach-api.html

Discussions on the topic include:

* https://etherpad.openstack.org/p/YVR-neutron-ironic

* https://etherpad.openstack.org/p/liberty-ironic-network-isolation

* https://etherpad.openstack.org/p/network-interface-vifs-configdrive

* Logs from https://wiki.openstack.org/wiki/Meetings/Ironic-neutron
