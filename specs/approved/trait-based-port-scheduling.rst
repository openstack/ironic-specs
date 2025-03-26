..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=========================================================
Trait based Port Scheduling to achieve Dynamic Networking
=========================================================

OpenStack is a system originally built with virtual machines and virtual
networking in mind. One of the most complex parts of Ironic's interactions
with OpenStack networking is mapping a "virtual interface" which represents
the idea of a connection to a network to a physical/Ironic port or portgroup on
a server to make that connection become reality.

Today, Ironic has extremely basic rules for how to perform these mappings,
which are inadequate in situations with a large number of networks or NICs on
a machine (among many others).

Problem description
===================

As of the the 2025.1 release, Ironic schedules ports using the following model:

* Require a matching or undefined physical network
* Prefer ports or port groups with a physical network defined
* Prefer (static, preconfigured) portgroups to ports
* Prefer ports which are PXE Enabled

Except, this is fundamentally limited in that with this model, we cannot:

* Dynamically assemble portgroups
* Hint or weight to a specific port, portgroup, or device class.
* Avoid other specific types of interfaces or networks.

For example, an operator may have a machine with:

- 2 "Green" Network Devices
- 4 "Purple" Network Devices

Even though traffic may be capable of using any one of these six interfaces,
it may be ideally handled by a specific device. This usually is for
improvements in performance, such as using a higher-speed network adapter
or DPU to improve performance on that network.

This doesn't mean we want Ironic to fully understand and parse all these
details or all hardware and network combinations, however, we need to give
operators the tools they need to perform these mappings themselves.


Proposed change
===============

Overview
--------

In order to permit operators to model these complex networking situations, we
propose implementation of a new yaml configuration, whose key would be a
custom trait and whose value would be configuration dictating the attachment
and configuration of network ports. When Ironic performs a deployment with
one of these traits, Ironic will perform network attachments according to the
configured rule.

For users using Ironic fronted by Nova, they will be able to
configure custom flavors which will transmit the desired traits to Ironic to
perform network mapping. Traits are already used in this way to modify
deployment process at deploy time in ``deploy_templates``.

Ultimately, this requires advances in both data model and scheduling,
but the overall hope is to facilitate a flavor based model to enable
this mapping so a user leveraging Nova can request a baremetal node
and Ironic does the needful. Additionally, direct hinting of a port for
interface attachments will not be supported when using these modes. See the
:ref:`Alternatives` section for more information.


Milestone One: Single Port Mappings
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

As a first milestone, Ironic will implement this functionality for
preconfigured portgroups and single ports.

For an example at this milestone, if an operator has a flavor named
``fast_purple`` with a trait ``CUSTOM_FAST_PURPLE_NETWORK``, they could
configure any network tagged with "purple" to use a port associated with a
specific vendor. The operator could also have a flavor ``fast_green`` which
has the trait ``CUSTOM_FAST_GREEN_NETWORK``, which would, instead, connect
networks tagged with "green" to the port associated with the vendor.

It's important when implementing this to ensure that the configuration,
node, existing ports, and requested networks are resolvable before taking
any configuration action. Avoid a situation where network configuration
is in-progress before we determine we cannot fulfill the request.

Milestone Two: Dynamic Portgrouping
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

As a second milestone, we will add the additional ability to dynamically
create portgroups out of single ports as well.

For example, if I have a flavor named ``double_purple``, which has a trait
``CUSTOM_BOND_TWO_PURPLE``, an operator could configure this trait to
perform an action to attach two existing ports together into a dynamic
portgroup connected to a network tagged purple. Additionally, they could have
a flavor named ``double_green``, which does the same action except for green
tagged networks. In both cases, the dynamically assembled portgroup would be
torn down when the node transits out of ACTIVE state.

Dynamic portgrouping will be disjointed from the existing portgroups
model, which currently treats portgroups as a static attribute of a node.


Port Modeling
-------------

In order to enable a more dynamic model of port allocation, we need some
additional fields which a user of this feature can leverage to make decisions
in filter logic. Initially, we will add ``vendor`` and ``class`` fields to the
Port object. For milestone two, we will add ``available_for_dynamic_portgroup``
to Port objects, which can be used to opt Ports in and out of dynamic
portgrouping functionality.

Other fields may be identified during implementation, but the intent is for
filtering to provide the port object as part of the filter logic.


.. _Overall flow of request handling:

Overall flow of request handling
--------------------------------

In order for Nova to leverage this model, the overall flow of a request needs
to take the following shape:

1) A node is reserved by setting ``instance_uuid``.
2) The desirable ``instance_info`` is set for the node. This should be able to
   be done with the same patch operation as setting ``instance_uuid``.
   The result, today, is that the node's ``instance_info`` value has a
   ``trait`` field which has a list of traits which were defined from the
   flavor.
