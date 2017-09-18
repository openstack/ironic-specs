..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

================
Deploy Templates
================

https://storyboard.openstack.org/#!/story/1722275

This builds on the `deployment steps
spec <http://specs.openstack.org/openstack/ironic-specs/specs/11.1/deployment-steps-framework.html>`__,
such that it is possible to request a particular set of deployment steps by
requesting a set of traits.

When Ironic is used with Nova, this allows the end user to pick a Flavor, that
requires a specific set of traits, that Ironic turns into a request for a
specific set of deployment steps in Ironic.

Problem description
===================

One node can be configured in many ways. Different user workloads require the
node to be configured in different ways. As such, operators would like a single
pool of hardware to be reconfigured to match each users requirements, rather
than attempting to guess how many of each configurations are required in
advance.

In this spec, we are focusing on reconfiguring regular hardware to match the
needs of each users workload. We are not considering composable hardware.

When creating a Nova instance with Ironic as the backend, there is currently no
way to influence the deployment steps used by Ironic to provision the node.

Example Use Case
----------------

Consider a bare metal node that has three disks. Different workloads may
require different RAID configurations. Operators want to test their hardware
and determine the specific set of RAID configurations that work best, and offer
that choice to users of Nova, so they can pick the configuration that best
matches their workload.

Proposed change
===============

Context: Deployment Steps Framework
-----------------------------------

This spec depends on the deployment steps framework spec. The deployment steps
framework provides the concept of a deployment step that may be executed when a
node is deployed.

It is assumed that there is a default set of steps that an operator configures
to happen by default on every deploy. Each step task has a priority defined, to
determine the order that that step runs relative to other enabled deploy steps.
Configuration options and hard-coded priorities define if a task runs by
default or not. The priority says when a task runs if the task should run
during deployment.

Deploy Templates
----------------

This spec introduces the concept of a ``Deploy Template``. It is a mapping
from a valid trait name for the node to one or more Deployment Steps and all
the arguments that should be given to those deployment steps. There is a new
API added to Ironic for Operators to specify these ``Deploy Templates``.

To allow a ``Deploy Template`` for a given Ironic node, you add the
trait name of the deploy template to the ``traits`` list on each Ironic
node that needs the deploy template enabled. The validation of the node must
fail if any of the enabled ``Deploy Templates`` are not supported on that node.

It is worth noting that all traits set on the node are synchronised to Nova's
placement API. In turn, should a user request a flavor that requires a trait
(that may or may not map to a deploy template) only nodes that have the trait
set will be offered as candidates by Nova's Placement API.

To request the specified ``Deploy Template`` when you provision a particular
Ironic node, the corresponding trait is added to a list in
``node.instance_info`` under the key of ``traits``. This is what Nova's ironic
virt driver already does for any required trait in the flavor's extra specs for
that instance. Again, Ironic already validates that the traits in
``node.instance_info`` are a subset of the traits that the Operator has set on
the Ironic node, via the new node-traits API.

During the provisioning process Ironic checks the list of traits set in
``node.instance_info`` and checks if they match any ``Deploy Templates``. The
list of matching ``Deploy Templates`` are then used to extend the list of
deployment steps for this particular provision operation. As already
defined in the deployment steps framework, this is then combined with the list
of deployment steps from what is configured to happen by default for all
builds.

The order in which the steps are executed will be defined by the priority of
each step. If the code for a deploy step defines a deploy priority of 0, and
that is not changed by a configuration option, that deploy step does not
get executed by default. If a deploy template specifies a priority
(this is required if the code has a default priority of 0), this overrides both
the code default and any configuration override.

It is acceptable to request the same deploy step more than once. This could be
done to execute a deploy step multiple times with different arguments, for
example to partition multiple disks.

Any deploy step in a requested deploy template will override the default
arguments and priority for that deploy step.  0 is the only priority override
that can be set for any of the core deploy steps, i.e. you can only disable the
core step, you can't change the order of its execution.

Trait names used in Deploy Templates should be unique - no two deploy templates
should specify the same trait name.

In summary, you can use traits to specify additional deploy steps, by the
mapping between traits and deploy steps specified in the new
``Deploy Templates`` API.

