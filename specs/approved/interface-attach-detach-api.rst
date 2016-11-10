..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===============================
Interface Attach and Detach API
===============================

https://bugs.launchpad.net/ironic/+bug/1582188

We are adding pluggable network interfaces to Ironic. These interfaces will be
configurable per Ironic node, this means that different nodes might have
different ways of handling their network interfaces. We need a way that
different network interfaces can override the virtual network interface (VIF)
to physical network interface (PIF) mapping logic currently contained in nova.

Problem description
===================

Currently we use an Ironic port update to assign tenant neutron ports to Ironic
ports using their extra field. Doing the mapping this way may not work for a
third party network interface implementation. This also ties the ironic nova
virt driver to a particular network VIF to PIF mapping implementation. If a
third party network interface wants to do something different with network VIF
to PIF mapping such as storing the port IDs for dynamic vNIC creation later in
the provisioning process or we as the Ironic team want to change an
implementation detail we have to submit changes into nova. Additionally if we
want to support post-deployment attach and detach of a network VIF then we have
to watch for any updates made to the port object and interpret certain changes
as certain actions.

Proposed change
===============

To solve this problem I propose to add a new API endpoint,

* POST v1/nodes/<node_id>/vifs
* GET v1/nodes/<node_id>/vifs
* DELETE v1/nodes/<node_id>/vifs/<vif_id>

These API endpoints will take via a POST body, a JSON representation of a
generic VIF object. Making it generic allows for non-neutron based
implementations to use this API. This VIF object will be passed to new
functions in the pluggable network interfaces:

def vif_attach(self, vif):
    ...

def vif_detach(self, vif_id):
    ...

def vif_list(self):
    ...

The network interface can use these functions to handle attaching the VIF to
the Ironic node in whichever way it needs to for its implementation. This could
be by adding a field to the Ironic port as with the existing implementation, or
it might be different for example storing it in a list in the node's
driver_internal_info.

The ironic nova virt driver will be updated to use this new API in the
plug_vifs and unplug_vifs functions, unbinding it from the underlying
implementation details.

Alternatives
------------

* Continue to use a port update to allow nova to interact with ironic ports and
  soon portgroups, documenting the vif_port_id etc logic as a defined API for
  the network interfaces to use.

Data model impact
-----------------

None

State Machine Impact
--------------------

None

REST API impact
---------------

* GET v1/nodes/<node_id>/vifs

  - Calls to vif_list on the node's network interface
  - This is a synchronous API endpoint, and the normal ironic rules apply for
    avoiding implementing tasks that take a long time or are unstable under
    synchronous endpoints.
  - Method: GET
  - Successful http response: 200
  - Expected response body is a JSON

    + JSON Schema::

        {
            "title": "VIFS",
            "type": "object",
            "properties": {
                "vifs": {
                    "description": "List of vifs currently attached"
                    "type": "list"
                },
            },
            "required": ["vifs"]
        }

    + Example::

        {
            "vifs": [
                "8e6ba175-1c16-4dfa-82b9-dfc12f129170",
            ]
        }

* POST v1/nodes/<node_id>/vifs

  - Calls vif_attach on the network interface for the node, passing in the json
    provided
  - This is a synchronous API endpoint, and the normal ironic rules apply for
    avoiding implementing tasks that take a long time or are unstable under
    synchronous endpoints.
  - Method: POST
  - Successful http response: 204
  - Expected error response codes:

    + 404, Node not found
    + 400, Request was malformed
    + 409, Conflict between the requested VIF to attach and other VIFs already
      attached
    + 422, The request was good but unable to attach the VIF for a
      defined reason, for example: "No physical interface's available to attach
      too"

  - Expected data is a JSON

    + JSON Schema::

        {
            "title": "Attachment",
            "type": "object",
            "properties": {
                "id": {
                    "description": "ID of interface to attach"
                    "type": "string"
                },
            },
            "required": ["id"]
        }

    + Example::

        {
          "id": "8e6ba175-1c16-4dfa-82b9-dfc12f129170"
        }

  - Expected response body is empty

