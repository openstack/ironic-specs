..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=========================================
Promote agent vendor passthru to core API
=========================================

https://bugs.launchpad.net/ironic/+bug/1570841

This spec suggests making the current agent vendor passthru API (lookup and
heartbeat) first class API endpoints and deprecate the agent vendor passthru
interface.

Problem description
===================

The vendor passthru was designed for vendors to place their specific features
before they get wider adoption in Ironic and get promoted to the core API.

However, when IPA is used (which is the only ramdisk available in-tree), these
two API endpoints play the critical role in both deployment and cleaning
processes. Thus every IPA-based driver must mix agent vendor passthru into
its vendor passthru.

There was a bug in the drac driver when it was not done, and the driver
did not work with IPA.

This proposal also tries to reduce the amount of data sent to and from
unauthenticated endpoints. The current vendor passthru API accepts the whole
inventory and returns the whole node record, including IPMI credentials.

Proposed change
===============

* Create new API endpoints for lookup and heartbeat - see `REST API impact`_
  for details.

* Extend the deploy interface with a heartbeat method - see
  `Driver API impact`_ for details.

Alternatives
------------

* Continue doing what we do now.

* Make the lookup call driver-dependent (as the passthru used to be).

  This looks like unnecessary complication (e.g. we have to pass a driver to
  IPA from the conductor nowadays).

* We could use this change to move the unauthenticated endpoints away from the
  main API completely. This could be done by introducing a new API service,
  say ``ironic-agent-api``, serving only these two endpoints. Then we will
  recommend operators to make this service only listen on the provisioning
  network, but not on the network accessible to users.

  Arguably the same result can be achieved by configuring a WSGI container
  (Apache mod_wsgi or similar), so it might not be worth complication.

Data model impact
-----------------

None

State Machine Impact
--------------------

None

REST API impact
---------------

Two new endpoints are added. Both endpoints are **NOT** authenticated.

* ``GET /v1/lookup?addresses=MAC1,MAC2&node_uuid=UUID``

  Look up node details for further use in the ramdisk.

  No body; at least one of the following URL parameters must be present:

  * ``addresses`` comma-separated list of hardware addresses (e.g. MAC) from
    the node for lookup;

  * ``node_uuid`` node UUID, if known (e.g. by inspection).

  If ``node_uuid`` is present, ``addresses`` are ignored.

  By default only return a node if it's in one of transient states:
  ``deploying``, ``deploy wait``, ``cleaning``, ``clean wait``,
  ``inspecting``, ``inspect wait``. Deployers who need lookup to always work
  will be able to set a new option ``[api]restrict_lookup`` to ``False``.

  .. note::
     In theory, we don't need ``-ing`` states here either. But when we reboot
     during cleaning, we don't currently reset the state to ``clean wait``.
     The other ``-ing`` states are supported in case 3rd party drivers have
     similar restrictions.

  Response: HTTP 200 with JSON body containing keys:

  * ``config`` dictionary for passing configuration options from conductor
    to the ramdisk. For the IPA ramdisk only one is currently used:

    * ``heartbeat_timeout`` timeout (in seconds) between heart beats from
      the ramdisk, expected by Ironic.

  * ``node`` partial node representation as a JSON object, with the following
    fields sent:

    * ``properties`` for root device hints,
    * ``instance_info`` for disk sizing details,
    * ``uuid`` node UUID,
    * ``driver_internal_info`` for passing other runtime information.

    More fields can be exposed with time with an appropriate API version bump.

  Error codes:

  * 400 - bad request,

  * 404 - a node was not found.

* ``POST /v1/heartbeat/<UUID>``

  Record a heartbeat message from the ramdisk.

  Body is a JSON with fields:

  * ``callback_url`` - the IPA URL to call back. Note that for potential
    non-IPA-based drivers it might have a different meaning (e.g. if we agree
    on the ansible driver, this can be an SSH "URL" for it).

  Response: HTTP 202 with no body.

  Error codes:

  * 400 - bad request,

  * 404 - a node was not found,

  * 409 - node is locked (should be retried by the ramdisk).

