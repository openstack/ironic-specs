..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=======================================
Migrate inspection rules from Inspector
=======================================

https://storyboard.openstack.org/#!/story/2010275

This specification finishes the work started in
:doc:`/approved/merge-inspector` by migrating the inspection rules API.

Please see the :ref:`inspector-glossary` for the concepts required to
understand this specification.

Problem description
===================

Inspection is a pretty opinionated process. A few areas often require
site-specific customizations:

* Auto-discovery. For example, credentials may be populated for new nodes
  following a certain pattern or by fetching them from a CMDB.

* Validation logic. Some operators want to fail inspection if the nodes do not
  fulfill certain criteria. In the context of auto-discovery, such a validation
  may be used to prevent unexpected machines from getting enrolled.

These requests can be covered by inspection hooks. But, as explained in
alternatives_, writing and deploying hooks can be too inflexible.

Proposed change
===============

Migrate a streamlined version of `introspection rules`_ from Inspector.

These useful features are added on top of what Inspector provides:

Built-in rules
  Allow operators to load rules from a YAML file. These rules will be always
  present, won't be stored in the database and won't be deletable.
  Such rules are both an easier way to write hooks and a replacement for
  awkward Inspector's configuration options such as
  ``[discovery]enabled_bmc_address_version``.

Phases
  In Inspector, rules are always run at the end of processing. We'll add
  a new field ``phase`` to rules with values:

  * ``early`` - run before any other processing, even before auto-discovery and
    lookup. Such rules will not have access to the node object.
  * ``preprocess`` - run after the ``preprocess`` phase of all inspection
    hooks, but before the main phase.
  * ``main`` (the default) - run after all inspection hooks.

Updating rules
  Inspector does not provide API for updating rules. There is no reason for
  that, and we'll add ``PATCH`` support for them.

Sensitive rules
  Conditions and actions of the rules may contain sensitive information, e.g.
  BMC information. If a rule is marked as sensitive, its actions and conditions
  will not be returned as part of the ``GET`` request response. It will not be
  possible to make a sensitive rule not sensitive.

  Error messages resulting from running sensitive rules will also be a bit
  terse to avoid accidentally disclosing sensitive information.

Priorities
  In Inspector, rules are always run in the creation order. This is obviously
  inconvenient, so in Ironic we'll add priorities to them. Priorities between 0
  and 9999 can be used by all rules, negative value and values above 10000 are
  reserved for built-in rules. The default priority is 0. Rules within the same
  priority are still run in the creation order for compatibility.

Database storage
  Currently, Inspector spreads each rule into three tables (rules, conditions
  and actions). This may be more correct from the database design perspective,
  but is actually inconvenient to work with, since conditions and actions are
  never accessed outside of a Rule context. Nor are rules ever accessed without
  their conditions and actions. This specification buts them as JSON fields
  inside the Rule table.

Consistent arguments for conditions and actions
  A condition has a ``field`` attribute that is special-cased to be a field of
  either the node or the inventory. This specification changes both to
  structure with one operation and several arguments, see `data model impact`_.

Alternatives
------------

* Use the inspection hooks mechanism. Hooks are less flexible since they
  require Python code to be installed alongside Ironic and the service to be
  restarted on any change. The former is especially problematic for
  container-based deployments.

* Radically change the rules DSL to something less awkward, e.g. Ansible-like
  miniscript_. While I still want to do it eventually, I think such an
  undertaking will increate the scope of this already large work too much.
  With API versioning in place, we can always change the language under the
  hood.

* Allow API users to upload Python code. No comments.

* Seriously, though, write the rules in `Lua <https://pypi.org/project/lupa/>`_
  or any other "grown-up" embedded language. I haven't researched this option
  enough.  Maybe it's the way to go? Will deployers mind a new C dependency
  (on liblua or LuaJIT)?

* Copy inspection rules verbatim, no removals, no additions. I don't see why
  not make small improvements for better long-term maintenance. Some of the
  additions are related to security.

* Make inspection rules into a service separate from Ironic. Defeats the
  purpose of the Inspector merger. For example, no access to the node database
  means less efficient operations.

* Do not migrate inspection rules at all. They do bring a bit of complexity,
  but also proved a helpful instrument for operations. CERN uses them, which is
  my benchmark for usefulness among advanced operators.

Data model impact
-----------------

Adapted from Inspector with the additions described in `Proposed change`_:

