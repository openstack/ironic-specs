..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=============================
Expose supported power states
=============================

https://bugs.launchpad.net/ironic/+bug/1734827

This SPEC proposes adding a new API to expose supported power states of nodes.
This API would be helpful to see if a power action is supported by a node
because it depends on whether a power interface supports power actions such as
soft power off and soft reboot.

Problem description
===================

Ironic supports soft shutdown and soft reboot since Ocata. However, not all
power interfaces support these new power actions. A new API would be necessary
to see if a power action is supported by a node. This proposed API is similar
to the one for getting a node's supported boot devices, which is described
`here <https://developer.openstack.org/api-ref/baremetal/#get-supported-boot-devices>`_.

Proposed change
===============

The new APIs will be introduced to get the current power status and the
supported power states of nodes. See the 'REST API impact' section and for the
details:

  - GET /v1/nodes/{node_ident}/states/power
  - GET /v1/nodes/{node_ident}/states/power/supported

The new CLI will be also added for the new APIs. See the 'Client (CLI) impact'
section and for the details:

  - ``openstack baremetal node power show [--supported] <node>``

Alternatives
------------

There is another option to only add a new API to get supported power states.
There are also a few other options to support the API by the CLI:

  - Add a new option to display the supported power states to
    ``openstack baremetal node show``.
  - Add a new subcommand to show the supported power states like:
    ``openstack baremetal node supported power show``.

However, the current design is better for consistency with the existing APIs
and the `CLI
<https://docs.openstack.org/python-ironicclient/latest/cli/osc/v1/index.html#baremetal-node-boot-device-show>`_
for the boot devices.

Data model impact
-----------------

None

State Machine Impact
--------------------

None

REST API impact
---------------

We will introduce the two APIs. They will be available starting with a new Bare
Metal API version.

* Get the current power state of a node:

    GET /v1/nodes/{node_ident}/states/power

  The response is like::

    {
      "power_state": "power on"
    }

* Get the supported power states of a node:

    GET /v1/nodes/{node_ident}/states/power/supported

  The response contains supported power states of the node: For example::

    {
      "supported_power_states": [
        "power on",
        "power off",
        "rebooting",
        "soft rebooting",
        "soft power off"
      ]
    }

Client (CLI) impact
-------------------

The ``openstack baremetal`` CLI will support the new API.

"ironic" CLI
~~~~~~~~~~~~

None

A new feature is no longer added to the "ironic" CLI.

"openstack baremetal" CLI
~~~~~~~~~~~~~~~~~~~~~~~~~

A new subcommnad will be added::

  openstack baremetal node power show [--supported] <node>

Without the ``--supported`` option, this command displays the power state of
the specified node. When the ``--supported`` option is specified, this command
displays the supported power states.

RPC API impact
--------------

A new RPC API, ``get_supported_power_states`` will be added. This returns a
list of the supported power states of the specified node synchronously.

Driver API impact
-----------------

None

The driver API ``get_suuported_power_states`` was already defined in the
base power interface. If a power interface doesn't override the method, the
default list which contains power on, power off, and reboot is returned.

Nova driver impact
------------------

None

The new API is available to see if a requested power action is supported or
not. Though it might be helpful for the Nova driver, no change is planned
currently.

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
  shiina-hironori (irc:hshiina)

Other contributors:
  None

Work Items
----------

* Add the new RPC API.
* Add the new Baremetal APIs.
* Add the OSC baremetal subcommand.
* Add a new API test to tempest.
* Add the new APIs to the API reference.

Dependencies
============

None


Testing
=======

An API test will be added to Tempest.

Upgrades and Backwards Compatibility
====================================

None

Documentation Impact
====================

The new APIs will be added to the Baremetal API Reference.

References
==========

This change was originally mentioned in reviewing a SPEC to support soft
shutdown.: https://review.opendev.org/#/c/186700/
