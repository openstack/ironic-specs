.. _2026-2-work-items:

=========================
2026.2 Project Work Items
=========================
The OpenStack Ironic Project Team Gathering happened in April 2026.
Ironic developers and operators discussed many different potential features and
other ongoing work for the 2026.2 (Hibiscus) release. These discussions are
memorialized in this document, providing a list of the main priorities for
the next development cycle. For more information please look at the link for
each topic or contact the Ironic team in #openstack-ironic on OFTC or via
openstack-discuss mailing list.

The 2026.1 cycle was ambitious and we landed a large number of impactful
features. For this reason, the team agreed to commit to overall less feature
work for 2026.2 to allow contributors to have extra time for triaging and
fixing incoming issues.

Ironic contributors are busy; they work spanning multiple open source projects,
and have varied downstream responsibilities. We cannot guarantee any or all
planned work will be completed, nor is this a comprehensive list of
everything Ironic team members may do in the next six months.

Each item in the table includes:
    - Name of the work item, linked to the description
    - Category can be...
        - Maintenance: work that must be performed to keep Ironic working
        - Bugfix: work to enhance existing code to cover more corner cases and
          resolve bugs
        - Feature: a new Ironic feature that did not previously exist
    - Champions are the people most familiar with the technologies involved,
      and are a good resource if you'd like to implement the work item.
    - Tracking link is a link to the bug (usually) tracking the work.

.. list-table:: 2026.2 Work Items
   :widths: 50 20 20 10
   :header-rows: 1

   * - Name
     - Category
     - Tracking
     - Champions

   * - `Deferred tasks`_
     - Feature
     - https://review.opendev.org/c/openstack/ironic-specs/+/954612
     - TheJulia, cid

   * - `Nova-Compute startup performance`_
     - Bugfix
     - https://etherpad.opendev.org/p/ironic-nova-compute-startup-2026.2
     - JayF, Clif

   * - `Bulk node operations`_
     - Feature
     - https://review.opendev.org/c/openstack/ironic-specs/+/983183
     - cid, JayF

   * - `Power lockout/tagout`_
     - Feature
     - https://review.opendev.org/c/openstack/ironic-specs/+/974894
     - cid, JayF

   * - `Sushy in-tree and async Redfish`_
     - Maintenance
     - N/A
     - cardoe, dtantsur, iurygregory

   * - `Firmware upgrades improvements`_
     - Bugfix
     - N/A
     - cardoe, iurygregory, janders

   * - `Observability and IPE improvements`_
     - Bugfix
     - https://bugs.launchpad.net/ironic/+bug/2150125
     - dtantsur, iurygregory

   * - `PQC and TLS controls`_
     - Feature
     - N/A
     - TheJulia

   * - `gdisk replacement`_
     - Maintenance
     - N/A
     - rpittau

   * - `GPU information in inspection`_
     - Feature
     - N/A
     - dtantsur, JayF

   * - `OOB inspection while active`_
     - Feature
     - https://bugs.launchpad.net/ironic/+bug/2049913
     - cardoe, dtantsur

   * - `Root disk encryption`_
     - Feature
     - N/A
     - Adam (Metal3)

   * - `VMedia/HTTP boot and port.pxe_enabled cleanup`_
     - Maintenance
     - https://bugs.launchpad.net/ironic/+bug/2043019
     - JayF

Goals Details
=============

Deferred tasks
--------------
The goal is to eliminate sleep() calls in conductor threads, which are
particularly expensive in the post-eventlet world. Deferred tasks will allow
Ironic to schedule work to be performed later, such as resuming from port
binding, checking BMC readiness, and handling firmware upgrades.

While initial milestones will focus on the cases made worse in a post-eventlet
Ironic, this work is expected to eventually culminate in an operator-visible
API endpoint to track the status of long-running tasks.

This work is a prerequisite for bulk node operations and other features that
require tracking long-running tasks. This is an extensive rework of how Ironic
manages long-running work, and we expect it to span multiple release cycles.

Nova-Compute startup performance
--------------------------------
Ironic developers are coordinating with Nova developers to improve
nova-compute startup times in large Ironic installations. This addresses
real-world pain points where nova-compute can take minutes to start when
managing hundreds of bare metal nodes.

These startup time issues are a part of a larger problem of syncing up
node statuses between Ironic, Nova, and Placement. This project is aimed
at reducing overall latency when performing these syncs or, when possible,
removing them altogether.

The work for this improvement will be split between Ironic and Nova code
repositories. This work includes:

- Adding a devstack CI job using fake-hardware to measure startup time.
- Implementing and backporting transparent performance improvements.
- Updating reserved flag directly in Placement when nodes transit states.

Future improvements in this area, not planned for 2026.2, may include Ironic
taking over publishing and management of Placement API entries for Ironic
resources.

Bulk node operations
--------------------
For cases where operators need to perform the same action across many nodes,
we are adding a bulk-actions API endpoint. This will allow applying operations
at scale on any number of nodes matching filter criteria.

This feature will be asynchronous and will leverage the deferred tasks
infrastructure for tracking status and handling failures.

Given it has a hard dependency on the deferred tasks work, it is a stretch
goal for the team to make progress on this work item.

Power lockout/tagout
--------------------
A feature to ensure no automated Ironic process or project member can alter
power state on a given node. This mirrors physical facility lockout/tagout
practices for safe maintenance in the physical world.

