.. _2024-1-work-items:

=========================
2024.1 Project Work Items
=========================
Ironic developers and operators met at the vPTG in October, 2023 to plan the
2024.1 (Caracal) release. This document is the output of that planning, and
will not be updated once published. For information or current status of items
in progress, please look at the linked bugs. For information about items
completed, please see the Ironic release notes for the given release in
question.

Ironic contributors are busy; they work spanning multiple open source projects,
and have varied downstream responsibilities. We cannot guarantee any or all
planned work will be completed.


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

.. list-table:: 2024.1 Work Items
   :widths: 50 20 20 10
   :header-rows: 1

   * - Name
     - Category
     - Tracking
     - Champions

   * - `Eliminating Bug Backlog`_
     - Maintenance
     - `2040552 <https://bugs.launchpad.net/ironic/+bug/2040552>`_
     - JayF, dtantsur

   * - `Nova Ironic Driver sharding`_
     - Bugfix
     - `ironic-shards <https://blueprints.launchpad.net/nova/+spec/ironic-shards>`_
     - JayF, johnthetubaguy, TheJulia

   * - `Merging Inspector into Ironic`_
     - Maintenance
     - `Migrate inspection rules from inspector <https://specs.openstack.org/openstack/ironic-specs/specs/not-implemented/inspection-rules.html>`_
     - dtantsur

   * - `Develop plan for streamlined testing`_
     - Maintenance
     - N/A
     - TheJulia, iurygregory

   * - `Feature Parity with Metalsmith`_
     - Feature
     - `2042575 <https://bugs.launchpad.net/ironic/+bug/2042575>`_
     - dtantsur

   * - `Redfish HttpBoot`_
     - Feature
     - `2032380 <https://bugs.launchpad.net/ironic/+bug/2032380>`_
     - TheJulia

   * - `Step Templates`_
     - Feature
     - `2027690 <https://bugs.launchpad.net/ironic/+bug/2027690>`_
     - TheJulia, JayF

   * - `Cleanup Legacy Client Library Use in Ironic`_
     - Maintenance
     - `2042493 <https://bugs.launchpad.net/ironic/+bug/2042493>`_, `2042494 <https://bugs.launchpad.net/ironic/+bug/2042494>`_, `2042495 <https://bugs.launchpad.net/ironic/+bug/2042495>`_
     - stevebaker

   * - `Marking Multiple Drivers for Removal`_
     - Maintenance
     - N/A
     - JayF, TheJulia

   * - `Purging UEFI boot records`_
     - Feature
     - `2042570 <https://bugs.launchpad.net/ironic/+bug/2042570>`_, `2041901 <https://bugs.launchpad.net/ironic/+bug/2041901>`_
     - dtantsur, stevebaker

Goals Details
=============

Eliminating Bug Backlog
-----------------------
The Ironic core team has not prioritized bug triage or cleanup in recent
years for a myriad of reasons. We will resolve this issue, and pay off
related bug debt, during the 2023.2 cycle. A new bug deputy role will be
created and rotate on a schedule. The deputy will be responsible for
performing bug triage on new bugs, providing a report on bugs for the
weekly meeting, and moderating at least one "bug jam" meeting a week to
work through the backlog of neglected untriaged or outdated bugs. Our goal
is that by the end of the 2023.2 cycle, no untriaged bugs older than two
weeks will exist in any supported Ironic projects.

We define a triaged bug as one that has been read, prioritized, and usually
commented on by an Ironic developer. Bug triage is important because it
ensures that critical issues are seen quickly once reported.

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

This work was nearly completed last cycle, but was held to permit more
automated testing to be completed before release.

Develop Plan for Streamlined Testing
------------------------------------
Ironic is a complex system, with many different ways of configuring it. This
leads to complicated matrices of test jobs. In the 2024.1 cycle, Ironic
contributors will work to develop a plan to simplify the testing matrix,
consolidating jobs where possible and identifying minimal next steps we can
take next cycle.

Merging Inspector into Ironic
-----------------------------
Ironic Inspector was originally created as a service external to Ironic. Now,
it's used by a large number of Ironic operators around the world and should
be integrated with the primary service.

This work has been progressing well. We will continue to work on this until it
is complete.

Feature Parity with Metalsmith
------------------------------
Metalsmith was created to simplify human interaction with the deployment of
nodes using Ironic, primarily to support TripleO use cases. This simplified
deployment model should be brought to all Ironic deployments. We will do this
by adding a new deployment API to Ironic, allowing the deployment of a server
through one single API call.

Additionally, we will add logic and usage ergonomics to Ironic's interactive
client, with the goal of provisioning a single machine with python-ironicclient
with the new deployment API being as easy as deploying one today with
metalsmith.

