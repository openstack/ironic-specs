..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==============================================================
OSC commands to get descriptions of driver-related information
==============================================================

* https://bugs.launchpad.net/python-ironicclient/+bug/1619052
* https://bugs.launchpad.net/python-ironicclient/+bug/1619053

Almost all the ironic CLI commands have corresponding OpenStack Client (OSC)
commands. This was done in `Implementation of ironic commands as an OSC
plugin`_.

There are two ironic CLI commands:

* ``ironic driver-properties`` and
* ``ironic driver-raid-logical-disk-properties``

that do not have corresponding OSC commands. This specification proposes OSC
commands for them.

Properties of hardware types with non-default interfaces is addressed in
`RFE to get properties for a dynamic driver and non-default interfaces`_.
That proposal will most likely result in a richer REST API (and corresponding
OSC commands). In light of that, we propose simple OSC commands with the goal
of providing equivalent behaviours to the ironic CLI commands, and nothing
more.

Problem description
===================

This table shows the ironic driver-related commands and their associated
OSC commands.

=============================================== ===============================
ironic                                          openstack baremetal
=============================================== ===============================
driver-get-vendor-passthru-methods <driver>     driver passthru list <driver>
driver-list                                     driver list
driver-show <driver>                            driver show <driver>
driver-vendor-passthru <driver> <method> ...    driver passthru call <driver>
                                                <method> ...
driver-properties <driver>                      ?
driver-raid-logical-disk-properties <driver>    ?
=============================================== ===============================

The question is what to use for the OSC commands corresponding to these ironic
commands:

* ``ironic driver-properties <driver>``
* ``ironic driver-raid-logical-disk-properties <driver>``.

These commands return tables with two columns; the names and descriptions for
driver-related information.

To complicate things a bit, there is a lack of symmetry. Although the names
(and descriptions) are available via the driver, the values for these are
specified via the nodes that use these drivers, rather than directly via
the driver.

There have been a few discussions related to this:

* http://lists.openstack.org/pipermail/openstack-dev/2016-September/103490.html
* briefly discussed at the OpenStack PTG in Atlanta in February 2017, see
  "How to call (a name for it) the OSC command for listing RAID properties?
  (dtantsur)" in the `PTG operations etherpad`_.

Properties of hardware types with non-default interfaces is addressed in
`RFE to get properties for a dynamic driver and non-default interfaces`_.
That proposal will most likely result in a richer REST API (and corresponding
OSC commands). In light of that, we propose simple OSC commands with the goal
of providing equivalent behaviours to the ironic CLI commands, and nothing
more.

ironic driver-properties <driver>
---------------------------------

The ``ironic driver-properties <driver>`` command returns the "properties" of
a driver that must be specified via the nodes that use that driver.

For example, ``ironic driver-properties agent_ipmitool`` returns a table of
information::

  +--------------------------+---------------------------------------------+
  | Property                 | Description                                 |
  +--------------------------+---------------------------------------------+
  | deploy_forces_oob_reboot | Whether Ironic should force a reboot of t...|
  | deploy_kernel            | UUID (from Glance) of the deployment kern...|
  | deploy_ramdisk           | UUID (from Glance) of the ramdisk that is...|
  | image_http_proxy         | URL of a proxy server for HTTP connection...|
  | image_https_proxy        | URL of a proxy server for HTTPS connectio...|
  | image_no_proxy           | A comma-separated list of host names, IP ...|
  | ...                      | ...                                         |
  +--------------------------+---------------------------------------------+

The values for these driver properties are set per node, for each node that
uses the driver. The information is in the node's ``driver_info`` dictionary
field. They can be set when creating a node or when `updating a node`_, for
example with ``openstack baremetal node set <node> --driver-info``.

ironic driver-raid-logical-disk-properties <driver>
---------------------------------------------------
The ``ironic driver-raid-logical-disk-properties <driver>`` command returns
the RAID logical disk properties that can be specified for a particular driver.

For example, ``ironic driver-raid-logical-disk-properties agent_ipmitool``
returns a table of information::

  +--------------------------+---------------------------------------------+
  | Property                 | Description                                 |
  +--------------------------+---------------------------------------------+
  | controller               | Controller to use for this logical disk. ...|
  | disk_type                | The type of disk preferred. Valid values ...|
  | interface_type           | The interface type of disk. Valid values ...|
  | is_root_volume           | Specifies whether this disk is a root vol...|
  | number_of_physical_disks | Number of physical disks to use for this ...|
  | physical_disks           | The physical disks to use for this logica...|
  | raid_level               | RAID level for the logical disk. Valid va...|
  | share_physical_disks     | Specifies whether other logical disks can...|
  | size_gb                  | Size in GiB (Integer) for the logical dis...|
  | ...                      | ...                                         |
  +--------------------------+---------------------------------------------+

