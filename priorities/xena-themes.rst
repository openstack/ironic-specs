.. _xena-themes:

===================
Xena Project Themes
===================


"Alala" [#f1]_

During the `Wallaby development cycle <https://specs.openstack.org/openstack/ironic-specs/priorities/wallaby-priorities.html>`_,
we had a goal in which "History favors the bold". It was clear early
on in that development cycle that we just had too much work coming up
for contributors, that it simply was not going to be gotten to during
the cycle. Unfortunately, it happens and in the grand scheme of things
it is good that the community recognized it simply did not have the
capacity to push it forward.

It is hard lesson to learn. But an important lesson.

The theme of that specific work is still true. History does favor the bold.
And while we shouldn't have a war cry, much less ever declare war. We should
be tactical in our thinking, and execution to meet everyone's needs.
Be it operator, contributor, or ultimately end user.

And so, it seems the best path is to be bold. For us to charge forth!
Declare our vision, and spread the song of our successes.
Of course, needs change. Requirements change. But underlying themes
should be remembered.

Purpose
=======

Every deployer and developer has different wants, desires, needs, and hopes.
The intention of this document is to lay out a consensus of the community as
to what work we feel is important for the release.
A work item noted in this document will get more reviews and support
from the community than new or unprioritized work, but there's no guarantee
they'll get done in the Xena cycle, or at all.

This is a list of goals the Ironic team is prioritizing for
the Xena development cycle, in order of relative size with context of
our dependencies and roughly referenced against the anticipated sprints
and release cycle for the Xena development cycle.

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


Shifting to a Theme
===================

The Ironic community reached consensus during the Xena PTG that our
choice of word to describe things needed to be revised. Specifically,
one person's priority is not another person's priority, and priorities
can shift rapidly for individual contributors based upon present
needs of their employers.

And so we seemed to reach consensus that the word was more along the
line of ``themes`` instead of ``priorities``. We can have a higher level
theme for the release or cycle but then we can have some specific smaller
themes which may, or may not make it into the release. From the outside,
this may seem like a drastic change, but this is more in alignment with
existing project practice and the realities we live with.

Going back to the `Purpose`_ of this document, what we document here is our
consensus forecast. And is subject to change. Consensus may shift after the
fact, but it is of the utmost importance to have a mutually agreeable starting
point, which this document provides.

Goals
=====

+-------------------------------------+-------------------------+-----------+
| Priority                            | Primary Contacts        | Target    |
+=====================================+=========================+===========+
| `Being Bold`_                       | Ironic Developers,      | Theme     |
|                                     | Baremetal SIG           |           |
+-------------------------------------+-------------------------+-----------+
| `Finishing anaconda deployment`_    | zer0cool, rpittau       | Sprint 1  |
+-------------------------------------+-------------------------+-----------+
| `iSCSI deployment removal`_         | dtantsur                | Sprint 2  |
+-------------------------------------+-------------------------+-----------+
| `Database performance`_             | TheJulia                | Sprint 2  |
+-------------------------------------+-------------------------+-----------+
| `Node error history`_               | kaifeng, arne_wiebalck  | Sprint 2  |
+-------------------------------------+-------------------------+-----------+
| `Enhancing storage cleaning`_       | janders                 | Sprint 2  |
+-------------------------------------+-------------------------+-----------+
| `Move to oslo.privsep`_             | iurygregory, rpittau    | Sprint 2  |
+-------------------------------------+-------------------------+-----------+
| `Virtual Media visibility`_         | iurygregory, dtantsur   | Sprint 2  |
+-------------------------------------+-------------------------+-----------+
| `Driver structure and model`_       | TheJulia, TheJulia      | Sprint 3  |
+-------------------------------------+-------------------------+-----------+
| `Finishing Secure RBAC`             | TheJulia                | Sprint 3  |
+-------------------------------------+-------------------------+-----------+
| `Snapshots`_                        | kaifeng, TheJulia       | Future    |
+-------------------------------------+-------------------------+-----------+
| `Security Interface`_               | kaifeng, ljmcgann,      | Future    |
|                                     | rpittau, sdanni         |           |
+-------------------------------------+-------------------------+-----------+
| `Keylime`_                          | ljmcgann, sdanni        | Future    |
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

We anticipate the release from the first sprint to be on the week of
May 31st, 2021. This is six weeks after the initial planning week.

Sprint 2
++++++++

The second sprint is anticipated to start the week of June 7th, 2021 and
proceed until July 19th, 2021. This is approximately 7 weeks for the second
sprint.

Sprint 3
++++++++

After the second sprint release, The third sprint is anticipated to end the
week of September 6th. Features and Driver enhancements which are not
"review ready" will not be considered to hold the release on. This is
anticipated to be a window of seven weeks. In essence, this can be viewed
as a "freeze" but is more of a "the release train must depart on time"
model.

Anticipated release date is September 9th.

Post Release Sprint
+++++++++++++++++++

After the release, it seems to be a good time to ensure we've taken of needful
and any necessary backports, along with bug triaging, and resolution of any
"low-hanging-fruit" bugs with major impact. Example being documentation not
rendering configuration options, or deployments fail under Y conditions.

This time also aligns with the general community shift after releases, where
people tend to take some time off to recharge before planning, and the planning
steps and discussions take place.

This sprint is anticipated to end October 8th, 2021. Additional releases may
take place to address bug fixes that need to be backported during this window.
The following week is anticipated to be the
`Project Teams Gathering <http://ptg.openstack.org/>`_ and the start of the
following development cycle.

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

Being Bold
----------

In alignment with our general theme of alala_, it is important for us to
be bold, and acknowledge when we do and do not have capacity to push
things forward. At the same time, we need to broadcast out. We need to
speak of our successes. Our wins... and failures. And everything in between.

This visibility, can unfortunately make some of us uncomfortable, but it
takes many forms. Mentorship, Public Speaking, and engagement outside
of your day to day primary mission focus. This is also how we grow.
How we grow ourselves, along with the community.

So be bold, think alala_ and go forth and cross the division. Do the thing
which is uncomfortable. Propose the crazy idea. And when the times permit
it, get on stage at a local conference, and speak of the experience.

For history favors the bold.

Of course, we also want to keep our santiy, or at least some of it.

Database Performance
--------------------

During the Xena development cycle, the community driven Secure RBAC work
added additional database interactions with-in the API which has the general
effect of increasing load upon the database when ``project`` scoped tokens
request items. As this is the new direction for access control in OpenStack,
we need to make sure we are not making this a burden for operators with API
access activity. Since some configuration patterns, could result in even more
activity, depending on how the end operator chooses to configure their
deployment.

Also during the cycle, one of the larger operators encountered a thundering
herd situation. In essence, the database could not keep up. We need to try
and be smart to prevent some of these situations from happening, or at least
minimize the impact as many operators now also launch services using
Kubernetes, which can result in all services coming online at the same
moment, an aspect which aggrevates a thundering herd.

It should be noted, not all of this is intended to be feature work, as some
of the work product will end up being backported to the Wallaby release which
may take slightly different approaches.

This work may also extend into APIs for bulk data, but this ultimately also
requires additional information before we can make such a decision.

Finishing Secure RBAC
---------------------

The community driven Secure RBAC work which has really been underway community
wide for a number of years made a large push, also community wide for projects
to implement and adopt new policies whilst deprecating their old policies.

We anticipate we will seek to remove the old policies during the Xena cycle,
however we need to consider `Database Performance`_ and needs of the operator.

Secure RBAC is also a fairly new configuration, we may find cross-service bugs
or issues, that require additional work. This ultimately was somewhat expected.

Node error history
------------------

To boldly go forth, we must provide more insight into error history of nodes.
The concept of adding support to record the important events and surface them
in a human parsable way has long been under discussion and been a desired
feature. It is time we make it happen.

This work was started during the Wallaby development cycle but we did not have
the capcity to move it forward last cycle. This cycle we ought to finish it.

Finishing anaconda deployment
-----------------------------

Some operators are invested in Anaconda configurations and using Anaconda
kickstart files to facilitate deployments. More information can be found in
`anaconda deployment specification <https://review.opendev.org/748503>`_.

This work started during the Wallaby development cycle and continues. It
should be wrapped up early in the first sprint as a dependency was identified
too late in the Wallaby development cycle to be addressed until Xena.

Snapshots
---------

A major compatibility gap with Nova's Compute interaction with VMs that
is lacking with Ironic baremetal nodes is support for Snapshots.
This is a bit of a complex problem which may require an iterative
development process. This is presently under discussion and the community
is interested in the functionality. Information about this feature can
be found in the `snapshot specification document <https://review.opendev.org/746935>`_.

Move to oslo.privsep
--------------------

This effort is being carried over from the prior cycle as it became clear the
work required would take longer than time existed for us to move the changes
forward. More information can be found in the `migrate to privsep goal <https://governance.openstack.org/tc/goals/selected/wallaby/migrate-to-privsep.html>`_
documentation.

Security Interface
------------------

Recent interest in having an integration with `Keylime <https://keylime.dev/>`_
has brought forth interest in resurrecting the `security interface <https://review.opendev.org/576718>`_
which was proposed some time ago to provide an integration point for Ironic
to have the understanding and capability to take the appropriate action
in the event a machine has been identified to no longer match the expected
profile.

Keylime
-------

The `Keylime project <https://keylime.dev/>`_ is an open source system
security and attestation framework which was originally developed at
`MIT Lincoln Laboratory <https://www.ll.mit.edu>`_ and has evolved in
close contact with the Ironic community over the past few years while
it has become a project on it's own.

Keylime helps ensure that the underlying hardware of a deployment has
not been tampered with, and that ultimately the system is running the
firmware and software expected. It does this with low level Trusted
Platform Module integration, and a set of services that an operator
may choose to deploy.

Ultimately having support for integration helps ensure a greater level
of operational security by helping operators identify and isolate
machines which have had malicious actions taken on them and also
potentialy help increase the level of security of the deployment
process by helping identify if a malicious actor has attempted to
modify a running ramdisk's contents.

This work requires the implementation of the `Security Interface`_.

Boot from URL
-------------

This is a long sought after feature, and one more likely to surface as time
goes on. Part of the conundrum is the multiple routes possible in what
is interpreted as Boot from URL. Luckily Redfish has defined a standard
interface to assert the configuration via the BMC.

At a minimum this cycle, we would like to make a step forward in attempting
to support this functionality such that we can support it when vendors
implement the feature outside of vendor OEM specific mechanisms.

Basic information on the hope of this can be found at `HTTPClient Booting <https://storyboard.openstack.org/#!/story/2003934>`_.
Additional prior art can be found in the ``ilo`` hardware type as well, but
the hope is to support this genericly, if at all possible.

Virtual Media Visibility
------------------------

One of the biggest headaches for the operator and developer community, when it
comes to virtual media, is the nature of the integration point in firmware.

This feature set involves a complex interaction of open source software with
semi-proprietary or standards based APIs over an HTTP connection. Often this
is greatly complicated by the teams which develop the firmware often are on
entirely separate teams inside organizations which doesn't have the level of
insight that the community has. Ultimately, the result is sometimes virtual
media breaks.

The idea is simple. Identify if the machine is *known-good* for virtual media
and expose that in some way/shape/form, if appropriate, along with what is
historically treated as tribal knowledge in terms of workarounds or potential
fixes. This may be contentiouns to some, because perceptions do matter, but
so does usability and we need to somehow balance this ever evolving pain
point.

Driver structure and model
--------------------------

Our driver model has the advantage of operators being able to be very specific
and ultimately have some level of knowledge or trust in the behavior of the
node. Except, that power also comes with sources of confusion, and some pain
points which are related where some overlapping code *can* result in
unintended consequences.

We recognize the need to try and build consensus on one or more improvements
to help alleviate some of these issues and possibly provide a forward path,
while still providing a level of flexibility.

This is largely only anticipated to be a specification document this cycle,
which may only be used to settle on consensus for policy moving forward.
This may also drive future code enhancements, but we won't know until
consensus is reached on this topic.

Related to part of this is `story 2008804 <https://storyboard.openstack.org/#!/story/2008804>`_
and `story 2005328 <https://storyboard.openstack.org/#!/story/2005328>`_
which propose some ideas related to this.

Enhancing storage cleaning
--------------------------

Storage is a complex issue with Bare Metal. In essence two different schools
of thought exist which support operators. The first is where we want to
absolutely make sure nothing is still present anywhere on the machine. Some
operators need this level of cleanliness. Where as others just need to know
they can safely re-deploy on to the machine without repercussions.

Also, as time shifts, so do our positions and takes, so we want to make
metadata wipe more akin to help provide a greater level of assurance to
the "just want to be able to reuse my machine safely" group of operators.

This may result in some changes to how Secure Erase/Format operations are
handled, as well as additional portions of data to be removed from disks to
aid in re-use. Specifically for operators with Ceph.

iSCSI deployment removal
------------------------

The first deployment method in Ironic, is also one of the more
"we just need to trust" the underlying mechanisms and hope nothing happens
sort of drivers. It turns out those substrates don't handle intermittent
transient failures or issues such as a port state resetting mid-flight.
Due to this, deployments are easily broken or interrupted which is not
ideal in varying infrastructures with different network configurations.
These factors led the community to reach consensus that it was time
to deprecate this deployment mechanism, and ultimately remove it from Ironic.

We anticipate it to disappear before our final release for the Xena
development cycle, in part because it is extremely difficult to troubleshoot
and is reliant upon the conductor block-io interface which creates a natural
performance bottleneck which limits the ability to scale a deployment.

.. [#f1] `Alala <https://en.wikipedia.org/wiki/Alala>`_ is a reference to
         Greek mythology where it was the female personification of raising
         a war cry. In this context, it is a reference to the television
         show `Xena: Warrior Princess <https://en.wikipedia.org/wiki/Xena#Skills_and_abilities>`_.
