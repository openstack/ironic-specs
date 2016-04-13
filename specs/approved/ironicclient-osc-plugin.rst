..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==================================================
Implementation of ironic commands as an OSC plugin
==================================================

https://bugs.launchpad.net/ironic/+bug/1526479

The OpenStackClient is becoming the defacto cli client for OpenStack. This spec
will spell out what the command structure should look like, including
parameters and command names.

Problem description
===================

The OpenStackClient has become the preferred method of creating clients for
OpenStack APIs. The initial implementation has been done. What needs to happen
now is to define what the command structure should be. There has been some
confusion/discussion about what these commands should look like, so it seemed
the proper thing to create a spec.

The goal of the OpenStackClient is to make the CLI clients more 'natural' for
the End User. This spec will specify the commands that the End User will use
when interacting with Ironic.

Proposed change
===============

The proposed implementation will have all of the commands implemented as
specified below.

Alternatives
------------

Continue with the current client and remove the existing OSC plugin bits.

Data model impact
-----------------

None

State Machine Impact
--------------------

None

REST API impact
---------------

None

Client (CLI) impact
-------------------

openstack baremetal chassis
~~~~~~~~~~~~~~~~~~~~~~~~~~~

* openstack baremetal chassis show <uuid>

  --fields <field,[field,...]>  Select fields to fetch and display

* openstack baremetal chassis list

  --long                        Show detailed chassis info (Mutually exclusive
                                to --fields)
  --limit <limit>               Limit the number of items to return
  --marker <uuid>               Which chassis uuid to start after
  --sort <key[:direction]>      Key and direction of sort. <direction> is
                                optional. Defaults to ascending order.
  --fields <field,[field,...]>  Select fields to fetch and display. (Mutually
                                exclusive to --long)

* openstack baremetal chassis create

  --description <description>  Chassis description
  --extra <key=value>          Extra chassis properties. Can be specified
                               multiple times.

* openstack baremetal chassis delete <uuid> [<uuid> ...]

* openstack baremetal chassis set <uuid>

  --extra <key=value>          Property to set or update. Can be specified
                               multiple times.
  --description <description>  Chassis description

* openstack baremetal chassis unset <uuid>

  --extra <key>                Key of property to unset. Can be specified
                               multiple times.
  --description <description>  Will unset the chassis description ('')

openstack baremetal driver
~~~~~~~~~~~~~~~~~~~~~~~~~~

* openstack baremetal driver show <driver_name>

* openstack baremetal driver show properties <driver_name>

* openstack baremetal driver show passthru <driver_name>

* openstack baremetal driver list

* openstack baremetal driver passthru <driver_name> <method>

  <method>             Vendor passthru method to call.

  --param <key=value>  key=value to add to passthru call. Can be specified
                       multiple times.
  --http-method <http_method>  one of 'POST', 'PUT', 'GET', 'DELETE', 'PATCH'

openstack baremetal node
~~~~~~~~~~~~~~~~~~~~~~~~

* openstack baremetal node show <uuid>

  Obsoletes: openstack baremetal show

  --instance       Interpret <uuid> as an instance UUID
  --long           Display detailed information about node.
  --states         Include state information. Mutually exclusive with --long.

* openstack baremetal node show passthru <uuid>

* openstack baremetal node list

  Obsoletes: openstack baremetal list

  --limit <limit>         Limit the number of items to return
  --marker <uuid>         Which node to start after
  --sort <key[:direction]>  Key and direction of sort. <direction> is optional.
  --maintenance           List nodes in maintenance mode
  --associated            List nodes associated with an instance
  --chassis <uuid>        UUID of chassis to limit node list
  --provision-state <state>  Show nodes in specified <state>
  --fields <field,[field,...]>  Select fields to fetch and display. (Mutually
                                exclusive to --long)

* openstack baremetal node create

  Obsoletes: openstack baremetal create

  --chassis-uuid <uuid>   Chassis this node belongs to
  --driver <driver>       Driver used to control the node
  --driver-info <key=value>   key=value pair used by the driver. Can be
                              specified multiple times.
  --property <key=value>      Property of the node. Can be specified multiple
                              times.
  --extra <key=value>         Arbitrary metadata. Can be specified multiple
                              times.
  --uuid <uuid>               Unique UUID of the node. Optional.
  --name <name>               Unique name of the node.

* openstack baremetal node delete <uuid> [<uuid> ...]

  Obsoletes: openstack baremetal delete

