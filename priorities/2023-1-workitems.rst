.. _2023-1-work-items:

=========================
2023.1 Project Work Items
=========================

Most Ironic contributors have a large number of responsibilities, including
but not limited to, keeping CI working across all branches and projects,
backporting bugfixes, and any downstream job responsibilities that do not
include Ironic contribution.

Because of how much this work can vary over a six month release cycle, we've
chosen to no longer specify timelines for specific work items. Instead, we
will document work items we would like to see completed, and then allow the
community to pick up and work on them as time permits.

We strongly encourage all corporate and individual contributors to dedicate
resources to help maintain the commons; including CI and stable branches. The
more contributors we have helping keep the commons healthy, the more time we
have to work on new items.

This document represents our outlook for 2023.1, and will not be updated once
published. For information or current status of items in progress, please see
the Ironic Whiteboard at https://etherpad.openstack.org/p/IronicWhiteBoard.
For information about items completed, please see the Ironic release notes.

Each item in the table includes:
    - Name of the work item, linked to the description
    - Category can be...
        - Maintenance: work that must be performed to keep Ironic working
        - Bugfix: work to enhance existing code to cover more corner cases and
          resolve bugs
        - Feature: a new Ironic feature that did not previously exist
    - Champions are the people most familiar with the technologies involved,
      and are a good resource if you'd like to implement the work item.

.. list-table:: 2023.1 Work Items
   :widths: 70 20 10
   :header-rows: 1

   * - Name
     - Category
     - Champions

   * - `SQLAlchemy 2.0 Compatibility`_
     - Maintenance
     - TheJulia

   * - `Nova Ironic Driver sharding`_
     - Bugfix
     - JayF, johnthetubaguy, TheJulia

   * - `Cleaning up RAID created by tenants`_
     - Bugfix
     - dtantsur, ftarasenko

   * - `Remove default use of MD5`_
     - Bugfix
     - TheJulia

   * - `Merging Inspector into Ironic`_
     - Maintenance
     - dtantsur, jjelinek

   * - `Active Steps`_
     - Feature
     - moshele, janders

   * - `Conductor Scaling & Locking`_
     - Bugfix
     - stevebaker

Goals Details
=============

SQLAlchemy 2.0 Compatibility
----------------------------
Our DB layer is currently using SQLAlchemy 1.4 or older, and relies heavily on
autocommit behaviors. Additionally as part of the migration to 2.0, SQLAlchemy
now requires developers be more explicit about querying than in previous
versions. There is a significant amount of work to be done as part of this
migration, but the resulting DB layer in the code should be clearer as a
result.

Nova Ironic Driver Sharding
---------------------------
The failure scenarios around the existing Nova Ironic driver are grim: when
an instance is provisioned, it's permanently tied to the nova-compute that
provisioned it and cannot be managed if that compute goes down. Additionally,
at high scale, there are more race conditions due to the length of time it
takes to query all Ironic nodes.

Instead, we will be adding support to Ironic, adding a sharding key which
Nova can consume. This will allow us to split Ironic node management across
a cluster of nova-compute services. Additionally, operators who want high
availabililty will be able to setup active/passive failover on nova-compute
services managing Ironic nodes.

Cleaning up RAID created by tenants
-----------------------------------
It has come to the Ironic community's attention that more and more cases are
arising where customers of BMaaS systems are doing things such as setting up
their own RAID sets. This can complicate undeploy/cleaning, and in some cases
redeployment of the machine.

To address this, the Ironic community is considering changes to the overall
cleaning workflow to disassemble discovered raid sets. While this is not yet
clearly defined, we hope that doing so will improve operator's and end user's
experiences.

Remove default use of MD5
-------------------------
The MD5 hashing algorithm is still supported in Ironic for image hashing.
This is not ideal as MD5 is broken. This work will be a breaking change;
forbidding use of MD5 hashes by default. Operators who wish to
continue using MD5 for API compatibility reasons will be able to re-enable
it via config.

Merging Inspector into Ironic
-----------------------------
Ironic Inspector was originally created as a service external to Ironic. Now,
it's used by a large number of Ironic operators around the world and should
be integrated with the primary service. Now is a good time to do this work as
well, as Ironic Inspector also needs to be updated to work with SQLAlchemy 2.0.

Active Steps
------------
Ironic uses steps to perform actions on a node during deployment or cleaning.
We'd like to extend this concept of steps to allow for maintenance on actively
deployed nodes. This new Active Steps feature will allow operators to perform a
firmware update -- or any other automated action on a provisioned, ACTIVE node.

Conductor Scaling & Locking
---------------------------
Traditionally, Ironic has taken an aggressive approach to locking nodes while
work is being performed at the expense of operations failing when a conductor
is shutdown or unavailable. This change will allow operators to gracefully
shutdown a conductor from the cluster, ensuring that no in-progress actions
will fail. As part of implementing and improving this, we will also need to
narrow the situations in which Ironic will lock a node and improve our methods
of locking.

Release Schedule
================
Contributors are reminded of our scheduled releases when they are choosing
items to work on.

The dates below are a guide; please view
https://releases.openstack.org/antelope/schedule.html for the full schedule
relating to the release and
https://docs.openstack.org/ironic/latest/contributor/releasing.html for Ironic
specific release information.

Bugfix Release 1
----------------
The first bugfix release is scheduled to happen the first week of December.

Bugfix release 2
----------------
The second bugfix release is scheduled to happen the first week of February.

Deadline Week
-------------
There are multiple deadlines/freezes the week of February 13th:
* Final release of client libraries must be performed
* Requirements freeze
* Soft string freeze - Ironic services are minimally translated; this
generally doesn't apply to our services, such as API and Conductor, but may
impact us via other projects which are translated.
* Feature Freeze - Ironic does not typically have a feature freeze, but we may
be impacted by other projects that do have a feature freeze at this date.

Final 2023.1 (Integrated) Release
---------------------------------
The final releases for Ironic projects in 2023.1 must be cut by March 17th,
2023.