3) Vif attachments occur and logic is triggered internally to dynamically
   assemble portgroups *and* influence mapping. Ironic would use this time to
   take any preparations on the node, such as configuring NICs or assembling
   dynamic portgroups.
4) Nova would then be able to look up the node's ports and portgroups and
   generate required user metadata which is **required** to be submitted
   upon the deploy command.
5) The node would then be ``deploy`` -ed via the set_provision_state API.
6) Network Interfaces would then take action to configure the
   Ports/Portgroups (which were updated to reflect dynamic mappings in #3).
   It is only expected to work with the ``neutron`` interface, but it may be
   possible to use other interfaces in the future.

On a positive note, Nova **already** does this *exact* process we need
to be able to perform logic along these lines.

A standalone user *can* also follow this exact process, or if so inclined,
directly request specific VIF to portgroup or port mappings they are manually
managing. Again, the overall goal for this specification is automatic and
streamlined for an integrated use case. The *major* difference which
delineates the standalone use case from this feature is that standalone
users are able to make those decisions upfront and change other resources.
Where as a Nova user in an integrated context simply cannot because they
don't know in advance what machine they may be mapped to nor can they
influence that in any other way beyond what is provided today.

Trait mappings
--------------

An initial proposed model is to make the mapping of trait to action modeling
a static YAML configuration file deployed to the conductor. The location of
this file will be configurable.

For actions which can work on any number of ports, all ports that match the
expression will be used. For actions which can work only on a single port,
the first port that matches the expression will be used. When no min or max
is configured, any number of ports are eligible.

If there is no YAML file in place, or no trait match we fall back to previous
behavior.

YAML Structure/Grammar
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    <trait_name>:
      - action: <action_name>
        filter: <filter_expression>
        min_count: <min_count>
      - action: <action_name>
        filter: <filter_expression>
        max_count: <max_count>
    <trait_name>:
      - action: <action_name>
        filter: <action_name>
    ...

``trait_name`` is validated as a valid trait, which means it must begin with
``CUSTOM_``, be less than 255 characters, and only contain alphanumeric
characters or underscores.

``action_name`` is a valid action as listed in :ref:`Actions`

``filter_expression`` is an expression as defined in :ref:`Filters`

``min_count``, and ``max_count`` are optional fields:
  - ``min_count``, if set, defines the minimum number of ports that must
    match for the action to be performed
  - ``max_count``, if set, defines the maximum number of ports that will
    be acted on. The first ``max_count`` ports matched will be passed to the
    action.

Any number of traits can be listed, with any number of action/filter pairs
listed beneath it. Traits, and their associated action/filter pairs, are
processed in a specific order: trait names are applied first, in
ABC order (e.g. deploying with traits ``CUSTOM_NETWORK_X`` and
``CUSTOM_NETWORK_Y`` would lead to ``CUSTOM_NETWORK_X`` action/filter pairs
being evaluated first, then ``CUSTOM_NETWORK_Y`` action/filter pairs would be
applied.) Action/filter/count sets are evaluated in the order listed under
the trait name.

.. _Actions:

Actions
~~~~~~~
At milestone one, we expect to have the following two actions implemented:

  - ``attach_port`` (attach the first port that matches)
  - ``attach_portgroup`` (attach the first statically defined portgroup that
    matches)

At milestone two, we expect to have an additional action implemented:

  - ``group_and_attach_ports`` (create a dynamic portgroup of matching ports
    and attach them)

Ironic may add more actions in the future.

.. _Filters:

Filters
~~~~~~~

**Expressions**

- Comparators:
  - ``==`` (equality)
  - ``!=`` (inequality)
  - ``>=`` (greater than or equal to)
  - ``>`` (greater than)
  - ``<=`` (less than or equal to)
  - ``<`` (less than)
  - ``=~`` (prefix match, equivalent to python's ``string.startswith()``)
- Boolean Operators:
  - ``&&`` (logical AND)
  - ``||`` (logical OR)
- Expressions can be grouped using parentheses ``(`` and ``)`` and boolean
  operators.

Simple expressions consist of three parts:
- Value to compare against (e.g. ``port.vendor``)
- Comparator to apply
- string for comparison

e.g. ``port.vendor == 'fastNIC'`` or ``network.tag == 'fastNET'``


**Objects to Filter With**

Ironic will provide access to some of the network metadata to compare against
using this configuration. They will include:

A ``port``-like object, representing either a port or static portgroup,
containing (at least):

  - address
  - class
  - physical_network
  - vendor
  - is_port (bool)
  - is_portgroup (bool)


A ``network``-like object, representing the network object on the virtual
interface (``vif``), containing (at least):

  - name
  - tags
  - (more TBD)

Other objects/fields that are available to Ironic may be added at
implementation time depending on availability and applicability. The full
list will be explicitly documented at implementation time.

**Example Config**

An example config for Ironic once both milestones are completed:

.. code-block:: yaml

  ---
  CUSTOM_TRAIT_NAME:
    - action: bond_ports
      filter: port.vendor == 'vendor_string'
      min_count: 2
  CUSTOM_DIRECT_ATTACH_A_PURPLE_TO_STORAGE:
    - action: attach_port
      filter: port.vendor == 'purple' && network.name == 'storage':
  CUSTOM_BOND_PURPLE_BY_2:
    - action: group_and_attach_ports
      filter: port.vendor == 'purple'
      max_count: 2
  CUSTOM_BOND_GREEN_STORAGE_TO_STORAGE_BY_2:
    - action: group_and_attach_ports
      filter: port.vendor == 'green' && port.class == 'storage' && ( network.name =~ 'storage' or network.tags =~ 'storage' )
      max_count: 2
      min_count: 2
  CUSTOM_USE_PHYSNET_A_OR_B:
    - action: attach_port
      filter: port.physical_network == 'fabric_a' && network.tag == 'a'
    - action: attach_port
      filter: port.physical_network == 'fabric_b' && network.tag == 'b'


Filtering Undesired Networks
----------------------------

As such, in this model to help alignment, and help prevent
Ironic service or port fabric usage from crossing over into
undesirable network fabrics which may have specific purposes,
for example dedicated storage network fabrics, then we will
also add a new option to ironic.conf and filtering behavior
wrapped around the internal network attachments.

This option shall be in the ``[DEFAULT]`` configuration section
and called ``ironic_network_attachment_filter``, and will take
a filter value like one which could be set for a flavor mapping.


Future Enhancements
-------------------

Obvious minor future enhancements to this feature would include:

  - specifying a default set of rules to apply to a single node  (e.g.
    node.driver_info.default_network_rule=CUSTOM_MANUAL_NETWORKING_EXPLICIT)
  - specifying a default set of rules to apply to a group of nodes (e.g. a
    default for all nodes, or for all nodes of a given resource_class)
  - support for non-integrated OpenStack use cases
  - use of dynamic port mapping functionality for system networks, such as
    ``service_network`` or ``cleaning_network``
  - populating new Port.class and/or Port.vendor fields in inspection
  - exposing the contents of port.extra/portgroup.extra fields to expressions

While none of these are to be implemented as part of the MVP, they are minor
enhancements many of which will be required for most use cases. They
are included here to round out the full possible vision of network mapping in
Ironic.

This change also opens the door for performing other pre-provisioning actions
to a node, although this spec limits itself to network mappings and
configuration.

.. _Alternatives:

Alternatives
------------

The overall idea which has been presented marries two basic requirements,
being dynamically associate bonding for nodes with deploy-time operations,
and to do it in a way which is minimally invasive to Nova as it is modeled
to operate today.

This is because many operators have multi-tenant environments they
leverage bare metal within, and they want more precise control over their
networking.

To reach the same level of flexibility, we would ultimately have to implement
similar ideas in Nova, which is largely viewed as unlikely to move forward due
to lack of general virtual machine applicability.

OR, a more costly and interruptive option for mixed workloads, operators
may need to work to remove Nova from their operational picture and either
directly write their own logic to facilitate these sorts of configurations,
or just orchestrate the configuration directly in advance. Neither of which
approach may be palatable to operators who are deeply invested in convereged
multitenant platforms.

Advance direct association - Similar Functionality
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

At a point in the past, the ability to request a VIF to be paired to
a specific port or portgroup was added in change
I82efa90994325aa37cca865920d656f510a691b2, however no *known* user of
Ironic API surface leverages this functionality and for the general
usage case.

This *does* technically allow a user to explicitly know the details and
request a mapping, but that requires a high level of detail about the
infrastructure which for unprivileged users would be inappropriate.

No change to the direct mapping is anticipated as part of this work.

That being said this functionality, while sort of related in terms of solving
mapping of a "virtual interface" to a "physical port" is useful, it requires
advance configuration as well which is largely unsuitable for operations close
to deploy.

.. _Data model impact:

Data model impact
-----------------

In order to facilitate this, we'll need to add new field values on ports and
portgroups to enable more verbose operator interactions with the objects in
order for an operator to be able to easily identify and tag ports/portgroups
for filtering.

To the Port object, and ultimately API:

Milestone 1:

- "vendor" - String field - 32 characters
- "class" - String field - 80 characters

Milestone 2:

- "available_for_dynamic_portgroup" - Boolean - Default False

To the Portgroup object, and ultimately API:

Milestone 1:

- "class" - String field - String field - 80 characters
- "physical_network" - String field - 64 characters - Read only to API
  consumers, will reflect physical_network set on member ports.

Milestone 2:

- "dynamic_portgroup" - Boolean value - Read only to API consumers,
  default False but set to True internally so Ironic can know when
  the portgroup must be torn down.

The default states for these fields will be null with no data migration
necessary. Implementer may choose to add all fields in milestone one DB
migration to prevent operators from needing two migrations.

State Machine Impact
--------------------

None

REST API impact
---------------
The fields listed in :ref:`Data Model Impact` will be exposed in the port and
portgroup APIs using standard Ironic conventions for those objects.

Accordingly, the REST API microversion will also need to be incremented.

All port group members must have the same physical network.

If a port needs to change its physical_network then any existing portgroups
that it is a member of must be torn down or deleted.

Client (CLI) impact
-------------------

"openstack baremetal" CLI
~~~~~~~~~~~~~~~~~~~~~~~~~

The baremetal client will need to be modified to include the additional
fields.

"openstacksdk"
~~~~~~~~~~~~~~

The openstacksdk will need to be modified to include the additional fields.

RPC API impact
--------------

The objects for port and portgroup will be updated with the new fields.

Driver API impact
-----------------

None

Nova driver impact
------------------

In :ref:`Overall flow of request handling`, we dictate an order of operations
which are required in order for this new functionality to work. It's
currently our belief that the code in the virt driver, as written today, may
facilitate that.

Ramdisk impact
--------------

None

Security impact
---------------

None

Other end user impact
---------------------

None

Scalability impact
------------------

It's not ideal for scaling that we are adding an additional config to
aggregate which will have to be potentially updated as network layouts change.
Operators are encouraged to use the expression grammar with prefix
matching and network tagging to make configurations which can apply to "N"
network configurations in large scale environments.

Performance Impact
------------------

Under this model, vif attachment actions will take some additional actions
per-request which will be defined by the operator supplied rules. In other
words the rules will be evaluated, and depending on rule complexity,
additional queries may be triggered such as to Neutron to aid in populating
information necessary to complete the requested action.

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
  - Jay Faulkner <jay at gr-oss.io, IRC: JayF)
  - Clif Houck <clif at gr-oss.io, IRC: clif)

