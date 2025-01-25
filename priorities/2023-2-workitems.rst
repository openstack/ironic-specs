.. _2023-2-work-items:

=========================
2023.2 Project Work Items
=========================

Most Ironic contributors have a large number of responsibilities, including
but not limited to, keeping CI working across all branches and projects,
backporting bugfixes, and any downstream job responsibilities that do not
include Ironic contribution.

Because of how much this work can vary over a six month release cycle, we
do not specify timelines for specific work items. Instead, we document planned
items we would like to see completed, and then allow the community to pick up
and work on them as time permits. Items are listed in no particular order.

This document represents our outlook for 2023.2, and will not be updated once
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

.. list-table:: 2023.2 Work Items
   :widths: 70 20 10
   :header-rows: 1

   * - Name
     - Category
     - Champions

   * - `Nova Ironic Driver sharding`_
     - Bugfix
     - JayF, johnthetubaguy, TheJulia

   * - `Remove default use of MD5`_
     - Bugfix
     - TheJulia

   * - `Merging Inspector into Ironic`_
     - Maintenance
     - dtantsur

   * - `Service Steps`_
     - Feature
     - TheJulia

   * - `Conductor Graceful Shutdown`_
     - Bugfix
     - stevebaker

   * - `FIPS Compatibility jobs in CI`_
     - Feature
     - Ade Lee

   * - `Cross-conductor communication`_
     - Feature
     - TheJulia

   * - `Hierarchical Nodes`_
     - Feature
     - TheJulia

   * - `Improving Deploy Kernel/Ramdisk Config`_
     - Feature
     - None

   * - `IPA Communication`_
     - Bugfix
     - kaloyank

   * - `Firmware Updates`_
     - Feature
     - iurygregory, dtantsur, janders

Goals Details
=============

Nova Ironic Driver Sharding
---------------------------
The failure scenarios around the existing Nova Ironic driver are grim: when
an instance is provisioned, it's permanently tied to the nova-compute that
provisioned it and cannot be managed if that compute goes down. Additionally,
at high scale, there are more race conditions due to the length of time it
takes to query all Ironic nodes.

Last cycle we added support for Ironic, to allow assigning a shard key to
nodes that can be used by clients, including Nova, can consume to split
Ironic node management across a cluster of services.

We hope to continue progress on this goal by implementing support for sharding
APIs in openstacksdk and python-ironicclient. Then, we will add support in the
Nova driver and networking-baremetal for sharding queries.

Remove default use of MD5
--------------------------
The MD5 hashing algorithm is still supported in Ironic for image hashing.
This is not ideal as MD5 is broken. This work will be a breaking change;
forbidding use of MD5 hashes by default. Operators who wish to
continue using MD5 for API compatibility reasons will be able to re-enable
it via config.

Merging Inspector into Ironic
-----------------------------
Ironic Inspector was originally created as a service external to Ironic. Now,
it's used by a large number of Ironic operators around the world and should
be integrated with the primary service.

Last cycle, the Node Inventory API was implemented in Ironic. Next, we will
move the rest of inspector functionality into Ironic. For more information,
see the relevant specs:

`Merge Inspector into Ironic <https://review.opendev.org/c/openstack/ironic-specs/+/878001>`_
`Migrate inspection rules from Inspector <https://review.opendev.org/c/openstack/ironic-specs/+/878230>`_

Service Steps
-------------
Ironic uses steps to perform actions on a node during deployment or cleaning.
We'd like to extend this concept of steps to allow for maintenance on actively
deployed nodes. This new Service Steps (formerly referred to as "Active Steps")
feature will allow operators to perform a firmware update -- or any other
automated action on a provisioned, ACTIVE node.

We will also be implementing some basic flow control steps into Ironic. These
commands, such as 'hold' and 'pause' will enable using steps to inform Ironic
to wait for an external API client or a configured period of time before
continuing. Additionally, we will evaluate more hardware and API actions to
expose as steps, such as power and BMC actions.

