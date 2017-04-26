.. _pike-priorities:

=======================
Pike Project Priorities
=======================

This is a list of development priorities the Ironic team is prioritizing for
Pike development, in order of priority. The primary contact(s) listed
is/are responsible for tracking the status of that work and herding cats
to help get that work done. They are not the only contributor(s) to this work!
The number of primary contacts is limited to 2 maximum to simplify
communication. We expect at least one of them to have core privileges
to simplify getting changes in.

Essential Priorities
~~~~~~~~~~~~~~~~~~~~

+---------------------------------------+-------------------------------------+
| Priority                              | Primary Contacts                    |
+=======================================+=====================================+
| `Standalone CI tests`_                | vsaienk0                            |
+---------------------------------------+-------------------------------------+
| `Generic boot-from-volume`_           | TheJulia, dtantsur                  |
+---------------------------------------+-------------------------------------+
| `Rolling upgrades`_                   | rloo, jlvillal                      |
+---------------------------------------+-------------------------------------+
| `Reference architecture guide`_       | jroll, dtantsur                     |
+---------------------------------------+-------------------------------------+
| Python 3.5 compatibility              | Nisha                               |
+---------------------------------------+-------------------------------------+
| Deploying with Apache and WSGI in CI  | vsaienk0                            |
+---------------------------------------+-------------------------------------+
| `Driver composition`_                 | jroll, dtantsur                     |
+---------------------------------------+-------------------------------------+
| `Feature parity between two CLIs`_    | rloo, dtantsur                      |
+---------------------------------------+-------------------------------------+
| `OSC default API version change`_     | dtantsur                            |
+---------------------------------------+-------------------------------------+
| Finish node tags                      | zhenguo, dtantsur                   |
+---------------------------------------+-------------------------------------+

High Priorities
~~~~~~~~~~~~~~~

+---------------------------------------+-------------------------------------+
| Priority                              | Primary Contacts                    |
+=======================================+=====================================+
| `Rescue mode`_                        | stendulker, aparnav                 |
+---------------------------------------+-------------------------------------+
| `Post-deploy VIF attach/detach`_      | sambetts, vsaienk0                  |
+---------------------------------------+-------------------------------------+
| `Physical network awareness`_         | sambetts, vsaienk0                  |
+---------------------------------------+-------------------------------------+
| `Routed networks support`_            | sambetts, vsaienk0                  |
+---------------------------------------+-------------------------------------+
| `Neutron event processing`_           | vdrok, vsaienk0                     |
+---------------------------------------+-------------------------------------+
| `IPA REST API versioning`_            | sambetts                            |
+---------------------------------------+-------------------------------------+

Optional Priorities
~~~~~~~~~~~~~~~~~~~

+---------------------------------------+-------------------------------------+
| Priority                              | Primary Contacts                    |
+=======================================+=====================================+
| `Split away the tempest plugin`_      | soliosg, jlvillal                   |
+---------------------------------------+-------------------------------------+
| `Deploy steps`_                       | yolanda, rloo                       |
+---------------------------------------+-------------------------------------+
| Redfish driver                        | lucasagomes, jroll                  |
+---------------------------------------+-------------------------------------+
| `Supported power states API`_         | dtantsur                            |
+---------------------------------------+-------------------------------------+
| `Available clean steps API`_          | rloo                                |
+---------------------------------------+-------------------------------------+
| `E-Tags in API`_                      | galyna, vdrok                       |
+---------------------------------------+-------------------------------------+

Details
~~~~~~~

Standalone CI tests
-------------------

We are working on a set of tests that can be run without nova present. We
expect this work to improve CI time, coverage and help test certain features
(e.g. adoption) that are not quite compatible with nova.

Generic boot-from-volume
------------------------

This work allows generic hardware to boot from remote storage, allowing
diskless nodes to be managed by ironic. This also lays down the framework for
hardware-specific implementations to be built.

Rolling upgrades
----------------

Many OpenStack projects are beginning to support rolling upgrades - we should
too. Let's do our part to make downtimes a thing of the past. This involves
code changes, new multi-node grenade CI jobs, and reviewer/developer
documentation. The target now is Ocata -> Pike rolling upgrades.

Reference architecture guide
----------------------------

To help new deployers make the right choices, we need a document describing a
reference architecture for an ironic deployment, especially around
multi-tenant networking and co-existing with VMs.

Driver composition
------------------

We've done most of the coding. Let's concentrate on stabilizing the feature,
writing new hardware types, polishing documentation and helping vendors with
onboarding.

Feature parity between two CLIs
-------------------------------

Let us make sure that all features implemented in the old ``ironic`` CLI are
available in the new OSC-based ``openstack baremetal`` CLI.

OSC default API version change
------------------------------

Currently the default API version OSC sends to ironic is an old Kilo-era one.
We need to figure out the path towards making the latest version the default.

Rescue mode
-----------

This is necessary for users that lose regular access to their machine (e.g.
lost passwords). The spec was merged in Newton, the code is partially done,
let's put some effort into making progress here in Pike.

Post-deploy VIF attach/detach
-----------------------------

We already support attaching and detaching VIFs to nodes as part of the
deployment process. Now we need to support the same for active nodes.

Physical network awareness
--------------------------

We need to make sure instances are not scheduled on nodes that cannot
physically reach the networks they're connected to. This may require data
model changes around ports. This is required for `Routed networks support`_.

Routed networks support
-----------------------

Ironic should become aware of L2 segments available to connected networks as
well as which L2 networks are actually available to nodes to correctly pick
subnet (IP address) when doing provisioning/cleaning.

Neutron event processing
------------------------

Currently ironic has no way to determine when certain asynchronous events
actually finish in neutron, and with what result. Nova, on the contrary, uses
a special neutron driver, which filters out notifications and posts some of
them to a special nova API endpoint. We should do the same.

IPA REST API versioning
-----------------------

IPA API is currently not versioned, which causes problems when ironic starts
relying on new features. Versioning similar to ironic API is expected to fix
it and simplify upgrades.

Split away the tempest plugin
-----------------------------

Currently we rely on certain hacks to make our CI use master version of the
tempest plugin on all branches. The QA team suggests moving our tempest plugin
to a separate branch instead, let's do it. We should also merge ironic and
ironic-inspector plugins for simpler maintenance and consumption.

Deploy steps
------------

This is an effort to split parts of our monolithic deployment process into
steps, similar to cleaning. That will give driver authors a bit more freedom in
customizing the deploy process, and simplify potential additions to it
(like RAID, for example).

Supported power states API
--------------------------

The `soft power/NMI spec
<http://specs.openstack.org/openstack/ironic-specs/specs/not-implemented/enhance-power-interface-for-soft-reboot-and-nmi.html>`_
proposes exposing available power states in the API. We didn't implement this
part in Ocata, let us finish it now.

Available clean steps API
-------------------------

We need to expose available clean steps in the API, so that users know which
actions they can run during manual cleaning. This is a part of the
`manual cleaning spec
<http://specs.openstack.org/openstack/ironic-specs/specs/5.0/manual-cleaning.html>`_
which was never implemented, despite the spec being marked as done.

E-Tags in API
-------------

We should add E-Tag support to our API to avoid race conditions during
concurrent updates.