Once this work has completed, we will retire the dedicated metalsmith client.

Redfish HttpBoot
----------------
An often requested method utilized to boot machines is to leverage the ability
to tell the remote BMC that the item to boot is available via an HTTP(S) URL.

By informing the BMC directly what to boot, we can remove fragile parts of the
boot process such as TFTP or even in some cases PXE altogether. This will be
integrated and share code with the existing implementations of virtual media on
Redfish.

Step Templates
--------------
Ironic has used automated step processes to perform needed tasks on machines
for a long time. However, these have always operated in two modes, either
fully automated, or fully specified. This makes it difficult to use these
step-based automations in a way that is friendly to a less-technical operator.

To address this, we propose changing the current concept of Deploy Templates to
a generic concept of Step Templates. These templates would be RBAC-aware, and
would be able to be used in the API anywhere you'd currently pass a dictionary
of steps, such as for manual cleaning or service.

Our goal for the this cycle will be to fully specify this feature and identify
any potential pain points that could occur during the upgrade process.

Cleanup Legacy Client Library Use in Ironic
-------------------------------------------
Ironic is integrated with a number of OpenStack services, interacting via
client requests. Requests to some services (nova, neutron, keystone) are made
via openstacksdk while others (swift, cinder, glance) are still made via the
legacy client libraries. During the caracal cycle, we intend to complete the
migration to use only openstacksdk.

Marking Multiple Drivers for Removal
------------------------------------
Ironic has a long history of working closely with hardware vendors, and they've
reciprocated in kind by helping develop drivers and manage CI against them for
many years. However, with the emergence of advanced hardware management
standards, like Redfish, the need for vendor-specific drivers is diminishing.

Furthermore, many of the legacy drivers originally targeted at older,
nonstandard interfaces or server management solutions, due to their naming,
often sound like they more closely match a given vendor's hardware than the
Redfish driver. These drivers, while still useful for older hardware which may
not support redfish, are not ideal for modern hardware.

For this reason, and others, we have selected a number of drivers to be marked
for removal. We do not intend to actively remove any of these drivers until
it is clear any hardware they exclusively support has gone end of life. We
are primarily taking this action to indicate to operators that they should
be provisioning new hardware with Redfish-based drivers.

The Ironic community is extremely grateful to these vendors for supporting
their drivers in Ironic for so long, and for supporting the open standards
which, in most cases, are obsoleting the need for specific drivers.

Please note that suggested alternatives are not tested by Ironic CI and are
suggestions based on specified system support or vendor recommendations.

.. list-table:: Drivers to be marked for removal
   :widths: 20 40 40
   :header-rows: 1

   * - Driver
     - Hardware
     - Alternatives

   * - ``ibmc``
     - Huawei
     - ``redfish``

   * - ``idrac-wsman``
     - Dell (iDRAC 5,6)
     - ``idrac-redfish`` (iDRAC 7+)

   * - ``xclarity``
     - Lenovo (cluster manager)
     - ``redfish`` (to individual systems)

   * - ``ilo``
     - HPE servers (iLO 5 or older)
     - ``redfish`` (iLO 6 and newer)

Purging UEFI boot records
-------------------------
Stale EFI boot records can cause problems with booting or adding new records.
Since Ironic manages a node it should be responsible for removing any existing
boot record which resembles a disk or attached boot device (USB, CDROM, etc).

This can be done in-band with a step which can optionally be included during
cleaning or deployment. However it also needs to be possible to do it via
Redfish to handle the cases where the node won't boot at all due to stale
incorrect records.

Release Schedule
================
Contributors are reminded of our scheduled releases when they are choosing
items to work on.

The dates below are a guide; please view
https://releases.openstack.org/caracal/schedule.html for the full schedule
relating to the release and
https://docs.openstack.org/ironic/latest/contributor/releasing.html for Ironic
specific release information.

Bugfix Release 1
----------------
The first bugfix release is scheduled to happen around the first week of
December, 2023.

Bugfix release 2
----------------
The second bugfix release is scheduled to happen the first week of February,
2024.

Deadline Week
-------------
There are multiple deadlines/freezes the final week of February:
* Final release of client libraries must be performed
* Requirements freeze
* Soft string freeze - Ironic services are minimally translated; this
generally doesn't apply to our services, such as API and Conductor, but may
impact us via other projects which are translated.
* Feature Freeze - Ironic does not typically have a feature freeze, but we may
be impacted by other projects that do have a feature freeze at this date.

Final 2024.1 (Integrated) Release
---------------------------------
The final releases for Ironic projects in 2024.1 must be cut by March 25.