Conductor Graceful Shutdown
---------------------------
Initial work on gracefully shutting down by waiting for all locks to be
released was completed early in the Bobcat cycle. Next, we will work on support
for draining a conductor of tasks before shutting it down. The goal is to
ensure no in-progress actions are interrupted. This will allow for truly
non-disruptive conductor shutdowns and restarts.

FIPS Compatibility jobs in CI
-----------------------------
FIPS compatibility is a `cross-project goal <https://governance.openstack.org/tc/goals/selected/fips.html>`_
in OpenStack. We hope to have CI jobs added to identify areas in Ironic that
are not FIPS compatible. No major incompatibilities are anticipated, but we may
need to update some hashlib.md5() calls and other minor changes.

Cross-conductor communication
-----------------------------
Many conductor management actions taken on a node are written with assuming
a single conductor will perform them. This is not great for availability or
maintenance scenarios. We will be looking to implement some form of
cross-conductor communication to permit conductors to hand off work when being
shut off.

For more information, see
`the cross-conductor rpc hand-off spec <https://review.opendev.org/c/openstack/ironic-specs/+/873662>`_.

Hierarchical Nodes
------------------
Many new pieces of technology, such as DPUs, are presenting more complex
interfaces to hardware integrators. Architectures have emerged with nested
devices, with multiple firmwares and multiple nested operating systems to
manage. In order to support these, we are introducing parent/child relationship
to nodes. For more information, see `the DPU management/orchestration spec <https://review.opendev.org/c/openstack/ironic-specs/+/874189>`_.

Improving Deploy Kernel/Ramdisk Config
--------------------------------------
Ironic currently offers two places to easily manage deploy kernel and ramdisk:
configuration file, for global settings, and node metadata for per-node
overrides. This presents a problem for operators who want to operate Ironic
with hardware that requires different ramdisks; such as ARM and x86 -- they
will have to make "N" API calls for "N" nodes to update their non-default arch
ramdisks.

To resolve this problem, we'll be introducing config to allow setting default
ramdisks per-architecture. This will allow operators to set a different default
ramdisk for ARM and x86 nodes.

IPA Communication
-----------------
The current method of communication between Ironic and the Ironic Python Agent
ramdisk, including the agent token for security, is fragile in some use cases,
including neutron-integrated deployments with fast-track mode enabled.

Ironic contributors will be looking at ways to improve the communication with
the goal in mind to improve behavior around complex scenarios like the one
mentioned above.

For more information, see `the IPA communication spec <https://review.opendev.org/c/openstack/ironic-specs/+/777172>`_.

Firmware Updates
----------------
Ironic currently supports firmware updates via steps run in cleaning or
deployment. However, this is not ideal because it requires significant operator
understanding to perform updates.

Instead, as we have for BIOS and RAID, we will create a dedicated firmware
update interface, which will give a standard way to upgrade and manage
firmware.

See `the firmware update spec <https://review.opendev.org/c/openstack/ironic-specs/+/878505>`_
for more information.


Release Schedule
================
Contributors are reminded of our scheduled releases when they are choosing
items to work on.

The dates below are a guide; please view
https://releases.openstack.org/bobcat/schedule.html for the full schedule
relating to the release and
https://docs.openstack.org/ironic/latest/contributor/releasing.html for Ironic
specific release information. Please reach out to the Ironic team if you
would like to request a bugfix release.

Bugfix Release 1
----------------
The first bugfix release opportunity is the first week of May.

Bugfix release 2
----------------
The second bugfix release opportunity is the first week of July.

Deadline Week
-------------
There are multiple deadlines/freezes the week of August 28th:
* Final release of client libraries must be performed
* Requirements freeze
* Soft string freeze - Ironic services are minimally translated; this
generally doesn't apply to our services, such as API and Conductor, but may
impact us via other projects which are translated.
* Feature Freeze - Ironic does not typically have a feature freeze, but we may
be impacted by other projects that do have a feature freeze at this date.

Final 2023.2 (Integrated) Release
---------------------------------
The final releases for Ironic projects in 2023.1 must be cut by September 29,
2023.
