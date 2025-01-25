..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===========================
Merge Inspector into Ironic
===========================

https://storyboard.openstack.org/#!/story/2010275

This specification proposes merging the ironic-inspector_ project (*Inspector*)
into the main Ironic project completely, making all its API feature a part of
the Bare Metal API and deprecating the separate project.

Problem description
===================

*Inspector* was born from a bunch of unmerged patches to Ironic back in the
middle of year 2014 under the name *ironic-discoverd*. The Ironic team
considered the patches, especially the idea of auto-discovery, going too much
outside of the Bare Metal project scope. In early 2015, the Ironic team has
agreed to move the already established and functioning project under its wing,
changing the name to *ironic-inspector*. Over time, Inspector gained and then
lost again its own core reviewer team, while becoming more and more aligned
with the standard practices in the Ironic community.

Fast forward to year 2023, very few still standing members of the community
remember this story. "Why is Inspector separate from Ironic?" is a common
question among newcomers. There are few problems with the current state of
things:

Maintenance load.
  A great example is the SQLAlchemy 2.0 transition. Since *Inspector* has
  a separate database, we need to do the work twice.

Operating load.
  One more service - one more problem. It has to be installed, secured and
  updated regularly.

Scaling/HA issues.
  Ironic has been designed with horizontal scaling and high availability in
  mind; Inspector has not. To a certain extent, it makes sense: Inspector is
  only used occasionally. Still, in a really large deployment (like CERN's)
  even rarely used services are accessed often enough for the availability
  to matter.

  The problem has been mostly mitigated by introducing support for a message
  bus (RabbitMQ) and membership tracking (ZooKeeper/etcd). Mostly - because the
  solution depends on two services that are normally present in OpenStack, but
  are not present in standalone solutions like Bifrost or Metal3_
  [#metal3-and-etcd]_.

Performance issues.
  Since Inspector has a separate database, it has to maintain its own nodes
  table and synchronize it with Ironic periodically. This is inefficient and
  may contribute to scalability problems.

  Similarly, every inspection hook (see the Glossary_) has to issue some API
  requests to Ironic to update information. A pipeline with several hooks may
  generate noticeable traffic.

Resource utilization.
  Inspector, being written in Python, has a non-negligible RAM footprint, while
  doing nearly nothing most of the time.

Discoverability.
  Since Inspector has its own documentation, API reference and client, it's
  harder to discover information about it.

.. _inspector-glossary:

Glossary
--------

In-band inspection
  Hardware inspection that is conducted through the use of a ramdisk with IPA
  (ironic-python-agent_).  The other option is out-of-band inspection, where
  the data is collected through the BMC without powering on the node.

  The term *introspection* is used as a synonym in the Inspector code base and
  documentation.

Inspection data
  Generic term for all information collected by IPA during inspection and sent
  back to Inspector (in the future - to Ironic).

Inventory
  In the broad sense - synonym to inspection data. In the narrower sense -
  hardware inventory_ as defined by IPA and returned by its hardware managers.

Inspection collectors
  IPA plugin responsible for collecting inspection data on the ramdisk side.
  The ``default`` one collects inventory_. Collectors are currently independent
  from hardware managers, but this may change in the future.

Processing hooks
  Inspector (in the future - Ironic) plugins for processing inspection data and
  updating the node as a result. Allow operators to fine-tune the inspection
  process by configuring a pipeline of processing hooks.

  This document introduces the term *inspection* hooks to avoid ambiguity
  in the larger Ironic context.

Inspection hooks and collectors may correspond to each other. For example, the
``extra-hardware`` collector has a corresponding ``extra_hardware`` hook.

Managed/unmanaged inspection
  We are talking about *managed* inspection when it is Ironic that completely
  sets up the boot environment, be it (i)PXE or virtual media boot. Inspection
  is *unmanaged* when the (i)PXE environment from Inspector, usually a
  separate *dnsmasq* installation, is used.

  Unmanaged inspection has been the default for Inspector for a long time.
  Managed inspection was introduced to support virtual media, first and
  foremost. With the proposed merge, managed inspection will become the default
  mode, while unmanaged inspection will require an explicit configuration.

PXE filters
  A way for the separate Inspector's PXE environment to co-exist with Neutron
  by limiting which MAC addresses it serves. Inspector has two implementations:

  * ``iptables`` uses firewall to open/close access to a DHCP server
  * ``dnsmasq`` updated *dnsmasq* host files with MAC addresses to serve/deny

  Over time, the ``dnsmasq`` PXE filter was found to be more scalable and
  flexible (e.g. it supports spine/leaf architectures with DHCP relays) at the
  cost of supporting only one DHCP server implementation.

  This specification proposes migrating only the ``dnsmasq`` PXE filter. The
  ``iptables`` one will follow if we see a demand for it (the deprecation
  release notes will mention it).

Auto-discovery
  Process of enrolling new nodes automatically. When unmanaged inspection is
  configured, unknown nodes on the provisioning network will boot into the IPA
  ramdisk, get inspected and registered in Ironic.

  This operation is disabled by default.

Proposed change
===============

Inspector features will be migrated step-by-step into the Ironic code base,
predominantly into the ``ironic.drivers.modules.inspector`` package. We will
try to avoid radical changes in the design with the following exceptions:

* Split the poorly defined *inspection data* into the formally defined and
  version (although not in the sense of API microversions) inventory_ and
  free-form plugin data (influenced by inspection collectors in IPA and
  processing hooks in Inspector/Ironic - see the glossary_).

  Inventory will not be mutated by any inspection hooks, thus reducing
  the need for having unprocessed inspection data API (which Inspector has).

* Avoid poorly documented internals data formats in the processed data.
  For example, Inspector generates fields ``interfaces`` and ``all_interfaces``
  that are not based on the ``interfaces`` collection in the inventory.

* Split the migrated PXE filter into a new script to avoid coupling it (and
  thus the *dnsmasq* instance behind it) to Ironic processes. This way, it can
  be scaled separately.

* Rework inspection (former processing) hooks for more obvious naming and
  better composability.

  Consistently use dashes instead of underscores in entry point names.

  Fewer hooks will run in the default configuration.

* Consistently use the term *inspection* instead of *introspection*.

For the sake of keeping this specification's size reasonable and my sanity
(relatively) intact, inspection rules are omitted here. They're relatively
trivial, but require a lot of explanation and can be implemented independently.

Alternatives
------------

Keep Inspector separate.
  Possible arguments for it include:

  * Better utilizing CPU cores by having a separate process. This should better
    be solved by allowing several conductors per physical host. Such a solution
    will benefit also more intensive operations and deployments without
    Inspector.

  * More manageable (i.e. smaller) code base. However, a lot of code in
    Inspector exists only because it's a separate project. This includes most
    of the database code, some of the API endpoints and the node
    synchronization routine.

Do not migrate some of the major features.
  This will hinder the migration and will prevent us from ever deprecating
  Inspector.

Do not migrate PXE filters.
  This will make auto-discovery in the presence of Neutron impossible.
  Auto-discovery is a commonly requested feature (`example request
  <https://github.com/metal3-io/baremetal-operator/issues/1124>`_).

Data model impact
-----------------

Inventory table
~~~~~~~~~~~~~~~

Add a new table for storing inspection data when the Object Storage service is
not available:

.. code-block:: python

    class NodeInventory(Base):
        """Represents an inventory of a baremetal node."""
        __tablename__ = 'node_inventory'
        __table_args__ = (
            Index('inventory_node_id_idx', 'node_id'),
            table_args())
        id = Column(Integer, primary_key=True)
        inventory_data = Column(db_types.JsonEncodedDict(mysql_as_long=True))
        plugin_data = Column(db_types.JsonEncodedDict(mysql_as_long=True))
        node_id = Column(Integer, ForeignKey('nodes.id'), nullable=True)

Here, ``inventory_data`` contains the inventory as defined by IPA (see the
Glossary_), while ``plugin_data`` contains auxiliary data returned by various
collectors or generated by inspection hooks.

The ``NodeInventory`` object is deleted on node deletion.

.. note:: This table already exists at the time of writing this specification.
          It is included here for completeness.

Node modifications
~~~~~~~~~~~~~~~~~~

Add a new boolean field ``auto_discovered`` to the ``nodes`` table. It will be
read-only from the API standpoint and will be used to mark auto-discovered
nodes.

State Machine Impact
--------------------

The only expected change is a possibility of transition from ``INSPECT WAIT``
to ``INSPECTING``, which is arguably missing by mistake.

REST API impact
---------------

Add a new API endpoint to fetch the inventory and the optional plugin data:

``GET /v1/nodes/{node}/inventory``
    Returns a JSON object with two keys: ``inventory`` and ``plugin_data``.

    HTTP status codes:

    * 200 on success.

    * 404 if the node is not found, no inventory is recorded, or the API is not
      available in the requested version.

.. note:: This API already exists at the time of writing this specification.
          It is included here for completeness.

Add a new API to accept the inspection data from the ramdisk:

``POST /v1/continue_inspection``
    Accepts inspection data in exactly the same format as Inspector, namely
    as a JSON object with at least an ``inventory`` field.

    The only query parameter is ``node_uuid`` - an optional UUID of the node.
    This parameter is designed for virtual media deployments to safely pass
    the node identity to the ramdisk. See `lookup process`_ for some details.

    This API is **not authenticated** and does not require an agent token since
    inspection always happens first on agent start-up.

    The result depends on the requested API version:

    * In the base API version, Inspector compatibility mode is used. The
      resulting JSON object has one key: ``uuid`` (the node's UUID).

    * In the new API version, the result is the same as in the normal lookup
      API. In this case, the API generates and returns an agent token,
      effectively replacing lookup when inspection is used.

    HTTP status codes:

    * 200 on success.

    * 404 if the node is not found, several nodes match the provided data,
      or the node state is not ``INSPECT WAIT``.

      .. note:: We use the same generic HTTP 404 response to avoid disclosing
                any information to a potential intruder.

Return the ``auto_discovered`` field in the full node representation. Update
the node listing (``GET /v1/nodes``) with an ability to filter by this field.

Lookup process
~~~~~~~~~~~~~~

The lookup process is somewhat more complicated than the normal Ironic lookup
because the inspected nodes may not have any ports enrolled. The procedure will
try to find one and *only one* node that satisfies the provided node UUID,
MAC addresses and BMC addresses.

BMC addresses are not indexed in the database and require some pre-processing.
When *starting* inspection, BMC addresses will be collected from the node's
``driver_info``, resolved into IP addresses and cached in the
``driver_internal_info``. On lookup, ``driver_internal_info`` from all nodes in
the ``INSPECT WAIT`` state will be checked.

If none or several nodes match the data, HTTP 404 with no explanation will be
returned. Extensive logging will be provided for debugging purposes.

Auto-discovery
~~~~~~~~~~~~~~

If auto-discovery is enabled (see `auto-discovery configuration`_), the lookup
process will work a bit differently for completely new nodes. If no node at all
can be found for data (as opposed to a node in an invalid state), a new node
will be created by the API layer. The rest of inspection happens the same way.

Nodes created this way will have an ``auto_discovered`` field set to ``True``.

Client (CLI) impact
-------------------

All new API features will need to be exposed.

"openstack baremetal" CLI
~~~~~~~~~~~~~~~~~~~~~~~~~

Starting and aborting inspection.
  No changes here, use the same commands:

  .. code-block:: console

    $ openstack baremetal node set --inspect-interface agent <node>
    $ openstack baremetal node inspect <node>
    $ openstack baremetal node abort <node>

Exposing inspection data.
  I would like to have command to display certain parts of the inventory,
  filter it, etc. It is unclear if we should do it on the client or server side
  (or not do it at all). Inspector has a couple of comments for extracting
  parts of the inventory. I suggest not to migrate them in the first iteration.

  We'll start with migrating the most basic command, simply saving the complete
  JSON to a file or displaying it:

  .. code-block:: console

    $ openstack baremetal node inventory save [--file <file path>] <node>

The callback endpoint will not be exposed via the CLI.

Filtering auto-discovered nodes
  Can be useful for auditing purposes, especially together with filtering on
  provision state:

  .. code-block:: console

    $ openstack baremetal node list --provision-state enroll --auto-discovered

"openstacksdk"
~~~~~~~~~~~~~~

Expose a call to fetch inventory, very similar to the existing call for
Inspector:

.. code-block:: python

    def get_inventory(self, node):
        """Get inventory for the node.

        :param node: The value can be the name or ID of a node or a
            :class:`~openstack.baremetal.v1.node.Node` instance.
        :returns: inspection data from the most recent successful run.
        :rtype: dict
        """

Update the node API with filtering on ``auto_discovered``.

RPC API impact
--------------

A new RPC call will be introduced for handling the inspection data:

.. code-block:: python

  def continue_inspection(self, context, node_id, inventory,
                          plugin_data=None):
      """Continue in-band inspection.

      :param context: request context.
      :param node_id: node ID or UUID.
      :param inventory: hardware inventory from the node.
      :param plugin_data: optional plugin-specific data.
      :raises: NodeLocked if node is locked by another conductor.
      :raises: NotFound if node is in invalid state.
      """

On receiving this call, the conductor will acquire an exclusive lock,
double-check the provision state and launch a thread for further processing.

See `PXE filter script`_ for further impact.

Driver API impact
-----------------

Extend the *inspect interface* with an additional call:

.. code-block:: python

  def continue_inspection(self, task, inventory, plugin_data=None):
      """Continue in-band hardware inspection.

      Should not be implemented for purely out-of-band implementations.

      :param task: a task from TaskManager.
      :param inventory: hardware inventory from the node.
      :param plugin_data: optional plugin-specific data.
      :raises: UnsupportedDriverExtension, if the method is not implemented
               by specific inspect interface.
      """

Inspection hooks
~~~~~~~~~~~~~~~~

Inspection hooks are a new kind of Ironic plugins, closely based on the
Inspector's processing hooks (see the Glossary_).

The current Inspector's processing hook interface looks like this (shortening
docstrings for readability):

.. code-block:: python

    class ProcessingHook(object, metaclass=abc.ABCMeta):

        dependencies = []
        """An ordered list of hooks that must be enabled before this one."""

        def before_processing(self, introspection_data, **kwargs):
            """Hook to run before any other data processing."""

        def before_update(self, introspection_data, node_info, **kwargs):
            """Hook to run before Ironic node update."""

Adapting to the Ironic terminology, new API and internal structures, this
becomes:

.. code-block:: python

    class InspectionHook(metaclass=abc.ABCMeta):

        dependencies = []
        """An ordered list of hooks that must be enabled before this one."""

        def preprocess(self, task, inventory, plugin_data):
            """Hook to run before the main inspection data processing."""

        def __call__(self, task, inventory, plugin_data):
            """Hook to run to process the inspection data."""

Hooks…

* **must** override ``__call__`` and *may* override the other two methods.

* are always run with an exclusive lock with the node in the ``INSPECTING``
  provision state.

* *may* modify the plugin data but *should not* modify the inventory.

* *should avoid* permanently modifying the node or any related resources
  in the ``preprocess`` phase.

* **must** call ``task.node.save()`` explicitly on modifications.

The ordered list of hooks that will run by default (see `hooks
configuration`_):

``ramdisk-error``
  Fails the inspection early if an error message is passed along the
  inspection data.

``architecture``
  Sets the ``cpu_arch`` property based on the inventory.

``validate_interfaces``
  Validates interfaces in the inventory. Valid interfaces are stored in
  ``plugin_data`` in the new key ``valid_interfaces`` with an additional field
  ``pxe_enabled``.

``ports``
  Creates ports based on the ``add_ports``/``keep_ports`` options (see `port
  creation configuration`_). Requires the ``validate_interfaces`` hook. Updates
  the ``valid_interfaces`` collection with a new boolean interface field
  ``is_added``.

The list of available optional hooks (adapted from existing Inspector hooks):

``accelerators``
  Sets the ``accelerators`` property based on the available accelerator devices
  and the configuration.

``boot-mode``
  Sets the ``boot_mode`` capability based on the boot mode during the ramdisk
  run.

``cpu-capabilities``
  Updates capabilities based on CPU flags from the inventory.

``extra-hardware``
  Converts the extra collected data from the format of the hardware-detect_
  tool (list of lists) to a nested dictionary. Removes the original ``data``
  field from the ``plugin_data`` and creates a new field ``extra`` instead.

``local-link-connection``
  Uses LLDP information to set the ``local_link_connection`` field on ports.
  Can be used together with ``parse-lldp``.

``memory``
  Sets the ``memory_mb`` property based on the inventory.

``parse-lldp``
  Converts binary LLDP information into a readable form, which is then stored
  in the ``plugin_data`` as a new ``parsed_lldp`` dictionary with interface
  names as keys.

  https://specs.openstack.org/openstack/ironic-inspector-specs/specs/lldp-reporting.html

``pci-devices``
  Updates the node's capabilities with PCI devices using a mapping from
  the configuration.

  https://specs.openstack.org/openstack/ironic-inspector-specs/specs/generic-pci-resource.html

``physical-network``
  Allows setting the port's ``physical_network`` field based on the CIDR
  mapping in the configuration.

  Can be subclassed to implement a different logic.

``raid-device``
  Uses a diff between two inspection to detect the freshly created RAID device
  and configure it as a root device.

  .. note:: The current implementation caches devices in the node's ``extra``.
            We should rather fetch the old inventory for that.

``root-device``
  Uses root device hints to determine the root device and sets the ``local_gb``
  property.

.. note::
   Nothing will set the ``cpus`` property. It's not used by Nova any more and
   should be removed from essential properties.

Nova driver impact
------------------

Fortunately, none.

Ramdisk impact
--------------

At the first pass, there will be no changes to the ramdisk. The new callback
API will be fully compatible with its counterpart in Inspector.

The follow-up change will be to make lookup and inspection mutually exclusive:
if inspection (at least its synchronous lookup part) succeeds, the token and
node data are returned in the response, and the lookup is not needed.

Security impact
---------------

* This change introduces one more API endpoint without authentication. Knowing
  either UUID, MAC address or BMC address, an intruder can receive some
  information as well as the agent token (if it hasn't been retrieved yet)
  for a node in the ``INSPECT WAIT`` state.

  If in-band inspection is disabled or simply not used, no nodes will ever be
  in the ``INSPECT WAIT`` state since it is not used by out-of-band inspection
  implementations.

Other end user impact
---------------------

None?

Scalability impact
------------------

The scalability impact on a deployment with in-band inspection will probably be
net positive because periodic sync-ups of Inspector with Ironic will no longer
be necessary.

Having PXE filters as a separate process means that they can be scaled
separately from the rest of Ironic (e.g. it may make sense to keep them
in an active/standby setup, while the rest of Ironic is active/active).

Performance Impact
------------------

The expected performance impact is also positive:

* Removal of the periodic task that synchronizes inspection results from
  Inspector to Ironic.

* More efficient database queries on inspection lookup and in PXE filters.

Storing inventory in the database does impact its size, but it is already the
case for Inspector. However, during the transition period, there will be two
copies of inventory. If this becomes a problem, an operator may opt to disable
the inventory storage on the Ironic side until ready to switch over completely.

Other deployer impact
---------------------

Hooks configuration
~~~~~~~~~~~~~~~~~~~

New configuration options in the ``[inspector]`` section:

``default_hooks``
  A comma-separated lists of inspection hooks that are run by default. In most
  cases, the operators will not modify this.

  The default (somewhat conservative) hooks set will create ports and set
  ``cpu_arch``.

``hooks``
  A comma-separated lists of inspection hooks to run. Defaults to
  ``$default_hooks``.

.. note::
   This scheme allows easily inserting hooks in the beginning or the end of
   the list without hardcoding the default list, e.g.:

   .. code-block:: ini

    [inspector]
    hooks = my-early-hook,$default_hooks,later-hook-1,later-hook-2

Port creation configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Various inspection hooks will come with their configuration. The most important
is the port creation options in the ``[inspector]`` section:

``add_ports``
  Which interfaces to enroll as ports for the node. Options:

  * ``all`` (the default) - all valid interfaces.
  * ``active`` - only interfaces with an IP address.
  * ``pxe`` - only the PXE booting interface.

``keep_ports``
  Which existing ports to keep.

  * ``all`` (the default) - keep all ports, do not delete anything.
  * ``present`` - delete all ports that do not correspond to interfaces
    in the inventory.
  * ``added`` - delete all ports except for ones selected via the ``add_ports``
    option (only makes sense if ``add_ports`` is not set to ``all``).

Disk spacing configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~

An odd quirk of our partitioning code is that the ``local_gb`` field has to be
smaller than the actual disk, otherwise the partitioning may fail. Inspector
has been dealing it by making ``local_gb`` 1G smaller. This will be reflected
in the following option:

``disk_partitioning_spacing``
  Size in GiB to leave reserved. Defaults to 1, set to 0 to disable.

Auto-discovery configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The new ``[auto_discovery]`` section will have these options:

``enabled``
  Boolean field, defaults to ``False``.

``driver``
  The driver to use for newly enrolled nodes. Required when the feature is
  enabled.

.. note::
   Inspector has several options to tune the freshly created nodes. I believe
   that this complex logic should rather be implemented with inspection
   rules. The follow-up inspection rules spec will have some additions to make
   it easier.

PXE filter script
~~~~~~~~~~~~~~~~~

A new executable ``ironic-pxe-filter`` will be introduced to support unmanaged
inspection in environments with Neutron. It will be designed to be deployed
alongside a separate *dnsmasq* process. Unlike the current implementation in
Inspector, the script will have direct access to the Ironic database for
efficiency.

Operators that do not need PXE filtering, e.g. because they only use managed
inspection or use a single PXE environment (without Neutron), can opt out of
running ``ironic-pxe-filter``. This applies, for example, to Bifrost and
Metal3.

The only downside of this approach is knowing when inspection starts or
finishes. Inspector learns it immediately and is able to update the filters
without a further delay. The periodic task approach will result in a delay
that is probably acceptable for real hardware but will be problematic for
virtual machines.

To overcome this limitation, the new executable will feature an RPC service
when the RPC transport is *oslo.messaging*. This service will use a separate
*topic* ``ironic.pxe_filter`` and will receive broadcast messages from
the conductor handling inspection. The RPC call will be:

.. code-block:: python

  def update_pxe_filters(self, context, allow=None, deny=None):
      """Update the PXE filter with the given addresses.

      Modifies the allowlist and the denylist with the given addresses.
      The state of addresses that are not mentioned does not change.

      :param allow: MAC addresses to enable in the filters.
      :param deny: MAC addresses to disable in the filters.
      """

No notifications will be done for JSON RPC transport. This will be documented
as a known limitation. The further work as part of the `cross-conductor RPC
effort <https://review.opendev.org/c/openstack/ironic-specs/+/873662>`_ may
eventually lift it.

Developer impact
----------------

While other in-band inspection implementations are possible, they'll probably
happen as downstream modifications to the proposed implementation.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Dmitry Tantsur (IRC: dtantsur, dtantsur@protonmail.com)

Other contributors:
  Jakub Jelínek (IRC: kubajj) - inventory API

Work Items
----------

Too many to mention - see tasks in
https://storyboard.openstack.org/#!/story/2010275.


Dependencies
============

None so far.

Testing
=======

* Bifrost will be migrated to the new implementation as early as possible.

* DevStack CI coverage will be added, possibly in form of tests in standalone
  jobs.

* Eventually, the existing Inspector job will be migrated over or deleted.

Upgrades and Backwards Compatibility
====================================

Other than the eventual deprecation of Inspector itself and the corresponding
*inspect interface*, the change is backward compatible on the Ironic side.

Migration will be reasonably easy, but not necessarily friction-free. Possible
concerns:

* No migration for inspection data. We could provide a tool, I'm just not sure
  if it's worth the effort. Can be done as an afterthought.

* Co-existence of the new and old *inspect interfaces*.

  * The callback API will be designed to work with the old interface by
    proxying the data to Inspector. This way, an operator can use the same
    callback URL for both implementations.

  * The new PXE filters script will also function the same way for both
    implementations.

  * The inventory API will be implemented for the old implementation by
    fetching the data from Inspector on successful inspection.

Documentation Impact
====================

A lot of documentation has to be written, or rather adapted from
ironic-inspector. API reference will be added for all new API endpoints.

References
==========

.. [#metal3-and-etcd] Technically, any Kubernetes deployment includes etcd, but
   it is against best practices for non-Kubernetes applications to rely on it.

.. _ironic-inspector: https://opendev.org/openstack/ironic-inspector
.. _ironic-python-agent: https://opendev.org/openstack/ironic-python-agent
.. _Metal3: https://metal3.io/
.. _inventory: https://docs.openstack.org/ironic-python-agent/latest/admin/how_it_works.html#hardware-inventory
.. _hardware-detect: https://github.com/redhat-cip/hardware
.. _osc-lib: https://docs.openstack.org/osc-lib/latest/reference/api/osc_lib.utils.html
