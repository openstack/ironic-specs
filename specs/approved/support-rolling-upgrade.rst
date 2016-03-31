..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=======================
Support Rolling Upgrade
=======================

https://bugs.launchpad.net/ironic/+bug/1526283

This proposes support for "rolling upgrades" of ironic, which will allow
operators to roll out new code to the ironic services without having to
restart all services on the new code simultaneously. There could be minimal
downtime when upgrading ironic services. During the upgrade of ironic,
instances will not be impacted; they should continue to run and have network
access. There might be slightly longer delays for ironic operations to be
performed on baremetal nodes though.

This support for rolling upgrade will satisfy the criteria mentioned in the
OpenStack governance [1]_.

Problem description
===================

People operating an OpenStack cloud face the same problem: how to upgrade the
cloud to the latest version so as to enjoy the new features and changes.

The upgrade of a cloud is typically done one component at a time. For example,
these components of OpenStack could be upgraded in this order:

#. upgrade keystone
#. upgrade glance
#. upgrade ironic
#. upgrade nova
#. upgrade neutron
#. upgrade cinder

Ironic already supports "cold upgrades" [14]_, where the ironic services have
to be down during the upgrade. For time-consuming upgrades, it may be
unacceptable for the services to be unavailable for a long period of time.
The steps [13]_ to do a cold upgrade could be:

#. stop all ironic-api and ironic-conductor services
#. uninstall old code
#. install new code
#. update configurations
#. DB sync (most time-consuming task)
#. start ironic-api and ironic-conductor services

A rolling upgrade would provide a better experience for the users and operators
of the cloud. In the context of ironic's rolling upgrade, it means it wouldn't
be necessary to upgrade all the ironic-api and ironic-conductor
services simultaneously as in a cold upgrade. A rolling upgrade would allow
individual ironic-api and ironic-conductor services to be upgraded one at a
time, with the rest of the services still available. This upgrade would have
minimal downtime.

The rolling upgrade solution presented here is modelled after nova's
upgrade process [2]_, with some differences. In addition, there have been
several discussions about rolling upgrades ([3]_, [9]_, [10]_).


Proposed change
===============

For a rolling upgrade to have minimal downtime, there should be at least
two ironic-api services and two ironic-conductor services running.

Since ironic doesn't support database downgrades, rollbacks will not be
supported.

To support rolling upgrade for ironic, the following are needed:

* code changes
* a contribution guide for developers and reviewers
* a multi-node grenade CI to prevent breaking the mechanism of rolling upgrade
* a rolling upgrade operation guide for operators.

The following sub-sections describe:

* support for rolling upgrades between ironic releases
* the proposed rolling upgrade process
* the changes that are needed

Rolling upgrades between releases
---------------------------------
Ironic follows the release-cycle-with-intermediary release model [6]_.
The releases are semantic-versioned [7]_, in the form <major>.<minor>.<patch>.
We refer to a "named release" of ironic as the release associated with a
development cycle like Mitaka.

In addition, ironic follows the standard deprecation policy [8]_, which says
that the deprecation period must be at least three months and a cycle
boundary. This means that there will never be anything that is both
deprecated *and* removed between two named releases.

Rolling upgrades will be supported between:

* Named release N to N+1.
  (N would start with Newton if this feature is merged in Ocata.)
* Any named release to its latest revision, containing backported bug fixes.
  Because those bug fixes can contain improvements to the upgrade process, the
  operator should patch the system before upgrading between named releases.
* Most recent named release N (and semver releases newer than N) to master.
  As with the above bullet point, there may be a bug or a feature introduced
  on a master branch, that we want to remove before publishing a named release.
  Deprecation policy allows to do this in a 3 month time frame [8]_.
  If the feature was included and removed in intermediate releases, there
  should be a release note added, with instructions on how to do a rolling
  upgrade to master from an affected release or release span. This would
  typically instruct the operator to upgrade to a particular intermediate
  release, before upgrading to master.

Rolling upgrade process
-----------------------

The rolling upgrade process to upgrade ironic from version ``FromVer`` to the
next version ``ToVer`` is as follows:

#. Upgrade Ironic Python Agent image before upgrading ironic.

