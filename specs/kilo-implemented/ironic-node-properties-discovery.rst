..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==============================================================
Discover node properties with node-set-provision-state
==============================================================

Blueprint URL:
https://blueprints.launchpad.net/ironic/+spec/ironic-node-properties-discovery

This proposal adds the ability to perform out-of-band node
inspection and automatically update node properties using
node-set-provision-state (new target 'inspect') process. The same set of
APIs can be used by in-band properties discovery too.

Problem description
===================

Today, Ironic is unable to automatically detect node properties
which are required for scheduling or for deploy (ports creation).

The properties required by scheduler/deploy:

* memory size

* Disk Size

* CPU count

* CPU Arch

* NIC(s) MAC address

Proposed change
===============

The spec proposes to add these abilities:

1. Discover the hardware properties and update the node.properties.
   It update all the properties with the new set values, even if the
   values were already set.

2. Create ports for the NIC MAC addresses discovered. This will be done
   automatically after the NICS are discovered with above step.
   If a port already exists, it will not create a new port for
   that MAC address. It will take care of adding as well as deleting
   of the ports for the NIC changes. The ports no longer associated with
   the node at the time of discovery will be auto deleted.
   Ideally the ports shall be created for PXE enabled mac addresses,
   however it is each driver responsibility to get list of pxe enabled
   mac addresses from the hardware.

Following would be done to achieve properties inspection:

* A new target 'inspect' would be added to the end point provision
  /v1/nodes/<uuid>/states/provision

* When inspection is finished, puts node.provision_state as MANAGED
  and node.target_provision_state as None.

* The possible new states are:
  INSPECTING, INSPECTFAIL, MANAGED, INSPECTED.

  Refer to [1] for more details on each state.

  Initial state :
  node.provision_state = INSPECTING
  node.target_provision_state = INSPECTED

  On Success:
  Final State :
  node.provision_state = MANAGED
  node.target_provision_state = None

  On Failure:
  Final State:
  node.provision_state = INSPECTFAIL
  node.target_provision_state = None
  And the error is updated at the last error.

  The provision state will be marked as INSPECTFAIL if any
  of the properties (scheduler required properties) could
  not be inspected. In this case, no properties will be updated.
  So its either all or none.

  A node must be in MANAGED state before initiating inspection.

* The properties values will be overwritten with every invocation
  of discovery APIs. It is done so because there may be addition/deletions
  in the hardware between two invocations of the discovery CLI/APIs.

* Implement timeouts for inspection. There should be a periodic task in the
  conductor, checking that every mapped node is not in INSPECTING state for
  more then ``inspect_timeout``. This will be added as a config
  option in /etc/ironic/ironic.conf.

The Node.properties introspected properties will be updated whenever
introspection is executed.

Hardware properties to be discovered:
-------------------------------------
The following properties would be discovered :

* NICs mac addresses

* cpus

* cpu_arch

* local_gb

* memory_mb

The NICs data would be used to auto-create the ports.
The other properties are mandatory properties for the scheduler,
hence will be updated in Node.properties field.

Alternatives
------------

The discovery can be initiated by node-create with single request to the API
as below:

POST /v1/nodes/?discover=true :

In this, it requires the Nodes.post to be completely asynchronous.
This would be a compatibility break for node-create as it requires a
node object to be returned back. On the other hand, if discovery is done
synchronously then Nodes.post will become slow.
In this if Nodes.post still returns the node object without properties
updated to the CLI and still do discovery in the background then Nodes.post
becomes half synchronous and half asynchronous, then it will be wrong for REST
API structure as the REST API shall be either synchronous or asynchronous.
Hence, here node-create becomes partly synchronous and partly asynchronous.
Given above reasons, this approach is not chosen.

The auto-discovery can also be used for discovering node properties
but it also doesn't provide the ability to discover properties at
node-create and node-set-provision-state.

Data model impact
-----------------

The discovered properties will be stored as part of the 'properties'
field of the node. It will add two fields to the ``nodes`` table:

1.  ``last_inspected``: It will be updated with time (when last inspection
    finished).

