..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode


===================
BMC event framework
===================

https://storyboard.openstack.org/#!/story/2008366

The goal of this spec is to provide an API to manage subscriptions for BMC
events. The user will be able to provide a URL where the BMC will post the
events.

Non-goals:
* Unify event formats or payloads across drivers.

* Provide a way to poll for events.

* Proxy notifications (see [RFE 2008555](https://storyboard.openstack.org/#!/story/2008555)).

* Store events in ironic at all.

* Update an existing subscription in the BMC, at this time, as some vendors
  support partial updates where as other vendors essentially require a
  delete/re-creation to perform an update. This may be something that can
  be added later, but it seems not feasible at this time.

* Choosing EventTypes when creating a subscription won't be supported,
  since option is deprecated since [EventDestination v1_5_0](https://redfish.dmtf.org/schemas/v1/EventDestination.v1_5_0.json).

* Support for creating subscriptions with HTTP Headers.

Problem description
===================

Some BMC's have support to subscribe to specific event notifications about the
hardware (e.g., overheating, removal of the device).

* As an ironic user, I want to configure the BMC to send event notifications
  about potential failures to a specific URI.

Proposed change
===============

Overview
--------

This RFE proposes a new top level ReST API `subscriptions` that will allow
listing, creating and deleting subscriptions for nodes.

Subscriptions workflow
----------------------

#. Create a subscription ``POST /v1/nodes/<node_ident>/management/``
   ``subscriptions``

#. Delete a subscription ``DELETE /v1/nodes/<node_ident>/management/``
   ``subscriptions/<subscription_bmc_id>``

#. List subscriptions ``GET /v1/nodes/<node_ident>/management/subscriptions``

#. Show subscription ``GET /v1/nodes/<node_ident>/management/subscriptions/``
   ``<subscription_bmc_id>``


Alternatives
------------

The user can directly access the BMC and configure the subscriptions.


Data model impact
-----------------

None.

State Machine Impact
--------------------

None.

REST API impact
---------------

Update the REST API for the node object to allow create/delete/list
event subscriptions.

* ``GET /v1/nodes/<node_ident>/management/subscriptions``

  Retrieves a list of all subscriptions available.
  Returns a JSON object listing all available subscriptions or
  empty list.

  Error codes:

  * 404 - Node Not Found / microversion not high enough for API consumer.

  Example response object:

  .. code-block:: json

      {
        "subscriptions": [
          {
            "id": "<subscription_bmc_id1>",
            "links": [
              {
                "href": "http://127.0.0.1:6486/v1/nodes/<node_id>/management/
                subscriptions/<subscription_bmc_id1>",
                "rel": "self"
              },
              {
                "href": "http://127.0.0.1:6486/nodes/<node_id>/management/
                subscriptions/<subscription_bmc_id1>",
                "rel": "bookmark"
              }
            ]
          },
          {
            "id": "<subscription_bmc_id2>",
            "links": [
              {
                "href": "http://127.0.0.1:6486/v1/nodes/<node_id>/management/
                subscriptions/<subscription_bmc_id2>",
                "rel": "self"
              },
              {
                "href": "http://127.0.0.1:6486/nodes/<node_id>/management/
                subscriptions/<subscription_bmc_id2>",
                "rel": "bookmark"
              }
            ]
          },
        ]
      }


* ``GET /v1/nodes/<node_ident>/management/subscriptions/subscription_bmc_id``

  Retrieves a sbuscription. Returns a JSON object representing the chosen
  subscription (``subscription_bmc_id``).

  Error codes:

  * 404 Not Found if node or subscription is not found.

  .. code-block:: json

      {
        "id": "<subscription_bmc_id>",
        "destination": "<destinatination_url>",
        "protocol": "<protocol>",
        "context": "<context>",
        "event_types": ["Alert"]
      }

* ``POST /v1/nodes/<node_ident>/management/subscriptions``

  Requests the creation of a subscription.

  * Required: `destination`.


  HTTP codes:

  * 201 Created
  * 400 Bad Request

  .. code-block:: json

      {
       "destination": "http(s)://host/path",
      }

* ``DELETE /v1/nodes/<node_ident>/management/subscriptions/
  <subscription__bmc_id>``

  Requests the deletion of a subscription

  HTPP codes:

  * 204 No Content
  * 404 Not Found

.. note::
   The PATCH verb is not being supported at this time in this feature.

Client (CLI) impact
-------------------

The following commands will be created:

.. code-block:: bash

    baremetal node create subscription [node_uuid] [destination]
    baremetal node subscription delete [subscription_uuid]
    baremetal node subscription list [node]
    baremetal node subscription show [node] [subscription_uuid]

"openstacksdk"
~~~~~~~~~~~~~~

Add support for the event subscriptions in openstacksdk.

RPC API impact
--------------

The following new RPC calls will be added:

* Create subscription

  .. code-block:: python

      def create_subscription(self, context, node_id, destination, topic=None):

* Delete subscription

  .. code-block:: python

      def delete_subscription(self, context, node_id, subscription_bmc_id, topic=None):

* List subscriptions

  .. code-block:: python

      def get_all_subscriptions(self, context, node_id, topic=None):

* Get a subscription

  .. code-block:: python

      def get_subscription(self, context, node_id, subscription_bmc_id, topic=None):

Driver API impact
-----------------

The `ManagementInterface` will be updated with the following functions:

.. code-block:: python

    def create_subscription(self, task, destination):
        """Add the new subscription object to the BMC."""

    def delete_subscription(self, task, subscription_bmc_id):
        """Remove the subscription from the BMC."""

    def get_all_subscriptions(self, task):
        """List all subscriptions from the BMC"""

    def get_subscriptions(self, task, subscription_bmc_id):
        """Get a subscriptions from the BMC"""


The above methods are implemented for Redfish hardware types.
We will disallow changing the management interface of a node if there are
any subscriptions.

Nova driver impact
------------------

None.

Ramdisk impact
--------------

None.

Security impact
---------------

It is recommended to use https.

Other end user impact
---------------------

The user won't be able to choose the ``EventTypes`` for the subscription,
since the option is deprecated in Redfish EventDestination v1_5_0.
We will be using `Alert` by default for the ``EventTypes``.

The user won't be able to choose the ``Protocol`` for the subscription,
by default it will be `Redfish` following the schema for EventDestination.

Scalability impact
------------------

None.

Performance Impact
------------------

None.

Other deployer impact
---------------------

None.

Developer impact
----------------

Other drivers may implement this feature if the BMC has support for
event subscription.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  <iurygregory, iurygregory@gmail.com>

Redfish Implementation Details
------------------------------

The actual support for EventDestination in sushy is based on schema [2]_,
since HW vendors are still working on adding support for newer versions where
the property ``EventTypes`` is deprecated. Based on this the Ironic API
will only accept the following redfish properties to create a subscription:

* Destination - Required

By default we are considering ``Protocol`` as `Redfish`, ``EventTypes`` as
`["Alert"]` and ``Context`` as `""`.

When vendors have the support for newer EventDestination new fields will be
added to the Ironic API.

Work Items
----------

* Add support for Events Subscriptions in sushy [1]_ [2]_.
* Add event subscription support to ManagementInterface
* Add event subscription support to redfish hardware type
* Add RPC for event subscriptions
* Add REST API for event subscriptions


Dependencies
============

None.

Testing
=======

* Unit Tests
* Tempest tests


Upgrades and Backwards Compatibility
====================================

No upgrade impact.


Documentation Impact
====================

* API reference will be added
* Client documentation will be added.

References
==========

.. [1] https://redfish.dmtf.org/schemas/v1/EventService.v1_0_8.json
.. [2] https://redfish.dmtf.org/schemas/v1/EventDestination.v1_0_0.json