An initial spec for this exists, but will be revised considerably to turn
it into a new form of maintenance system, rather than a parallel one relating
only to power. In 2026.2, we intend on finalizing these plans but may not
begin implementation.

Sushy in-tree and async Redfish
-------------------------------
Ironic would like to move the Sushy redfish library directly into the
Ironic repository to reduce maintenance overhead, simplify releases, and
eliminate API surface management between projects.

This change is similar to the integration and retirement of ironic-lib last
year.

Once migrated in-tree, Ironic developers will explore use of async python
to improve performance for various redfish driver methods.

Firmware upgrades improvements
------------------------------
Continued work on firmware upgrades reliability and functionality:

- Implementing PUSH firmware updates (used by Dell and HPE instead of PULL)
- Addressing NIC update challenges where target properties are unavailable
- Improving the firmware upgrade state machine visibility
- DMTF engagement on multi-component update standards

This work addresses ongoing pain points discovered as more operators adopt
the firmware upgrade feature.

Observability and IPE improvements
-----------------------------------
Continued improvements to the ironic-prometheus-exporter (IPE) and metrics
collection. These circle primarily around moving the metrics gathering
from the external IPE application into Ironic directly.

This may lead, in the medium-term, to the retirement of IPE in favor of
direct prometheus polling of Ironic.

Additionally, we plan to improve server health monitoring, providing
detail on outstanding faults instead of just reporting an OK/Warning/Critical
status.

PQC and TLS controls
--------------------
Operators have long asked Ironic to permit them more control over TLS
versions and ciphers used during provisioning operations. This project
adds controls for Post-Quantum Cryptography (PQC) readiness and TLS version
management, including:

- Minimum TLS version knob for Redfish BMC connections
- Cipher selection controls for both global and per-node configuration
- Improving agent certificate/TLS flow to support configurable algorithms

This work prepares Ironic for environments requiring PQC-safe ciphers and
enables operators to enforce modern TLS standards across heterogeneous BMC
firmware.

gdisk replacement
-----------------
The gdisk/sgdisk tools have been obsoleted (last release 2024) and removed
from some distributions. This work will replace gdisk usage in IPA with
alternatives. This is necessary maintenance to keep IPA functional on
modern distributions.

GPU information in inspection
-----------------------------
Adding basic GPU information to inspection data including vendor, model, and
other relevant details. This enables operators to track GPU hardware inventory
and potentially set traits based on GPU capabilities.

OOB inspection while active
---------------------------
Enabling out-of-band (OOB / Redfish) inspection to run while nodes are in
active state. This allows operators to update inspection data after hardware
changes without disrupting running workloads.

The approach under consideration is exposing inspection methods as service
steps, allowing them to be invoked during servicing workflows. This would
include a merge mode to avoid overwriting in-band collected data.

Root disk encryption
--------------------
Resurrecting upstream work on root disk encryption. This feature allows
encrypting the root disk of deployed instances for security compliance.

This work is being picked up by Metal3 contributors and is tentative for
this cycle.

VMedia/HTTP boot and port.pxe_enabled cleanup
---------------------------------------------
The pxe_enabled flag on ports is overloaded and causes confusion with HTTP
boot. For instance, when using virtual media to provision an Ironic instance,
Ironic attempts to enable all ports marked as pxe_enabled, even though
``PXE``, the netboot technology, is not in use. When failing on port
binding failures is enabled, the default, this can lead to erroneous
failures in some configurations.

Ironic developers will work to disambiguate this flag and create a method for
operators to more verbosely indicate which ports are required to be attached
for which boot interfaces.

Maintenance Tasks
=================
There are some periodic tasks which must be done by project leadership during
the release cycle. These should be followed up on at every scheduled team
meeting to ensure they are being followed.

.. list-table:: 2026.2 Maintenance Tasks
   :widths: 20 30 30 20
   :header-rows: 1

   * - Item
     - Document
     - Cadence
     - Responsible parties

   * - Release bugfix branches
     - https://docs.openstack.org/ironic/latest/contributor/releasing.html#bugfix-branches
     - Two additional releases per cycle, approximately at milestones 1 and 2.
     - DPL Release Liaisons

   * - Retire expired bugfix branches
     - https://docs.openstack.org/ironic/latest/contributor/releasing.html#bugfix-branches
     - Bugfix branches older than 9 months must be retired.
     - DPL Release Liaisons

   * - Bug triage
     - https://docs.openstack.org/ironic/latest/contributor/bug-deputy.html
     - Triage and respond to bugs, ensure periodic CI is happy.
     - Rotating volunteer 'deputy' from meeting

   * - Release Deadlines
     - https://docs.openstack.org/ironic/latest/contributor/releasing.html
     - Ensure we meet various release deadlines and freezes.
     - DPL Release Liaisons

Release Schedule
================
Contributors are reminded of our scheduled releases when they are choosing
items to work on.

The dates below are a guide; please view
https://releases.openstack.org/hibiscus/schedule.html for the full schedule
relating to the release and
https://docs.openstack.org/ironic/latest/contributor/releasing.html for Ironic
specific release information.

Bugfix Release 1
----------------
The first bugfix release is scheduled to happen around the last week of
May, 2026.

Bugfix release 2
----------------
The second bugfix release is scheduled to happen around the last week of
July, 2026.

Deadline Week
-------------
There are multiple deadlines/freezes in the final weeks of the release,
please refer to the release schedule for exact dates.

Final 2026.2 (Integrated) Release
---------------------------------
The final releases for Ironic projects in 2026.2 must be cut before
September 30, 2026.