2.  ``inspection_started_at``: It will store the start time of
    invocation of inspection. This will be required to
    calculate the ``inspection_timeout``.
    It shall be cleared out after inspection finishes or timeout.

Ironic CLI impact
-----------------

The node-set-provision-state target 'inspect' need to be defined.
The synopsis will look like:

usage: ironic node-set-provision-state <UUID> inspect

REST API impact
---------------

The endpoint 'provision' will be enhanced with a new target:

* PUT /v1/nodes/<uuid>/states/provision {"target": "inspect"}

  * Changes provision_state as INSPECTING.

  * Changes target_provision_state as INSPECTED.

  * Method type: PUT

  * Normal response code: 202

  * Expected errors:

    * 404 if the node with <uuid> does not exist.

    * 400 if a conductor for the node's driver cannot be found.

    * 409 CONFLICT, if the node cannot be transitioned to INSPECTING
      state.

  * URL: /v1/nodes/<uuid>/states/provision {"target": "inspect"}

  * URL parameters: None.

  * Response body is empty if successful.

  * When inspection is finished, puts node.provision_state as MANAGED
    and node.target_provision_state as None.

RPC API impact
--------------

* A new rpcapi method inspect_hardware() will be added.
  It will be synchronous call to the conductor and will spawn a worker
  thread to perform discovery.
  This will allow the API service to receive the acknowledgement
  from the conductor that the inspecting has been initiated and returns
  status 202 to the client.

Driver API impact
-----------------

It will add new interface InspectInterface with
the method inspect_hardware()::

    def inspect_hardware(self, task):
        """Inspect hardware.

        :param task: a task from TaskManager.

        """

A driver may choose to implement the InspectInterface.

Since InspectInterface is a standard interface, following methods
will also be added:

* validate()

* get_properties()

Nova driver impact
------------------

None.

Security impact
---------------

None.

Other end user impact
---------------------

This feature will improve user experience as users no longer
need to manually update the node properties info.

Scalability impact
------------------

None.

Performance Impact
------------------

None.

Other deployer impact
---------------------

The ``inspect_timeout`` is introduced in the ironic.conf under
conductor. The default value for same shall be 1800 secs as
required by in-band implementations.

Developer impact
----------------

The drivers who need to implement base.InspectInterface(),
may decide to implement/define the abstract methods added by this
proposal.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
    Nisha Agarwal (launchpad ID: agarwalnisha1980, IRC login ID: Nisha)

Other Contributors:
    Wan-Yen Hsu (launchpad ID : wan-yen-hsu, IRC login ID: wanyen)

Work Items
----------

* A new rpcapi method inspect_hardware() is added which
  will invoke the InspectInterface for discovering, updating node properties
  and creating/updating ports.

* Add a new interface as InspectInterface to ironic driver.

* Adding new method inspect_hardware to class InspectInterface.

* Add new elements ``last_inspected`` and ``inspection_started_at`` to
  the ``nodes`` table. Ironic cli will be changed to show these fields
  while running ``ironic node-show``.

* The node.last_inspected  will be updated with the last discovered time.

* The node.inspection_started_at will be updated with the time when
  inspection was initiated. This will help to check the timeout for
  inspection. The periodic task needs to be created for the same.

* The reference implementation will be done for iLO drivers.

* Add a new target 'inspect' to node-set-provision-state for updating the
  hardware properties for already registered node.(ironic-client
  changes)

Dependencies
============

Requires implementation of
http://specs.openstack.org/openstack/ironic-specs/specs/kilo/new-ironic-state-machine.html
for the states MANAGED, INSPECTED, INSPECTING and INSPECTFAIL.

Testing
=======

Unit tests will be added conforming to ironic testing requirements.
The test suites for tempest can be written for specific implementations.

Upgrades and Backwards Compatibility
====================================
No impact.

Documentation Impact
====================

It needs to be documented properly.

References
==========

[1] All possible states for a ironic node spec:
http://specs.openstack.org/openstack/ironic-specs/specs/kilo/new-ironic-state-machine.html
