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

Although we'd like the rolling upgrade solution presented here to be the same
as that used by nova's upgrade process [2]_, there are some differences between
nova and ironic that prevent us from using the same solution. The differences
are mentioned below, in other sections of this specification.

There have been several discussions about rolling upgrades ([3]_, [9]_, [10]_).


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

1. Upgrade Ironic Python Agent image before upgrading ironic.

2. Upgrade DB schema to ``ToVer`` via **ironic-dbsync upgrade**.
   Ironic already has the code in place to do this. However, a new DB
   migration policy (described below in `New DB model change policy`_) needs
   to be documented.

3. Pin RPC and IronicObject versions to the same ``FromVer`` for both
   ironic-api and ironic-conductor services, via the new configuration option
   described below in `RPC and object version pinning`_.

4. Upgrade code and restart ironic-conductor services, one at a time.

5. Upgrade code and restart ironic-api services, one at a time.

6. Unpin RPC and object versions so that the services can now use the latest
   versions in ``ToVer``. This is done via updating the new configuration
   option described below in `RPC and object version pinning`_ and then
   restarting the services. ironic-conductor services should be restarted
   first, followed by the ironic-api services. This is to ensure that when new
   functionality is exposed on the unpinned API service (via API micro
   version), it is available on the backend.

7. Run a new command **ironic-dbsync online_data_migration** to ensure
   that all DB records are "upgraded" to the new data version.
   This new command is discussed in a separate RFE [12]_ (and is a dependency
   for this work).

8. Upgrade ironic client libraries (e.g. python-ironicclient) and other
   services which use the newly introduced API features and depend on the
   new version.

The above process will cause the ironic services to be running the ``FromVer``
and ``ToVer`` releases in this order (where 'step' refers to the steps above):

+------+---------------------------------+---------------------------------+
| step | ironic-api                      | ironic-conductor                |
+======+=================================+=================================+
|  0   | all FromVer                     | all FromVer                     |
+------+---------------------------------+---------------------------------+
|  4.1 | all FromVer                     | some FromVer, some ToVer-pinned |
+------+---------------------------------+---------------------------------+
|  4.2 | all FromVer                     | all ToVer-pinned                |
+------+---------------------------------+---------------------------------+
|  5.1 | some FromVer, some ToVer-pinned | all ToVer-pinned                |
+------+---------------------------------+---------------------------------+
|  5.2 | all ToVer-pinned                | all ToVer-pinned                |
+------+---------------------------------+---------------------------------+
|  6.1 | all ToVer-pinned                | some ToVer-pinned, some ToVer   |
+------+---------------------------------+---------------------------------+
|  6.2 | all ToVer-pinned                | all ToVer                       |
+------+---------------------------------+---------------------------------+
|  6.3 | some ToVer-pinned, some ToVer   | all ToVer                       |
+------+---------------------------------+---------------------------------+
|  6.4 | all ToVer                       | all ToVer                       |
+------+---------------------------------+---------------------------------+


New DB model change policy
--------------------------

This is not a code change but it impacts the SQLAlchemy DB model and needs to
be documented well for developers as well as reviewers.
This new DB model change policy is as follows:

* Adding new items to the DB model is supported.

* The dropping of columns/tables and corresponding objects fields is subject
  to ironic deprecation policy [8]_.
  But its alembic script has to wait one more deprecation period, otherwise
  an "unknown column" exception will be thrown when ``FromVer`` services
  access the DB. This is because **ironic-dbsync upgrade** upgrades the
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
------------------------------

For the ironic (ironic-api and ironic-conductor) services to be running
old and new releases at the same time during a rolling upgrade, the services
need to be able to handle different RPC versions and object versions.

[4]_ has a good description of why we need RPC versioning, and describes how
nova deals with it. This proposes taking a similar approach in ironic.

For object versioning, ironic uses oslo.versionedobjects. [5]_ describes nova's
approach to the problem. Unfortunately, ironic's solution is different, since
ironic has a more complex situation. In nova, all database access (reads and
writes) is done via the nova-conductor service. This makes it possible for the
nova-conductor service to be the only service to handle conversions between
different object versions. (See [5]_ for more details.) Given an object that
it doesn't understand, a (non nova-conductor) service will issue an RPC request
to the nova-conductor service to get the object converted to its desired target
version. Furthermore, for a nova rolling upgrade, all the non-nova-compute
services are shut down, and then restarted with the new releases;
nova-conductor being the first service to be restarted ([2]_). Thus, the
nova-conductor services are always running the same release and don't have to
deal with differing object versions amongst themselves. Once they are running
the new release, they can handle requests from other services running old or
new releases.

