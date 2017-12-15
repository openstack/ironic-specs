..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=====================================
Expose conductor information from API
=====================================

https://storyboard.openstack.org/#!/story/1724474

The spec proposes to expose conductor information from API, as well as
the mapping between conductors and nodes.

Problem description
===================

In deployment with multiple ironic conductors incorporated, nodes are
distributed across conductors by hashring, currently we have no mechanism to
identify the specific conductor for a given node without database query.

There are several cases we need to locate the host of the conductor for a
node, for example:

* A node failed to boot from PXE during node deploy, we need to check the
  PXE environment of the conductor host.
* Ramdisk logs are stored in the conductor host if the backend is set to
  local, this requires identifying the exact conductor which serves a node.

Meanwhile we are lacking support from API for information related with
conductors, which might be useful for diagnostic. For example:

* How many conductors in this cloud, whether they are alive.
* The conductor group each conductor belongs to.
* Nodes currently mapped to this conductor.

This information also makes it possible to implement features like service
monitoring, alarming from the outside of ironic.

Proposed change
===============

Adds an API endpoint ``/v1/conductors`` to retrieve a list of conductor
information, including the hostname, conductor group, and alive flag.

The alive flag is calculated in the same way as how ironic assumes a conductor
is not alive, by checking ``update_at`` and ``heartbeat_timeout``.

Adds API endpoint ``/v/conductors/{hostname}`` to retrieve detailed conductor
information, including nodes affiliated with this conductor. The mapping is
retrieved from hashring.

Adds a field ``conductor`` to the Node API object, which indicates the
hostname of the conductor currently the node is mapped to.

Alternatives
------------

Admins can directly query the ironic database for a conductor list. To locate
the last conductor that served a node, query nodes table for the
``conductor_affinity`` field, then query ``conductors`` table for the hostname
of the conductor. The ``conductor_affinity`` is updated in several cases,
mainly during node deployment time. There is no alternative to get the
real time mapping from the hashring.

Data model impact
-----------------

None

State Machine Impact
--------------------

None

REST API impact
---------------

API microversion will be bumped.

Add a new ``conductor`` API object, and three API endpoints:

* GET /v1/conductors

  * Get the list of conductors known by ironic

  * Client with earlier microversion before this feature implemented will
    receive 404. For a normal request, 200 is returned.

  * Sample response data::

      {
        "conductors": [
          {
            "hostname": "Compute01",
            "conductor_group": "region1",
            "alive": true,
            "links": [
              {
                "href": "http://127.0.0.1:6385/v1/conductors/Compute01",
                "rel": "self"
              },
              {
                "href": "http://127.0.0.1:6385/conductors/Compute01",
                "rel": "bookmark"
              }
            ]
          },
          {
            "hostname": "Compute03",
            "conductor_group": "region1",
            "alive": true,
            "links": [...]
          }
        ]
      }

* GET /v1/conductors/{hostname}

  * Get detailed information of a conductor by hostname

  * Client with earlier microversion before this feature implemented will
    receive 404. For a normal request, 200 is returned.

  * Sample response data::

      {
        "hostname": "Compute01",
        "conductor_group": "region1",
        "alive": true
        "drivers": ["ipmi"],
        "last_seen": "2018-09-10 19:53:17"
        "links": [
          {
            "href": "http://127.0.0.1:6385/v1/conductors/Compute01",
            "rel": "self"
          },
          {
            "href": "http://127.0.0.1:6385/conductors/Compute01",
            "rel": "bookmark"
          }
        ]
      }

* GET /v1/nodes/{node_ident}/conductor

  * Get detailed information of a conductor for given node

  * Client with earlier microversion before this feature implemented will
    receive 404. For a normal request, 200 is returned.

  * The response data is same as /v1/conductors/{hostname}

Change ``Node`` API object in the following way:

* Add a read-only attribute ``conductor`` to indicate the hostname of
  associated conductor.
* Retrieve and assign the conductor hostname in ``Node.convert_with_links``.

The hostname of the conductor will be returned in these endpoints:

* ``POST /v1/nodes``
* ``GET /v1/nodes`` (when ``detail`` is set to true)
* ``GET /v1/nodes/detail``
* ``GET /v1/nodes/{node_ident}``

Sample response data for ``GET /v1/nodes/{node_ident}`` would be::

    {
      "nodes": [
        {
          "instance_uuid": null,
          "conductor": "Compute01",
          "uuid": "a308bca6-e6a3-4349-b8ea-695e17672898",
          "links": ...,
          "maintenance": false,
          "provision_state": "available",
          "power_state": "power off",
          "name": "node-0"
        }
      ]
    }

Add support for querying nodes by conductor hostname for endpoints:

* ``GET /v1/nodes``
* ``GET /v1/nodes/detail``

For example, ``GET /v1/nodes/?conductor=Compute01`` will return nodes mapped
to the conductor whose hostname is Compute01.

Client (CLI) impact
-------------------

"ironic" CLI
~~~~~~~~~~~~

None

"openstack baremetal" CLI
~~~~~~~~~~~~~~~~~~~~~~~~~

Enhance ironic client with two new command:

* ``openstack baremetal conductor list``
* ``openstack baremetal conductor show <hostname>``

Expose the conductor field in command:

* ``openstack baremetal node list --detail``
* ``openstack baremetal node show <node>``

Support node querying by conductor hostname:

* ``openstack baremetal node list --conductor <hostname>``

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

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  kaifeng <kaifeng.w@gmail.com>

Work Items
----------

* Implement the API endpoints.
* Add ``conductor`` field to node API object.
* CLI enhancement for API changes.
* Documentation and api reference.

Dependencies
============

None

Testing
=======

The feature will be covered by unit tests.

Upgrades and Backwards Compatibility
====================================

The feature will be guarded by microversion.

Documentation Impact
====================

New APIs will be documented in the API reference. New commands will be
documented in the ironicclient documentation.

References
==========

None
