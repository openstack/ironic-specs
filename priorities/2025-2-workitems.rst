.. _2025-2-work-items:

=========================
2025.2 Project Work Items
=========================
The latest virtual Project Team Gathering happened in April 2025. Ironic
developers and operators discussed many different potential features and
other ongoing work for the 2025.2 (Flamingo) release. These discussions are
memorialized in this document, providing a list of the main priorities for
the next development cycle. For more information please look at the link for
each topic or contact the Ironic team on IRC.

Ironic contributors are busy; they work spanning multiple open source projects,
and have varied downstream responsibilities. We cannot guarantee any or all
planned work will be completed, nor is this a comprehensive list of
everything Ironic may do in the next six months.

A few work items from past cycles have been dropped from this list without
being completed. These items include kea DHCP backend implementation, in-band
disk encryption, and tinycore ramdisk replacement. These are still valid
features we hope will be implemented, but we do not have confidence we can
commit time to these items during this cycle.

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

.. list-table:: 2025.2 Work Items
   :widths: 50 20 20 10
   :header-rows: 1

   * - Name
     - Category
     - Tracking
     - Champions

   * - `Eventlet Migration`_
     - Maintenance
     - https://wiki.openstack.org/wiki/Eventlet-removal
     - dtantsur, JayF

   * - `Networking: Scheduling and dynamic portgroups`_
     - Feature
     - https://review.opendev.org/c/openstack/ironic-specs/+/945642
     - JayF, TheJulia

   * - `Networking: Project Mercury`_
     - Feature
     - `Mailing list thread about new working group <https://lists.openstack.org/archives/list/openstack-discuss@lists.openstack.org/thread/S4OZH7PC3NAZC2HXBGAQ7YSJUOPFKBW3/#WS5VO2PIXW42N3LQ2A6UD3WQU5YVZ56X>`_
     - BM Networking WG

   * - `Improve OEM handling in Sushy`_
     - Maintenance/Feature
     - `Sushy to include OEM support <https://bugs.launchpad.net/ironic/+bug/2086725>`_
     - cardoe, dtantsur

   * - `API response schema validation, OpenAPI Spec`_
     - Maintenance
     - `Add OpenAPI support for Ironic via codegenerator <https://launchpad.net/bugs/2086121>`_
     - stephenfin, adammcarthur5

   * - `Redfish-based servicing improvements`_
     - Feature
     - N/A
     - iurygregory, janders, dtantsur

   * - `Document steps used in Node History`_
     - Feature
     - `[RFE] Log steps performed in step-based flows (cleaning/deploying/servicing) <https://bugs.launchpad.net/ironic/+bug/2106758>`_
     - TheJulia, JayF, cardoe

Goals Details
=============

Eventlet Migration
------------------
All of OpenStack, including Ironic, was written against a greenthreading event
loop library called eventlet. This package is slowly losing relevancy in modern
python and must be replaced. Support in oslo libraries for Eventlet will be
removed in 2026.2 -- if we haven't retired eventlet by then, we'll no longer
be able to run.

Networking: Scheduling and dynamic portgroups
---------------------------------------------
Ironic currently supports portgroups, combinations of ports bonded together
for increased network performance. However, these portgroups are modeled in
a similar, static way to physical hardware, when technically they can be
dynamically configured. This cycle, Ironic wants to add the ability to direct
scheduling of networks to ports and portgroups, including the ability to
assemble portgroups dynamically based on Ironic configuration and requested
traits.

Networking: Project Mercury
---------------------------
Networking represents the next step for a truly standalone Ironic, and this
means finding alternatives to Openstack-integrated scenarios and therefore
to Neutron.

For complete usage in an enterprise use case, Ironic needs a means of
networking control, which today is manual unless in a fully integrated
OpenStack context. The Ironic team and interested operators have formed a
working group around this and other networking improvements that can be
made in Ironic as we refine our design for standalone networking.

Additional discussion occurred about this vision at the 2025.2 PTG, and
ensuring additional network functionality proposed this cycle is
compatible with this vision. There are no specific actions beyond further
design discussion in the working group planned for this cycle.

Improve OEM handling in Sushy
-----------------------------
Currently, sushy has minimal support for OEM specific code. In Epoxy cycle,
we integrated ``sushy-oem-drac``, directly into the ``sushy`` project,
beginning down a path of adopting OEM logic directly into ``sushy``,
simplifying our codebase and making it easier to support quirky vendor
implementations of Redfish and potentially enabling utilization of OEM
extensions. We intend on further enhancing the ability for Sushy to adjust
behavior based on vendor and be able to query custom OEM redfish endpoints.

API response schema validation, OpenAPI Spec
--------------------------------------------
The Ironic team is joining an effort by the OpenStack SDK team to generate
OpenAPI specification documents from API code. This will ensure our
API documentation will match the code by generating it from the code.
As part of this work, the Ironic team will be refactoring handling of
API microversions to help with the generation process and improve code
readability.

In the Epoxy cycle, the Ironic team focused on implementing additional
API validation tests to allow this change to be less risky. We hope to
complete that work and begin merging more patches related to this
change in Flamingo.

Redfish-based servicing improvements
------------------------------------
In the past cycles, we have introduced an ability for out-of-band servicing of
bare-metal nodes via Redfish. We want to continue further developing this
feature.

The planned improvements involve supporting NIC firmware updates via
SimpleUpdate and improving the downtime this feature causes by cutting down
on the number of reboots.

Document steps used in node history
-----------------------------------
Ironic has had operators requesting the ability to predict what steps may
run on a node during the next automated flow. This is extremely difficult to
do just-in-time due to the dynamic nature of IPA-based-steps.

Instead, we are going to document what steps *have run* as part of a
step-based process. We will provide an option to send events to Node History
when a step-based process begins or succeeds. These events will include the
steps to be run in that process (when beginning) or the steps actually run in
the process (when successful).

Release Schedule
================
Contributors are reminded of our scheduled releases when they are choosing
items to work on.

The dates below are a guide; please view
https://releases.openstack.org/flamingo/schedule.html for the full schedule
relating to the release and
https://docs.openstack.org/ironic/latest/contributor/releasing.html for Ironic
specific release information.

Bugfix Release 1
----------------
The first bugfix release is scheduled to happen around the first week of
May, 2025.

Bugfix release 2
----------------
The second bugfix release is scheduled to happen the first week of August,
2025.

Deadline Week
-------------
There are multiple deadlines/freezes in the final weeks of the release,
please refer to the release schedule for exact dates.

Final 2025.2 (Integrated) Release
---------------------------------
The final releases for Ironic projects in 2025.2 must be cut by
September 26, 2025.
