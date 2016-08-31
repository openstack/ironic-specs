..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==================================================
Implementation of ironic commands as an OSC plugin
==================================================

https://bugs.launchpad.net/ironic/+bug/1526479

The OpenStackClient is becoming the defacto CLI client for OpenStack. This spec
will spell out what the command structure should look like, including
parameters and command names.

Problem description
===================

The OpenStackClient [#]_ has become the preferred method of creating clients
for OpenStack APIs. The initial implementation has been done. What needs to
happen is to define what the command structure should be. There has been some
confusion/discussion [#]_ about what these commands should look like, so it
seemed the proper thing to create a spec.

The goal of the OpenStackClient is to make the CLI clients more 'natural' for
the End User. This spec will specify the commands that the End User will use
when interacting with Ironic.

Proposed change
===============

The proposed implementation will have all of the commands implemented as
specified in the `Client (CLI) impact`_ section below.

In addition (or as clarification) to the OpenStackClient command
structure [#]_ :

* the OpenStackClient command structure is described as
  ``<object1> <action> <object2>``. This doesn't work if there are commands
  of the form ``<object1> <action>``. Instead, we will use the form
  ``<object1> <object2> <action>``. (Perhaps think of it as one object with
  two parts). For example, instead of "openstack baremetal node
  set maintenance" (because we have "openstack baremetal node set"), we will
  use "openstack baremetal node maintenance set".

* don't use hyphenated nouns, because the commands should be more 'natural'
  and there aren't any commands (yet) that use hyphens. For example,
  instead of "openstack baremetal node boot-device set", we are going to use
  "openstack baremetal node boot device set".

* only provide one OpenStackClient command to do something; avoid aliasing

* for naming, the trend is to use Americanised spelling, eg 'favor' instead of
  'favour'. Having said that, it is important to take into consideration
  the terminology/usage outside of OpenStack, e.g. by operators and
  administrators.

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
  --uuid <uuid>                UUID of the chassis

* openstack baremetal chassis delete <uuid> [<uuid> ...]

* openstack baremetal chassis set <uuid>

  --extra <key=value>          Property to set or update. Can be specified
                               multiple times.
  --description <description>  Chassis description

* openstack baremetal chassis unset <uuid>

  --extra <key>                Key of property to unset. Can be specified
                               multiple times.
  --description <description>  Will unset the chassis description ('')

ironic CLI users who want to see a list of nodes belonging to a given chassis
should use ``openstack baremetal node list --chassis``, since we will not
provide an ``openstack baremetal chassis xxx`` equivalent to
``ironic chassis-node-list``.

openstack baremetal driver
~~~~~~~~~~~~~~~~~~~~~~~~~~

* openstack baremetal driver list

* openstack baremetal driver show <driver>

* openstack baremetal driver passthru list <driver>

* openstack baremetal driver passthru call <driver> <method>

  <method>             Vendor passthru method to call.

  --arg <key=value>    key=value to add to passthru method. Can be
                       specified multiple times.
  --http-method <http_method>  one of 'POST', 'PUT', 'GET', 'DELETE', 'PATCH'

openstack baremetal node
~~~~~~~~~~~~~~~~~~~~~~~~

* openstack baremetal node show <uuid>

  Obsoletes: openstack baremetal show

  --instance       Interpret <uuid> as an instance UUID
  --fields <field,[field,...]>  Select fields to fetch and display.

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
  --target-raid-config <config>  Set the target RAID configuration (JSON) for
                                 the node. This can be one of: 1. a file
                                 containing JSON data of the RAID
                                 configuration; 2. "-" to read the contents
                                 from standard input; or 3. a valid JSON
                                 string.

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
  --name                 Name of the node.
  --target-raid_config   target RAID configuration

* openstack baremetal node passthru list <uuid>

* openstack baremetal node passthru call <uuid> <method>

  <method>              Vendor passthru method to be called

  --arg <key=value>     argument to send to passthru method. Can
                        be specified multiple times.
  --http-method <http_method>  One of 'POST', 'PUT', 'GET', 'DELETE', 'PATCH'

* openstack baremetal node console show <uuid>

* openstack baremetal node console enable <uuid>

* openstack baremetal node console disable <uuid>

* openstack baremetal node boot device show <uuid>

  --supported       Show the supported boot devices

* openstack baremetal node boot device set <uuid> <device>

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

* openstack baremetal node maintenance set <uuid>

  --reason <reason>         Reason for setting to maintenance mode

* openstack baremetal node maintenance unset <uuid>

* openstack baremetal node power on <uuid>

* openstack baremetal node power off <uuid>

* openstack baremetal node reboot <uuid>

* openstack baremetal node validate <uuid>

ironic CLI users who want to see a list of ports belonging to a given node
should use ``openstack baremetal port list --node``, since we will not
provide an ``openstack baremetal node xxx`` equivalent to
``ironic node-port-list``.

ironic CLI users who want the equivalent to ``ironic node-show-states`` should
use the following command::

  openstack baremetal node show <node> --fields console_enabled last_error
  power_state provision_state provision_updated_at raid_config
  target_power_state target_provision_state target_raid_config

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


Not addressed
~~~~~~~~~~~~~
OpenStackClient commands corresponding to these ironic CLI commands are not
addressed by this proposal. They will be addressed in a future release.

* ``ironic driver-raid-logical-disk-properties``.  Get RAID logical disk
                                                   properties for a driver.

* ``ironic driver-properties``.  Get properties (node.driver_info keys and
                                 descriptions) for a driver.

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

N/A

.. NOTE: This section was not present at the time this spec was approved.

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

* brad-9 <brad@redhat.com>

Other contributors:

* Romanenko_K <kromanenko@mirantis.com>
* rloo <ruby.loo@intel.com>

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
.. [#] http://docs.openstack.org/developer/python-openstackclient/commands.html