#. Upgrade DB schema to ``ToVer`` via :command:`ironic-dbsync upgrade`.
   Ironic already has the code in place to do this. However, a new DB
   migration policy (described below in `New DB model change policy`_) needs
   to be documented.

#. Pin RPC and IronicObject versions to the same ``FromVer`` for both
   ironic-api and ironic-conductor services, via the new configuration option
   described below in `RPC and object version pinning`_.

#. Upgrade code and restart ironic-conductor services, one at a time.

#. Upgrade code and restart ironic-api services, one at a time.

#. Unpin RPC and object versions so that the services can now use the latest
   versions in ``ToVer``. This is done via updating the new configuration
   option described below in `RPC and object version pinning`_ and then
   restarting the services. ironic-conductor services should be restarted
   first, followed by the ironic-api services. This is to ensure that when new
   functionality is exposed on the unpinned API service (via API micro
   version), it is available on the backend.

#. Run a new command :command:`ironic-dbsync online_data_migration` to ensure
   that all DB records are "upgraded" to the new data version.
   This new command is discussed in a separate RFE [12]_ (and is a dependency
   for this work).

#. Upgrade ironic client libraries (e.g. python-ironicclient) and other
   services which use the newly introduced API features and depend on the
   new version.

Changes needed to support rolling upgrade
-----------------------------------------

For the above to work, there are several changes that have to be done.
A framework patch [4]_ and an implementation reference patch [5]_ exist to
verify the concept.

New DB model change policy
``````````````````````````

This is not a code change but it impacts the SQLAlchemy DB model and needs to
be documented well for developers as well as reviewers.
This new DB model change policy is as follows:

* Adding new items to the DB model is supported.

* The dropping of columns/tables and corresponding objects fields is subject
  to ironic deprecation policy [8]_.
  But its alembic script has to wait one more deprecation period, otherwise
  an "unknown column" exception will be thrown when ``FromVer`` services
  access the DB. This is because :command:`ironic-dbsync upgrade` upgrades the
  DB schema but ``FromVer`` services still contain the dropped field in their
  SQLAlchemy DB model.

* alter_column like rename or resize is not supported anymore. This has to
  be split into multiple operations, like add column, then remove column.
  Some changes may have to be split into multiple releases to maintain
  compatibility with an old SQLAlchemy model.

* some implementations of ALTER TABLE like adding foreign keys in PostgreSQL
  may impose table locks and cause downtime. If the change cannot be avoided
  and the impact is significant (the table can be frequently accessed and/or
  store a large dataset), these cases must be mentioned in the release notes.

RPC and object version pinning
``````````````````````````````

A new configuration option will be added. It will be used to pin the RPC and
IronicObject (e.g., Node, Conductor, Chassis, Port, and Portgroup) versions for
all the ironic services. With this configuration option, a service will be able
to properly handle the communication between different versions of services.

The new configuration option is: ``[DEFAULT]/pin_release_version``.
The default value of empty indicates that ironic-api and ironic-conductor
will use the latest versions of RPC and IronicObjects. Its possible values are
releases, named (e.g. ``newton``) or sem-versioned (e.g. ``5.2``).

Internally, ironic will maintain a mapping that indicates the RPC and
IronicObject versions associated with each release. This mapping will be
maintained manually. (It is possible, but outside the scope of this
specification, to add an automated process for the mapping.) Here is an
example:

* objects_mapping::

              {'mitaka': {'Node': '1.14', 'Conductor': '1.1',
                          'Chassis': '1.3', 'Port': '1.5', 'Portgroup': '1.0'},
               '5.23': {'Node': '1.15', 'Conductor': '1.1',
                        'Chassis': '1.3', 'Port': '1.5', 'Portgroup': '1.0'}}

* rpc_mapping::

              {'mitaka': '1.33', '5.23': '1.33'}

Set version_cap to pinned version
:::::::::::::::::::::::::::::::::
``ConductorAPI.__init__()`` already sets a ``version_cap`` to the latest
RPC API version and passes it to the ``RPCClient`` as an initialization
parameter.  This ``version_cap`` is used to determine the maximum requested
message version that the ``RPCClient`` can send.

