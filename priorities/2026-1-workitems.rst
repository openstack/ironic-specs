.. _2026-1-work-items:

=========================
2026.1 Project Work Items
=========================
The OpenStack Ironic virtual Project Team Gathering happened in October 2025.
Ironic developers and operators discussed many different potential features and
other ongoing work for the 2026.1 (Gazpacho) release. These discussions are
memorialized in this document, providing a list of the main priorities for
the next development cycle. For more information please look at the link for
each topic or contact the Ironic team in #openstack-discuss on OFTC or via
openstack-discuss mailing list.

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

.. list-table:: 2026.1 Work Items
   :widths: 50 20 20 10
   :header-rows: 1

   * - Name
     - Category
     - Tracking
     - Champions

   * - `Post-eventlet performance improvements`_
     - Feature
     - https://etherpad.opendev.org/p/ironic-asyncio
     - cid, dtantsur, iurygregory

   * - `Deferred tasks`_
     - Feature
     - https://review.opendev.org/c/openstack/ironic-specs/+/954612
     - TheJulia, dtantsur, cid

   * - `Sushy integration into Ironic`_
     - Maintenance
     - N/A
     - iurygregory

   * - `NVMe-over-TCP support`_
     - Feature
     - https://bugs.launchpad.net/nova/+bug/2126675
     - TheJulia, cardoe

   * - `Graphical Console Improvements`_
     - Feature
     - https://review.opendev.org/c/openstack/nova/+/942528
     - stevebaker, TheJulia

   * - `Trait Based Networking`_
     - Feature
     - https://specs.openstack.org/openstack/ironic-specs/specs/approved/trait-based-port-scheduling.html
     - clif, JayF, TheJulia

   * - `VXLAN attachments`_
     - Feature
     - https://review.opendev.org/c/openstack/ironic-specs/+/959401
     - cardoe, TheJulia

   * - `Standalone Networking`_
     - Feature
     - N/A
     - alegacy, dtantsur, JayF

   * - `API response schema validation, OpenAPI Spec`_
     - Maintenance
     - `Add OpenAPI support for Ironic via codegenerator <https://launchpad.net/bugs/2086121>`_
     - stephenfin, adammcarthur5

   * - `Redfish Virtual Media via NFS and SMB`_
     - Feature
     - https://bugs.launchpad.net/ironic/+bug/2119212
     - cid

   * - `Hardware health monitoring`_
     - Feature
     - N/A
     - janders, dtantsur

   * - `Database charset migration`_
     - Maintenance
     - https://bugs.launchpad.net/ironic/+bug/2130359
     - rpittau

   * - `Driver retirements`_
     - Maintenance
     - N/A
     - JayF, janders, iurygregory

Goals Details
=============

Post-eventlet performance improvements
--------------------------------------
In the post-eventlet world, Ironic has the opportunity to implement async/await
patterns to achieve high parallelism for metrics collection and power syncs.
This work will focus on proof of concept implementations for sensor data
collection, paying particular attention to the Redfish session cache. The goal
is to measure performance improvements and determine the appropriate scope for
async implementation within Ironic.

This work will initially focus on the management and power driver interfaces,
as these are the areas where we see the most benefit from parallelism. The team
will use sushy-tools to create test environments with many nodes and measure
performance improvements before and after implementation.

Deferred tasks
--------------
The goal is to eliminate sleep() calls in conductor threads, which are
particularly expensive in the post-eventlet world. Deferred tasks will allow
Ironic to schedule work to be performed later, such as resuming from port
binding, checking BMC readiness, and handling firmware upgrades. This work
overlaps with async/await implementation and the two efforts will be
coordinated.

The initial implementation will not expose a public API, to prevent abuse. The
decision on whether to add an API endpoint will be revisited after the
async/await design is finalized.

Sushy integration into Ironic
-----------------------------
The team is evaluating moving sushy into the ironic repository to reduce
maintenance overhead, simplify releases, and eliminate API surface management
between projects. This change would be similar to the ironic-lib integration.
A mailing list discussion has been initiated to gather community feedback
before proceeding with this change.

We intend to allow sushy imports to still be made even if the module itself may
move into ironic directly.

NVMe-over-TCP support
---------------------
This work will add support for NVMe-over-TCP volume attachments in Ironic,
including:

- Adding NVMe-over-TCP connector support
- Implementing BMC configuration for NVMe boot
- Coordinating with Cinder and Nova on attachment flow improvements

