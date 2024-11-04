.. _2025-1-work-items:

=========================
2025.1 Project Work Items
=========================
The latest virtual Project Team Gathering happened in October 2024. Ironic
developers and operators discussed many different potential features and
other ongoing work for the 2025.1 (Epoxy) release. These discussions are
memorialized in this document, providing a list of the main priorities for
the next development cycle. For more information please look at the link for
each topic or contact the Ironic team on IRC.

Ironic contributors are busy; they work spanning multiple open source projects,
and have varied downstream responsibilities. We cannot guarantee any or all
planned work will be completed, nor is this a comprehensive list of
everything Ironic may do in the next six months.

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

.. list-table:: 2025.1 Work Items
   :widths: 50 20 20 10
   :header-rows: 1

   * - Name
     - Category
     - Tracking
     - Champions

   * - `Redfish Console Support`_
     - Feature
     - `Redfish console support <https://bugs.launchpad.net/ironic/+bug/2086715>`_
     - TheJulia, JayF

   * - `Support OCI as a container for image files`_
     - Feature
     - `Support OCI formatted URLs for artifact retrieval <https://launchpad.net/bugs/2085565>`_
     - TheJulia, help wanted

   * - `Support container-based deployment via bootc`_
     - Feature
     - `Deployment of bootable containers <https://launchpad.net/bugs/2085801>`_
     - TheJulia

   * - `Networking: Project Mercury`_
     - Feature
     - `Mailing list thread about new working group <https://lists.openstack.org/archives/list/openstack-discuss@lists.openstack.org/thread/S4OZH7PC3NAZC2HXBGAQ7YSJUOPFKBW3/#WS5VO2PIXW42N3LQ2A6UD3WQU5YVZ56X>`_
     - BM Networking WG

   * - `Inspection hooks for Out-of-Band inspection`_
     - Feature
     - `Standardize inspection hooks/data <https://launchpad.net/bugs/2086723>`_
     - cardoe

   * - `kea DHCP backend`_
     - Feature
     - `Add a kea DHCP backend <https://launchpad.net/bugs/2081847>`_
     - cid

   * - `In-band Disk Encryption`_
     - Feature
     - `Root device partition encryption (LUKS) <https://bugs.launchpad.net/ironic/+bug/2073762>`_
     - adam-metal3

   * - `Container-based IPA steps`_
     - Feature
     - `Reserved step name format for agent container launch <https://bugs.launchpad.net/ironic/+bug/2059948>`_
     - JayF

   * - `Improve OEM handling in Sushy`_
     - Maintenance/Feature
     - `Sushy to include OEM support <https://bugs.launchpad.net/ironic/+bug/2086725>`_
     - cardoe, dtantsur

   * - `Support NC-SI Hardware`_
     - Feature
     - `Hardware that cannot be powered off <https://launchpad.net/bugs/2077432>`_
     - dtantsur

   * - `API response schema validation, OpenAPI Spec`_
     - Maintenance
     - `Add OpenAPI support for Ironic via codegenerator <https://launchpad.net/bugs/2086121>`_
     - stephenfin, adammcarthur5

   * - `Adopt pre-commit for linting in Ironic projects`_
     - Maintenance
     - N/A
     - JayF

   * - `Tinycore Alternative for IPA ramdisk`_
     - Maintenance
     - N/A
     - JayF

   * - `Retire ironic-lib`_
     - Maintenance
     - `deprecate and retire ironic-lib <https://bugs.launchpad.net/ironic/+bug/2086672>`_
     - JayF, dtantsur

Goals Details
=============

Redfish Console Support
-----------------------
Ironic has had a console interface with basic support for IPMI-based serial
consoles for years. However, most machines now expose graphical KVMIP-based
consoles via redfish interface. The Ironic team will work on adding support
for these consoles in the coming months.

