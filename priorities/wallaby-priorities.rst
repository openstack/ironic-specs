.. _wallaby-priorities:

==========================
Wallaby Project Priorities
==========================

For the maximum irony!

Of course, we have wants, desires, needs, and hopes. The intention of
this document is to convey the priorities for and amongst the community
in a published way. Not all of these goals, efforts, and ultimately the
features may reach the Wallaby release, nor is it a complete list. It
is the list that makes sense to raise visibility of.

This is a list of goals the Ironic team is prioritizing for
the Wallaby development cycle, in order of relative size with context of
our dependencies and roughly referenced against the anticipated sprints
and release cycle for the Wallaby development cycle.

The primary contact(s) listed are responsible for tracking the status of
that work and herding cats to help get that work done. They are not the only
contributor(s) to this work, and not necessarily doing most of the coding!
They are expected to be available on IRC and the ML for questions, and report
status on the whiteboard_ for the weekly IRC sync-up. The number of primary
contacts is typically limited to 2-3 individuals to simplify communication.
We expect at least one of them to have core privileges to simplify getting
changes in.

.. _whiteboard: https://etherpad.opendev.org/p/IronicWhiteBoard

.. note::
   In the interests of keeping our work fun and enjoyable, while continuing
   to foster community engagement, this document may have a bit of silliness
   intertwined. It is all okay, we haven't lost all of our sanity, yet.

Goals
=====

+-------------------------------------+-------------------------+-----------+
| Priority                            | Primary Contacts        | Target    |
+=====================================+=========================+===========+
| `Not getting (more) insane`_        | Ironic Developers       | Theme     |
+-------------------------------------+-------------------------+-----------+
| `Replacing WSME`_                   | stevebaker              | Sprint 1  |
+-------------------------------------+-------------------------+-----------+
| `Default to GPT`_                   | TheJulia                | Sprint 1  |
+-------------------------------------+-------------------------+-----------+
| `Make UEFI happy`_                  | dtantsur, TheJulia      | Sprint 1  |
|                                     | rpittau                 |           |
+-------------------------------------+-------------------------+-----------+
| `NVMe Secure Erase`_                | janders, dtantsur,      | Sprint 1  |
|                                     | rpittau                 |           |
+-------------------------------------+-------------------------+-----------+
| `History favors the bold`_          | kaifeng, arne_wiebalck  | Sprint 2  |
+-------------------------------------+-------------------------+-----------+
| `Redfish RAID`_                     | bdodd, ajya, TheJulia   | Sprint 2  |
+-------------------------------------+-------------------------+-----------+
| `Move to oslo.privsep`_             | iurygregory, rpittau    | Sprint 2  |
+-------------------------------------+-------------------------+-----------+
| `Configuration molds`_              | rpioso, ajya            | Sprint 3  |
+-------------------------------------+-------------------------+-----------+
| `Anaconda deployment`_              | zer0cool, rpittau       | Sprint 3  |
+-------------------------------------+-------------------------+-----------+
| `Redfish Interop Profile`_          | arne_wiebalck, rpioso,  | Sprint 3  |
|                                     | rpittau                 |           |
+-------------------------------------+-------------------------+-----------+
| `Snapshots`_                        | kaifeng, TheJulia       | Future    |
+-------------------------------------+-------------------------+-----------+
| `Security Interface`_               | kaifeng, ljmcgann,      | Future    |
|                                     | rpittau                 |           |
+-------------------------------------+-------------------------+-----------+
| `Boot from URL`_                    | Multiple contributors   | Future    |
+-------------------------------------+-------------------------+-----------+

Schedule Structure
------------------

The indicator for this schedule is to help provide those reviewing this
document a rough idea of when one may anticipate functionality to merge and
be released. Things may merge sooner or later.

Sprint 1
++++++++

We anticipate the release from the first sprint of the Wallaby cycle to
be during the week of December 14th.

Sprint 2
++++++++

The second sprint starts after the first release and we anticipate the
release marking the end of the second sprint to be the week of February 8th,
2021.

Sprint 3
++++++++

After the second sprint release, the anticipated release date is expected
the week of April 5th, 2021.

Theme
~~~~~

General thematic work for general improvement in an area fall under the
classification of theme. Largely this is work that may run the course of
an entire release cycle or longer, where small incremental improvements
or related work takes place.

Future
~~~~~~

Items in the future which we as a community do not have a firm idea of
*when* this may merge. Being on this list does express that interest exists
in the community to push this effort forward during the cycle.

Goals Details
=============

In no particular order...

Not getting (more) insane
-------------------------

Ironic is finding increased adoption in use and naturally contributions
as needs evolve and new requirements are identified. This is a natural
progression. The key that we must keep in mind is that WE can only do
so much. We are not super-humans and super human efforts consume the
spoons we need to ultimately take over the world.

With this in mind, we must carefully chart our future course.
Ultimately we should expect a re-evaluation of our testing matrix,
and a focus on what makes the most sense.