Contrast that to ironic, where both the ironic-api and ironic-conductor
services access the database for reading and writing. Both these services need
to be aware of different object versions. For example, ironic-api can
create objects such as Chassis, Ports, and Portgroups, saving them directly to
the database without going through the conductor. We cannot take down the
ironic-conductor in a similar way as the nova-conductor service, because
ironic-conductor does a whole lot more than just interacting with the database,
and at least one ironic-conductor needs to be running during a rolling upgrade.

A new configuration option will be added. It will be used to pin the RPC and
IronicObject (e.g., Node, Conductor, Chassis, Port, and Portgroup) versions for
all the ironic services. With this configuration option, a service will be able
to properly handle the communication between different versions of services.

The new configuration option is: ``[DEFAULT]/pin_release_version``.
The default value of empty indicates that ironic-api and ironic-conductor
will use the latest versions of RPC and IronicObjects. Its possible values are
releases, named (e.g. ``ocata``) or sem-versioned (e.g. ``7.0``).

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

During a rolling upgrade, the services using the new release should set this
value to be the name (or version) of the old release. This will indicate
to the services running the new release, which RPC and object versions that
they should be compatible with, in order to communicate with the services
using the old release.


Handling RPC versions
~~~~~~~~~~~~~~~~~~~~~

``ConductorAPI.__init__()`` already sets a ``version_cap`` variable to the
latest RPC API version and passes it to the ``RPCClient`` as an initialization
parameter.  This ``version_cap`` is used to determine the maximum requested
message version that the ``RPCClient`` can send.

In order to make a compatible RPC call for a previous release, the code will
be changed so that the ``version_cap`` is set to a pinned version
(corresponding to the previous release) rather than the latest
``RPC_API_VERSION``. Then each RPC call will customize the request according
to this ``version_cap``.


Handling IronicObject versions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Internally, ironic services (ironic-api and ironic-conductor) will deal with
IronicObjects in their latest versions. Only at these boundaries, when the
IronicObject enters or leaves the service, will we need to deal with object
versioning:

* *getting objects from the database*: convert to latest version
* *saving objects to the database*: if pinned, save in pinned version; else
  save in latest version
* *serializing objects (to send over RPC)*: if pinned, send pinned version;
  else send latest version
* *deserializing objects (receiving objects from RPC)*: convert to latest
  version

The ironic-api service also has to handle API requests/responses
based on whether or how a feature is supported by the API version and object
versions. For example, when the ironic-api service is pinned, it can only
allow actions that are available to the object's pinned version, and cannot
allow actions that are only available for the latest version of that object.

To support this:

* add a new column named ``version`` to all the database tables (SQLAlchemy
  models) of the IronicObjects. The value is the version of the object that
  is saved in the database.

  This version column will be null at first and will be filled with the
  appropriate versions by a data migration script. If there is a change in
  Ocata that requires migration of data, we will check for null in the new
  version column.

  No project uses the version column mechanism for this purpose, but it is more
  complicated without it. For example, Cinder has a migration policy which
  spans 4 releases in which data is duplicated for some time. Keystone uses
  triggers to maintain duplicated data in one release cycle. In addition, the
  version column may prove useful for zero-downtime upgrades (in the future).

* add a new method ``IronicObject.get_target_version(self)``. This will return
  the target version. If pinned, the pinned version is returned. Otherwise,
  the latest version is returned.

* add a new method ``IronicObject.convert_to_version(self, target_version)``.
  This method will convert the object into the target version. The target
  version may be a newer or older version that the existing version of the
  object. The bulk of the work will be done in the new helper method
  ``IronicObject._convert_to_version(self, target_version)``. Subclasses that
  have new versions should redefine this to perform the actual conversions.

* add a new method ``IronicObject.do_version_changes_for_db(self)``. This is
  described below in `Saving objects to the database (API/conductor --> DB)`_.

