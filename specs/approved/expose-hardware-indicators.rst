..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

====================
Indicator management
====================

https://storyboard.openstack.org/#!/story/2005342

This spec proposed creating of API for hardware indicators management.

Problem description
===================

Depending on the hardware vendor, bare metal machines might carry on-board and
expose through the baseboard management controller (BMC) various indicators,
most commonly LEDs.

For example, a blade system might have LEDs on the chassis, on the blades
(compute cards), on the drives, on the PSUs, on the NICs.

The use-cases when ironic-manageable LEDs might make sense include:

* The DC staff member want to identify hardware unit in the rack by lighting
  up its LED in ironic
* The Deployer wants to identify ironic node by pressing a button
  on the physical unit to light up the LED
* The remote Admin user wants to be aware of the failure LEDs lighting on the
  bare metal nodes possibly indicating a failure

Proposed change
===============

Overview
--------

This RFE proposes an extension of the ``node`` ReST API endpoint that
will allow reading and toggling the indicators (e.g. LEDs) on the
hardware units.

Indicator management workflow
-----------------------------

#. An API client can choose to discover available node indicators by sending
   ``GET /v1/nodes/<node_ident>/management/indicators`` request. This step
   is optional.

#. An API client reads the indicator on the chosen component of the
   bare metal node by sending
   ``GET /v1/nodes/<node_ident>/management/indicators/<component>/<ind_ident>``
   request and presenting current indicator state to the user.

#. The API client can change the state of the indicator(s) on the given
   component by sending
   ``PUT /v1/nodes/<node_ident>/management/indicators/<component>`` request.

Alternatives
------------

The user can communicate with BMC independently from ironic for the same
purpose. Though ironic node correlation with physical node may be challenging.

Data model impact
-----------------

None.

Due to the interactive nature of indicator information, it seem that
user-indicator link should be as immediate as possible, having it cached by
the database can make indicators confusing.

State Machine Impact
--------------------

None.

Indicators should always work the same regardless of the machine state.

REST API impact
---------------

* ``GET /v1/nodes/<node_ident>/management/indicators``

  Retrieves bare metal node components. Returns a JSON object listing all
  available node components.

  Currently known components are: ``system``, ``chassis`` and ``drive``.
  Indicator names are free-form, but hopefully descriptive.

  Error codes:

  * 404 Not Found if node is not found.

  Example response object:

  .. code-block:: json

    {
        "components": [
            {
                "name": "system",
                "links": [
                    {
                        "href": "http://127.0.0.1:6385/v1/nodes/Compute0/
                        management/indicators/system",
                        "rel": "self"
                    },
                    {
                        "href": "http://127.0.0.1:6385/nodes/Compute0/
                        management/indicators/system",
                        "rel": "bookmark"
                    }
                ]
            },
            {
                "name": "chassis",
                "links": [
                    {
                        "href": "http://127.0.0.1:6385/v1/nodes/Compute0/
                        management/indicators/chassis",
                        "rel": "self"
                    },
                    {
                        "href": "http://127.0.0.1:6385/nodes/Compute0/
                        management/indicators/chassis",
                        "rel": "bookmark"
                    }
                ]
            }
        ]
    }


* ``GET /v1/nodes/<node_ident>/management/indicators/<component>``

  Retrieves indicators for a component. Returns a JSON object listing all
  available indicators for given hardware component along with their
  attributes.

  Currently known components are: ``system``, ``chassis`` and ``drive``.
  Indicator names are free-form, but hopefully descriptive.

  Error codes:

  * 404 Not Found if node or component is not found.

  Example response object:

  .. code-block:: json

    {
        "indicators": [
            {
                "name": "power",
                "readonly": true,
                "states": [
                    "OFF",
                    "ON"
                ],
                "links": [
                    {
                        "href": "http://127.0.0.1:6385/v1/nodes/Compute0/
                        management/indicators/system/power",
                        "rel": "self"
                    },
                    {
                        "href": "http://127.0.0.1:6385/nodes/Compute0/
                        management/indicators/system/power",
                        "rel": "bookmark"
                    }
                ]
            },
            {
                "name": "alert",
                "readonly": false,
                "states": [
                    "OFF",
                    "BLINKING",
                    "UNKNOWN"
                ],
                "links": [
                    {
                        "href": "http://127.0.0.1:6385/v1/nodes/Compute0/
                        management/indicators/system/alert",
                        "rel": "self"
                    },
                    {
                        "href": "http://127.0.0.1:6385/nodes/Compute0/
                        management/indicators/system/alert",
                        "rel": "bookmark"
                    }
                ]
            },
        ]
    }

* ``GET /v1/nodes/<node_ident>/management/indicators/<component>/<ind_ident>``

  Retrieves indicator state for the component. Returns a JSON object
  representing current state of the chosen indicator (``ind_ident``) sitting
  on the ``component``.

  The field of the response object is ``state``, the value is one of: ``OFF``,
  ``ON``, ``BLINKING`` or ``UNKNOWN``.

  Error codes:

  * 404 Not Found if node, component or indicator is not found.

  Example response object:

  .. code-block:: json

      {
        "state": "ON"
      }

