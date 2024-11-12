..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===============================
Synchronize events with Neutron
===============================

https://storyboard.openstack.org/#!/story/1304673

Most of neutron operations are asynchronous. We need to keep track of their
results by leveraging neutron's notifications, that it can send on certain
events to ironic via HTTP calls.


Problem description
===================

Updates to Neutron resources via its API are processed asynchronously on its
backend. This exposes potential races with Ironic.

Example: an API request from Ironic to update a port's DHCP settings will
return successfully long before the associated dnsmasq config has been updated
and the server restarted. There is a potential for a race condition where
ironic will boot a machine before its DHCP has been properly configured,
especially if the machine boots very quickly (e.g. a local VM).

Another issue, that has a more serious security impact, is if Neutron failed
to bind the port when configuring the tenant network, ironic proceeds with
finishing the deployment, leaving the port bound to the provisioning network.

Ironic should be able to receive notifications from neutron when the port state
is changed. Only Ironic related ports should cause neutron to send
notifications. This spec concentrates on the binding operations, but the event
handlers can be extended further, for example to be able to process updates to
DHCP options. Here is an example of nova notifier in neutron [1]_.

In this spec, the term "notification" is used when talking about the
notifications sent by neutron. The term "event" is more generic, and is used
when talking about the payload that is received on the ironic HTTP API.


Proposed change
===============

When ironic changes neutron port information during provisioning or cleaning
(e.g. updates port binding) or creates a port (multitenancy integration), we
put the node into a ``*WAIT`` state, and pause the deployment/cleaning
waiting for neutron notification. As several ports can be updated
simultaneously, we need to put the node into a ``*WAIT`` state only after
sending the requests for all of them.

The notifications are generated on neutron side, and are sent to a dedicated
ironic API endpoint - ``/events``. The framework for this is already present,
there is no need for additional work on neutron side. Nova notifier can be
seen at [1]_. An external network event will contain the following fields::

    {
        "events": [
            {
                "event": "network.bind_port"
                "port_id": "VIF UUID",
                "mac_address": "VIF MAC address",
                "status": "VIF port status",
                "device_id": "VIF device ID",
                "binding:host_id": "hostname",
            },
            ...
        ]
    }

Event handler is an object processing the events received on the ``/events``
endpoint. This spec handles the neutron notifications case, but to make it
more generic, it is proposed to define the event handlers inside the related
driver interface, in the interface class' ``event_handler`` field. For example,
for network related events, it is going to be the following::

 class NeutronNetwork(common.VIFPortIDMixin,
                      neutron.NeutronNetworkInterfaceMixin,
                      base.NetworkInterface):
     """Neutron v2 network interface"""

     event_handler = NeutronEventHandler()

The base ``BaseNetworkEventHandler`` class will contain the following
methods::

 class BaseNetworkEventHandler(object):

     @abc.abstractmethod
     def configure_tenant_networks(self, task):
         """Ensures that all tenant ports are ready to be used."""
         pass

     @abc.abstractmethod
     def unconfigure_tenant_networks(self, task):
         """Ensures that all tenant ports are down."""
         pass

     @abc.abstractmethod
     def add_provisioning_network(self, task):
         """Ensures that at least one provisioning port is active."""
         pass

     @abc.abstractmethod
     def remove_provisioning_network(self, task):
         """Ensures that all provisioning ports are deleted."""
         pass

     @abc.abstractmethod
     def add_cleaning_network(self, task):
         """Ensures that at least one cleaning port is active."""
         pass

     @abc.abstractmethod
     def remove_cleaning_network(self, task):
         """Ensures that all cleaning ports are deleted."""
         pass

In the conductor methods that deal with network interface (e.g.,
do_node_deploy), we're going to be saving the events we are expecting in the
node's ``driver_internal_info['waiting_for']`` field and calling the network
interface methods (this will be moved to conductor from the deploy interface).
If the call is synchronous, we'll just proceed to the next one when the
previous is done, otherwise we'll be triggering the state machine 'wait' event
and saving the callback that will be called when the corresponding event is
done. All callbacks will be stored in a simple dictionary keyed by node UUID.
``driver_internal_info['waiting_for']`` is going to be a simple list of
strings, each of which is going to be the corresponding driver interface and
event handler's method name, so that we know which method of the event handler
of a specific driver interface to trigger when an action is asynchronous and
we receive the event. If an unexpected event is received, we'll be ignoring
it (and logging that an unexpected event appeared in the API).