In order to make a compatible RPC call for a previous release, the code will
be changed so that the ``version_cap`` is set to a pinned version
(corresponding to the desired release) rather than the latest
``RPC_API_VERSION``. Then each RPC call will customize the request according
to this ``version_cap``.

Make use of target_version
::::::::::::::::::::::::::
Object instances will make use of a new value ``target_version`` when
the service interacts with another service.
If pinned version was given, the value of ``target_version`` will be set
to a corresponding value in ``objects_mapping``. Otherwise, the value is None.

Object instances are instantiated according to ``VERSION``, so ``FromVer``
and ``ToVer`` services are still running their own version object instances.
However at first, the database only contains old records in ``FromVer``.
When services interact, the serialized object instances can be converted to
``target_version`` by ``ToVer`` services. To assist in this, several methods
will be added or changed for ``ironic.objects.base.IronicObject``.

Putting it together
:::::::::::::::::::

In the following descriptions:

* ``FromVer`` uses version '1.14' of a Node object.
* ``ToVer`` uses version '1.15' of a Node object -- this has a deprecated
  ``extra`` field and a new ``fake`` field that replaces ``extra``.
* db_obj['fake'] and db_obj['extra'] are the database representations of those
  node fields.
* ``ToVer`` is pinned to ``FromVer``.

Instantiate services' version objects
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``IronicObject._from_db_object(obj, db_object)`` is a method that already
exists; it converts a database entity to a formal object.

Each IronicObject class will need to be changed, to implement its own
_from_db_object() to instantiate its own version objects (regardless of
any pinning) from the database. In this case:

* ``FromVer`` will instantiate version '1.14' of Node object,
  ignoring db_obj['fake'] but setting node.extra = db_obj['extra'].
* ``ToVer`` will instantiate version '1.15' of the Node object, setting
  node.fake = db_obj['extra'] and setting node.extra = None. (With
  pinning, db_obj['fake'] is still empty, but node.fake on the object should be
  available for the new code release to use.)

Get target version
~~~~~~~~~~~~~~~~~~
A new method ``IronicObjectSerializer._get_target_version(self, obj)`` will be
added. This will return a string, the IronicObject version corresponding to the
pinned release version. If there is no pinning, it will return the latest
version for that IronicObject.

In this case, ``ToVer`` is pinned to ``FromVer``, so
serializer._get_target_version(Node) would return version '1.14'.

Convert passed instance values to the target version
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Based on the target version, an IronicObject instance will be serialized
to correspond to the target version. This will be done before sending the
object over-the-wire to other services with IronicObjectSerializer.

In this case, since ``ToVer`` is pinned to ``FromVer``, a ``ToVer`` Node
object instance 'node' will be serialized to look like version '1.14',
with node.extra = node.fake, and no node.fake attribute.

Save pinned-version values to DB (API/Conductor --> DB)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
During the rolling upgrade, some services will be running ``ToVer`` and pinned
to ``FromVer``, while the others are still running ``FromVer``.
Since these services access the same database and to avoid saving
into different columns, ironic won't save values in new columns until after
the unpinning.

A new method ``IronicObject._obj_get_db_compatible_changes(self)``
will return a dictionary of DB-compatible changed fields and values.
These will be compatible with the pinned version.

Wherever an IronicObject writes to the database (typically in .create() and
.save()), it will call ._obj_get_db_compatible_changes() instead of
.obj_get_changes(), to get changes that are compatible with the database
(i.e., the database that corresponds to the pinned version).

Use actual versions when reading values from DB (API/Conductor <-- DB)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The unpinning operation is not atomic. There can also be a situation, where
all services are running in ``ToVer``, but some of the conductors are
unpinned. On the other extreme, all conductors can be unpinned and some of
api services may still be pinned. Because of this, a service may retrieve from
DB or receive via RPC a ``ToVer`` object instance, while it is still pinned to
``FromVer``.

For example, in case of retrieving an object from the DB, it could happen that
one conductor is pinned, the other is not. When data is

1. saved by the unpinned conductor
2. retrieved and saved by the pinned conductor

and if the pinned conductor assumes the data is in a previous (pinned) version,
the resulting state is, that the data is inconsistent.