Other contributors:
  - CID <cid at gr-oss.io, IRC: cid)

Work Items
----------

Pre-Work
~~~~~~~~
0) Before beginning, document how to setup a test environment in devstack for
   testing advanced networking. See :ref:`Testing`.


Milestone One
~~~~~~~~~~~~~

1) Add new fields to Port, Portgroup at object and DBAPI layers.
2) Add fields to REST API, bump microversion. Do not expose dynamic portgroup
   related fields at API level at this time.
3) Create logic to handle filters and match with source ports, portgroups.
4) Document new functionality, config file and syntax, and create a sample
   config


Milestone Two
~~~~~~~~~~~~~

1) Expose previously added dynamic portgroup related fields to REST API, bump
   microversion.
2) Add action to create portgroups on the fly (``group_and_attach_ports``)
3) Add logic to dynamically create port and portgroups from matches,
   and select that new portgroup for the dynamic portgroup.
4) Add logic upon teardown of a baremetal node VIF to tear down dynamic
   portgroups upon removal of the vif.
5) Update documentation to reference new functionality and actions. Create a
   sample configuration and use case around dynamic portgroups.


Dependencies
============

None

.. _Testing:

Testing
=======

Implementers will need to add a devstack configuration to the contributor
guide, indicating how to get a fully functional devstack installation with
some way to configure separate networks to schedule into. There may be
existing functionality in devstack to provide this or some may need to be
added; there may be CI jobs that can be used as a template (e.g.
networking-baremetal-multitenant-vlans).

Be sure to explicitly test the following cases:
  - A request to deploy that is unfulfillable
  - Restoration of configuration after node servicing works properly
  - Restoration of configuration after node rescuing works properly


Upgrades and Backwards Compatibility
====================================

Not applicable.

Documentation Impact
====================

Comprehensive documentation for this feature should be provided, including:
  - Specific example common use cases and configurations
  - A fully specified schema for our yaml configuration file and a full list of
    available values for use in expressions, similarly to how it's specified
    in this spec.
  - How to migrate an existing installation using physical_network mappings
    to be dynamically mapped.

References
==========

TBD
