..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=======================
Keystone Policy Support
=======================

https://bugs.launchpad.net/ironic/+bug/1526752

Keystone and oslo.policy have support for restricting access based on
information about the user authenticating, allowing partial access to be
granted as configured by operators. This spec lays out how this support will be
implemented in ironic.


Problem description
===================

Ironic has traditionally operated on an "all-or-nothing" access system, only
restricting access to passwords. This model is significantly limited when
multiple people and groups with different trust levels want to interact with
ironic. For example, a hardware technician may need access to set or unset
maintenance on the node, but should not have access to provision nodes.


Proposed change
===============

* Ensure proper metadata, such as role, is derived from the auth_token when
  authenticating by properly implementing KeystoneMiddleware.auth_token
  support.

* Define policy rules for each RESTful action on each API endpoint, scoped to
  the 'baremetal' namespace.

* Configure each API endpoint to verify a user is permitted by policy to access
  it.

* Implement specific restrictions for sensitive information, including
  configdrives and passwords. Default to hide all sensitive information.

* Define sane default policies in code [0]_ , with shipped roles including an
  admin role with full access and an observer role with read-only access to
  non-secret information. Names for these roles will be determined during
  implementation. A sample policy.json [1]_ shall be generatable using
  oslopolicy-sample-generator.

* Maintain compatibility with all roles in the previously-shipped policy.json
  configuration file.

Alternatives
------------

A deployer could implement ironic behind a reverse proxy and use another
authentication method to allow or disallow access based on path and HTTP
method. This is onerous, does not follow the pattern set by other OpenStack
services, and does not provide the granularity that properly implementing
policy support would.


Data model impact
-----------------

None.


State Machine Impact
--------------------

Users may be restricted by policy from moving nodes within the state machine.
However, there are no direct state machine modifications.


REST API impact
---------------

A properly restricted user may receive a 403 error if they are unable to use
the method/endpoint combination requested. However, the REST API will not be
returning 403 in any case it could not today, for instance, an unauthorized
user may receive 403 today. This simply increases the granularity available for
configuring this authorization.

The 403 response body shall indicate which resource access was denied to.


Client (CLI) impact
-------------------

A CLI client user will need to have a properly authorized user to perform any
requested actions.


RPC API impact
--------------

None.


Driver API impact
-----------------

Drivers can now enforce policy within any driver_vendor_passthru methods as
desired.


Nova driver impact
------------------

Existing deployments can continue to use a full-admin user as required prior
to this feature. Once upgraded, a deployer could use a less-privileged user
for nova-ironic interactions.

Ramdisk impact
--------------

N/A

.. NOTE: This section was not present at the time this spec was approved.

Security impact
---------------

This change's primary impact is around improving the security of the system.
Deployers of ironic will no longer need to provide an admin credential to
manipulate only a small part of ironic's API.


Other end user impact
---------------------

None.


Scalability impact
------------------

None.


Performance Impact
------------------

Policy support is a minimal increase in overhead. Additionally, most policies
will be implemented early in the API layer, to prevent ironic from doing
excessive work before a user is deemed unauthorized.


Other deployer impact
---------------------

Deployers will now be able to configure policies, in the policy.json DSL [1]_ ,
to meet their specific needs.


Developer impact
----------------

Whenever a developer implements a new API method, they will be required to add
a new policy rule to represent that API endpoint or method, define the default
rule, enforce the policy appropriately, and update default policy as necessary.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  devananda

Other contributors:
  JayF

Work Items
----------

* Update devstack to configure users properly.
* Change configuration of nova in devstack to use new baremetal_driver role.
* Document how to utilize policy, including how to create users in keystone
  and assign them to the baremetal project.
* Document any differences in how this impacts users of Keystone API v2 vs v3.

Dependencies
============

None.

Testing
=======

* Grenade testing to ensure we do not break existing deployments.
* Unit testing to ensure policies are being properly enforced.


Upgrades and Backwards Compatibility
====================================

Existing deployers are required to use an admin user for all uses of ironic,
these users will continue to have full access to the ironic API, allowing for
backwards compatibility.

On upgrade, an operator must define new keystone roles and assign these to
users in order to take advantage of the new policy support. The names for these
roles will be determined during implementation.

The operator may choose to customize the policy settings for their deployment.


Documentation Impact
====================

* Default policies will need to be documented.
* Install guide will need to be updated with instructions on how to create
  users with proper roles and project membership.
* Documentation must be written instructing users how to utilize the new policy
  functionality on upgrade.


References
==========

.. [0] Oslo Policy in Code
       https://specs.openstack.org/openstack/oslo-specs/specs/newton/policy-in-code.html
.. [1] Policy JSON syntax
       http://docs.openstack.org/kilo/config-reference/content/policy-json-file.html