* v1/nodes/<node_id>/vifs/<vif_id>

  - Calls vif_detach on the network interface for the node, passing in the json
    provided
  - This is a synchronous API endpoint, and the normal ironic rules apply for
    avoiding implementing tasks that take a long time or are unstable under
    synchronous endpoints.
  - Method: DELETE
  - Successful http response: 204
  - Expected error response codes:

    + 404, Node not found
    + 400, Request was malformed
    + 422, The request was good but unable to detach the VIF for a
      defined reason

  - Expected response body is empty.

* Does the API microversion need to increment? Yes

* Is a corresponding change in the client library and CLI necessary? Yes

* As these are new API entry points they will not affect older clients.

Client (CLI) impact
-------------------

"ironic" CLI
~~~~~~~~~~~~
* ironic node-vif-list <node_id>
* ironic node-vif-attach <node_id> <vif_id>
* ironic node-vif-detach <node_id> <vif_id>

"openstack baremetal" CLI
~~~~~~~~~~~~~~~~~~~~~~~~~
* openstack baremetal node vif list <node_id>
* openstack baremetal node vif attach <node_id> <vif_id>
* openstack baremetal node vif detach <node_id> <vif_id>

RPC API impact
--------------

The RPC API will implement:

* vif_attach(self, context, node_id, vif)
* vif_detach(self, context, node_id, vif_id)
* vif_list(self, context, node_id)

Driver API impact
-----------------

Base network interface will need to be extended with::

  def vif_list(self, task):
      # TODO(sambetts): Uncomment when vif_port_id in port.extra is removed.
      # raise NotImplemented
      default_vif_list()

  def vif_attach(self, task, vif):
      # TODO(sambetts): Uncomment when vif_port_id in port.extra is removed.
      # raise NotImplemented
      default_vif_attach(vif)

  def vif_detach(self, task, vif_id):
      # TODO(sambetts): Uncomment when vif_port_id in port.extra is removed.
      # raise NotImplemented
      default_vif_detach(vif_id)

Existing flat, neutron and noop network interfaces will need extending to
include implementations for these functions.

Flat network driver will need to implement add_provisioning_network to bind the
ports that used to be bound by nova.

Nova driver impact
------------------

plug/unplug_vifs logic will be replaced by calling attach/detach for every VIF
passed into those functions.

nova.virt.driver.IronicDriver.macs_for_instance will be removed because mapping
is handled inside Ironic so mac_address assignment must happen at binding later
in the process.

nova.virt.driver.IronicDriver.network_binding_host_id will be changed to return
None in all cases, so that neutron ports remain unbound until Ironic binds them
during deployment.

nova driver will need to include the nova compute host ID in the instance_info
so that the ironic flat network interface can use it to update the neutron
ports mimicking the existing nova behavior.

The nova driver ironic API version requirement will need to be increased to the
version that implements the attach and detach APIs. Operators will need to
ensure the version of python-ironicclient they have installed on the nova
compute service supports the new APIs.

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

Developers of network interfaces will need to consider how their network
interface wants to handle ports.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
    sambetts

Work Items
----------

* Add new APIs to Ironic
* Update existing ironic network interfaces to support the new APIs
* Add new APIs to ironic client
* Update nova virt driver to use new APIs via client

Dependencies
============

* Ironic neutron integration

  - https://specs.openstack.org/openstack/ironic-specs/specs/not-implemented/ironic-ml2-integration.html

Testing
=======

These changes will be tested as part of the normal gate process, as they will
be part of the normal ironic deployment workflow.

Upgrades and Backwards Compatibility
====================================

Setting vif_port_id via a port/portgroup update will be deprecated in favor of
the new APIs. A deprecation message should be issued on a port update if a user
is directly setting vif_port_id on a port or portgroup. Code will need to be
added to ensure that the network interfaces will still process a vif_port_id
set via that method.

As the old vif_port_id field is still supported although deprecated, old nova
virt drivers will continue to work using that method.

Ironic must be upgraded before Nova is as newer nova virt drivers won't work
with older versions of Ironic which are missing the new APIs.

Out-of-tree network interfaces may not immediately implement the
interface_attach and interface_detach methods, so during the period that
vif_port_id is a deprecated method, we should also ensure we provide a default
implementation of attach and detach, this default implementation should match
the behaviour of ironic nova virt driver implementation setting the vif_port_id
in port.extra and will be removed when support for vif_port_id in port.extra is
removed.

Documentation Impact
====================

New API and its usage needs to be documented.

References
==========

None