This work will enable operators to use modern storage protocols with bare metal
and is particularly important for operators using storage arrays that primarily
support NVMe-over-TCP.

Graphical Console Improvements
------------------------------
Building on the graphical console work from previous cycles, this work focuses
on:

- Merging remaining integration testing changes
- Exposing the graphical console features for Nova integrated users
- Implementing additional console drivers (e.g., Kubernetes-based)
- Switching browser tooling to use a Firefox extension

This work requires coordination with Nova and deployment projects to ensure
the feature is widely usable.

Trait Based Networking
----------------------
Continuation of work from previous cycles to enable dynamic port and portgroup
attachment based on traits defined in configuration. Current status:

- Port and portgroup model changes mostly complete
- Grammar and parsing for filter expressions done
- Configuration file implementation nearly complete
- Network planning and action generation in progress
- Next steps: executing actions at provision time, dynamic portgroup assembly

This work enables more flexible networking configuration and is a foundation
for other networking improvements.

VXLAN attachments
-----------------
Operators are expressing concern about scaling environments without native
VXLAN support. This work will enable bare metal nodes to connect to VXLAN
networks, working around VLAN scaling limitations. This requires:

- Neutron ML2 plugin support for VXLAN with physical networks
- Ironic support for VXLAN binding
- Coordination with networking-generic-switch for switch configuration

This work is particularly important for large-scale deployments that have
exhausted their VLAN space.

Standalone Networking
---------------------
Networking represents the next step for a truly standalone Ironic, finding
alternatives to OpenStack-integrated scenarios and therefore to Neutron. Over
the last cycle, discussions were traded for code as implementation began.

A working prototype for standalone networking has been written and is expected
to merge during this cycle with support for basically placement of nodes into
VLANs using networking-generic-switch called directly from ironic.

API response schema validation, OpenAPI Spec
--------------------------------------------
Continuation of work from previous cycles. The Ironic team is generating
OpenAPI specification documents from API code and refactoring microversion
handling. This effort will continue with a renewed vigor in the 2026.1 cycle.

Redfish Virtual Media via NFS and SMB
-------------------------------------
Some BMCs do not support HTTPS for virtual media and require NFS or SMB/CIFS
shares. This work will add support for these transport protocols but may not
include ironic management of the actual network file system services.

Hardware health monitoring
--------------------------
Add basic hardware health monitoring based on Redfish System Status fields.
This will collect health status from systems and potentially network adapters,
record status changes in node history, and expose the information via the API.
This work leverages existing power sync loops to collect additional hardware
state information.

This work will also investigate proxying health status to Metal3's
BareMetalHost.Status for Kubernetes-based deployments.

Database charset migration
--------------------------
MySQL's 3-byte UTF-8 charset encoding is deprecated. Ironic needs to migrate
to 4-byte UTF-8 (utf8mb4) encoding. This will require a database migration
and coordination with deployment projects to ensure smooth upgrades.

It's our expectation this will be an OpenStack-wide priority in the coming
cycles, and the ironic team is ready to do our part.

Driver retirements
------------------
The iLO driver will be deprecated and retired due to a dependency on pysnmp as
the versions it is compatible with are not security updated and there are no
volunteers to modernize it. The iRMC driver similarly has a dependency on
pysnmp via the snmp driver, and deprecation of that will proceed unless
Fujitsu or a user of iRMC are able to commit to upstream maintenance.

Both drivers will receive upgrade checks (backported to last release) warning
about deprecation before removal.

Maintenance Tasks
=================
There are some periodic tasks which must be done by project leadership during
the release cycle. These should be followed up on at every scheduled team
meeting to ensure they are being followed.

.. list-table:: 2026.1 Maintenance Tasks
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
https://releases.openstack.org/gazpacho/schedule.html for the full schedule
relating to the release and
https://docs.openstack.org/ironic/latest/contributor/releasing.html for Ironic
specific release information.

Bugfix Release 1
----------------
The first bugfix release is scheduled to happen around the last week of
November, 2025.

Bugfix release 2
----------------
The second bugfix release is scheduled to happen around the last week of
January, 2026.

Deadline Week
-------------
There are multiple deadlines/freezes in the final weeks of the release,
please refer to the release schedule for exact dates.

Final 2026.1 (Integrated) Release
---------------------------------
The final releases for Ironic projects in 2026.1 must be cut before
March 26, 2026.
