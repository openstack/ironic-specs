.. _2024-2-work-items:

=========================
2024.2 Project Work Items
=========================
During the latest virtual Project Team Gathering happened between April 8
and 12, the Ironic developers and operators discussed multiple
topics to plan the work for the next 2024.2 (Dalmatian) release.
We summarize the outcome of the discussion in this document, providing a list
of the main priorities for the next development cycle. For more information
please look at the link for each topic or contact the Ironic team on IRC.

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

.. list-table:: 2024.2 Work Items
   :widths: 50 20 20 10
   :header-rows: 1

   * - Name
     - Category
     - Tracking
     - Champions

   * - `Ironic Documentation Improvements`_
     - Maintenance
     - N/A
     - JayF

   * - `API response schema validation`_
     - Feature
     - N/A
     - stephenfin

   * - `Merging Inspector into Ironic`_
     - Feature
     - `Migrate inspection rules from inspector <https://specs.openstack.org/openstack/ironic-specs/specs/not-implemented/inspection-rules.html>`_
     - masghar

   * - `Redfish Virtual Media Push / UpdateService`_
     - Feature
     - N/A
     - janders, dtantsur, TheJulia

   * - `Virtual Media TLS Validation`_
     - Feature
     - N/A
     - dtantsur

   * - `Slimming Down CI`_
     - Maintenance
     - N/A
     - team effort

   * - `Tinycore Alternative for IPA ramdisk`_
     - Maintenance
     - N/A
     - JayF, rpittau

   * - `Ironic Guest Metadata from nova`_
     - Feature
     - `Ironic Guest Metadata <https://bugs.launchpad.net/ironic/+bug/2063352>`_
     - JayF

   * - `Service Steps templates`_
     - Feature
     - `Expose templates for all steps, with project-awareness <https://bugs.launchpad.net/ironic/+bug/2027690>`_
     - JayF, TheJulia

   * - `Networking: Project Mercury`_
     - Feature
     - N/A
     - TheJulia

   * - `Ironic ARM CI`_
     - Feature
     - N/A
     - JayF, cid


Goals Details
=============

Ironic Documentation Improvements
---------------------------------
We will use the expertise of a professional docs writer to review all the
Ironic documentation and propose a list of actionable work that can be
performed to improve it.

We went through a first draft during the PTG, but we aim to finalize it and
complete the main changes during the Dalmatian cycle.

API response schema validation
------------------------------
The SDK team would like to generate OpenAPI schemas for core OpenStack
services and store them in-tree to ensure things are complete and up-to-date,
to avoid landing another large deliverable on the SDK team, and to allow
service teams to fix their own issues.

Eventually API documentation will switch from os-api-ref to a new tool
developed and owned by the SDK team, but this is a stretch goal.
When this happens, only the Sphinx extension itself will live out-of-tree
(like os-api-ref today).

The list of advantages includes:

- Having a mechanism to avoid accidentally introducing API changes.
- API documentation will be (automatically) validated.
- Highlight bugs and issues with the API.

The first steps will be writing a spec and showing a framework example for one
API.

Merging Inspector into Ironic
-----------------------------
Ironic Inspector was originally created as a service external to Ironic. Now,
it's used by a large number of Ironic operators around the world and should
be integrated with the primary service. This work has been progressing well.
We will continue to work on this until it is complete.

Redfish Virtual Media Push / UpdateService
------------------------------------------
These are actually two separate proposals with a lot in common, the final
goal being finding a way to facilitate virtual media booting and firmware
updates by using a "push" model.

We'll monitor the evolution of the Virtual Media Image Push proposal to the
DMTF community, and we'll consider the UpdateService already present in
the Redfish standard as a future alternative to be evaluated possibly
in the next cycle.

Virtual Media TLS Validation
----------------------------
Fujitsu has already proposed the validation of the TLS connection to the BMC
from Ironic, but we need to work on the other direction to validate the
virtual media TLS connection from the BMC to the Ironic services.

Slimming Down CI
----------------
Ironic is one of the major CI consumers in terms of resources.

During the Caracal cycle we've been able to reduce the number of jobs run
by the Ironic project, but we've also added some more. We came to the
conclusion that we need to take an approach where we stack more tests
in fewer jobs, trying to consolidate down jobs as much as possible
and minimize boot interface variation testing.

During the Dalmatian cycle we'll work first on trying to have Redfish and
ipmi in a single ironic job, and update the list of jobs to understand
where we can avoid duplication.

Tinycore Alternative for IPA ramdisk
------------------------------------
Tinycore has been the base for the Ironic Python Agent ramdisk (TinyIPA) used
in the tests in the Ironic CI for a long time. Unfortunately it has become less
and less tiny during the years, it lacks mirror https support, it uses a
lightweight libc which caused issues multiple times, and we need to
maintain a very specific series of scripts to be able to build it.

We'd like to explore alternatives to it, the main candidate being a gentoo
based image that has also support in DiskImage-Builder.

Ironic Guest Metadata from Nova
-------------------------------
We seek to unify the guest metadata sent to Ironic with that sent to libvirt.

Ironic currently only sets instance_info/instance_uuid, we want to expand this
to include project_id, user_id and flavor name, such that we are more
consistent with what is set in Libvirt guest metadata.

All of these fields are deleted when a node is undeployed, similar to
instance_uuid today. The project_id might in the future be used to help
with Ironic API RBAC.

Service Steps templates
-----------------------
We discussed this during the Caracal PTG in October, and as a result a
`spec was composed <https://review.opendev
.org/c/openstack/ironic-specs/+/890164>`_.

To move forward we need first to revise the spec with the latest outcome of
the discussion during the most recent PTG.

Networking: Project Mercury
---------------------------
Networking represents the next step for a truly standalone Ironic, and this
means finding alternatives to Openstack-integrated scenarios and therefore
to Neutron.

For complete usage in an enterprise use case, Ironic needs a means of
networking control, which today is manual unless in a fully integrated
OpenStack context. Furthermore, the OpenStack integrated context has some
known issues which makes it harder to adopt, so we plan to look for solutions
to this difficult operations problem during this development cycle.

Ironic ARM CI
-------------
OpenStack Ironic uses extensive CI testing to validate things work.

While we support ARM, and have reports in the field of it working, we do
not have any ARM representation, aside from unit tests, in our CI.

We aim to use ARM vms as we do for x86 vms and run one or more tempest
scenario jobs in Ironic CI.

Release Schedule
================
Contributors are reminded of our scheduled releases when they are choosing
items to work on.

The dates below are a guide; please view
https://releases.openstack.org/dalmatian/schedule.html for the full schedule
relating to the release and
https://docs.openstack.org/ironic/latest/contributor/releasing.html for Ironic
specific release information.

Bugfix Release 1
----------------
The first bugfix release is scheduled to happen around the first week of
June, 2024.

Bugfix release 2
----------------
The second bugfix release is scheduled to happen the first week of August,
2024.

Deadline Week
-------------
There are multiple deadlines/freezes the final week of:

* Final release of client libraries must be performed
* Requirements freeze
* Soft string freeze - Ironic services are minimally translated; this
  generally doesn't apply to our services, such as API and Conductor, but may
  impact us via other projects which are translated.
* Feature Freeze - Ironic does not typically have a feature freeze, but we may
  be impacted by other projects that do have a feature freeze at this date.

Final 2024.2 (Integrated) Release
---------------------------------
The final releases for Ironic projects in 2024.2 must be cut by September 27.
