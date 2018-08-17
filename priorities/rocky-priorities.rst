.. _rocky-priorities:

========================
Rocky Project Priorities
========================

This is a list of development priorities the Ironic team is prioritizing for
Rocky development, in order of priority. Note that this is not our complete
backlog for the cycle, we still hope to review and land non-priority items.

The primary contact(s) listed is/are responsible for tracking the status of
that work and herding cats to help get that work done. They are not the only
contributor(s) to this work, and not necessary doing most of the coding!
They are expected to be available on IRC and the ML for questions, and report
status on the whiteboard_ for the weekly IRC sync-up. The number of primary
contacts is typically limited to 2-3 individuals to simplify communication.
We expect at least one of them to have core privileges to simplify getting
changes in.

.. _whiteboard: https://etherpad.openstack.org/p/IronicWhiteBoard

Priorities
~~~~~~~~~~

+---------------------------------------+-------------------------------------+
| Priority                              | Primary Contacts                    |
+=======================================+=====================================+
| `Deploy Steps`_                       | rloo, mgoddard                      |
+---------------------------------------+-------------------------------------+
| `BIOS config framework`_              | zshi, yolanda, moddard, hshiina     |
+---------------------------------------+-------------------------------------+
| `Conductor Location Awareness`_       | jroll                               |
+---------------------------------------+-------------------------------------+
| `Reference architecture guide`_       | dtantsur, jroll                     |
+---------------------------------------+-------------------------------------+
| `Graphical console`_                  | mkrai, anup-d-navare, TheJulia      |
+---------------------------------------+-------------------------------------+
| `Neutron Event Processing`_           | vdrok                               |
+---------------------------------------+-------------------------------------+

Goals
~~~~~

+---------------------------------------+-------------------------------------+
| Goal                                  | Primary Contacts                    |
+=======================================+=====================================+
| `Updating nova virt to use REST API`_ | TheJulia                            |
+---------------------------------------+-------------------------------------+
| `Storyboard migration`_               | TheJulia, dtantsur                  |
+---------------------------------------+-------------------------------------+
| `Management interface refactoring`_   | etingof, dtantsur                   |
+---------------------------------------+-------------------------------------+
| `Getting clean steps`_                | rloo, TheJulia                      |
+---------------------------------------+-------------------------------------+
| `Project vision`_                     | jroll, TheJulia                     |
+---------------------------------------+-------------------------------------+
| `SIGHUP Support`_                     | rloo                                |
+---------------------------------------+-------------------------------------+

Stretch Goals
~~~~~~~~~~~~~

.. note:: Upon completion of `Storyboard migration`_, the stretch goals
          documented here will be migrated to and tracked in Storyboard.

+---------------------------------------+-------------------------------------+
| Stretch Goals                         | Primary Contacts                    |
+=======================================+=====================================+
| `Classic driver removal`_             | dtantsur                            |
+---------------------------------------+-------------------------------------+
| `Redfish OOB inspection`_             | etingof, deray, stendulker          |
+---------------------------------------+-------------------------------------+
| `Zuul v3 playbook refactoring`_       | sambetts, pas-ha                    |
+---------------------------------------+-------------------------------------+

Details
~~~~~~~

Deploy Steps
------------

We created cleaning with the ability to compose an ordered list of
actions to be taken. However we left deployment as a static set of actions.

In order to allow templates to apply using chosen traits, we want to have
the same functionality and framework that we obtained with cleaning to apply
to the deployment of a node.

This will start with the goal of splitting apart the action of writing the
image during the deployment from the act of writing the configuration drive
into two distinct steps. From there, we will further iterate.

This may ultimately facilitate de-duplication of deployment logic which
was an uncompleted goal from the Queens development cycle.

BIOS config framework
---------------------

Some drivers support setting BIOS (UEFI, etc) configuration out-of-band. We
would like to introduce a framework (HTTP and driver API) for drivers to
expose this feature to users.

Conductor location awareness
----------------------------

Often operators have made changes to driver names to facilitate mapping of
conductors to individual nodes, such that conductors are local to nodes,
and a conductor in Los Angeles is not trying to control machines in Europe.

This allows ironic to remain a single pane of glass, and provides increased
flexibility in deployments of ironic. For now, we will focus on hard
affinity with an upgrade path.

Reference architecture guide
----------------------------

To help new deployers make the right choices, we need a document describing a
reference architecture for an ironic deployment, especially around
multi-tenant networking and co-existing with VMs.

Graphical console
-----------------

We need a way to expose graphical (e.g. VNC) consoles to users from drivers
that support it. Specifications and patches are in various states, and
need to be picked up again. We are hoping to have the initial framework
to support graphical console usage in this cycle.

Neutron event processing
------------------------

Currently ironic has no way to determine when certain asynchronous events
actually finish in neutron, and with what result. Nova, on the contrary, uses
a special neutron driver, which filters out notifications and posts some of
them to a special nova API endpoint. We should do the same.

Updating nova virt to use REST API
----------------------------------

Cycle after cycle we encounter issues with the upgrade sequence and the API
version pin that we increment in the Nova virt driver that supports ironic.

It is time to put this to an end and better properly support versioned
interactions with our API. Upon discussing with the Nova community,
we reached consensus that it is time to transition our API calls to
direct REST calls as opposed to calls through the python-ironicclient library.

Storyboard migration
--------------------

Ironic has planned work in many different ways over the years, and we have
learned that there are positives to each approach.

As our team has also become smaller, we must also enable better focus by
integrating distinct tools, systems, and processes together.

With Storyboard, we will gain the advantage of planning and tracking work
in a single system.

Management interface refactoring
--------------------------------

As time has gone on, we have found the need to have a single place to
control the boot mode for nodes. This effort is refactoring the
management interface so we move distinct boot mode related
actions into a single interface.

Getting clean steps
-------------------

One of the biggest frustrations that people have with our cleaning model
is the lack of visibility into what they can do. We have ideas on this
and we need to begin providing the mechanisms to raise that visibility.

Project vision
--------------

We all have different ideas of where we would like to see ironic in
two, five, and ten years. Discussing this as a group helped us scope and
frame our discussions so we were on the same page.

We should write down our collective vision of the future, and see where it
takes us.

SIGHUP support
--------------

SIGHUP is the signaling mechanism to indicate that a program should attempt to
reload configuration and possibly restart itself. Supporting SIGHUP_ is an
OpenStack project wide goal, and it should be easy for us. Let's do it!

.. _SIGHUP: https://governance.openstack.org/tc/goals/rocky/enable-mutable-configuration.html

Classic driver removal
----------------------

We have deprecated the classic drivers, and soon is approaching the time to
remove these drivers now that we have provided a means to migrate users to
hardware types. Deprecation took place on Feb 1, 2018, and thus this code can
be removed after May 1, 2018.

Redfish OOB inspection
----------------------

Redfish is one of our in-tree "reference" hardware types, however we have no
support for out-of-band inspection. In terms of providing feature parity,
we should move forward with this, as more vendors are moving to Redfish.

Zuul v3 playbook refactoring
----------------------------

One of the powerful features with Zuul v3 is that we execute ansible playbooks
as opposed to traditional shell scripting. The migration left quite a bit of
legacy shell scripts in the testing process.

Efforts are underway to remove the bulk of this launch scripting from our
normal devstack jobs. We should expect our grenade jobs to remain untouched.