* openstack baremetal node set <uuid>

  Obsoletes: openstack baremetal set

  --name <name>           Name of the node
  --instance-uuid <uuid>  Instance UUID
  --driver <driverid>     Driver name or UUID
  --property <key=value>  Property to set/update on the node. Can be specified
                          multiple times.
  --extra <key=value>     Extra to set/update on the node. Can be
                          specified multiple times.
  --driver-info <key=value>  driver-info to set/update on the node. Can be
                             specified multiple times.
  --instance-info <key=value>  instance-info to set/update on the node. Can be
                               specified multiple times.

* openstack baremetal node unset <uuid>

  Obsoletes: openstack baremetal unset

  --property <key>       key to unset on the node. Can be specified multiple
                         times.
  --extra <key>          key from extra to unset. Can be specified multiple
                         times.
  --driver-info <key>    key to unset from driver-info. Can be specified
                         multiple times.
  --instance-info <key>  key to unset from instance-info. Can be specified
                         multiple times.
  --instance-uuid <uuid>  Instance uuid.

* openstack baremetal node passthru <uuid> <method>

  <method>              Vendor-passthru method to be called

  --param <key=value>   param to send to passthru method. Can be specified
                        multiple times.
  --http-method <http_method>  One of 'POST', 'PUT', 'GET', 'DELETE', 'PATCH'

* openstack baremetal node show console <uuid>

* openstack baremetal node set console <uuid>

* openstack baremetal node unset console <uuid>

* openstack baremetal node show boot-device <uuid>

  --supported       Show the supported boot devices

* openstack baremetal node set boot-device <uuid> <device>

  <device>          One of 'pxe', 'disk', 'cdrom', 'bios', 'safe'

  --persistent      Make changes persistent for all future boots.

* openstack baremetal node deploy <uuid>

  --config-drive <config_drive>   A gzipped, base64-encoded configuration drive
                                  string OR the path to the configuration drive
                                  file OR the path to a directory containing
                                  the config drive files. In case it's a
                                  directory, a config drive will be generated
                                  from it.

* openstack baremetal node undeploy <uuid>

* openstack baremetal node rebuild <uuid>

* openstack baremetal node inspect <uuid>

* openstack baremetal node provide <uuid>

* openstack baremetal node manage <uuid>

* openstack baremetal node abort <uuid>

* openstack baremetal node set maintenance <uuid>

  --reason <reason>         Reason for setting to maintenance mode

* openstack baremetal node unset maintenance <uuid>

* openstack baremetal node power on <uuid>

* openstack baremetal node power off <uuid>

* openstack baremetal node reboot <uuid>

* openstack baremetal node validate <uuid>

* openstack baremetal node create port <uuid> <address>

  This is an alias for
  'openstack baremetal port create <address> --node <uuid>'

  --extra <key=value>       Arbitrary key=value metadata. Can be specified
                            multiple times.

openstack baremetal port
~~~~~~~~~~~~~~~~~~~~~~~~

* openstack baremetal port show <uuid|mac>

  --address <mac>               Mac address instead of uuid
  --fields <field[,field,...]>  Fields to display

* openstack baremetal port list

  --limit <limit>            Limit the number of items to return
  --marker <marker>          Which port to start after
  --sort <key[:direction]>  Key and direction of sort
  --long                     Display detailed information about ports.
                             Mutually exclusive with --fields.
  --fields <field[,field,...]>  Fields to display. Mutually exclusive with
                                --long.
  --node <nodeid>           UUID or name of node to limit the port display

* openstack baremetal port create <address>

  --node <uuid>             Node uuid to add the port to
  --extra <key=value>       Arbitrary key=value metadata. Can be specified
                            multiple times.

* openstack baremetal port delete <uuid> [<uuid> ...]

* openstack baremetal port set <uuid>

  --extra <key=value>     property to set. Can be specified multiple times.
  --address <macaddress>  Set new MAC address of port
  --node <nodeid>         Set UUID or name of node the port is assigned to

* openstack baremetal port unset <uuid>

  --extra <key>           key to remove. Can be specified multiple times.


RPC API impact
--------------

None

Driver API impact
-----------------

None

Nova driver impact
------------------

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
  brad-9 <brad@redhat.com>

Other contributors:
  None

Work Items
----------

TBD

Dependencies
============

None

Testing
=======

Unittests will be added.

Upgrades and Backwards Compatibility
====================================

There is already an implementation of some of these commands. A few are likely
to change with this spec. These existing commands will go through a deprecation
period.

Documentation Impact
====================

The command line documentation will be updated to show these new commands.

References
==========

.. [#] http://docs.openstack.org/developer/python-openstackclient/index.html
.. [#] http://lists.openstack.org/pipermail/openstack-dev/2015-November/078998.html