* ``PUT /v1/nodes/<node_ident>/management/indicators/<component>/<ind_ident>``

  Set the state of the desired indicators of the component. The endpoint
  accepts a JSON object. The following field is mandatory:

  * ``state`` requested indicator state

  * 400 Bad Request if ``state`` is not an accepted value
  * 404 Not Found if node, component or indicator is not found.

  Example request object:

  .. code-block:: json

      {
        "state": "ON"
      }

Client (CLI) impact
-------------------

"ironic" CLI
~~~~~~~~~~~~

None.

"openstack baremetal" CLI
~~~~~~~~~~~~~~~~~~~~~~~~~

The following commands will be created:

.. code-block:: bash

    openstack baremetal indicator list [component]
    openstack baremetal indicator show <component> indicator
    openstack baremetal indicator set <component> <indicator> --state {ON,OFF,BLINKING}

RPC API impact
--------------

The new RPC calls are introduced:

* Listing the indicators

  .. code-block:: python

      def get_supported_indicators(self, context, node_id, component=None):
         """Get node hardware components and their indicators.

         :param context: request context.
         :param node_id: node id or uuid.
         :param component: The hardware component, one of
             :mod:`ironic.common.components` or `None` to return all
             available components.
         :returns: a `dict` holding indicator IDs as keys, indicator properties
             as values. Indicator properties is a `dict` that includes:
             `readonly` bool, `states` list containing zero or more values from
             mod:`ironic.common.indicator_states`.
         """

* Reading the indicator

  .. code-block:: python

      def get_indicator_state(self, context, node_id, component, indicator):
          """Get node hardware component indicator state.

          :param context: request context.
          :param node_id: node id or uuid.
          :param component: The hardware component, one of
              :mod:`ironic.common.components`.
          :param indicator: Indicator IDs, as
              reported by `get_supported_indicators`
          :returns: current indicator state. One of the values from
              mod:`ironic.common.indicator_states`.
          """"

* Setting the indicator

  .. code-block:: python

      def set_indicator_state(self, context, node_id, component,
                             indicator, state):
          """Set node hardware components indicator to the desired state.

          :param context: request context.
          :param node_id: node id or uuid.
          :param component: The hardware component, one of
              :mod:`ironic.common.components`.
          :param indicator: Indicator IDs, as
              reported by `get_supported_indicators`)
          :param state: Indicator state, one of
              mod:`ironic.common.indicator_states`.
          """

Driver API impact
-----------------

Optional indicator API methods is added to `ManagementInterface`:

* Listing the indicators

  .. code-block:: python

      def get_supported_indicators(self, task, component=None):
          """Get a map of the supported indicators (e.g. LEDs).

          :param task: A task from TaskManager.
          :returns: A dictionary of hardware components
              (:mod:`ironic.common.components`) as keys with indicator
              properties as values. Indicator properties is a `dict`
              that includes: `readonly` bool, `states` list containing
              zero or more values from mod:`ironic.common.indicator_states`.
          """

* Reading the indicator

  .. code-block:: python

      def get_indicator_state(self, task, component, indicator):
          """Get current state of the indicator of the hardware component.

          :param task: A task from TaskManager.
          :param component: The hardware component, one of
              :mod:`ironic.common.components`.
          :param indicator: Indicator ID (as reported by
              `get_supported_indicators`).
          :returns: current indicator state. One of the values from
              mod:`ironic.common.indicator_states`.
          """

* Setting the indicator

  .. code-block:: python

      def set_indicator_state(self, task, component, indicator, state):
          """Set indicator on the hardware component to the desired state.

          :param task: A task from TaskManager.
          :param component: The hardware component, one of
              :mod:`ironic.common.components`.
          :param indicator: Indicator ID (as reported by
              `get_supported_indicators`).
          :state: Desired state of the indicator, one of
              :mod:`ironic.common.indicator_states`.
          """

The above methods are implemented for Redfish and IPMI hardware types.

Nova driver impact
------------------

None.

Ramdisk impact
--------------

None.

Security impact
---------------

None.

Other end user impact
---------------------

The indicators can be made accessible through Horizon or other UI tools.

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

None.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  <etingof>

Work Items
----------

* Add indicator management methods to ironic management interface
* Add indicator management to ironic ipmi and redfish hardware types
* Add RPC for indicator management
* Add REST API endpoint for indicator management

Dependencies
============

None.

Testing
=======

* Unit tests and Tempest API will be provided

Upgrades and Backwards Compatibility
====================================

This change is fully backward compatible.

Documentation Impact
====================

API reference will be provided.

References
==========

.. _Story: https://storyboard.openstack.org/#!/story/2005342
.. _Management Interface change: https://review.opendev.org/649675
.. _Redfish change: https://review.opendev.org/652740
.. _REST API and RPC change: https://review.opendev.org/651785