Third-party driver interface methods can be also adding things they want to
wait for by:

* adding event names into the ``driver_internal_info['waiting_for']`` list;

* adding event names to callback mappings into global per-node ``CALLBACKS``
  dictionary, along with the arguments with which it should be called.

This will allow to wait for custom events registered in custom driver
interfaces.

Neutron does not know which method name it should include in the request
body, as it only operates on the neutron entities, it knows about things such
as port bound, port unbound, port deleted etc. We will be mapping the things
we're waiting for to things neutron passes in via the simple dictionary::

  NETWORK_HANDLER_TO_EVENT_MAP = {
      'network.unconfigure_tenant_networks': 'network.unbind_port',
      'network.configure_tenant_networks': 'network.bind_port',
      'network.add_provisioning_network': 'network.bind_port',
      'network.remove_provisioning_network': 'network.delete_port',
      'network.add_cleaning_network': 'network.bind_port',
      'network.remove_cleaning_network': 'network.delete_port',
  }

When an external network event is received, and if we're waiting for it, ironic
API performs node-by-mac and port-by-mac lookup, to check that the respective
node and port exist. The port status received in the request body is saved to
the port's ``internal_info['network_status']``, and then
``process_event`` is triggered. On the conductor side,
``process_event`` will be doing the event name to event handler method
translation via ``NETWORK_HANDLER_TO_EVENT_MAP``, and calling the event
handler. Conductor will also be dealing with state machine transitions.

The event handler will be looking at the status of the ironic resources, for
example, in case of network events, we want to save the neutron port status in
each port or port group to ``internal_info['network_status']`` and consider an
asynchronous action "done" only when port(group)s have the desired status. The
event handler method that needs to be called on the event retrieval should be
present in the event body generated by neutron. In case of desired event is
"done", it should be removed from the ``driver_internal_info['waiting_for']``
list, and the provisioning action can proceed, by triggering the 'continue'
state machine event and calling the callback that we have saved before.

To ensure that we don't wait for events forever, the usual ``*WAIT`` states
timeout periodic tasks will be used. A new one will be added for the new
``DELETE WAIT`` state. An example of such periodic task is at [2]_.

Alternatives
------------

* Using semaphores to pause the greenthread while waiting for events. This will
  make the code clearer and simpler, with only one downside -- if the conductor
  is going to be restarted, we'll loose the info about the events we wait for.
  This is still better than what we have now, and possibly can be worked
  around. Another downsides here being possible performance issues if a lot of
  greenthreads are running sumiltaneously, and the fact that conductor goes
  down during the rolling upgrade.

* Use Neutron port status polling. There is an issue with that, as even if
  the neutron port's status is ACTIVE, some actions might not have finished
  yet. The neutron's notifier framework handles this problem for us.


Data model impact
-----------------

None.

State Machine Impact
--------------------

A new ``DELETE WAIT`` state is introduced. Nodes can move to it from
``DELETING`` state, upon receiving 'wait' event.
When 'continue' event is triggered while the node is in ``DELETE WAIT``, the
node switches back to the ``DELETING`` state.
This is introduced because we need to unconfigure the tenant networks prior to
starting the cleaning.

REST API impact
---------------

The new endpoint ``POST /events`` needs to be created. The default policy for
this endpoint will be ``"rule:is_admin"``. Request body format is going to be
the following::

    {
        "events": [
            {
                "event": "network.bind_port"
                "port_id": "VIF UUID",
                "mac_address": "VIF MAC address",
                "status": "VIF port status",
                "device_id": "VIF device ID",
                "binding:host_id": "hostname",
            },
            ...
        ]
    }

Only ``event`` field is required, and it has the format of
``<event_type>.<event>``, where:

* ``<event_type>`` is a name of the interface whose event handler will be
  called, during this spec implementation only ``network`` interface handlers
  will be added.

