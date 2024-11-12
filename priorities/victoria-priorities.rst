.. _victoria-priorities:

===========================
Victoria Project Priorities
===========================

This is a list of goals the Ironic team is prioritizing for
the Victoria development cycle, in order of relative size and
dependency addressing.

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
=====

+-------------------------------------+-------------------------+-----------+
| Priority                            | Primary Contacts        | Target    |
+=====================================+=========================+===========+
| `Break the Cycle`_                  | Ironic Developers       | Sprint 1  |
+-------------------------------------+-------------------------+-----------+
| `Move to all native Zuulv3 jobs`_   | iurygregory             | Sprint 1  |
+-------------------------------------+-------------------------+-----------+
| `Standalone Basic Authentication`_  | stevebaker              | Sprint 1  |
+-------------------------------------+-------------------------+-----------+
| `ISO Boot media pass-through`_      | TheJulia                | Sprint 1  |
+-------------------------------------+-------------------------+-----------+
| `Compatibility Matrix`_             | TheJulia                | Sprint 1  |
+-------------------------------------+-------------------------+-----------+
| `Replacing WSME`_                   | stevebaker              | Sprint 2  |
+-------------------------------------+-------------------------+-----------+
| `Ramdisk TLS`_                      | dtantsur                | Sprint 2  |
+-------------------------------------+-------------------------+-----------+
| `Make CI Manageable`_               | Ironic Developers       | Sprint 2  |
+-------------------------------------+-------------------------+-----------+
| `DHCP-less Deployments`_            | iurygregory             | Sprint 2  |
+-------------------------------------+-------------------------+-----------+
| `Move to oslo.privsep`_             | iurygregory             | Sprint 2  |
+-------------------------------------+-------------------------+-----------+
| `In-band Deploy Steps`_             | dtantsur, mgoddard      | Sprint 3  |
+-------------------------------------+-------------------------+-----------+
| `Redfish Interop Profile`_          | arne_wiebalck, rpioso,  | Sprint 3  |
|                                     | rpittau                 |           |
+-------------------------------------+-------------------------+-----------+
| `Bare metal program/SIG`_           | TheJulia, arne_wiebalck | Theme     |
+-------------------------------------+-------------------------+-----------+

Schedule Structure
------------------

The indicator for this schedule is to help provide those reviewing this
document a rough idea of when one may anticipate functionality to merge and
be released. Things may merge sooner or later.

Sprint 1
++++++++

Targeted to be released around the week of June 29th, 2020.

Sprint 2
++++++++

Starting after the release for Sprint 1.

Anticipated to be released the week of August 10th, 2020. Roughly two months
after Sprint 1.

Sprint 3
++++++++

Starting after the release of Sprint 2, anticipated to run the course of
two months. This should be anticipated around the week of September 28th, 2020.
It is important to note that the week of the OpenStack deadline for the
final release candidate as part of the Victoria cycle. Ironic's "latest"
release will be consumed by OpenStack for the Victoria release at this time.

Theme
~~~~~

General thematic work for general improvement in an area fall under the
classification of theme. Largely this is work that may run the course of
an entire release cycle or longer, where small incremental improvements
or related work takes place.

Goals Details
=============

In no particular order...

Break the Cycle
---------------

Ironic is a project which is consumed by other projects and ultimately makes its
way into multiple products through these channels. In many ways, it is a
swiss-army knife for operators. At the same time it becomes a semi-hidden
implementation detail behind projects like `TripleO <http://tripleo.org>`_
`Metal3 <https://metal3.io>`_, and even in a sense it can be a hidden detail
for users of the `OpenStack Compute API
<https://docs.openstack.org/nova/latest/admin/configuration/hypervisor-ironic>`_.

With this use, and ultimately to support their use cases, we need to do better
in terms of trying to release early and often.

Sometimes there is no reason TO make a brand new release of Ironic or
any of its components unless WE NEED to take action to fix it or we have
added a new feature. Largely this is because we
rely upon stable APIs and interfaces, at least in most cases.

While we would all love to see all of the features, we should be delivering
in a model which conforms to `Sem-Ver <http://semver.org>`_ and not force
artificial major version changes to match a cycle boundary and to create a
branch point.

Having said this, it is time for us to move to an
`independent release model <https://specs.openstack.org/openstack/ironic-specs/specs/not-implemented/new-release-model.html>`_.

This has drawbacks, and will require a different approach for planning.
And yet not all of Ironic's assets should be released in such a way.
Some items that fall under our governance as a project have
inter-dependencies which ultimately require continuing with the OpenStack
release cycle model. Does that make those items any less part of Ironic?
Absolutely not! But they are specific integration points, and we will always
need to be mindful of the need to maintain those integration points.

Make CI Manageable
------------------

