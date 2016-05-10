.. _mitaka-priorities:

=========================
Mitaka Project Priorities
=========================

This is a list of development priorities the Ironic team is prioritizing for
Mitaka development, in no particular order.

You may notice this list seems long for a single cycle. Note that much of this
work is in flight already and just needs to be completed during the Mitaka
cycle; they are not starting from scratch.

+-----------------------------------------+----------------------------------+
| Priority                                | Primary Contacts                 |
+=========================================+==================================+
| `ironic-lib refactor`_                  | rloo                             |
+-----------------------------------------+----------------------------------+
| `Manual cleaning`_                      | rloo                             |
+-----------------------------------------+----------------------------------+
| `RAID`_                                 | rameshg87, lucasagomes           |
+-----------------------------------------+----------------------------------+
| `Network isolation`_                    | jroll                            |
+-----------------------------------------+----------------------------------+
| `Live upgrades`_                        | lucasagomes, lintan              |
+-----------------------------------------+----------------------------------+
| `Boot interface refactor`_              | jroll                            |
+-----------------------------------------+----------------------------------+
| `Parallel tasks with futurist`_         | dtantsur                         |
+-----------------------------------------+----------------------------------+
| `Node filter API and claims endpoint`_  | jroll, devananda                 |
+-----------------------------------------+----------------------------------+
| `Multiple compute hosts`_               | jroll, devananda                 |
+-----------------------------------------+----------------------------------+
| `Improving testing`_                    | jlvillal, krtaylor, lekha        |
+-----------------------------------------+----------------------------------+
| `Improving docs`_                       | jroll, liliars                   |
+-----------------------------------------+----------------------------------+

*May 2016. These were completed in the Mitaka cycle*:

* `ironic-lib refactor`_

* `Manual cleaning`_

* `RAID`_

* `Boot interface refactor`_

* `Parallel tasks with futurist`_

ironic-lib refactor
-------------------

Work to refactor much of Ironic's disk partitioning code into a library
(ironic-lib) began in Liberty, getting the library set up and released. The
team would like to finish that work in Mitaka by removing the code in Ironic
and replacing it with library calls. This enables advanced partitioning in
ironic-python-agent via this library, which will be needed for supporting
partitioned disk images.

Manual cleaning
---------------

Work began on a feature called "zapping" in Liberty. This came late in the
cycle, and the implementation identified some issues with the architecture and
name. This is being re-spun as "manual cleaning" in Mitaka. It's needed to
complete the RAID work and for operators to be able to trigger other cleaning
tasks manually.

RAID
----

Much of the groundwork was laid down for RAID support in Liberty. To complete
this work in Mitaka, we need to integrate it with (manual) cleaning and write
ample documentation for operators.

Network isolation
-----------------

This feature was designed in Liberty, and much of the code was written. The
code was not ready in time to land in Liberty. We need to complete this work in
Mitaka, along with the Nova side of the work. This is one of our biggest
feature asks from users.

Live upgrades
-------------

This is necessary, especially with frequent releases, to allow our operators to
upgrade without downtime. There isn't much code work left to do here; mostly
docs, increasing awareness, and building a culture of coding and reviewing for
live upgrades.

Boot interface refactor
-----------------------

This work was completed for most drivers in Liberty. Two drivers (iLO and iRMC)
remain to be completed. The code is complete for this and just needs review.

Parallel tasks with futurist
----------------------------

This will help scale our conductor service, as we have a handful of periodic
tasks that currently run serially. Additionally, drivers may register periodic
tasks that compound this problem.

Node filter API and claims endpoint
-----------------------------------

This lays the groundwork for the work being done in Nova to allow the Ironic
driver to utilize multiple compute hosts. The filter API also helps users query
nodes much more intelligently, and the claims endpoint will help clients other
than Nova schedule to nodes more easily.

Multiple compute hosts
----------------------

This is an effort to allow the Ironic virt driver in Nova scale across many
compute hosts. Currently only one compute host is supported. This shrinks the
failure domain of the nova-compute service in an Ironic deployment, and also
helps schedule Ironic resources more efficiently. Note that this work is in the
Nova codebase, but is an Ironic effort.

Improving testing
-----------------

There are a number of gaps in our testing that we need to close. This includes
full tempest, microversion testing, grenade jobs, functional testing, third
party CI, and more. These will help us to keep our releases more stable.

Improving docs
--------------

We currently don't have any presence in the official OpenStack documentation,
and somewhat related, there is currently no way to update documentation for
stable branches. We also need to create a developer's guide of sorts, to help
developers follow our processes more easily and submit better code, as well as
help reviewers review code in a consistent manner.
