..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

======================================
Allow Node Owners to Administer Nodes
======================================

https://storyboard.openstack.org/#!/story/2006506

This spec describes an update that allows a node owner to administer
their node through the Ironic API without being able to administer the
entire node cluster. This is accomplished by exposing owner node
data in the REST API for policy checks.

Problem description
===================

Ironic is not multi-tenant; anyone with API access to one node has access
to all nodes. While nodes have an ``owner`` field, it is purely
informational and not tied into any form of access control.

Bringing full multi-tenant support to Ironic would allow us to address the
following user stories:

Standalone Ironic
-----------------

As users of a shared data center, we would like to use Ironic to manage our
hardware resources. Each work group should be able to control their own
resources without having access to hardware resources owned by other groups.

Data center operator
--------------------

As the operator of shared datacenter, I would like to delegate power control of
baremetal hardware to the hardware owners using the Ironic API. By using the
Ironic API instead of existing embedded management protocols (such as IPMI) I
can maintain the simplicity of a shared management network while having
granular control over who can access what hardware.

Proposed change
===============

The Ironic API already has a way of controlling access to the REST API: a
policy engine [0]_ that is used throughout the REST API. However, when the
node controller uses the policy engine [1]_, it does so without passing in
any information about the node being checked. Other services such as Nova
[2]_ and Barbican [3]_ pass in additional information, and we propose doing
the same. In summary, we would like to:

* Assume that a node's ``owner`` field is set to the id of a Keystone project.
  We refer to this project as the "node owner".

* Update the node controller so that policy checks also pass in information
  about the node, including the ``owner`` field.

* Update Ironic's default generated policy file to include an
  ``is_node_owner`` rule:

   *  "is_node_owner": "project_id:%(node.owner)s"

  The remainder of the policy file would stay the same, meaning that there is
  no change to default API access.

* Create documentation explaining how to update an Ironic policy file to give
  API access to owners. For example:

   *  "baremetal:node:set_power_state": "rule:is_admin or rule:is_node_owner"

  Note that Nova grants API access in a similar manner [4]_.

This update is enough to control access for most API functions - except for
list functions. For those, we propose the following:

* Right now, the policy rule 'baremetal:node:get' is used for both ``get_all``
  and ``get_one``. We can add two new policy rules: ``baremetal:node:list_all``
  for retrieving all nodes, and ``baremetal:node:list`` for retrieving nodes
  whose ``owner`` field matches the querying project.

* Updating the REST API node list functions to first perform a policy check
  against ``baremetal:node:list_all``. If it passes, then we return all nodes;
  otherwise we perform a policy check against ``baremetal:node:list``. If that
  passes, then we return nodes filtered by the ``owner`` field against the
  project specified in the request context. These list functions already have
  the option of filtering by ``owner`` [5]_.

* Updating the default generated policy file to set
  ``baremetal:node:list_all`` and ``baremetal:node:list`` to
  ``rule:baremetal:node:get`` to ensure backwards compatibility.

Note that this change does not imply any change to the allocations API. Right
now, only users with full Ironic API access can take advantage of allocations,
and that will not change with this spec.


Alternatives
------------

One alternative is to perform these checks at the database API level. However
that requires a new code pattern to be used on a large number of individual
functions.

Data model impact
-----------------

None

State Machine Impact
--------------------

None

REST API impact
---------------

See details in "Proposed change" above.

Client (CLI) impact
-------------------

None

"ironic" CLI
~~~~~~~~~~~~

None

"openstack baremetal" CLI
~~~~~~~~~~~~~~~~~~~~~~~~~

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

Ramdisk impact
--------------

None

Security impact
---------------

This change allows functionality to be exposed to additional users. However
this access is blocked off by default; it requires an update to the Oslo
policy file, and can be adjusted as an administrator desires.

Other end user impact
---------------------

None

Scalability impact
------------------

None

Performance Impact
------------------

None: although node data needs to be retrieved in order to pass that
information into a policy check, the controller functions already fetch
that information. [6]_

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

Primary assignees:
* tzumainn - tzumainn@redhat.com
* larsks - lars@redhat.com

Work Items
----------

* Update node controller.
* Add documentation.
* Write tests.

Dependencies
============

None

Testing
=======

We will add unit tests and Tempest tests.

Upgrades and Backwards Compatibility
====================================

Existing Ironic installations that use the ``owner`` field for something other
than a project ID will be minimally affected for two reasons:

* If the ``owner`` field does not match a project ID (or is None), the
  proposed update to the policy file will not give any non-admin access to
  the Ironic API.

* This change has no end-user impact if the policy file is not updated. An
  existing install can simply choose not to update their policy file.

Documentation Impact
====================

We will include additional documentation describing the possible
applications of using the ``node_owner`` policy roles.

References
==========

.. [0] https://github.com/openstack/ironic/blob/master/ironic/common/policy.py
.. [1] https://github.com/openstack/ironic/blob/master/ironic/api/controllers/v1/node.py#L225
   Example of a current policy check. Note the use of ``cdict``; it is being
   passed in as both the ``target`` and the ``creds``.
.. [2] https://github.com/openstack/nova/blob/master/nova/api/openstack/compute/servers.py#L648-L652
   Example of Nova creating a ``target`` dictionary.
.. [3] https://github.com/openstack/barbican/blob/stable/rocky/barbican/api/controllers/__init__.py#L59-L72
   Example of Barbican creating a ``target`` dictionary.
.. [4] https://github.com/openstack/nova/blob/master/nova/policies/base.py#L27-L30
   Example of Nova defaulting a rule that uses information from a ``target``
   dictionary.
.. [5] https://github.com/openstack/ironic/blob/master/ironic/api/controllers/v1/node.py#L1872
.. [6] https://github.com/openstack/ironic/blob/master/ironic/api/controllers/v1/node.py#L227