CI is a never ending pain point. It is a truth of the existence of a CI system
in any software development process. The conundrum we face though, is we
have an explosion of drivers, specific use cases we are concerned about,
and ultimately we never want to break anyone. The natural end result
is we have a huge number of CI jobs.

With a number of different jobs, one may think that it is easy to maintain.

And in a sense, they are right. Except what is lost is our testing model
forces ``rechecks`` to re-run all jobs. It is actually a good thing in that
context, yet bad in that any single transient failure can force the
re-execution of all tests, again. And Again. And sometimes, yet again.

Ultimately, In order to make CI manageable, we need to improve our concurrency,
and greatly reduce our overall job count. We do this by trying to use the same
job to test multiple scenarios. Where we can't, we likely have a defect we
should explore fixing. And if there is anything we can do to improve job
execution time, we ultimately improve time to results for not just ourselves,
but everyone.

Move to all native Zuulv3 jobs
------------------------------

The chosen OpenStack community goal for the Victoria cycle is to ensure that all
jobs are Zuulv3 native. You can learn about this effort
`here <https://governance.openstack.org/tc/goals/selected/victoria/native-zuulv3-jobs.html>`_.

Move to oslo.privsep
--------------------

One of the proposed, but not selected by the OpenStack TC changes is to adopt
the use of Oslo.Privsep. We think this is a good idea and will go ahead and
proceed with this
`effort <https://governance.openstack.org/tc/goals/proposed/migrate-to-privsep.html>`_.

Compatibility Matrix
--------------------

One of the weaknesses in Ironic's documentation is a lack of clarity regarding
the functionality of features with-in drivers when comparing drivers
side-by-side. Mainly because we want to encourage but not force driver
maintainers to take particular improvements to their driver code.

And so, the hope is to fix this weakness in our documentation.
Through clarity, the overall user experience should improve, and that is
ultimately what we all seek.

In-band Deploy Steps
--------------------

While a theme that has been part of several of our past cycles, we continue to
working towards improving the functionality of Deploy Steps, and in this case
the focus is for in-band usage.

Bare metal program/SIG
----------------------

The most powerful thing the Ironic community can do this cycle is not actually
in code, but in documentation. The recently created
`Bare Metal SIG <https://etherpad.openstack.org/p/bare-metal-sig>`_ is working
on creation of a white paper as part of the
`Bare Metal logo program <https://www.openstack.org/bare-metal/>`_, and needs
our help for stand-alone use cases.

Ramdisk TLS
-----------

One of the structural weaknesses in the ``ironic-conductor`` to
``ironic-python-agent`` security is that by default, it is not encrypted.

In large part because this is a difficult surface to secure. It is ephemeral,
temporary, and often short-lived. Mechanisms to sign a certificate are also
a bit more difficult to put in place. Does the TLS client check the
certificate "common name" or "alias" field. Does that even matter for this
usage. How do we handle virtual media versus PXE booting with a supplied
ramdisk.

These are all questions and concerns that we must answer, with the ultimate
goal of ensuring that an agent can automatically offer a TLS encrypted
Restful API endpoint for the ``ironic-conductor`` to connect to.

Replacing WSME
--------------

Most long time contributors are aware of the headaches that WSME has brought
the community, along with the fact that many projects have migrated away from
it.

In order to move us to something which is supported by a broader community,
the consensus from the Train Project Teams Gathering, was to move Ironic
towards using Flask. We'll start with re-working a single endpoint and
hopefully move through the rest of the API in a rapid fashion.

Standalone Basic Authentication
-------------------------------

For standalone use cases to flourish, we must support another authentication
mechanism. The simplest, is rather simple. Just HTTP Basic Authentication.

Maybe we won't just stop there, but "noauth" is simply not acceptable with
edge infrastructure management.

DHCP-less Deployments
---------------------

Deployment of machines at the edge requires the case where we do not control
DHCP. Except there are cases where there might not be any DHCP server,
and in such cases, we must supply networking configuration in the
virtual media being attached to the physical machine being deployed.

This effort is carried over from the Ussuri development cycle, and with any
luck will be merged early in the Victoria development cycle.

ISO Boot media pass-through
---------------------------

A recent idea is to better support the use of the ramdisk use case for
operators wishing to trigger machine boot operations via a pre-mastered ISO,
much like the existing ramdisk interface, however in this case, they have
everything they need.

More information about this can be found in the
`specification <https://review.opendev.org/#/c/725949/>`_ document.

Redfish Interop Profile
-----------------------

The Redfish Forum has an `interop profile <https://github.com/DMTF/Redfish-Interop-Validator>`_
mechanism to allow feedback in the process to convey what is and
what is not supported.

Such a profile can be used by hardware vendors/manufacturers to
assess/advertise to which degree Ironic can interact with their hardware.
Equally consumers/clients of such hardware can use the
profile to make sure the hardware they intend to buy works with Ironic or even
make this part of their tendering/purchase process.