It may happen because there was a new column introduced (the ``fake`` column
from the above example), so:

1. the unpinned conductor saves data into a new column (the ``fake`` column),
2. the pinned conductor reads and updates data in an old column (``extra``).

The end result is that we don't know in which column we have the up-to date
values. At the same time, if an outdated value was used to calculate a new one,
data is lost.

To maintain data consistency, when a ``ToVer`` object is retrieved from the DB
by a ``ToVer`` service, which is still pinned to ``FromVer``, it should ignore
the globally configured pin for this instance of the object and use its actual
version. The same follows for receiving a ``ToVer`` object through RPC.

In short, use target version: api/conductor --> db (when creating/saving a new
object) and use actual (unpinned) version: api/conductor <-- db.

When we receive an unpinned object, we should save it in its actual version,
so that we don't lose data which may have been added to it in ``ToVer``.

To make sure reading the DB object versions happens transparently for the
developer, a version column will be introduced to SQLAlchemy models.

This version column will be null at first and will be filled with the
appropriate versions by a data migration script. If there is a change in
Ocata that requires migration of data, we will check for null in the new
version column.

No project uses the version column mechanism for this purpose, but it is more
complicated without it. For example, Cinder has a migration policy which spans
4 releases in which data is duplicated for some time. Keystone uses triggers to
maintain duplicated data in one release cycle. In addition, the version column
may prove useful for zero-downtime upgrades (in the future).

Passing target version object instances via RPC (API <---> Conductor)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
When ironic-api makes an RPC call to update an object instance (in
ironic.conductor.rpcapi.ConductorAPI: e.g., create_node(), update_node(),
update_port() and update_portgroup()), the object instance `with updates` is
passed as a parameter to the method. After updating the database, an updated
object instance is returned.

It could happen that a ``FromVer`` API gets a '1.15' Node object from
a ``ToVer`` (unpinned) Conductor. In this case, IronicObjectSerializer will
convert the object based on the target version (``FromVer``), so that the API
is dealing with the correctly versioned node object.
The object_backport_versions RPC method is called to convert the object.
The sequence of events is the following:

#. API (FromVer) -> RPC -> conductor (unpinned ToVer)
#. conductor -> (1.15 obj) -> RPC -> API
#. API raises eyebrow, err exception -> RPC -> conductor
#. conductor -> (1.14 obj) -> RPC -> API

Likewise, a ``FromVer`` API could send an older version object to a
``ToVer`` conductor. So the conductor has to accept and handle older,
compatible objects.
destroy_port() and destroy_portgroup() RPC calls are also affected by this.

Alternatives
------------

A cold upgrade can be done, but it means the ironic services will not be
available during the upgrade, which may be time consuming.

Data model impact
-----------------

A DB migration policy is adopted and introduced above in
`New DB model change policy`_.

State Machine Impact
--------------------

None

REST API impact
---------------

There is no change to the REST API itself.

During the rolling upgrade process, the API services may run in different
versions at the same time. Both API service versions should be compatible with
the python-ironicclient library from the older release (we already use
microversions to guarantee this). New API functionality is available
everywhere only after completing the upgrade process, which includes unpinning
of the internal RPC communication versions on all ironic services. Therefore,
until the upgrade is completed, API requests should not be issued for new
functionality (i.e., with new API micro versions) since there is no guarantee
that they will work properly.

As a future enhancement (outside the scope of this specification), we could
disallow requests for new functionality while the API service is pinned.

Client (CLI) impact
-------------------
None

RPC API impact
--------------

There is no change to the RPC API itself, although changes are needed for
supporting different RPC API versions. ``version_cap`` will be set to the
pinned version (the previous release) to make compatible RPC calls of the
previous release.

Developers should keep this in mind when changing an existing RPC API call.

Driver API impact
-----------------

None

Nova driver impact
------------------

Since there is no change to the REST API, there
is no need to change the nova driver. Ironic should be upgraded before
nova, and nova calls ironic using a specific micro version that will still be
supported in the upgraded ironic. Thus everything will work fine without
any changes to the nova driver.

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

None

Performance Impact
------------------

Operations which involve migration of data may take longer during the upgrade.
Each such change should be mentioned in the release notes provided with the
impacted release.

