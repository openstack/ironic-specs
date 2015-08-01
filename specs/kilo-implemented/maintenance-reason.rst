..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

============================
Add maintenance reason field
============================

https://blueprints.launchpad.net/ironic/+spec/maintenance-reason

When a node is put into maintenance (manually or automatically), Ironic
and the operator should know why.


Problem description
===================

Ironic has the ability to mark a node in "maintenance" mode, to be ignored
for the purposes of scheduling and verifying state. However:

* When Ironic automatically puts a node into maintenance mode, it sets the
  reason in the `last_error` field, which may get overwritten by other
  tasks later.

* When an operator manually puts a node into maintenance mode, they have no
  method to show why it was put into maintenance, for other operators or to
  remind themselves later.


Proposed change
===============

The following should be enough to solve this problem:

* A `maintenance_reason` field should be added to the nodes table, as the
  canonical place to store the reason the node was put into maintenance mode.
  This should be an internal attribute not directly editable by calling
  the node.update API.

* A new API endpoint should be added to more easily manage maintenance mode.
  This endpoint can toggle maintenance mode on or off, with an optional
  reason for 'on', and clearing the reason when toggled 'off'. Changing
  maintenance mode using the old methods should still be allowed for
  backwards compatibility.

* Modify node.update to clear the maintenance reason when turning
  maintenance mode off via node.update API.

Alternatives
------------

Alternatively, operators could store this in another system, such as a CMDB.

While I think this would be fine, this would not allow for Ironic to
automatically set a maintenance reason when putting a node into maintenance
mode. Work would need to be done to make Ironic notify the operator or
integrate with the other system; and possibly cause the operator to do manual
work to put the reason in the other system.

Data model impact
-----------------

This will add a `maintenance_reason` field to the `node` table, with an
accompanying database migration. This field will default to NULL, which will
also be the value when there is no reason, or when maintenance reason is
cleared via the new API.

REST API impact
---------------

One new endpoint will be added, with two methods:

* PUT /v1/nodes/<uuid>/maintenance

  * Puts a node into maintenance mode, with an optional reason.

  * Method type: PUT

  * Normal response code: 202

  * Expected errors:

    * 404 if the node with <uuid> does not exist.

    * 400 if a conductor for the node's driver cannot be found.

  * URL: /v1/nodes/<uuid>/maintenance

  * URL parameters: None.

  * JSON body: {"reason": "Some reason."}, or {} or empty for no reason.

  * Response body is empty if successful.

* DELETE /v1/nodes/<uuid>/maintenance

  * Takes a node out of maintenance mode and clears the reason.

  * Method type: DELETE

  * Normal response code: 202

  * Expected errors:

    * 404 if the node with <uuid> does not exist.

    * 400 if a conductor for the node's driver cannot be found.

  * URL: /v1/nodes/<uuid>/maintenance

  * URL parameters: None.

  * JSON body: None.

  * Response body is empty if successful.

The `maintenance_reason` field should be added to the node details API.

RPC API impact
--------------

None.

Driver API impact
-----------------

None.

Nova driver impact
------------------

None.

Security impact
---------------

None.

Other end user impact
---------------------

Support for this will be added in python-ironicclient. The CLI will look like:

::

  usage: ironic node-set-maintenance [--reason <reason>]
                                     <node id> <maintenance mode>

  Set maintenance mode on or off.

  Positional arguments:
    <node id>           UUID of node
    <maintenance mode>  Supported states: 'on' or 'off'

  Optional arguments:
    --reason <reason>   The reason for setting maintenance mode to "on"; not
                        valid when setting to "off".



Scalability impact
------------------

None.

Performance Impact
------------------

None.

Other deployer impact
---------------------

Deployers may wish to start using this feature when it is deployed; however
there should be no impact otherwise.

Developer impact
----------------

None.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  jroll

Other contributors:
  lucasagomes

Work Items
----------

* Add `maintenance_reason` to the nodes table with a migration.

* Set `maintenance_reason` when automatically setting maintenance mode.

* Add the new API endpoints.

* Clear maintenance_reason when using node.update to set maintenance mode off.

* Add client support for the new API endpoints.

* Add Tempest tests for the new API endpoints.


Dependencies
============

None.


Testing
=======

Tempest tests should be added for the new API endpoints.


Upgrades and Backwards Compatibility
====================================

This change will be backwards compatible with existing clients, as they may
still use the node.update call to set maintenance on or off. Updating via
the node.update call will not be deprecated in v1, since there isn't any
reasonable programmatic way to inform users of its deprecation. It will be
deprecated in v2.

To avoid having an outdated maintenance reason, using the node.update call
to set maintenance mode off will clear the maintenance reason.


Documentation Impact
====================

The new API endpoints and client methods should be documented.


References
==========

None.
