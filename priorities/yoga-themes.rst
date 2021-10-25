.. _yoga-themes:

===================
Yoga Project Themes
===================

Themes
======


.. list-table:: Yoga Themes
   :widths: 50 40 10
   :header-rows: 1

   * - Theme
     - Primary Contacts
     - Target
   * - `ARM effort`_
     - rpittau
     -  1
   * - `Redfish improvements`_
     - dtantsur
     -  2
   * - `Nova improvements`_
     - TheJulia
     -  3
   * - `Attestation Interface`_
     - sdanni, lmcgann, TheJulia, iurygregory
     -  2
   * - `Enhancing storage cleaning`_
     - janders
     -  3
   * - `Start Merging Ironic Inspector in Ironic`_
     - tkot, dtantsur
     -  3
   * - `Drop privileged operations from Ironic`_
     - iurygregory, dtantsur, rpittau
     - 2
   * - `Make it easier to deploy and operate`_
     - dtantsur, TheJulia
     -  3
   * - `Tempest on bifrost`_
     - iurygregory
     -  2
   * - `Troubleshooting FAQ/Guide`_
     - Ironic contributors
     -  3
   * - `RBAC on ironic-tempest`_
     - TheJulia
     -  3


Schedule Structure
------------------

Sprint 1
++++++++

The release for this sprint will happen on the first week of
December (06 - 10).

Sprint 2
++++++++

The second release is scheduled to happen on the first week of
February (01-04).

Sprint 3
++++++++

This is the release that will create the stable/yoga branch,
according to the release team schedule we have:

* non-client libraries: Feb 14 / Feb 18.
* client libraries: Feb 22 / Feb 25.
* final release: Mar 21 / Mar 25.


Goals Details
=============


ARM effort
----------

The interest in ARM Hardware has grown, since the opendev infra has some
resources we will start building ramdisk image for this architecture.
We will have images published for the architecture and having bifrost testing.


Attestation Interface
---------------------

Recent interest in having an integration with `Keylime <https://keylime.dev/>`_
has brought forth interest in resurrecting the `attestation interface <https://review.opendev.org/576718>`_
which was proposed some time ago to provide an integration point for Ironic
to have the understanding and capability to take the appropriate action
in the event a machine has been identified to no longer match the expected
profile.


Enhancing storage cleaning
--------------------------

We want to improve storage cleaning in hybrid scenarios, the proposal is
described  in `Improve efficiency of storage cleaning in hybrid NVMe+other
storage configurations <https://storyboard.openstack.org/#!/story/2009264>`_.


Tempest on bifrost
------------------

The idea here is that we can improve bifrost so we can run tempest, having this
can reduce the dependency on devstack in our CI and also for 3rd Party CI.


Start Merging Ironic Inspector in Ironic
----------------------------------------

Based on the PTG discussions, we will provide a new home for introspection
rules using a `new format
<https://owlet.today/posts/miniscript-and-future-of-introspection-rules/>`_
(still need to be discused with the community), we also want to add the
`ability to generate ironic-inspector iPXE scripts
<https://storyboard.openstack.org/#!/story/2009294>`_.


Troubleshooting FAQ/Guide
-------------------------

We should always engage in trying to improve the user experience,
this is something that we as a community should improve.


RBAC on ironic-tempest
----------------------

We've reached consensus we want to add an additional set of tests in an
attempt to help provide additional guards in the terms of
"this should never work". The prime purpose of such is to help the
community and operators identify major issues and potential
configuration issues and have comprehensive and exhaustive testing.


Redfish improvements
--------------------

Refactor sushy to add features/deprecations for newer Redfish standards.
Some improvements already includes: switching constants to python enum,
auto-generation of code for enums.


Nova improvements
-----------------

With twenty percent of OpenStack compute deployments leveraging Ironic as
their hypervisor, it is critical for the ironic community to take the needs
and issues experienced by those operators critical in the interaction between
Nova and Ironic. Most of the issues revolve around attempting to fit a model
of bare metal into a model of virtual machines. Obviously, this has issues,
but we will be spending some bandwidth to improve the overall experience in
an attempt to make things better.


Drop privileged operations from Ironic
--------------------------------------

Given the memory impact that the `oslo.privsep` could cause we decided
to drop privileged operations from Ironic, the work will be trackted
in the `Story 2009704 <https://storyboard.openstack.org/#!/story/2009704>`_.


Make it easier to deploy and operate
------------------------------------

It will consist of improvements that aim to make the operator life easier,
like: removing the need for some manual commands during installation,
automatic movement of machines through the workflow.