Support OCI as a container for image files
------------------------------------------
OCI image urls (``oci://``) are getting more common in clouds, especially
mixed clouds including both kubernetes and OpenStack. Ironic plans to
implement support for fetching images from a container registry using this
URL scheme -- alongside existing support for ``http``, ``https`` and
``glance``.

Support container-based deployment via bootc
--------------------------------------------
Tooling has emerged in the cloud ecosystem allowing a container to be
adapted for running on bare metal. We plan to implement one of these tools,
``bootc``, as an additional deployment option over the coming months.

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

There are no specific actions beyond further design discussion in the working
group planned for this cycle.

Inspection hooks for Out-of-Band inspection
-------------------------------------------
With the migration of inspection functionality into Ironic directly, we now
have an opportunity to bridge some feature gaps between out-of-band (BMC)
and in-band (agent) inspection methods. This feature will enable hooks to
run based on out of band inspection data, similar to the existing support
for in-band inspection data.

kea DHCP backend
----------------
Ironic currently has a "single point of failure" dependency in ``dnsmasq``.
The Ironic team will resolve this by adding support for an additional
DHCP interface which will interface with ``kea`` DHCP server. This task
is Ironic-specific; however the Ironic team also intends on specifying and
implementing ``kea`` support in ``neutron-dhcp-agent`` as a next step.

In-band Disk Encryption
-----------------------
Linux servers frequently use disk encryption technology known as "Linux
Unifed Key Setup", (LUKS). The proposed implementation will allow operators
to optionally enable data encryption at rest utilizing LUKS with a TPM-stored
key.

Container-based IPA steps
-------------------------
Ironic Python Agent has long supported customization via HardwareManager,
however, building and testing custom steps and HardwareManagers can be time
consuming. With this change, the Ironic team will simplify agent customization
by permitting operators to run steps out of containers, and modify them without
being forced to rebuild their ramdisk.

Improve OEM handling in Sushy
-----------------------------
Currently, sushy has minimal support for OEM endpoints, and historically
required implementations of them -- e.g. ``sushy-oem-drac`` -- to remain out
of tree. At the recent PTG, the Ironic team formed a consensus to adopt OEM
logic directly into Sushy, simplifying our codebase and making it easier to
support quirky vendor implementations of Redfish and potentially enabling
utilization of OEM extensions.

Support NC-SI Hardware
----------------------
Some hardware, such as that implementing the DTMF
`NC-SI <https://en.wikipedia.org/wiki/NC-SI>`_ specification, may not support
power off. The Ironic team is working to support this hardware, and other
hardware that may lack the ability to power off explicitly.

API response schema validation, OpenAPI Spec
--------------------------------------------
The Ironic team is joining an effort by the OpenStack SDK team to generate
OpenAPI specification documents from API code. This will ensure our
API documentation will match the code by generating it from the code.
As part of this work, the Ironic team will be refactoring handling of
API microversions to help with the generation process and improve code
readability.

Adopt pre-commit for linting in Ironic projects
-----------------------------------------------
Many OpenStack, and python projects in general, are adopting
`pre-commit <https://pre-commit.com>`_ to run the linting in their CI. The
Ironic team is following this pattern, and will be consolidating lint jobs
across all Ironic projects to be driven by pre-commit. This will also enable
developers to enable a hook in their local git checkouts to have files
automatically linted on save. We expect this to lower CI utilization by
lessening the amount of lint failures on initial patch pushes and by
consolidating multiple separate jobs -- e.g. ``bandit``, ``codespell``,
and ``hacking`` all into a single test job.

Tinycore Alternative for IPA ramdisk
------------------------------------
Tinycore has been the base for the Ironic Python Agent ramdisk (TinyIPA) used
in the tests in the Ironic CI for a long time. Unfortunately it has become less
and less tiny during the years, it lacks mirror https support, it uses a
lightweight libc which caused issues multiple times, and we need to
maintain a very specific series of scripts to be able to build it.

We'd like to explore alternatives to it, the main candidate being a gentoo
based image that has also support in DiskImage-Builder.

Retire ironic-lib
-----------------
Ironic-lib was originally created to enable sharing of deployment code
between the now-obsolete ``iscsi`` driver and ``direct`` driver. With the
``iscsi`` driver removed, keeping the minimal shared code between IPA and
Ironic is no longer worth the effort of managing an additional, separate
project. The Ironic team will remove uses of the ironic-lib library, and
we expect its final release in this cycle.

Release Schedule
================
Contributors are reminded of our scheduled releases when they are choosing
items to work on.

The dates below are a guide; please view
https://releases.openstack.org/epoxy/schedule.html for the full schedule
relating to the release and
https://docs.openstack.org/ironic/latest/contributor/releasing.html for Ironic
specific release information.

Bugfix Release 1
----------------
The first bugfix release is scheduled to happen around the first week of
December, 2024.

Bugfix release 2
----------------
The second bugfix release is scheduled to happen the first week of February,
2024.

Deadline Week
-------------
There are multiple deadlines/freezes in the final weeks of the release,
please refer to the release schedule for exact dates.

Final 2025.1 (Integrated) Release
---------------------------------
The final releases for Ironic projects in 2025.1 must be cut by March 24.
