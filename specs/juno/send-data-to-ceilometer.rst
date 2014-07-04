..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Send Sensor Data to Ceilometer
==========================================

https://blueprints.launchpad.net/ironic/+spec/send-data-to-ceilometer

This blueprint will define the sensor data collection interface and implement
a driver based on IPMI to collect sensor data and send them to Ceilometer.


Problem description
===================

Ceilometer needs the hardware level performance/status data collection from
monitored physical nodes. Ironic owns the IPMI credential, so that is easy for
Ironic to get IPMI sensor data and send to Ceilometer via OpenStack common
AMQP notification bus.


Proposed change
===============

* Creates a new ironic.driver.base.ManagementInterface common method
  *get_sensors_data* for gathering hardware sensor data:

  def get_sensors_data(self, task):
      """ Get the sensors data from physical node

      This method get_sensors_data() will return a dict which is the common
      data structure to support both IPMI and non-IPMI sensors as below:
      'Sensor Type' -> 'Sensor ID' -> 'Field':'Value'
      The sensor current reading value should be found in 'Sensor Reading'
      field.

      :returns: a consistent format dict of sensor data group by sensor type,
                which can be processed by Ceilometer.

      """

  Example of actual message: http://paste.openstack.org/show/85130/



* Implements the interface into 'ipmitool' driver to gather data via IPMI
  command call.

  We call IPMI command 'ipmitool sdr -v' to retrieve sensor data. With '-v'
  option we get the entire sensor data including the extended sensor
  information and the current value in 'Sensor Reading' field.

  Here is an example which is the command return result:

  http://paste.openstack.org/show/63267/

  So we can translate the result to a dict format which is grouped by 'Sensor
  Type'. For different types, we have different field names. By default, the
  IPMI node can support the basic three types: 'Fan', 'Temperature', and
  'Voltage'.

  The non-varying sensors which have no 'Sensor Reading' field will be filtered
  out and will not be sent to Ceilometer.

* Adds periodic task to conductor which emits notification to Ceilometer by an
  interval.

  New *periodic_task* method *_send_sensor_data* will be added into
  *ironic.conductor.manager*.
  It calls get_sensor_data for all deployed nodes. If get_sensor_data returns
  None (not implemented) for the node, does not send anything.


  Supports configurations options:

  conductor.send_sensor_data - boolean value, whether to enable collecting
  and sending sensor data, default value is False.

  conductor.send_sensor_data_interval - Seconds between conductor sending
  sensor data message to Ceilometer via the AMQP notification bus. The default
  value is 600.

  Here is the sample message which will be sent to Ceilometer:

  http://paste.openstack.org/show/85053/

* Supports 'send_sensor_data_types' configuration option, where we could list
  what types of data user want to send, that would allow people to tune which
  type of data they want to consume and not waste bandwidth sending everything
  all the time. By default we could send everything. Examples:

  * Default option setting:

    send_sensor_data_types=ALL
    #by default, send all which has 'Sensor Reading' field, required by
    Ceilometer.

  * For customization setting:

    send_sensor_data_types=Temperature,Fan,Voltage,Current
    #which match sensor data's 'Sensor Type' field value.


Alternatives
------------

* An alternative way to do it is that we can enable our 'ipminative' driver to
  support IPMI sensor data collection, using *pyghmi* lib *get_sensor_data*
  command method call to access IPMI node.

  However this *get_sensor_data* is one new command introduced recently in
  latest release still not stable now, I did some testing with physical server,
  it still does not work, some IPMI sensor raw data can not be parsed by
  *get_sensor_data* command.

  So we will support 'ipminative' driver later with a separate spec.



* For the *interface* with Ceilometer, we have alternative way to call
  Ceilometer API directly to avoid less-secure AMQP medium.

* We can allow sensor types to be collected configurable so that it will only
  collect the sensor data of interest. The default can be all sensors. This can
  be an optional feature that some Ironic drivers (IPMI dirver or non-IPMI
  vendor drivers) may choose to support later with a separate spec.

* Another way, Ceilometer can pull Ironic API *get_sensors_data* to retrieve
  the sensor data actively.

Data model impact
-----------------

None

REST API impact
---------------

The management interface will expose the new method *get_sensors_data*. User
can call this api to retrieve the sensors data.

Driver API impact
-----------------

A new function called *get_sensors_data* will be added to the
*ironic.driver.base.ManagementInterface*.



Nova driver impact
------------------

None

Security impact
---------------

We emit notification to Ceilometer via AMQP, AMQP-mediated interactions are
assumed to be secure.


Other end user impact
---------------------

None

Scalability impact
------------------

None

Performance Impact
------------------

Have some Performance impact about the periodic tasks, they run one after the
other in a single greenthread. So periodic tasks like this which poke the BMC
will affect the timing of other periodic tasks waiting to run.


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
  Haomeng, Wang(LP ID == whaom)

Other contributors:
  Co-work with Ceilometer team developer Chris Dent (LP ID == chdent)

Work Items
----------

- Add a new function interface, *get_sensors_data*, in
  *ironic.drivers.base.ManagementInterface*.

- Add support in *ipmitool* driver to call IPMI command to get sensor data.

- Add periodic task to conductor to send data by a default interval.

Dependencies
============

The data notification structure defined by Ironic should be confirmed with
Ceilometer team to consume the notifications as well.

So will work with Ceilometer team and fix the structure on demand.

Testing
=======

We will have at least unit tests. But for the IPMI data collection with
physical server integration, it is difficult for us to do the *real* testing
in CI.


Documentation Impact
====================

Documentation will be extended to explain how it works, and what drivers are
supported, and how to enable it.


References
==========

* `Ceilometer spec`_
* `Review in progress`_ for sending notifcation from Ironic.
* `Sample data`_

.. _Ceilometer spec: https://blueprints.launchpad.net/ironic/+spec/send-data-to-ceilometer
.. _Review in progress: https://review.openstack.org/#/c/72538/
.. _Sample data: http://paste.openstack.org/show/85053/



