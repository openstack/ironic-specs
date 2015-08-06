..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==================================================
Ironic Neutron Integration
==================================================

https://blueprints.launchpad.net/ironic/+spec/ironic-ml2-integration

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
tenant network as specified in the `network-provider spec
<https://blueprints.launchpad.net/ironic/+spec/network-provider>`_. To help
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
* extra

The 'address' field represents the MAC address for bonded NICs of the bare
metal server. The 'extra' field can be used to hold any additional information
that operators or developers want to store in the portgroup.

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
| bind_requested         | A way to specify whether to bind the port or     |
|                        | defer binding.                                   |
+------------------------+--------------------------------------------------+
| host_id                | This should be set to the Ironic node uuid.      |
+------------------------+--------------------------------------------------+

A JSON example to describe the structure is:

{"port":
   {
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

               } ]

        "bind_requested": true/false,

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

+-----------------------+-------------------------+
| Field Name            | Field Type              |
+=======================+=========================+
| id                    | int                     |
+-----------------------+-------------------------+
| uuid                  | str                     |
+-----------------------+-------------------------+
| name                  | str_or_none             |
+-----------------------+-------------------------+
| node_id               | int_or_none             |
+-----------------------+-------------------------+
| address               | str                     |
+-----------------------+-------------------------+
| extra                 | dict_or_none            |
+-----------------------+-------------------------+
| created_at            | datetime_or_str_or_none |
+-----------------------+-------------------------+
| updated_at            | datetime_or_str_or_none |
+-----------------------+-------------------------+

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

      * JSON schema definition of PortgroupCollection



* JSON schema definition of Portgroup (data sample):

::

  {
    "address": "fe:54:00:77:07:d9",
    "created_at": "2015-05-12T10:10:00.529243+00:00",
    "extra": {
      "foo": "bar",
    },
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
    "node_uuid": "e7a6f1e2-7176-4fe8-b8e9-ed71c77d74dd",
    "updated_at": "2015-05-15T09:04:12.011844+00:00",
    "uuid": "6eb02b44-18a3-4659-8c0b-8d2802581ae4",
    "name": "node1_portgroup1"
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

The python-ironicclient would need updated to support the new portgroup APIs.

Example usage of the new methods:

  * For ports, the CLI would support port creation with new optional
    parameters specifying the new port attributes (local_link_connection,
    portgroup_id and pxe_enabled) and would also support update of these
    attributes. As examples:

    * ironic port-create -a <address> -n <node> [-e <key=value>]
      [--local_link_connection <local_link_connection>]
      [--portgroup_uuid <portgroup_uuid>] [--pxe_enabled <pxe_enabled>]

    * ironic port-update port_uuid replace portgroup_uuid=<portgroup_uuid>


  * For portgroups, the CLI would support the following new methods:

    * ironic portgroup-create --node <node> [--name <portgroupname>]
      [--address <mac-address>] [-e <key=value>]

        * To add ports to a portgroup, the portgroup should first
          be created and then port_update called.

    * ironic portgroup-delete <portgroup_uuid>

    * ironic portgroup-list [--detail] [--node <node>]
      [--address <mac-address>]
      [--limit <limit>]  [--marker <portgroup_uuid] [--sort-key <field>]
      [--sort-dir <direction>]

    * ironic portgroup-show [--address] <id>

        * <id> is the UUID of the portgroup (or MAC address if --address is
          specified)

    * ironic portgroup-update <portgroup_uuid> <op> <path=value>
      [<path=value> ... ]

        * <op> is add, remove or replace.

        * <path=value> is the attribute to add, remove or replace. Can be
          specified multiple times. For 'remove' only <path> is necessary.


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

The complementary `network-provider spec
<https://blueprints.launchpad.net/ironic/+spec/network-provider>`_ provides
details regarding the workflow of the network flip and the point at which
the binding profile will be passed to Neutron to bind the port.



Nova driver impact
------------------

There will be changes necessary to the Nova driver. Proposed changes are:

* To enable the mapping between Neutron ports and Ironic ports and
  portgroups.

  The Ironic Nova driver has methods ``macs_for_instance``,
  ``dhcp_options_for_instance``, ``extra_options_for_instance`` and
  ``plug_vifs``. Currently Nova puts a network on one port at random - see
  `ports cannot be mapped to networks
  <https://bugs.launchpad.net/ironic/+bug/1405131>`_. This bug has high
  priority and the issue is being addressed.  Once addressed, these methods
  should determine the number of Neutron ports that are
  created as well as the mapping between Neutron and Ironic ports. These
  methods should be updated to not only account for Ironic ports but also
  Ironic portgroups. The selection process would be:

  * Select all Ironic ports that do not belong to Ironic portgroups
    (possible if the Ironic port list API returns portgroup_uuid as
    standard, as suggested in the above section)

  * Select all Ironic portgroups

  This modified functionality could be implemented using a new config flag in
  Nova to allow toggling between the old and the new methods. The flag could
  help de-couple the upgrading of Nova and of Ironic.


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
discussed in the complementary `network-provider spec
<https://blueprints.launchpad.net/ironic/+spec/network-provider>`_.

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
this feature. Deployers will need to set a flag in the Nova config file to
turn this new feature on or off, which would be important when upgrading
Nova and Ironic.

Deployers should be aware that automated upgrade or migration for
already-provisioned nodes is not supported.  Deployers should follow this
recommendation for upgrading a node in an existing deployment to use this
new feature:

* Upgrade the OpenStack services.

* Update the flag in the Nova config file to turn this feature on.

* Move node into the MANAGEABLE state.

* Update node driver field (see `network-provider spec
  <https://blueprints.launchpad.net/ironic/+spec/network-provider>`_).

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

Network flip is dependent on `network-provider spec
<https://blueprints.launchpad.net/ironic/+spec/network-provider>`_.

VLAN provisioning on switch(es) is dependent on ML2 driver functionality
being developed to support this feature.


Testing
=======

Existing default behaviour will be tested in the gate by default.

New tests will need to be written to test the new APIs and database
updates.

Simulation of connecting real hardware to real switches for testing
purposes is described in `network-provider spec
<https://blueprints.launchpad.net/ironic/+spec/network-provider>`_.


Upgrades and Backwards Compatibility
====================================

Default behavior is the current behavior, so this change should be fully
backwards compatible.


Documentation Impact
====================

This feature will be fully documented.


References
==========

Discussions on the topic include:

* https://etherpad.openstack.org/p/YVR-neutron-ironic

* https://etherpad.openstack.org/p/liberty-ironic-network-isolation

* Logs from https://wiki.openstack.org/wiki/Meetings/Ironic-neutron

* The network provider spec enabling the network flip between provisioning
  and tenant network: https://review.openstack.org/#/c/187829