.. code-block:: python

    class Rule(Base):
        uuid = Column(String(36), primary_key=True)
        created_at = Column(DateTime, nullable=False)
        updated_at = Column(DateTime, nullable=True)
        priority = Column(Integer, default=0)
        description = Column(String(255), nullable=True)
        scope = Column(String(255), nullable=True)  # indexed
        sensitive = Column(Boolean, default=False)
        phase = Column(String(16), nullable=True)  # indexed
        conditions = Column(db_types.JsonEncodedList(mysql_as_long=True))
        actions = Column(db_types.JsonEncodedList(mysql_as_long=True))

Conditions and actions
~~~~~~~~~~~~~~~~~~~~~~

In this specification, both conditions and actions have the same base
structure:

* ``op`` - operation: either boolean (conditions) or an action (actions).
* ``args`` - a list (in the sense of Python ``*args``) or a dict (in the sense
  of Python ``**kwargs``) with arguments.

The special attributes for actions in Inspector get a different form:

* Instead of ``invert``: put an exclamation mark (with an optional space)
  before the ``op``, e.g. ``eq`` - ``!eq``.

* Instead of just ``multiple``, support an Ansible-style ``loop`` field.
  On actions, several actions are run. On conditions, the ``multiple`` field
  defines how to join the results. Same as in Inspector:

  any (the default)
    require any to match

  all
    require all to match

  first
    effectively, short-circuits the loop after the first iteration

  last
    effectively, only runs the last iteration of the loop.

Variable interpolation
~~~~~~~~~~~~~~~~~~~~~~

String arguments are processed by Python formatting with ``node``,
``ports``, ``port_groups``, ``inventory`` and ``plugin_data`` objects
available, e.g.  ``{node.driver_info[ipmi_address]}``,
``{inventory[interfaces][0][mac_address]}``.

When running in the early phase, only ``inventory`` and ``plugin_data`` are
available.

The ``node`` is actually a proxy mapping taking into account the
``mask_secrets`` option (described in `other deployer impact`_).

If a value is a string surrounded by single curly brackets ``{`` and ``}`` (no
unformatted text), we'll evaluate what is inside and avoid converting it into a
string. This way, lists and dictionaries can be passed to actions and ``loop``.
This behavior will likely be implemented by hooking into the
`Formatter <https://docs.python.org/3/library/string.html#string.Formatter>`_
class.

Available conditions
~~~~~~~~~~~~~~~~~~~~

Unlike in Inspector, a list of conditions will be built into Ironic:

``is-true(value)``
  Check if value evaluates to boolean True. On top of actual booleans, non-zero
  numbers and strings "yes", "true" (in any case) are evaluated to True.
``is-false(value)``
  Check if value evaluates to boolean False. On top of actual booleans, zero
  ``None`` and strings "no", "false" (in any case) are evaluated to False.

.. note::
   These conditions can both be false for some values (e.g. random strings).
   This is intentional.

``is-none(value)``
  Check if value is None.
``is-empty(value)``
  Check if value is None or an empty string, list or a dictionary.
``eq/lt/gt(*values, *, force_strings=False)``
  Check if all values are equal/less than/greater than. If ``force_strings``,
  all values will be converted to strings first.

  .. note::
     Inspector has ``ne``, ``le`` and ``ge``, which can be implemented via
     ``!eq``, ``!gt`` and ``!lt`` instead.

``in-net(address, subnet)``
  Check if the given address is in the provided subnet.
``contains(value, regex)``
  Check if the value contains the given regular expression.
``matches(value, regex)``
  Check if the value fully matches the given regular expression.
``one-of(value, values)``
  Check if the value is in the provided list. Similar to ``contains``, but also
  works for non-string values. Equivalent to:

  .. code-block:: yaml

    - op: eq
      args: [<value>, "{item}"]
      loop: <values>

Available actions
~~~~~~~~~~~~~~~~~

Similar to Inspector, actions will be plugins from the entry point
``ironic.inspection_rules.actions``. Coming with Ironic are:

``fail(msg)``
  Fail inspection with the given message.
``set-plugin-data(path, value)``
  Set a value in the plugin data.
``extend-plugin-data(path, value, *, unique=False)``
  Treat a value in the plugin data as a list, append to it. If ``unique`` is
  True, do not append if the item exists.
``unset-plugin-data(path)``
  Unset a value in the plugin data.
``log(msg, level="info")``
  Write the message to the Ironic logs.

The following actions are not available in the ``early`` phase:

``set-attribute(path, value)``
  Set the given path (in the sense of JSON patch) to the value.
``extend-attribute(path, value, *, unique=False)``
  Treat the given path as a list, append to it.
``del-attribute(path)``
  Unset the given path. Fails on invalid node attributes, but does not fail on
  missing subdict fields.
