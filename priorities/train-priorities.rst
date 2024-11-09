.. _train-priorities:

========================
Train Project Priorities
========================

This is a list of priorities the Ironic team is prioritizing for
Train development, in order of relative size and dependency addressing.
Note that this is not our complete backlog for the cycle, we still hope
to review and land non-priority items.

The primary contact(s) listed are responsible for tracking the status of
that work and herding cats to help get that work done. They are not the only
contributor(s) to this work, and not necessarily doing most of the coding!
They are expected to be available on IRC and the ML for questions, and report
status on the whiteboard_ for the weekly IRC sync-up. The number of primary
contacts is typically limited to 2-3 individuals to simplify communication.
We expect at least one of them to have core privileges to simplify getting
changes in.

.. _whiteboard: https://etherpad.openstack.org/p/IronicWhiteBoard

Goals
~~~~~

+---------------------------------------+-------------------------------------+
| Priority                              | Primary Contacts                    |
+=======================================+=====================================+
| `Deploy Steps`_                       | mgoddard, rloo                      |
+---------------------------------------+-------------------------------------+
| `Faster Deployments`_                 | TheJulia, dtantsur, stendulker      |
+---------------------------------------+-------------------------------------+
| `Bare metal program`_                 | TheJulia, janders, hodgepodge       |
+---------------------------------------+-------------------------------------+
| `Replacing WSME`_                     | mkrai, dtantsur, kaifeng, rpittau   |
+---------------------------------------+-------------------------------------+
| `Redfish Virtual Media`_              | etingof, rpittau                    |
+---------------------------------------+-------------------------------------+
| `Node retirement/quarantine`_         | arne_wiebalck, rpittau              |
+---------------------------------------+-------------------------------------+
| `Software RAID`_                      | arne_wiebalck, TheJulia             |
+---------------------------------------+-------------------------------------+


Inter-Project Goals
-------------------

+---------------------------------------+-------------------------------------+
| `State callbacks to nova`_            | arne_wiebalck, tssurya              |
+---------------------------------------+-------------------------------------+
| `SmartNIC Support`_                   | TheJulia, mkrai, moshele            |
+---------------------------------------+-------------------------------------+

Community Goals
~~~~~~~~~~~~~~~

+---------------------------------------+-------------------------------------+
| Goal                                  | Primary Contacts                    |
+=======================================+=====================================+
| `IPv6 support`_                       | TheJulia, derekh, dtantsur          |
+---------------------------------------+-------------------------------------+
| `Single document generation`_         | kaifeng, rpittau                    |
+---------------------------------------+-------------------------------------+


Details
~~~~~~~

Deploy Steps
---------------

As a general theme of work for the Train Cycle, the Ironic project community
wishes to break the monolithic deployment step into multiple deployment steps
which will further enable operators to easily create more complex
declarative deployments. This work also includes the the ability to trigger
steps through the agent, something that is not presently possible today.

Faster Deployments
------------------

A repeating theme from the operator community is for ways to speed up the
overall deployment time and enable faster time to deployment.

Ironic has completed some work in this area with the
`Fast Track Deployments <https://storyboard.openstack.org/#!/story/2004965>`_,
But there are other areas that can and should be explored by the community.

Bare metal program
------------------

The most powerful thing the Ironic community can do this cycle is not actually
in code, but in documentation. The recently created
`Bare Metal SIG <https://etherpad.openstack.org/p/bare-metal-sig>`_ is working
on creation of a white paper as part of the
`Bare Metal logo program <https://www.openstack.org/bare-metal/>`_, and needs
our help for stand-alone use cases.

Replacing WSME
--------------

Most long time contributors are aware of the headaches that WSME has brought
the community, along with the fact that many projects have migrated away from
it.

In order to move us to something which is supported by a broader community,
the consensus from the Train Project Teams Gathering, was to move ironic
towards using Flask. We'll start with re-working a single endpoint and
hopefully move through the rest of the API in a rapid fashion.

Redfish Virtual Media
---------------------

One of the most powerful features we can offer to operators with distributed
and edge ironic nodes is to offer booting the ramdisk via a generic
Redfish Virtual Media boot interface. This will enable greater compatibility
and once completed in-gate testing of virtual media relate scenarios in CI.

More information can be found in
`story 1526753 <https://storyboard.openstack.org/#!/story/1526753>`_.

This work is also a logical step towards the
`L3 based deployments specification <http://specs.openstack.org/openstack/ironic-specs/specs/approved/L3-based-deployment.html>`_.

Node retirement/quarantine
--------------------------

Larger operators with Ironic have found themselves approaching a quandry of
"What is the proper way to retire a machine from ironic?". A nearly identical
topic has arisen from the Telecom world seeking to represent the state of the
node more accurately with-in ironic as to represent if a machine is in a fault
state or questionable state under-going investigation.

With that being said, we feel that we need to extend our states and state
machine to better fit these overall themes.

Software RAID
-------------

Software RAID support has been long desired after by larger operators to help
manage COTS server hardware where Hardware RAID controllers are undesirable
or prohibitive. Work started during the Stein cycle to support this
functionality, and work continues! You can learn more in the
`Software RAID specification <https://specs.openstack.org/openstack/ironic-specs/specs/not-implemented/software-raid.html>`_.

State callbacks to nova
-----------------------

One of the headaches and performance issues for larger operators is
the nature of power synchronization when nova is in use, as nova
performs a large number of API calls to update its database with
node power state. At larger scales, this is inefficient and results
in the power state nova having on record from being out of state
from ironic as the source of truth.

Conversely, nova presently assumes that it is always authoritative
in regards to power states. This work will allow ironic to inform
nova of the new power state such that nova does not attempt to
reset the power state.

While this is largely an effort in the nova project, we need to be
aware and attempt to support this work to move forward.
The nova-spec document can be found in review as
`change 636132 <https://review.opendev.org/#/c/636132/>`_.

SmartNIC Support
----------------

Smartnics complicates ironic as the NIC needs to be programmed with the
power in a state such that the configuration on the NIC can be changed.

While the work in Ironic was completed this past cycle ahead of expectations.
Work is on-going in Neutron this cycle to merge the functionality to make
this available to users.

The story can be found at `story 2003346 <https://storyboard.openstack.org/#!/story/2003346>`_.

IPv6 support
------------

The Technical Committee is presently finalizing a goal for the Train cycle for
projects to support and test IPv6-only deployments.

More information can be found in `change 657174 <https://review.opendev.org/#/c/657174>`_.

Single document generation
--------------------------

A goal from the Technical Committee is for each project to support the
generation of a single PDF document for the whole of the documentation tree.

More information on this community goal can be in governance
`pdf doc generation goal <https://governance.openstack.org/tc/goals/train/pdf-doc-generation.html>`_
documentation.
