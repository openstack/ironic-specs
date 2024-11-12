..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Support per driver sensor meters
==========================================

https://blueprints.launchpad.net/ironic/+spec/support-per-driver-sensor-meters

This blueprint is for changing the Ironic Conductor _send_sensor_data interface
implementation to support sending sensor meters from providers other than IPMI
to Ceilometer.

Problem description
===================

The current implementation of _send_sensor_data is IPMI specific in a number of
ways.  The Conductor will only acquire sensors from a node which is deployed
(has an instance_uuid) and the notifications sent by the Conductor to
Ceilometer go to an IPMI specific Ceilometer plugin via event type
hardware.ipmi.metrics.

I would like to be able to provide health (and potentially other) sensor
information from an iLO Management driver by implementing an iLO specific
driver.management.get_sensors_data() interface.  The sensor information
provided by the iLO Management driver should not be treated as IPMI sensors.
Also, health information about a platform should be available even if the node
has not yet been deployed with software.

Proposed change
===============

The Ironic Conductor _send_sensor_data routine should always call the
underlying driver.management.get_sensors_data routine at each poll interval.
It should be the responsibility of the underlying management get_sensors_data
routine to determine if it is appropriate to gather sensor information for the
node that it manages.  If a driver determines it is not appropriate to gather
sensor information for a node, the driver should simply return an empty sensor
list.

The Conductor should not need to interpret who the sensor provider is in
order to send the sensor information along to the metering system.

I see the Conductor's role in sensor metering as follows:

* Call Management Driver to read sensors at a specifiable interval

* Create per meter naming using the information provided in the sensors
  returned by the Management Driver.  This will ensure consistent meter naming
  across multiple providers.  It will also enable consistent meter naming for
  other metering systems (like Monasca) in the future.

* The Conductor must include the Ironic Node UUID in the message sent to the
  metering system so that the Ironic Node UUID will be included in the sensor
  meters that are created upon receipt of the message.

With the current implementation, per meter naming is not the responsibility of
the Conductor, but the responsibility of the metering system plugin.

I would like to propose a generic Ceilometer sensor notification plugin that
will not need to be modified to support new sensor types.  To create such a
plugin will require that the Ironic Conductor format sensor meters with
sufficient information for the metering system plugin to create the samples per
sensor meter without performing any sensor data transformations.  To accomplish
this, the Ironic Conductor will need to implement some operations currently
being performed by the Ceilometer plugin, like sensor meter naming, Resource ID
naming, and sensor reading parsing.  Also, any sensor fields added by the
Ceilometer notification plugin, like 'node' will need to be created by the
Ironic Conductor.

I would like to introduce a per sensor provider ID field in the driver returned
sensor dictionary so that consumers of the sensor resource_metadata can
identify the driver that provided the sensor.   This field will be named
'sensor_provider' and it will be set to a unique text value per driver.   For
the ipmitool driver, the value will be "ipmi" and for the HP iLO driver, it
will be "ilo".  Adding this field to each sensor record will require changing
each driver that implements the get_sensors_data interface.

In order to support these Conductor changes, a new Ceilometer notification
plugin will be needed and the naming for sensors in Ceilometer will need to be
changed.  See the Dependencies section for the Ceilometer blueprint associated
with creation of the generic sensor Ceilometer plugin.

Alternatives
------------

An additional Ceilometer plugin could be created for each sensor provider, but
this would require quite a bit of code duplication in each plugin.  Also, the
Conductor would need to have a mapping from the Ironic driver producing the
sensors to the appropriate Ceilometer plugin that the sensor should be sent to.

The generic sensor Ceilometer notification plugin and associated Conductor
changes for supporting multiple providers could be implemented without any
changes to the currently defined Ceilometer meter naming.   This would be
accomplished by placing the sensor provider name in the Ceilometer
meter name.    i.e. hardware.ilo.temperature for an iLO driver provided
temperature sensor.

Data model impact
-----------------

None

REST API impact
---------------

None

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

To support provider independent meter naming will require changing the user
visible meter names for sensors in Ceilometer.  The new provider independent
naming will not be backward compatible with the names used for sensor meters in
the Juno release.  Here is an example of Ceilometer plugin created meter names
for sensors in Juno.

::

| Name                     | Resource ID
| hardware.ipmi.current    | IronicNodeUUID-power_meter_(0x16)
| hardware.ipmi.temperature| IronicNodeUUID-16-system_board_(0x15)