A new API version will be introduced to cover both endpoints.

Client (CLI) impact
-------------------

Both endpoints will be exposed in the Python API for the ironic client as::

    ironic.node.lookup(addresses, node_uuid=None)
    ironic.node.heartbeat(node_uuid, callback_url)

However, as they are not intended for end users, they will not be exposed in
both CLI.

"ironic" CLI
~~~~~~~~~~~~

None

"openstack baremetal" CLI
~~~~~~~~~~~~~~~~~~~~~~~~~

None

RPC API impact
--------------

A new RPC call is created to connect the heart beat API endpoint and
the new deploy driver method: ``heartbeat`` (async).

Driver API impact
-----------------

A new method is added to the deploy driver interface:

::

    def heartbeat(self, task, callback_url):
        """Record a heart beat for the node.

        :param task: a task manager task
        :param callback_url: a URL to use to call to the ramdisk
        :return: None
        """
        LOG.warning('Got hearbeat message from node %(node)s, but the driver '
                    '%(driver)s does not support heartbeating',
                    {'node': task.node.uuid, 'driver': task.node.driver})

The heartbeat method from ``BaseAgentVendor`` will be refactored to a separate
mix-in class for reusing in both ``AgentDeploy`` and ``BaseAgentVendor``.

The new method will not be abstract to allow drivers that use a different
approach (e.g. which do not have a ramdisk at all). The default implementation
will do nothing to account for deploy drivers which do not need heart beats.

The new method will receive a shared node lock. It is up to the implementation
to upgrade the lock to exclusive, if required.

Nova driver impact
------------------

None

Ramdisk impact
--------------

None

Security impact
---------------

* This change will expose unauthenticated API to lookup a node by its MAC
  addresses. It does not have any impact on most deployments, as both in-tree
  deploy methods (iscsi and http) already expose such API.

* After the complete switch to the new API endpoints is finished, it will no
  longer be possible to fetch the whole node knowing its MAC address without
  authentication. Only limited fields will be available. Notably, the power
  credentials are not sent in the new API endpoints.

* We should clearly note that any deploy implementation should treat the
  incoming data in the new ``heartbeat`` call with care. Particularly, no
  sensitive information should be ever sent to the endpoint designated by the
  ``callback_url`` parameter.

Other end user impact
---------------------

None

Scalability impact
------------------

None

Performance Impact
------------------

* Unlike the old lookup passthru, the new lookup endpoint will not use RPC,
  lowering load on the message queue and the conductor.

Other deployer impact
---------------------

* An update of the IPA image will be recommended to make it use the new API.

* New option ``restrict_lookup`` in the ``api`` section (boolean, defaults to
  ``True``) - whether to restrict the new lookup API to only certain states in
  which lookup is expected.

Developer impact
----------------

3rd party driver developers should stop using the ``BaseAgentVendor`` class
in their drivers and just use the ``AgentDeploy`` class.

3rd party drivers should document whether they require the ``restrict_lookup``
option to be ``False`` for correct functioning.

Implementation
==============

Assignee(s)
-----------

* Dmitry Tantsur (lp: divius, irc: dtanstur)
* Jim Rollenhagen (irc: jroll)

Work Items
----------

* Create new deploy interface methods

* Implement them in the AgentDeploy

* Create new RPC calls and API endpoints

* Switch IPA to use the new endpoints, and fall back to old ones on failure

Dependencies
============

None

Testing
=======

Testing will be conducted as part of the current gate tests.

Upgrades and Backwards Compatibility
====================================

Full backward compatibility will be guaranteed independent of upgrade order
between IPA and ironic itself.

The ``BaseAgentVendor`` class will be deprecated, but stay for some time,
following the usual deprecation policy. Old IPA images will be able to run by
using the old passthru API.

The new IPA image will try to hit the new endpoints first, and will fall back
to the old ones on getting HTTP 406 Not Acceptable (meaning, the API version
is not supported).

Documentation Impact
====================

* Document how to implement new deploy drivers with the new heartbeat method.

* Document the potential security issues with both endpoints.

References
==========

