..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==================================
Add notification support to ironic
==================================

https://blueprints.launchpad.net/ironic/+spec/notifications

Near real-time inter-service notifications in OpenStack have a variety of use
cases. At the Mitaka design summit, some of the use cases discussed for ironic
included integration with billing systems, using notifications to support an
operations panel to keep track of potential failures, and integration with
TripleO. [#]_ Nova has supported some form of notifications since the Diablo
cycle. [#]_ This spec proposes a design for a general notification schema
that's versioned and structured but extensible enough to support future needs.

Problem description
===================

Ironic doesn't currently support any type of notifications for external
services to consume.

This makes it difficult for operators to monitor and keep track of events in
ironic like node state changes, node power events, and successful or failed
deployments. Sending notifications that contain relevant information about a
node at different points in time, like state transitions, would make it easier
for operators to use external tools to debug unexpected behavior.

Not having notifications also makes it difficult for external services to
identify state changes in ironic. Nova and inspector have to poll ironic
repeatedly to see when a state change has occurred. Adding notifications for
cases like these will allow ironic to push out these event changes rather than
putting the bulk of this burden on external services.

This is especially problematic if ironic were ever to be used in a standalone
deployment without a external service like Nova that keeps track of resources
and emits its own notifications, since the deployers of ironic wouldn't have
any way to keep track of any state changes outside of querying the ironic API
periodically or looking at logs.


Proposed change
===============

Notification support will be added to ironic using the notifier interface from
oslo.messaging. [#]_ oslo.messaging uses the following format for
notifications::

    {'message_id': six.text_type(uuid.uuid4()),
     'publisher_id': 'compute.host1',
     'timestamp': timeutils.utcnow(),
     'priority': 'WARN',
     'event_type': 'compute.create_instance',
     'payload': {'instance_id': 12, ... }}

Ironic notifications will adhere to that format.

Base classes will be created to model the notification format. The fields of
the notification that aren't auto-generated (everything except message_id and
timestamp) will be defined as follows for ironic:

* publisher_id will be taken from the service emitting the notification and the
  hostname

* priority will be one of DEBUG, WARN, INFO, or ERROR, depending on the
  notification. Whichever level a notification uses should follow the OpenStack
  logging standards. [#]_

* event_type will be a short string describing the notification.
  Each string will start with "baremetal." to distinguish ironic notifications
  from other notifications on the message bus.

  This will be followed by the object that's being acted on, optionally the
  field of the object being acted on, a descriptor of the action being taken,
  and the phase of the action ("start", "end", potentially "fail"), if
  applicable. event_type will have a base class defining these fields, with
  subclasses for each type of event that occurs. These subclasses will be
  versioned objects. Each of these fields will be separated by a period in the
  event_type string sent with the notification.

  A few examples of potential event_type strings:

  * "baremetal.node.set_power_state.start"
  * "baremetal.node.set_power_state.end"
  * "baremetal.node.state_change.start"
  * "baremetal.node.state_change.end"
  * "baremetal.conductor.start"
  * "baremetal.conductor.stop"

* payload will be a versioned object related to the notification topic. This
  should include relevant information about the event being notified on. For
  the notifications above about a node, for example, we would send an object
  containing a limited subset of the fields of the Node object, removing
  sensitive fields like private credentials as well as fields with an unknown
  length, along with the version of the notification object. A separate
  versioned notification object must be created for each type of notification
  to keep notification versions separate from other object versions in ironic.
  This is to prevent notifications from automatically changing as new fields
  are added to other objects like the Node object.

The initial implementation will consist of the base classes needed for modeling
the notification format and emitting notifications as well as the power state
notifications described above.

Alternatives
------------

One alternative would be to modify oslo.messaging's notifier interface to
provide the base class defining a notification as a versioned object. The
advantage of this is that we wouldn't have to rely on the payload to do
versioning. The disadvantage is that it would require significant changes to
oslo.messaging which affect other projects and require changes to every
notification consumer as well as any downstream tooling built around the
existing notification format.

We could also have a global notification version that gets incremented with
each change to any notification. This doesn't seem desirable because it could
potentially miss changes if a separate ironic object included in the payload
like the Node object gets changed and the notification itself doesn't get its
version bumped.

Data model impact
-----------------

No database changes will be required for this feature.

The change will introduce new versioned base objects for the general
notification schema and additional subclasses for individual notification
types. The base classes will look similar to those in the proposal in the nova
versioned notifications spec. [#]_

State Machine Impact
--------------------

No impact on states or transitions themselves.

Notifications will be sent out on node provision state changes if notifications
are enabled. This can be achieved by sending notifications every time a
TaskManager's process_event method starts and successfully executes.

All information related to a node's previous, current, and new target state
will be included in the notifications. The .start notification will have the
current provision_state before the state change and the target_provision_state.
After an event is successfully processed, the .end notification will include
the current provision_state (the .start notification's target state) and the
new target_provision_state. The notifications will also include the name of the
event that caused the state change. This will be useful for disambiguating
between cases where there are multiple potential transitions from one state to
another.


REST API impact
---------------

None.

Client (CLI) impact
-------------------

None.

RPC API impact
--------------

No impact from an API standpoint.

Modifications to the implementation of certain conductor RPC API methods will
need to be made for notifications that are sent when an RPC is dispatched to a
worker, however. See Driver API Impact for an example of how this might be done
for power notifications.

Driver API impact
-----------------

No impact from an API standpoint.

Notifications related to power state changes will be added, but that can be
done without modifying any of the driver classes in the following manner:

1) Send a baremetal.node.set_power_state.start notification after the
   ConductorManager receives the change_node_power_state call as a conductor
   background task.

2) On success, after the dispatched call to node_power_action finishes without
   raising an exception, send a baremetal.node.set_power_state.end
   notification.

3) On error, the power_state_error_handler hook will be called in the conductor
   manager. Send a baremetal.node.set_power_state.error notification here.

Nova driver impact
------------------

None.

Security impact
---------------

None.

Other end user impact
---------------------

None, except a message bus will have to be used if a deployer wants to use the
notification system.

Scalability impact
------------------

When enabled, notifications will put additional load on whichever message bus
the notifications are sent to.

Performance Impact
------------------

When enabled, code to send the notification will be called each time an event
occurs that triggers a notification. This shouldn't be much of a problem for
ironic itself, but the load on whatever message bus is used should be
considered (see Scalability Impact).

Other deployer impact
---------------------

The following configuration options will be added:

* The notification_transport_url option needed by oslo.messaging. [#]_ Defaults
  to None which indicates that the same configuration that's used for RPC will
  be used.

* A notification_level string parameter will be added to indicate the
  minimum priority level for which notifications will be sent. Available
  options will be DEBUG, INFO, WARN, ERROR, or None to disable notifications.
  None will be the default.

  An alternative to the notification_level global config option would be to
  create specific config options defining whether a particular notification
  type should be sent. This is what nova does, but summit discussions indicated
  that consistency is preferable.

Developer impact
----------------

Developers should adhere to proper versioning guidelines and use the
notification base classes when creating new notifications.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  * mariojv

Other contributors:
  * lucasagomes

Work Items
----------

* Create notification base classes and tests
* Write documentation for how to use the base classes consistently across all
  ironic notifications
* Implement an example of a notification for when a node power state is changed

Dependencies
============

None.

Testing
=======

Unit tests for both the base classes and the node power state notification will
be added.

Upgrades and Backwards Compatibility
====================================

No impact, but modifications to notifications created in the future must be
checked for backwards compatibility.

Documentation Impact
====================

* Developer documentation will be added for how to add new notifications or
  modify existing notifications
* Document an example of what an emitted notification will look like

References
==========

.. [#] Summit discussion: https://etherpad.openstack.org/p/summit-mitaka-ironic-notifications-bus
.. [#] https://blueprints.launchpad.net/nova/+spec/notification-system
.. [#] http://docs.openstack.org/developer/oslo.messaging/notifier.html
.. [#] https://wiki.openstack.org/wiki/LoggingStandards#Log_level_definitions
.. [#] Nova versioned notifications spec: https://github.com/openstack/nova-specs/blob/master/specs/mitaka/approved/versioned-notification-api.rst
.. [#] http://docs.openstack.org/developer/oslo.messaging/opts.html