The proposal is to drop the ipmi component string from the meter name so that
meter names become provider independent.  Transforming the above to the
proposed meter naming would result in the following meter names in Ceilometer.

::

| Name                | Resource ID
| hardware.current    | IronicNodeUUID-power_meter_(0x16)
| hardware.temperature| IronicNodeUUID-16-system_board_(0x15)

There are also non Ironic sensor polling agents implemented in Ceilometer which
use the ipmi component string in their meter names. These polling agents could
updated to adhere to the proposed ironic naming as well.  The impact on these
polling agents would be to remove the ".ipmi" identifier from the meter names
generated by the polling agent as is shown above.  Examples of meter names
generated by the IPMI and Intel Node manager polling agents are as follows:

::

| Name                          | Resource ID
| hardware.ipmi.current         | CONF.host-IPMI_SensorID
| hardware.ipmi.temperature     | CONF.host-IPMI_SensorID
| hardware.ipmi.node.temperature| CONF.host
| hardware.ipmi.node.power      | CONF.host

Note:  Even though 'hardware.ipmi.node.*' meters appear to be IPMI sensor
types, they are in fact vendor specific Intel Node Manager sensors.

Modifications to the polling agents to change their sensor naming convention is
not within the scope of work defined by this specification.

Scalability impact
------------------

None

Performance Impact
------------------

None

Other deployer impact
---------------------

Changing the Conductor to send notification messages to a new generic sensor
Ceilometer plugin will require updating Ceilometer in conjunction with the
Conductor if Ironic to Ceilometer sensor metering is enabled.

Developer impact
----------------

There will be a Conductor dependency on a the generic Ceilometer plugin in
order for sensor metering to occur.  Developer coordination of changes to
Ceilometer and the Ironic Conductor will be necessary for verification of
operation.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  <jmank@hp.com>

Other contributors:
  <None>

Work Items
----------

* Change the Conductor to remove all IPMI sensor related assumptions.

* Change the get_node_info_list query to not filter based on associated being
  true and move instance_uuid check into the ipmitool and ipminative drivers.

* Create a SensorMetrics base class and CeilometerSensorMetrics derived class
  to implement meter naming, sensor packaging  and sensor posting.  The
  Conductor will be modified to instantiate a CeilometerSensorMetrics class at
  initialization and invoke the SensorMetrics send_sensors interface from the
  the Conductor _send_sensor_data periodic timer routine.

The intent of the SensorMetrics class is to encapsulate any sensor data
transformations necessary for the targeted metering system.

::

    @six.add_metaclass(abc.ABCMeta)
    class SensorMetrics(object):
        @abc.abstractmethod
        def send_sensors(self, context, task, sensors):
            """Send Sensors in the list to the metering system

            : param context: request context
            : param task: TaskManager instance with shared lock
            : param instance_uuid: Running instance UUID or None if not
                                   deployed
            : param sensors: List of Sensors to send to metering system
            """


Dependencies
============

This work is dependent on the following Ceilometer blueprint and specification.

* https://blueprints.launchpad.net/ceilometer/+spec/generic-notification-sensor-meter-plugin

Testing
=======

Unit tests will be need to be added to verify the new code paths.  I plan on
doing ProLiant platform testing of the capabilities as well.


Upgrades and Backwards Compatibility
====================================

These changes to the Conductor will require installation of the Ceilometer
generic sensor notification plugin if the sending of sensor data messages is
enable for the Conductor via "send_sensors_data=true".    If Ironic is updated
without adding the generic sensor notification plugin, sensor data messages
will be sent, but they will not show up as meters in Ceilometer.
Documentation will need to be updated to indicate that Ironic Conductor sensor
data sending is dependent on the generic Ceilometer notification plugin for
Ceilometer.

If the new meter naming scheme is adopted, prior sensors already in the
Ceilometer database will retain their prior naming, so post upgrading to the
new Conductor and generic sensor Ceilometer plugin will cause a loss in
continuity in sensor naming.   Also, any existing Ceilometer sensor meter
queries based on the Juno sensor meter naming scheme will need to be changed to
use the Kilo sensor meter naming scheme.

Documentation Impact
====================

Documentation changes to docs/source/deploy/install-guide.rst will be necessary
to cover the visible functional changes as well as the upgrade dependency
with Ceilometer.

References
==========

* [openstack-dev] [Ironic][Ceilometer] Proposed Change to Sensor meter
  naming in Ceilometer
  http://lists.openstack.org/pipermail/openstack-dev/2014-October/048631.html