``set-port-attribute(port_id, path, value)``
  Set value on the port identified by a MAC or a UUID.
``extend-port-attribute(port_id, path, value, *, unique=False)``
  Treat the given path on the port as a list, append to it.
``del-port-attribute(port_id, path)``
  Unset value on the port identified by a MAC or a UUID.

.. note::
   Here *path* is a path in the sense of a JSON patch used by Ironic API.

Examples
~~~~~~~~

Partly taked from the Inspector docs, using YAML format.

.. code-block:: yaml

   - description: Initialize freshly discovered nodes
     sensitive: true
     conditions:
       - op: is-true
         args: ["{node.auto_discovered}"]
       - op: "!is-empty"
         args: ["{plugin_data[bmc_address}"]
     actions:
       - op: set-attribute
         args: ["/driver", "ipmi"]
       - op: set-attribute
         args: ["/driver_info/ipmi_address", "{plugin_data[bmc_address]}"]
       - op: set-attribute
         args: ["/driver_info/ipmi_username", "admin"]
       - op: set-attribute
         args: ["/driver_info/ipmi_password", "pa$$w0rd"]

.. note::
   The ``plugin_data[bmc_address]`` field is a side-effect of the
   ``validate_interfaces`` hook.

.. code-block:: yaml

   - description: Initialize Dell nodes using IPv6
     sensitive: true
     conditions:
       - op: is-true
         args: ["{node.auto_discovered}"]
       - op: contains
         args: ["{inventory[system_vendor][manufacturer]}", "(?i)dell"]
     actions:
       - op: set-attribute
         args: ["/driver", "idrac"]
       - op: set-attribute
         args: ["/driver_info/redfish_address", "https://{inventory[bmc_v6address]}"]
       - op: set-attribute
         args: ["/driver_info/redfish_username", "root"]
       - op: set-attribute
         args: ["/driver_info/redfish_password", "calvin"]

State Machine Impact
--------------------

None (rules are running in the ``INSPECTING`` state)

REST API impact
---------------

Migrate the API mostly verbatim, changing the prefix to ``inspection_rules``,
adding ``PATCH`` and more options for listing:

``POST /v1/inspection_rules``
  Create an inspection rule. The request body is the representation of the
  rule. All fields, except for ``built_in`` can be set on creation.
  Only ``actions`` are required (rules with empty conditions run
  unconditionally).

  Returns HTTP 400 on invalid input.

``GET /v1/inspection_rules/<uuid>``
  Return one inspection rule. The output fields mostly repeat the database
  fields, adding a boolean ``built_in`` field.

  For sensitive rules, ``null`` is returned instead of ``conditions`` and
  ``actions``.

  Returns HTTP 404 if the rule is not found.

``GET /v1/inspection_rules[?detail=true/false&scope=...&phase=...]``
  List all inspection rules. If ``detail`` is ``false`` or omitted, conditions
  and actions are not returned. Filtering by scope and phase is possible.

  Returns HTTP 400 on invalid input.

``PATCH /v1/inspection_rules/<uuid>``
  Update one rule and return it. Sensitive rules can be updated, but the result
  does not contain conditions or actions in any case.

  Returns HTTP 404 if the rule is not found.

  Returns HTTP 400 if the input is invalid, e.g. trying to modify ``built_in``,
  change ``sensitive`` to ``false`` or set priority outside of the allowed
  range (0 to 9999).

``DELETE /v1/inspection_rules/<uuid>``
  Remove one rule.

  Returns HTTP 404 if the rule is not found.

  Returns HTTP 400 if the rule is built-in.

``DELETE /v1/inspection_rules``
  Remove all rules except for built-in ones.

Client (CLI) impact
-------------------

"openstack baremetal" CLI
~~~~~~~~~~~~~~~~~~~~~~~~~

Inspection rules CRUD, adapted from the `Introspection Rules CLI
<https://docs.openstack.org/python-ironic-inspector-client/latest/cli/index.html#introspection-rules-api>`_,
simply replacing *introspection* with *inspection*:

.. code-block:: console

  $ openstack baremetal inspection rule import <file>
  $ openstack baremetal inspection rule list [--long]
  $ openstack baremetal inspection rule get <rule ID>
  $ openstack baremetal inspection rule delete <rule ID>

The mass-deletion command is changed for clarity:

.. code-block:: console

  $ # Inspector version:
  $ openstack baremetal introspection rule purge
  $ # New version:
  $ openstack baremetal inspection rule delete --all

Updating will be possible:

.. code-block:: console

  $ openstack baremetal inspection rule set <rule ID> \
        [--actions '<JSON>'] [--conditions '<JSON>'] \
        [--sensitive] [--scope '<scope>'] [--phase 'early|preprocess|main'] \
        [--uuid '<uuid>'] [--description '<description>']
  $ openstack baremetal inspection rule unset <rule ID> \
        [--conditions] [--scope] [--description]

Also adding a way to create from fields instead of one JSON:

.. code-block:: console

  $ openstack baremetal inspection rule create \
        --actions '<JSON>' [--conditions '<JSON>'] \
        [--sensitive] [--scope '<scope>'] [--phase 'early|preprocess|main'] \
        [--uuid '<uuid>'] [--description '<description>']

"openstacksdk"
~~~~~~~~~~~~~~

The baremetal module will be updated with the standard CRUD plus mass-deletion:

.. code-block:: python

   def inspection_rules(details=False): pass
   def get_inspection_rule(rule): pass
   def patch_inspection_rule(rule, patch): pass
   def update_inspection_rule(rule, **fields): pass
   def delete_inspection_rule(rule, ignore_missing=True):
   def delete_all_inspection_rules(): pass

RPC API impact
--------------

None

Driver API impact
-----------------

No driver impact. Operators may opt for running inspection rules on nodes with
all inspect interfaces, including out-of-band ones.

Nova driver impact
------------------

None

Ramdisk impact
--------------

None

Security impact
---------------

Inspection rules have access to all node and inventory data. Thus, they should
be restricted to admins only.

Other end user impact
---------------------

None

Scalability impact
------------------

None

Performance Impact
------------------

Having a lot of inspection rules will make inspection longer. But it should not
affect the rest of the system.

Other deployer impact
---------------------

The new section ``[inspection_rules]`` will have these options:

``built_in``
  An optional path to a YAML file with built-in inspection rules. Loaded on
  service start and thus not modifiable via SIGHUP.

``default_scope``
  The default value for ``scope`` for all rules where this field is not set
  (excluding built-in ones).

``mask_secrets``
  Whether to mask secrets in the node information passed to the rules:

  * ``always`` (the default) - always remove things like BMC passwords.
  * ``never`` - never mask anything, pass full node objects to all rules.
  * ``sensitive`` - allow secrets for rules marked as ``sensitive``.

  .. FIXME(dtantsur): mask_secrets=sensitive reads as the opposite from what
     it actually does... Better ideas? mask_secrets=when_not_sensitive is
     quite awkward.

``supported_interfaces``
  A regular expression to match *inspect interfaces* that run inspection rules.
  Defaults to ``^(agent|inspector)$`` to limit the rules to only in-band
  implementations. Can be set to ``.*`` to also run on all nodes.

One option will be added to the ``[auto_discovery]`` section:

``inspection_scope``
  The default value of inspection scope for nodes enrolled via auto-discovery.
  Simplifies targeting such nodes with inspection rules.

Developer impact
----------------

Actions are provided via plugins with entry points in the
``ironic.inspection_rules.actions`` namespace:

.. code-block:: python

    class InspectionRuleActionBase(metaclass=abc.ABCMeta):
        """Abstract base class for rule action plugins."""

        formatted_params = []
        """List of params to be formatted with python format."""

        supports_early = False
        """Whether the action is supported in the early phase."""

        def call_early(self, rule, *args, **kwargs):
            """Run action in the early phase."""
            raise NotImplementedError

        @abc.abstractmethod
        def __call__(self, task, rule, *args, **kwargs):
            """Run action on successful rule match."""

.. note::
   The interface in Inspector supports several additional validation features.
   I hope to derive the valid arguments from method signatures instead.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Dmitry Tantsur (IRC: dtantsur, dtantsur@protonmail.com)

Other contributors:
  TBD

Work Items
----------

See the RFE.

Dependencies
============

* :doc:`/approved/merge-inspector`

Testing
=======

* Add functional tests exercising inspection rules CRUD actions.

* Update the in-band inspection job to have a simple rule that we can verify
  is run (e.g. it sets something in the node's extra).

Upgrades and Backwards Compatibility
====================================

Existing rules will not be automatically migrated from Inspector to Ironic
since the conversion may not be always trivial (e.g. around variable
interpolation or loops).

Documentation Impact
====================

* API reference will be updated.

* User guide will be migrated from Inspector with a couple of real-life
  examples_.

References
==========

.. _introspection rules: https://docs.openstack.org/ironic-inspector/latest/user/usage.html#introspection-rules
.. _miniscript: https://github.com/dtantsur/miniscript