Other deployer impact
---------------------
During the rolling upgrade, the deployer will use the new configuration option
``[DEFAULT]/pin_release_version`` to pin and unpin the RPC and IronicObject
versions used by the services, as described above in `RPC and object version
pinning`_.

This specification doesn't address trying to stop/roll back to a previous
release.

Developer impact
----------------

The code contribution guide [11]_ will be updated to describe what a developer
needs to know and follow. It will mention:

* before a release is cut, manually add the mapping of release (named or
  sem-versioned) with the associated RPC and Object versions
* the new DB model change policy
* the contribution guide will point to design documentation, as it relates to
  how new features should be implemented in accordance with rolling upgrades

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  xek

Other contributors:

  mario-villaplana-j (documentation)

Work Items
----------

#. Add new configuration option ``[DEFAULT]/pin_release_version``
   and RPC/Object version mappings to releases.
#. Make Objects compatible with a previous version and handle the interaction
   with DB and user.
#. Make IronicObjectSerializer downgrade objects when passing via RPC.
#. Add tests.
#. Add documentation and pointers for RPC and oslo objects versioning.
#. Add documentation for the new DB model change policy.
#. Add admin documentation for operators, describing how to do a rolling
   upgrade, including the order in which all related services should be
   upgraded.

Dependencies
============

* Needs the new command :command:`ironic-dbsync online_data_migration` [12]_.

* Needs multi-node grenade CI working.

Testing
=======

* unit tests

* multi-node grenade CI. This tests that the rolling upgrade process
  continues to work from ``fromVer`` to ``toVer``.

  * grenade does a full upgrade, without pinning. This tests old API/conductor
    and new API/conductor unpinned. We won't run online data migrations, so
    the new services will be reading the old format of the data.
  * grenade multi-node will be running old API/conductor on the subnode,
    which won't be upgraded. The primary will have conductor only, which does
    get upgraded, but is pinned. This tests old API + old data, with 1. old
    conductor, and 2. new conductor with a pin. Tests are run pre/post-upgrade.
  * We could also move the API to the primary node, upgrade it, pinned, to test
    new API code with the pin. Since all the object translation happens at the
    objects layer, this may not be needed since it may not test much that
    hasn't already been exercised in the conductor.
  * The above two tests could be merged, if grenade can be set-up to stop the
    old API service on the subnode and start it on the upgraded primary after
    doing the first test.

Tests should cover the use cases described in
`Rolling upgrades between releases`_ as much as possible.

Upgrades and Backwards Compatibility
====================================

None; there is no change to the REST API or Driver API.

Documentation Impact
====================

Documentation will be added for:

* deployers. This will describe the rolling upgrade process and the steps
  they will need to take. This should be documented or linked from the upgrade
  guide [13]_.
* developers. This will describe what a developer needs to know so that
  the rolling upgrade process continues to work. This includes documentation
  on RPC and oslo objects versioning, as well as DB model change policy.

References
==========

.. [1] https://github.com/openstack/governance/blob/master/reference/tags/assert_supports-rolling-upgrade.rst
.. [2] http://docs.openstack.org/developer/nova/upgrade.html
.. [3] https://etherpad.openstack.org/p/ironic-mitaka-midcycle
.. [4] Ironic rolling upgrade framework https://review.openstack.org/#/c/306357/
.. [5] Refactor configdrive into a new field https://review.openstack.org/#/c/306358/
.. [6] https://releases.openstack.org/reference/release_models.html
.. [7] http://semver.org/
.. [8] http://governance.openstack.org/reference/tags/assert_follows-standard-deprecation.html
.. [9] http://lists.openstack.org/pipermail/openstack-dev/2016-April/092773.html
.. [10] https://etherpad.openstack.org/p/ironic-newton-summit-live-upgrades
.. [11] http://docs.openstack.org/developer/ironic/dev/code-contribution-guide.html#live-upgrade-related-concerns
.. [12] http://bugs.launchpad.net/ironic/+bug/1585141
.. [13] http://docs.openstack.org/developer/ironic/deploy/upgrade-guide.html
.. [14] https://github.com/openstack/governance/blob/master/reference/tags/assert_supports-upgrade.rst