Current Limitations
-------------------

When mapping this back to Nova integration, currently there would need to be
a flavor for each of these combinations of traits and resource_class. Longer
term Nova is expected to offer the option of a user specifying an override
trait on a boot request, based on what the flavor says is possible. This spec
has no impact on the Nova ironic virt driver beyond what is already implemented
to support `node-traits
<http://specs.openstack.org/openstack/ironic-specs/specs/approved/node-traits.html>`__.

Example
-------

Lets now look at how we could request a particular deploy template via Nova.

``FlavorVMXMirror`` has these extra specs:

* ``resource:CUSTOM_COMPUTE_A = 1``
* ``trait:CUSTOM_CLASS_A = required``
* ``trait:CUSTOM_BM_CONFIG_BIOS_VMX_ON = required``
* ``trait:CUSTOM_BM_CONFIG_RAID_DISK_MIRROR = required``

``FlavorNoVMXStripe`` has these extra specs:

* ``resource:CUSTOM_COMPUTE_A = 1``
* ``trait:CUSTOM_CLASS_A = required``
* ``trait:CUSTOM_BM_CONFIG_BIOS_VMX_OFF = required``
* ``trait:CUSTOM_BM_CONFIG_RAID_DISK_STRIPE = required``

It's possible the operator has set all of the Ironic nodes with ``COMPUTE_A``
as the resource class to have all of these traits assigned:

* ``CUSTOM_BM_CONFIG_BIOS_VMX_ON``
* ``CUSTOM_BM_CONFIG_BIOS_VMX_OFF``
* ``CUSTOM_OTHER_TRAIT_I_AM_USUALLY_IGNORED``
* ``CUSTOM_BM_CONFIG_RAID_DISK_MIRROR``
* ``CUSTOM_BM_CONFIG_RAID_DISK_STRIPE``

The Operator has also defined the following deploy templates::

    {
      "deploy-templates": [
        {
          "name": "CUSTOM_BM_CONFIG_RAID_DISK_MIRROR",
          "steps": [
            {
              "interface": "raid",
              "step": "create_configuration",
              "args": {
                "logical_disks": [
                  {
                    "size_gb": "MAX",
                    "raid_level": "1",
                    "is_root_volume": true
                  }
                ],
                "delete_configuration": true
              },
              "priority": 10
            }
          ]
        },
        {
          "name": "CUSTOM_BM_CONFIG_RAID_DISK_STRIPE",
          "steps": [
            {
              "interface": "raid",
              "step": "create_configuration",
              "args": {
                "logical_disks": [
                  {
                    "size_gb": "MAX",
                    "raid_level": "0",
                    "is_root_volume": true
                  }
                ],
                "delete_configuration": true
              },
              "priority": 10
            }
          ]
        },
        {
          "name": "CUSTOM_BM_CONFIG_BIOS_VMX_ON",
          "steps": [...]
        },
        {
          "name": "CUSTOM_BM_CONFIG_BIOS_VMX_OFF",
          "steps": [...]
        }
      ]
    }

When a Nova instance is created with ``FlavorVMXMirror``, the required traits
for that flavor are set on ``node.instance_info['traits']`` such that Ironic
adds the deploy steps defined in ``CUSTOM_BM_CONFIG_BIOS_VMX_ON`` and
``CUSTOM_BM_CONFIG_RAID_DISK_MIRROR``, and the node is appropriately configured
for workloads that want that specific flavor.

Alternatives
------------

Alternative approach
~~~~~~~~~~~~~~~~~~~~

This design solves two problems:

1. I want to request some custom configuration to be applied to my bare metal
   server during provisioning.
2. Ensure that my instance is scheduled to a bare metal node that supports
   the requested configuration.

As with capabilities, the proposed design uses a single field (traits) to
encode configuration and scheduling information. An alternative approach could
separate these two concerns.

Deploy templates could be requested by a name (not necessarily a trait) or UUID
as a nova flavor ``extra_spec``, and pushed to a ``deploy_templates`` field in
the ironic node's ``instance_info`` field by the nova virt driver. Ironic would
then apply the requested deploy templates during provisioning.