.. warning:: The effectiveness of super-human dresses has not been
             established in a clinical setting. Special thanks goes to
             kaifeng for reminding us that we all need to smile. :)

Default to GPT
--------------

Ironic supports a number of ways to deploy a physical machine. One of these
methods includes use of a partition image. This was defaulted to use a
BIOS partition format. But moving forward we need to change to GPT
as it is more in line with using UEFI boot when writing partition images
for local boot.

Make UEFI happy
---------------

UEFI and ultimately Secure Boot being the most community relevant features
of UEFI, require doing things in particular patterns which were not well
understood nor well documented when the features were ultimately added.

At the same time, there is always a technology adoption lag in data centers
and we are beginning to be exposed to various cases and issues where current
support is sub-optimal. Ultimately we need to improve this by making Ironic
smarter.

At the same time, we likely need to look at making Secure Boot enforceable
across drivers. Not all vendors support Secure Boot, but the data center
operator interest seems to be substantial at this time.

History favors the bold
-----------------------

To boldly go forth, we must provide more insight into error history of nodes.
The concept of adding support to record the important events and surface them
in a human parsable way has long been under discussion and been a desired
feature. It is time we make it happen.

`Node history <https://review.opendev.org/652811>` is presently in the
review process with strong support from the Project Teams Gathering.

Anaconda deployment
-------------------

Some operators are invested in Anaconda configurations and using Anaconda
kickstart files to facilitate deployments. More information can be found in
`anaconda deployment specification <https://review.opendev.org/748503>`_.

Redfish RAID
------------

Support for using `Redfish to configure RAID <https://storyboard.openstack.org/#!/story/2003514>`_
devices was proposed during the Victoria development cycle but was still in
development at the end of the cycle. We hope to see this merged into Ironic
during the Wallaby cycle.


NVMe Secure Erase
-----------------

Ironic needs to do better with more advanced storage devices where
secure erase and discard are `supported with NVMe devices <https://storyboard.openstack.org/#!/story/2008290>`_.
The Project Teams Gathering yielded discussion of this, and the possibility of
improved support seems likely in the near future.

Snapshots
---------

A major compatibility gap with Nova's Compute interaction with VMs that
is lacking with Ironic baremetal nodes is support for Snapshots.
This is a bit of a complex problem which may require an iterative
development process. This is presently under discussion and the community
is interested in the functionality. Information about this feature can
be found in the `snapshot specification document <https://review.opendev.org/746935>`_.

Configuration Molds
-------------------

Configuration molds is the name being given to the conceptual feature of being
able to capture the configuration of a machine, and being able to stamp it out
across multiple machines. While Ironic has many of these primitives, we do not
have the tooling to help enable the easy act of stamping the configuration
as a single action. More information can be found in the `change 740721
<https://review.opendev.org/740721>`_.

Move to oslo.privsep
--------------------

This effort is being carried over from the prior cycle as it became clear the
work required would take longer than time existed for us to move the changes
forward. More information can be found in the `migrate to privsep goal <https://governance.openstack.org/tc/goals/proposed/migrate-to-privsep.html>`_
documentation.

Replacing WSME
--------------

This work area was started in the Victoria cycle with the initial foundation
being put in place, and now it is time to move forward on merging this work.

Most long time contributors are aware of the headaches that WSME has brought
the community, along with the fact that many projects have migrated away from
it.

In order to move us to something which is supported by a broader community,
the consensus from the Train Project Teams Gathering, was to move Ironic
towards using Flask. We'll start with re-working a single endpoint and
hopefully move through the rest of the API in a rapid fashion.

Redfish Interop Profile
-----------------------

Started in the Victoria cycle, the purpose of the interop profile is to
declare what is required of a Redfish BMC for our driver to support
appropriate management of a baremetal node.

The Redfish Forum has an `interop validator utility <https://github.com/DMTF/Redfish-Interop-Validator>`_
mechanism to allow BMC vendors to validate their implementation of the
Redfish API against the profile that represents compatability with Ironic.

This work will also enable consumers of hardware to leverage the profile
to make sure the hardware they intend to buy works with Ironic or even
make this part of their tendering/purchase process.

Security Interface
------------------

Recent interest in having an integration with `Keylime <https://keylime.dev/>`_
has brought forth interest in resurecting the `security interface <https://review.opendev.org/576718>`_
which was proposed some time ago to provide an integration point for Ironic
to have the understanding and capability to take the appropriate action
in the event a machine has been identified to no longer match the expected
profile.

This interface will allow easy adoption of a keylime integration which
should allow ironic to halt the return to available inventory of machines
which have had unexpected modifications made to firmware.

Boot from URL
-------------

This is a long sought after feature, and one more likely to surface as time
goes on. Part of the conundrum is the multiple routes possible in what
is interpreted as Boot from URL. Luckily Redfish has defined a standard
interface to assert the configuration via the BMC.

At a minimum this cycle, we would like to make a step forward in attempting
to support this funcitonality such that we can support it when vendors
implement the feature outside of vendor OEM specific mechanisms.