* ``<event>`` is a name of the event that has happened, it will be converted
  to the event handler method name of the current ``<event_type>`` interface
  handler that will be called.

If the expected event handling fails, ``fail`` state machine event is triggered
by the conductor.

The normal response code to the request on this endpoint is 200 (OK), the error
codes are:

* 400 (Bad Request), in case of none of the event handlers can process the
  event.
* 404 (Not Found), in case of making a request with old API microversion
  header, or if the node can not be found by the MAC address that is sent in
  the request body.
* 401 (Unauthorized),  if the authorization has been refused for the provided
  credentials.
* 403 (Forbidden), if the user that has issued the request is not allowed to
  use this endpoint.

Client (CLI) impact
-------------------

Client will be updated to support sending an external notification. This
functionality will only be added to the client's python API, no new commands
are going to be introduced. The new method will just be passing the JSON it
receives to the ``/events`` endpoint.

This method will be used by the ironic notifier module within neutron to send
the notification to the ironic API.

RPC API impact
--------------

A new method ``process_event`` is going to be added. Received
external event is processed here.

In the conductor side of this method we compare current event we're waiting for
stored in ``driver_internal_info['waiting_for']`` field with received
``"event"`` in the event body. If we received the desired event for all
port(group)s we need, we trigger ``continue`` event on the state machine, and
the callback that was saved into the per-node ``CALLBACKS`` dictionary prior
to triggering the state machine's 'wait' is called.

Driver API impact
-----------------

As part of this change, to ensure that the network interface calls happen, and
we wait for their completion, we'll need to make the
``add_{cleaning,provisioning}_network`` network interface methods idempotent,
so that we can call them in the conductor without breaking the out-of-tree
network interfaces.

Nova driver impact
------------------

None.

Security impact
---------------

With the move of the network interface calls to conductor, and waiting for
their successful completion, we ensure that the network configuration
corresponds to what we expect, thus enhancing security, and getting rid of
bugs with giving an instance to a user that is still mapped to provisioning
network if ``remove_provisioning_network`` and ``configure_tenant_networks``
methods fail asynchronously for that port.

Other end user impact
---------------------

The neutron notifier needs to be configured. It needs the keystone admin
credentials and (optionally, if not provided will be discovered from keystone
endpoint catalog) the ironic API address to send events to.

Scalability impact
------------------

None.

Performance Impact
------------------

The node provisioning and unprovisioning may take some additional time when
we'll be waiting for the external events.

Other deployer impact
---------------------

None.

Ramdisk impact
--------------

None.

Developer impact
----------------

Developers will be able to create the needed event handlers for whatever
events they would like to use during provisioning, and add those to the driver
interfaces.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  vdrok

Other contributors:
  None

Work Items
----------

#. Add the event handlers to neutron and flat network interfaces.

#. Add the ``process_event`` conductor method, that will be handling
   the events.

#. Add the ``/events`` endpoint.

#. Implement the client side of changes.

Dependencies
============

* Nova should be cleaning up only the ports owned by "compute" in case of the
  InstanceDeployFailure [3]_.

Testing
=======

Integration and unit testing will be provided.

Upgrades and Backwards Compatibility
====================================

This does not affect the usual upgrade procedure. To make use of events, both
API and conductor need to be upgraded. During upgrade, the ironic notifier
needs to be configured in neutron. There is going to be no need to enable this
feature, it will be enabled by default.

In case of rolling upgrade, ironic conductors are upgraded first, then ironic
APIs, then neutron is reconfigured to enable the notifier.

If we decide to make all the network interface calls asynchronous, step of
enabling notifier in neutron becomes obligatory, otherwise an operator will
have to send the notifications to ironic API manually, or the deployment will
be failing by timeout as no network event is going to be received. This bit
might need to be revisisted during review :)

Documentation Impact
====================

This feature will be documented in the developer documentation and API
reference.

References
==========

.. [1] https://github.com/openstack/neutron/blob/master/neutron/notifiers/nova.py
.. [2] https://github.com/openstack/ironic/blob/f16e7cdf41701159704697775c436e9b7ffc0013/ironic/conductor/manager.py#L1458-L1479
.. [3] https://bugs.launchpad.net/nova/+bug/1673429