If some influence in the scheduling process is required, this could be provided
by traits, but this would be a separate concern.

Adapting the earlier example:

``FlavorVMXMirror`` has these extra specs:

* ``resource:CUSTOM_COMPUTE_A = 1``
* ``trait:CUSTOM_BM_CONFIG_BIOS_VMX_ON = required``
* ``trait:CUSTOM_BM_CONFIG_RAID_DISK_MIRROR = required``
* ``deploy_template:BIOS_VMX_ON=<?>``
* ``deploy_template:BIOS_RAID_DISK_MIRROR=<?>``

Only ironic nodes supporting the ``CUSTOM_BM_CONFIG_BIOS_VMX_ON`` and
``CUSTOM_BM_CONFIG_RAID_DISK_MIRROR`` traits would be scheduled to, and the
nova virt driver would set ``instance_info.deploy_templates`` to
``BIOS_VMX_ON,BIOS_RAID_DISK_MIRROR``.

There are some benefits to this alternative approach:

* It would automatically support cases beyond the simple one trait mapping to
  one deploy template case we have here. For example, to support deploy
  template ``X``, features ``Y`` and ``Z`` must be supported by the node
  (without combinatorial trait explosions).
* In isolation, the configuration mechanism is conceptually simpler - the
  flavor specifies a deploy template directly.
* It would work in standalone ironic installs without introducing concepts from
  placement.
* We don't overload the concept of traits for carrying configuration
  information.

There are also some drawbacks:

* Additional complexity for users and operators that now need to apply both
  traits and deploy templates to flavors.
* Less familiar for users of capabilities.
* Having flavors that specify resources, traits and deploy templates in
  ``extra_specs`` could leave operators and users scratching their heads.

Extensions
~~~~~~~~~~

This spec attempts to specify the minimum viable feature that builds on top
of the deployment steps framework specification. As such, there are many
possible extensions to this concept that are not being included:

* While you can use standard traits as names of the deploy templates, it is
  likely that many operators will be forced into using custom traits for most
  of their deploy templates. We could better support the users of standard
  traits if we added a list of traits associated with each deploy template,
  in addition to the trait based name. This list of traits will act as an alias
  for the name of the deploy template, but this alias may also be used
  by many other deploy templates. The node validate will fail if for any
  individual node one of traits set maps to multiple deploy templates.
  To disambiguate which deploy template is requested, you can look at what
  deploy template names are in the chosen node's trait list. For each deploy
  template you look at any other traits that can be used to trigger that
  template, eventually building up a trait to deploy template mapping for each
  trait set on the node (some traits will not map to any deploy template).
  That can be used to detect if any of the traits on the node map to multiple
  deploy templates, causing the node validate to fail.

* For some operators, they will end up creating a crazy number of flavors to
  cover all the possible combinations of hardware they want to offer. It is
  hoped Nova will eventually allow operators to have flavors that list possible
  traits, and a default set of traits, such that end users can request the
  specific set of traits they require in addition to the chosen flavor.

* While ironic inspector can be used to ensure each node is given an
  appropriate set of traits, it feels error prone to add so many traits to each
  Ironic node. It is hoped when a concept of node groups is added, traits could
  be applied to a group of nodes instead of only applying traits to individual
  nodes (possibly in a similar way to host aggregates in Nova). One suggestion
  was to use the Resource Class as a possible grouping, but that is only a very
  small part of the more general issue of groups nodes to physical networks,
  routed network segments, power distribution groups, all mapping to different
  ironic conductors, etc.

* There were discussions about automatically detecting which Deploy
  Templates each of the nodes supported. However most operators will want to
  control what is available to only the things they wish to support.

Data model impact
-----------------