* add a new method ``IronicObjectSerializer._process_object(self, context,
  objprim)``. This is described below in
  `Receiving objects via RPC (API/conductor <- RPC)`_.

In the following,

* The old release is ``FromVer``; it uses version '1.14' of a Node object.
* The new release is ``ToVer``; it uses version '1.15' of a Node object --
  this has a deprecated ``extra`` field and a new ``meta`` field that replaces
  ``extra``.
* db_obj['meta'] and db_obj['extra'] are the database representations of those
  node fields.


Getting objects from the database (API/conductor <-- DB)
::::::::::::::::::::::::::::::::::::::::::::::::::::::::

Both ironic-api and ironic-conductor services read values from the database.
These values are converted to IronicObjects via the existing method
``IronicObject._from_db_object(context, obj, db_object)``. This method will be
changed so that the IronicObject will be in the latest version, even if it was
in an older version in the database. This is done regardless of the service
being pinned or not.

Note that if an object is converted to a later version, that IronicObject will
retain any changes resulting from that conversion (in case the object later
gets saved in the latest version).

For example, if the node in the database is in version 1.14 and has
db_obj['extra'] set:

* a ``FromVer`` service will get a Node with node.extra = db_obj['extra']
  (and no knowledge of node.meta since it doesn't exist).

* a ``ToVer`` service (pinned or unpinned), will get a Node with:

  * node.meta = db_obj['extra']
  * node.extra = None
  * node._changed_fields = ['meta', 'extra']


Saving objects to the database (API/conductor --> DB)
:::::::::::::::::::::::::::::::::::::::::::::::::::::

The version used for saving IronicObjects to the database is determined as
follows:

* for an unpinned service, the object will be saved in its latest version.
  Since objects are always in their latest version, no conversions are needed.
* for a pinned service, the object will be saved in its pinned version. Since
  objects are always in their latest version, the object will need to be
  converted to the pinned version before being saved.

The new method ``IronicObject.do_version_changes_for_db()`` will handle this
logic, returning a dictionary of changed fields and their new values (similar
to the existing
``oslo.versionedobjects.VersionedObjectobj.obj_get_changes()``).
Since we do not keep track internally, of the database version of an object,
the object's ``version`` field will always be part of these changes.

The `Rolling upgrade process`_  (at step 6.1) ensures that by the time an
object can be saved in its latest version, all services are running the newer
release (although some may still be pinned) and can handle the latest object
versions.

An interesting situation can occur when the services are as described in step
6.1. It is possible for an IronicObject to be saved in a newer version and
subsequently get saved in an older version. For example, a ``ToVer`` unpinned
conductor might save a node in version 1.5. A subsequent request may cause a
``ToVer`` pinned conductor to replace and save the same node in version 1.4!


Sending objects via RPC (API/conductor -> RPC)
::::::::::::::::::::::::::::::::::::::::::::::

When a service makes an RPC request, any IronicObjects that are sent as
part of that request are serialized into entities or primitives (via
``oslo.versionedobjects.VersionedObjectSerializer.serialize_entity()``). The
version used for objects being serialized is as follows:

* for an unpinned service, the object will be serialized in its latest version.
  Since objects are always in their latest version, no conversions are needed.
* for a pinned service, the object will be serialized in its pinned version.
  Since objects are always in their latest version, the object will need to be
  converted to the pinned version before being serialized. The converted object
  will include changes that resulted from the conversion; this is needed so
  that the service at the other end of the RPC request has the necessary
  information if that object will be saved to the database.

The ``IronicObjectSerializer.serialize_entity()`` method will be modified to do
any IronicObject conversions.


Receiving objects via RPC (API/conductor <- RPC)
::::::::::::::::::::::::::::::::::::::::::::::::

When a service receives an RPC request, any entities that are part of the
request need to be deserialized (via
``oslo.versionedobjects.VersionedObjectSerializer.deserialize_entity()``).
For entities that represent IronicObjects, we want the deserialization process
to result in IronicObjects that are in their latest version, regardless of the
version they were sent in and regardless of whether the receiving service is
pinned or not. Again, any objects that are converted will retain the changes
that resulted from the conversion, useful if that object is later saved to the
database.

The deserialization method invokes
``VersionedObjectSerializer._process_object()`` to deserialize and get the
IronicObject. We will add ``IronicObjectSerializer._process_object()`` to
convert the IronicObject to its latest version.

For example, a ``FromVer`` ironic-api could issue an update_node() RPC request
with a node in version 1.4, where node.extra was changed (so
node._changed_fields = ['extra']). This node will be serialized in version 1.4.
The receiving ``ToVer`` pinned ironic-conductor deserializes it and converts
it to version 1.5. The resulting node will have node.meta set (to the changed
value from node.extra in v1.4), node.extra = None, and node._changed_fields =
['meta', 'extra'].

Alternatives
------------

A cold upgrade can be done, but it means the ironic services will not be
available during the upgrade, which may be time consuming.

Instead of having the services always treat objects in their latest versions,
a different design could be used, for example, where pinned services treat
their objects in their pinned versions. However, after some experimentation,
this proved to have more (corner) cases to consider and was more difficult
to understand. This approach would make it harder to maintain and trouble-shoot
in the future, assuming reviewers would be able to agree that it worked in the
first place!

What if we changed the ironic-api service, so that it had read-only access to
the DB and all writes would go via the ironic-conductor service. Would that
simplify the changes needed to support rolling upgrades? Perhaps; perhaps not.
(Although this author thinks it would be better, regardless, to have
all writes being done by the conductor.) With or without this change, we need
to ensure that objects are not saved in a newer version (i.e., that is newer
than the version in the older release) until all services are running with the
new release -- step 5.2 of the `Rolling upgrade process`_. The solution
described in this document has objects being saved in their newest versions
starting in step 6.1, because it seemed conceptually easy to understand if
we save objects in their latest versions only when a service is unpinned. We'd
need a similar mechanism regardless.

Of course, there are probably other ways to handle this, like having all
services "register" what versions they are running in the database and
leveraging that data somehow. Dmitry Tantsur mused about whether some remote
synchronization stuff (e.g. etcd) could be used for services to be aware of
the upgrade process.

Ideally, ironic would use some "OpenStack-preferred" way to implement
rolling upgrades but that doesn't seem to exist, so this tries to leverage the
work that nova did.

Data model impact
-----------------

A DB migration policy is adopted and introduced above in
`New DB model change policy`_.

A new ``version`` column will be added to all the database tables of the
IronicObject objects. Its value will be the version of the object that is
saved in the database.

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

"ironic" CLI
~~~~~~~~~~~~
None

"openstack baremetal" CLI
~~~~~~~~~~~~~~~~~~~~~~~~~
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

* xek
* rloo

Other contributors:

* mario-villaplana-j (documentation)

Work Items
----------

#. Add new configuration option ``[DEFAULT]/pin_release_version``
   and RPC/Object version mappings to releases.
#. Make Objects compatible with a previous version and handle the interaction
   with DB and services.
#. Make IronicObjectSerializer downgrade objects when passing via RPC.
#. Add tests.
#. Add documentation and pointers for RPC and oslo objects versioning.
#. Add documentation for the new DB model change policy.
#. Add admin documentation for operators, describing how to do a rolling
   upgrade, including the order in which all related services should be
   upgraded.

Dependencies
============

* Needs the new command **ironic-dbsync online_data_migration** [12]_.

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
.. [4] http://superuser.openstack.org/articles/upgrades-in-openstack-nova-remote-procedure-call-apis
.. [5] http://superuser.openstack.org/articles/upgrades-in-openstack-nova-objects/
.. [6] https://releases.openstack.org/reference/release_models.html
.. [7] http://semver.org/
.. [8] http://governance.openstack.org/reference/tags/assert_follows-standard-deprecation.html
.. [9] http://lists.openstack.org/pipermail/openstack-dev/2016-April/092773.html
.. [10] https://etherpad.openstack.org/p/ironic-newton-summit-live-upgrades
.. [11] http://docs.openstack.org/developer/ironic/dev/code-contribution-guide.html#live-upgrade-related-concerns
.. [12] http://bugs.launchpad.net/ironic/+bug/1585141
.. [13] http://docs.openstack.org/developer/ironic/deploy/upgrade-guide.html
.. [14] https://github.com/openstack/governance/blob/master/reference/tags/assert_supports-upgrade.rst
