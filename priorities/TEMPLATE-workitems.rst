.. _RELEASE-work-items:

==========================
YYYY.XX Project Work Items
==========================
OpenStack Ironic operates on a general six month long development cycle.
These cycles are planned at the OpenInfra PTG (Project Teams Gathering).
In addition to this planned feature work, there are ongoing maintenance,
security, and release management work to keep Ironic running. This document
is the primary source for information about what Ironic team is prioritizing
this cycle. For more information please look at the link for each topic or
contact the Ironic team on IRC or via openstack-discuss mailing list.

Ironic contributors are busy; they work spanning multiple open source projects,
and have varied downstream responsibilities. We cannot guarantee any or all
planned work will be completed, nor is this a comprehensive list of
everything Ironic team members may do in the next six months.

[OPTIONAL: Include a paragraph about any work items dropped from previous
cycles, if applicable. Example:
"A few work items from past cycles have been dropped from this list without
being completed. These items include [list items]. These are still valid
features we hope will be implemented, but we do not have confidence we can
commit time to these items during this cycle."]

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

.. list-table:: YYYY.XX Work Items
   :widths: 50 20 20 10
   :header-rows: 1

   * - Name
     - Category
     - Tracking
     - Champions

   * - `Work Item Name 1`_
     - [Maintenance|Bugfix|Feature]
     - [Bug/Spec URL or N/A]
     - [Champion names]

   * - `Work Item Name 2`_
     - [Maintenance|Bugfix|Feature]
     - [Bug/Spec URL or N/A]
     - [Champion names]

[Add additional rows as needed]

Goals Details
=============

Work Item Name 1
----------------
[Detailed description of the work item, including:
- Background/context
- What will be implemented
- Why this is important
- Any technical details
- Dependencies or relationships to other work items]

Work Item Name 2
----------------
[Detailed description of the work item]

[Add additional sections as needed for each work item]

Maintenance Tasks
=================
There are some periodic tasks which must be done by project leadership during
the release cycle. These should be followed up on at every scheduled team
meeting to ensure they are being followed.

.. list-table:: YYYY.XX Maintenance Tasks
   :widths: 20 30 30 20
   :header-rows: 1

   * - Item
     - Document
     - Cadence
     - Responsible parties

   * - Release bugfix branches
     - https://docs.openstack.org/ironic/latest/contributor/releasing.html#bugfix-branches
     - Two additional releases per cycle, approximately at milestones 1 and 2.
     - DPL Release Liaison

   * - Retire expired bugfix branches
     - https://docs.openstack.org/ironic/latest/contributor/releasing.html#bugfix-branches
     - Bugfix branches older than 6 months must be retired.
     - DPL Release Liaison

   * - Bug triage
     - https://docs.openstack.org/ironic/latest/contributor/bug-deputy.html
     - Triage and respond to bugs, ensure periodic CI is happy.
     - Rotating volunteer 'deputy' from meeting

   * - Release Deadlines
     - https://releases.openstack.org/CODENAME/schedule.html
     - Ensure we meet various release deadlines and freezes.
     - DPL Release Liaison