Two new database tables will be added for deploy templates::

    CREATE TABLE deploy_templates (
        id INT(11) NOT NULL AUTO_INCREMENT,
        name VARCHAR(255) CHARACTER SET utf8 NOT NULL,
        uuid varchar(36) DEFAULT NULL,
        PRIMARY KEY (id),
        UNIQUE KEY `uniq_deploy_templaes0uuid` (`uuid`),
        UNIQUE KEY `uniq_deploy_templaes0name` (`name`),
    )

    CREATE TABLE deploy_template_steps (
        deploy_template_id INT(11) NOT NULL,
        interface VARCHAR(255) NOT NULL,
        step VARCHAR(255) NOT NULL,
        args TEXT NOT NULL,
        priority INT NOT NULL,
        KEY `deploy_template_id` (`deploy_template_id`),
        KEY `deploy_template_steps_interface_idx` (`interface`),
        KEY `deploy_template_steps_step_idx` (`step`),
        CONSTRAINT `deploy_template_steps_ibfk_1` FOREIGN KEY (`deploy_template_id`) REFERENCES `deploy_templates` (`id`),
    )

The ``deploy_template_steps.args`` column is a JSON-encoded object of step
arguments, ``JsonEncodedDict``.

New ``ironic.objects.deploy_template.DeployTemplate`` and
``ironic.objects.deploy_template_step.DeployTemplateStep`` objects will be
added to the object model. The deploy template object will provide support for
looking up a list of deploy templates that match any of a list of trait names.

State Machine Impact
--------------------

No impact beyond that already specified in the deploy steps specification.

REST API impact
---------------

A new REST API endpoint will be added for deploy templates, hidden behind a new
API microversion. The endpoint will support standard CRUD operations.

In the following API, a UUID or trait name is accepted for a deploy template's
identity.

List all
~~~~~~~~

List all deploy templates::

    GET /v1/deploy-templates

Request: empty

Response::

    {
      "deploy-templates": [
        {
          "name": "CUSTOM_BM_CONFIG_RAID_DISK_MIRROR",
          "steps": [
            {
              "interface": "raid",
              "step": "create_configuration",
              "args": {
                "logical_disks": [
                  {
                    "size_gb": "MAX",
                    "raid_level": "1",
                    "is_root_volume": true
                  }
                ],
                "delete_configuration": true
              },
              "priority": 10
            }
          ],
          "uuid": "8221f906-208b-44a5-b575-f8e8a59c4a84"
        },
        {
          ...
        }
      ]
    }

Response codes: 200, 400

Policy: admin or observer.

Show one
~~~~~~~~

Show a single deploy template::

    GET /v1/deploy-templates/<deploy template ident>

Request: empty

Response::

    {
      "name": "CUSTOM_BM_CONFIG_RAID_DISK_MIRROR",
      "steps": [
        {
          "interface": "raid",
          "step": "create_configuration",
          "args": {
            "logical_disks": [
              {
                "size_gb": "MAX",
                "raid_level": "1",
                "is_root_volume": true
              }
            ],
            "delete_configuration": true
          },
          "priority": 10
        }
      ],
      "uuid": "8221f906-208b-44a5-b575-f8e8a59c4a84"
    }

Response codes: 200, 400, 404

Policy: admin or observer.

Create
~~~~~~

Create a deploy template::

    POST /v1/deploy-templates

Request::

    {
      "name": "CUSTOM_BM_CONFIG_RAID_DISK_MIRROR",
      "steps": [
        {
          "interface": "raid",
          "step": "create_configuration",
          "args": {
            "logical_disks": [
              {
                "size_gb": "MAX",
                "raid_level": "1",
                "is_root_volume": true
              }
            ],
            "delete_configuration": true
          },
          "priority": 10
        }
      ],
    }

Response: as for show one.

Response codes: 201, 400, 409

Policy: admin.

Update
~~~~~~

Update a deploy template::

    PATCH /v1/deploy-templates/{deploy template ident}

Request::

    [
      {
        "op": "replace",
        "path": "/name"
        "value": "CUSTOM_BM_CONFIG_RAID_DISK_MIRROR"
      },
      {
        "op": "replace",
        "path": "/steps"
        "value": [
          {
            "interface": "raid",
            "step": "create_configuration",
            "args": {
              "logical_disks": [
                {
                  "size_gb": "MAX",
                  "raid_level": "1",
                  "is_root_volume": true
                }
              ],
              "delete_configuration": true
            },
            "priority": 10
          }
        ]
      }
    ]

