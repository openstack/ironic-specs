.. _queens-priorities:

=========================
Queens Project Priorities
=========================

This is a list of development priorities the Ironic team is prioritizing for
Queens development, in order of priority. Note that this is not our complete
backlog for the cycle, we still hope to review and land non-priority items.

The primary contact(s) listed is/are responsible for tracking the status of
that work and herding cats to help get that work done. They are not the only
contributor(s) to this work, and not necessary doing most of the coding!
They are expected to be available on IRC and the ML for questions, and report
status on the whiteboard_ for the weekly IRC sync-up. The number of primary
contacts is limited to 2-3 maximum to simplify communication. We expect at
least one of them to have core privileges to simplify getting changes in.

.. _whiteboard: https://etherpad.openstack.org/p/IronicWhiteBoard

Essential Priorities
~~~~~~~~~~~~~~~~~~~~

+---------------------------------------+-------------------------------------+
| Priority                              | Primary Contacts                    |
+=======================================+=====================================+
| `Ironic client version negotiation`_  | TheJulia, dtantsur                  |
+---------------------------------------+-------------------------------------+
| `External project auth rework`_       | pas-ha, TheJulia                    |
+---------------------------------------+-------------------------------------+
| `Old ironic CLI deprecation`_         | rloo                                |
+---------------------------------------+-------------------------------------+
| `Classic drivers deprecation`_        | dtantsur                            |
+---------------------------------------+-------------------------------------+
| `Reference architecture guide`_       | dtantsur, sambetts                  |
+---------------------------------------+-------------------------------------+

High Priorities
~~~~~~~~~~~~~~~~~~

+---------------------------------------+-------------------------------------+
| Priority                              | Primary Contacts                    |
+=======================================+=====================================+
| `Neutron event processing`_           | vdrok, vsaienk0, sambetts           |
+---------------------------------------+-------------------------------------+
| `Routed networks support`_            | sambetts, vsaienk0, bfournie        |
+---------------------------------------+-------------------------------------+
| `Rescue mode`_                        | rloo, stendulker, aparnav           |
+---------------------------------------+-------------------------------------+
| `Clean up deploy interfaces`_         | vdrok                               |
+---------------------------------------+-------------------------------------+
| `Zuul v3 jobs in-tree`_               | sambetts, derekh, jlvillal          |
+---------------------------------------+-------------------------------------+
| `Graphical console`_                  | pas-ha, vdrok, rpioso               |
+---------------------------------------+-------------------------------------+
| `BIOS config framework`_              | dtantsur, yolanda, rpioso           |
+---------------------------------------+-------------------------------------+
| `Ansible deploy interface`_           | pas-ha, yuriyz                      |
+---------------------------------------+-------------------------------------+
| `Traits support planning`_            | johnthetubaguy, TheJulia, dtantsur  |
+---------------------------------------+-------------------------------------+

Details
~~~~~~~

Ironic client version negotiation
---------------------------------

Currently, we only support using a single API version for the whole life time
of an ironic client instance. We need to support using several versions in the
same client. We also need a way for the client to negotiate a maximum mutually
supported version with a server. Then we need to switch to using this
negotiated version in the OSC CLI by default. Finally, we will use the version
negotiation in the ironic virt driver.

External project auth rework
----------------------------

Work is under way to change how ironic `authenticates with other OpenStack
services <https://bugs.launchpad.net/ironic/+bug/1699547>`_, so that it uses
keystoneauth adapters. This will make it uniform, consistent, straightforward,
and compatible with the latest OpenStack best practices.

Old ironic CLI deprecation
--------------------------

We would like to deprecate the ``ironic`` CLI tool in favour of ``openstack
baremetal`` commands based on OpenStackClient.

Classic drivers deprecation
---------------------------

We would like to deprecate the ability to load classic drivers, as well as
classic drivers themselves, in favour of hardware types. We are providing
a migration guide for the switch, and we are also considering writing
an automated migration tool, though it may be tricky. See
:doc:`../specs/approved/classic-drivers-future` for details.

Reference architecture guide
----------------------------

To help new deployers make the right choices, we need a document describing a
reference architecture for an ironic deployment, especially around
multi-tenant networking and co-existing with VMs.

Neutron event processing
------------------------

Currently ironic has no way to determine when certain asynchronous events
actually finish in neutron, and with what result. Nova, on the contrary, uses
a special neutron driver, which filters out notifications and posts some of
them to a special nova API endpoint. We should do the same.

Routed networks support
-----------------------

Ironic should become aware of L2 segments available to connected networks as
well as which L2 networks are actually available to nodes to correctly pick
subnet (IP address) when doing provisioning/cleaning.

Rescue mode
-----------

This is necessary for users that lose regular access to their machine (e.g.
lost passwords). The :doc:`rescue mode spec
<../specs/approved/implement-rescue-mode>` was merged in Newton, the code is
partially done, let's put some effort into finishing it in Queens.

Clean up deploy interfaces
--------------------------

There is a lot of duplication between the ``iscsi`` and ``direct`` deploy
interface implementations. We need to clean them up to simplify future
maintenance.

Zuul v3 jobs in-tree
--------------------

With the switch to Zuul v3 we can now have our job definitions in our source
tree. Let us switch all jobs during this cycle.

Graphical console
-----------------

We need a way to expose graphical (e.g. VNC) consoles to users from drivers
that support it.

BIOS config framework
---------------------

Some drivers support setting BIOS (UEFI, etc) configuration out-of-band. We
would like to introduce a framework (HTTP and driver API) for drivers to
expose this feature to users.

Ansible deploy interface
------------------------

A deploy interface using ansible was developed out-of-tree and is currently a
part of ironic-staging-drivers. We need to import it into ironic to simplify
advanced use cases, requiring extensive customizations. The :doc:`spec
<../specs/approved/ansible-deploy-driver>` was approved, now we need to clean
up the code and move it in-tree.

Traits support planning
-----------------------

Nova is switching from *capabilities* to *traits* in the coming cycles. We
should make sure we are ready for the switch. The minimum goal for Queens is
to have a specification approved, outlining our plan on traits support.