The values for these disk properties are set per node, for each node that
uses the driver and RAID. This information is in the node's
``target_raid_config`` field and can be set (in JSON format) via the
`node's set raid config`_ API, or via ``openstack baremetal node
set <node> --target-raid-config``.


Proposed change
===============

The `OpenStackClient command`_ structure is::

  openstack [<global-options>] <object-1> <action> [<object-2>] [<command-arguments>]

ironic driver-properties <driver>
---------------------------------

The <object-1> part will be "baremetal driver property".

For the <action>, there were discussions at the PTG about the merits of
using "list" versus "show". In the context of existing OSC commands using
these two action words, neither of these action words seems to fit with the two
commands, since they return descriptions (or documentation) on what is
available. However, since this will very likely be replaced by a richer set of
OSC commands (resulting from `RFE to get properties for a dynamic driver and
non-default interfaces`_), we keep it simple and use "list". (Using "list"
might imply that a corresponding "show" exists to drill down and get more
information. The converse is true too though; using "show" might imply a
corresponding "list" command.)

The OSC command is::

    openstack baremetal driver property list <driver>

For example::

    $ openstack baremetal driver property list agent_ipmitool

    +--------------------------+---------------------------------------------+
    | Property                 | Description                                 |
    +--------------------------+---------------------------------------------+
    | deploy_forces_oob_reboot | Whether Ironic should force a reboot of t...|
    | deploy_kernel            | UUID (from Glance) of the deployment kern...|
    | deploy_ramdisk           | UUID (from Glance) of the ramdisk that is...|
    | image_http_proxy         | URL of a proxy server for HTTP connection...|
    | image_https_proxy        | URL of a proxy server for HTTPS connectio...|
    | image_no_proxy           | A comma-separated list of host names, IP ...|
    | ...                      | ...                                         |
    +--------------------------+---------------------------------------------+

ironic driver-raid-logical-disk-properties <driver>
---------------------------------------------------

Again, since this will very likely be replaced by a richer set of
OSC commands (that will result from `RFE to get properties for a dynamic driver
and non-default interfaces`_), we propose a simple OSC command.

<object-1> would be "baremetal driver raid property" and <action> would be
"list"::

    openstack baremetal driver raid property list <driver>

Alternatives
------------

There are alternatives, but in the interest of keeping this simple and
deprecating it when `RFE to get properties for a dynamic driver and non-default
interfaces`_ is available, we are focussed here on only providing
OSC-equivalent commands that may not be flexible or extensible, but provide
equivalence to the ironic CLI ones.

Data model impact
-----------------
None.

State Machine Impact
--------------------
None.

REST API impact
---------------
None.

Client (CLI) impact
-------------------
This specification is about the OSC CLI.

"ironic" CLI
~~~~~~~~~~~~
None.

"openstack baremetal" CLI
~~~~~~~~~~~~~~~~~~~~~~~~~
See above.

RPC API impact
--------------
None.

Driver API impact
-----------------
None.

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
None.

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
rloo (Ruby Loo)

Other contributors:
galyna (Galyna Zholtkevych)

Work Items
----------
* Code the two OSC commands in python-ironicclient.


Dependencies
============
None.

Testing
=======
Unit and functional testing similar to what exists for other OSC commands.

Upgrades and Backwards Compatibility
====================================
None.

Documentation Impact
====================
None. ironic doesn't have OSC-command related documentation.

References
==========

* `Implementation of ironic commands as an OSC plugin`_
* `OpenStackClient command`_
* `PTG operations etherpad`_
* `updating a node`_
* `node's set raid config`_
* http://lists.openstack.org/pipermail/openstack-dev/2016-September/103490.html
* `RFE to get properties for a dynamic driver and non-default interfaces`_

.. _`Implementation of ironic commands as an OSC plugin`: http://specs.openstack.org/openstack/ironic-specs/specs/6.2/ironicclient-osc-plugin.html
.. _`updating a node`: https://developer.openstack.org/api-ref/baremetal/?expanded=set-raid-config-detail,update-node-detail
.. _`node's set raid config`: https://developer.openstack.org/api-ref/baremetal/?expanded=set-raid-config-detail
.. _`PTG operations etherpad`: https://etherpad.openstack.org/p/ironic-pike-ptg-operations
.. _`OpenStackClient command`: https://docs.openstack.org/developer/python-openstackclient/commands.html
.. _`RFE to get properties for a dynamic driver and non-default interfaces`: https://bugs.launchpad.net/ironic/+bug/1671549