Response: as for show one.

Response codes: 200, 400, 404, 409

Policy: admin.

The ``name`` and ``steps`` fields can be updated. The ``uuid`` field cannot.

Delete
~~~~~~

Delete a deploy template::

    DELETE /v1/deploy-templates/{deploy template ident}

Request: empty

Response: empty

Response codes: 204, 400, 404

Policy: admin.

Client (CLI) impact
-------------------

"ironic" CLI
~~~~~~~~~~~~

None

"openstack baremetal" CLI
~~~~~~~~~~~~~~~~~~~~~~~~~

In each of the following commands, a UUID or trait name is accepted for the
deploy template's identity.

For the ``--steps`` argument, either a path to a file containing the JSON data
or ``-`` is required. If ``-`` is passed, the JSON data will be read from
standard input.

List deploy templates::

    openstack baremetal deploy template list

Show a single deploy template::

    openstack baremetal deploy template show <deploy template ident>

Create a deploy template::

    openstack baremetal deploy template create --name <trait> --steps <deploy steps>

Update a deploy template::

    openstack baremetal deploy template set <deploy template ident> [--name <trait] [--steps <deploy steps>]

Delete a deploy template::

    openstack baremetal deploy template delete <deploy template ident>

In these commands, ``<deploy steps>`` are in JSON format and support the same
input methods as clean steps - string, file or standard input.

RPC API impact
--------------

None

Driver API impact
-----------------

None

Nova driver impact
------------------

Existing traits integration is enough, only now the selected traits on boot
become more important.

Ramdisk impact
--------------

None

Security impact
---------------

Allowing the deployment process to be customised via deploy templates could
open up security holes. These risks are mitigated, as seen through the
following observations:

* Only admins can define the set of allowed traits for each node.
* Only admins can define the set of requested traits for each Nova flavor, and
  allow access to that flavor for other users.
* Only admins can create or update deploy templates via the API.
* Deploy steps referenced in deploy templates are defined in driver code.

Other end user impact
---------------------

Users will need to be able to discover what each Nova flavor does in terms of
deployment customisation. Beyond checking requested traits and
cross-referencing with the ironic deploy templates API, this is deemed to be
out of scope. Operators should provide sufficient documentation about the
properties of each flavor.  The ability to look up a deploy template by trait
name should help here.

Scalability impact
------------------

Increased activity during deployment could have a negative impact on the
scalability of ironic.

Performance Impact
------------------

Increased activity during deployment could have a negative impact on the
performance of ironic, including increasing the time required to provision a
node.

Other deployer impact
---------------------

Deployers will need to ensure that Nova flavors have required traits set
appropriately.

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Mark Goddard (mgoddard)

Other contributors:

* Dmitry Tantsur (dtantsur)
* Ruby Loo (rloo)

Work Items
----------

* Add DB tables and objects for deploy templates
* Write code to map traits to deploy templates
* Extend node validation to check all deploy templates are valid
* Add API to add deploy templates
* Extend CLI to support above API
* Write tests

Dependencies
============

* Node traits spec
  http://specs.openstack.org/openstack/ironic-specs/specs/approved/node-traits.html
* Deploy steps spec
  http://specs.openstack.org/openstack/ironic-specs/specs/11.1/deployment-steps-framework.html

Testing
=======

Unit tests will be added to ironic. Tempest API tests will exercise the deploy
templates CRUD API.

Upgrades and Backwards Compatibility
====================================

The deploy steps API endpoint will be hidden behind a new API version.

During normal operation when the ironic conductor is not pinned, deploy
templates will be used to add deploy steps during node provisioning, even if
the caller of the node state API uses a microversion that does not support
deploy templates.

During an upgrade when the ironic conductor is pinned, deploy templates will
not be used to add deploy steps during node provisioning.

Documentation Impact
====================

* Admin guide on how to configure Nova flavors and deploy templates
* Update API ref
* Update CLI docs

References
==========

* http://specs.openstack.org/openstack/ironic-specs/specs/11.1/deployment-steps-framework.html
* http://specs.openstack.org/openstack/ironic-specs/specs/approved/node-traits.html
