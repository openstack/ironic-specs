.. _stein-priorities:

========================
Stein Project Priorities
========================

This is a list of development priorities the Ironic team is prioritizing for
Stein development, in order of relative size and dependency addressing.
Note that this is not our complete backlog for the cycle, we still hope
to review and land non-priority items.

The primary contact(s) listed is/are responsible for tracking the status of
that work and herding cats to help get that work done. They are not the only
contributor(s) to this work, and not necessary doing most of the coding!
They are expected to be available on IRC and the ML for questions, and report
status on the whiteboard_ for the weekly IRC sync-up. The number of primary
contacts is typically limited to 2-3 individuals to simplify communication.
We expect at least one of them to have core privileges to simplify getting
changes in.

As the time remaining in the Stein cycle is approximately 30 weeks from the
Project Teams Gathering, the list of priorities has been split into two
major pieces based upon an estimate of relative size. The overall goal
is for the `Smaller Goals`_ items to be focused on with in the first few
months of the cycle, while the larger `Epic Goals`_ may receive some work
early on, but will be targeted for later in the cycle.

.. _whiteboard: https://etherpad.openstack.org/p/IronicWhiteBoard

Smaller Goals
~~~~~~~~~~~~~

+---------------------------------------+-------------------------------------+
| Priority                              | Primary Contacts                    |
+=======================================+=====================================+
| `Upgrade Checker`_                    | TheJulia                            |
+---------------------------------------+-------------------------------------+
| `Python3 First`_                      | ?                                   |
+---------------------------------------+-------------------------------------+
| `iPXE/PXE interface split`_           | TheJulia                            |
+---------------------------------------+-------------------------------------+
| `UEFI First`_                         | ?                                   |
+---------------------------------------+-------------------------------------+
| `HTTPClient booting`_                 | ?TheJulia?                          |
+---------------------------------------+-------------------------------------+
| `Nova conductor_group awareness`_     | jroll, TheJulia                     |
+---------------------------------------+-------------------------------------+
| `Enhanced Checksum Support`_          | jroll, kaifeng                      |
+---------------------------------------+-------------------------------------+
| `DHCP-less/L3 virtual media boot`_    | shekar                              |
+---------------------------------------+-------------------------------------+


Epic Goals
~~~~~~~~~~

+---------------------------------------+-------------------------------------+
| Goal                                  | Primary Contacts                    |
+=======================================+=====================================+
| `Deploy Templates`_                   | mgoddard, dtantsur, rloo            |
+---------------------------------------+-------------------------------------+
| `Graphical Console`_                  | mkrai, etingof                      |
+---------------------------------------+-------------------------------------+
| `Federation Capabilities`_            | TheJulia, dtantsur                  |
+---------------------------------------+-------------------------------------+
| `Task execution improvements`_        | etingof, TheJulia, mgoddard         |
+---------------------------------------+-------------------------------------+
| `No IPA to conductor communication`_  | jroll, rloo                         |
+---------------------------------------+-------------------------------------+
| `Getting steps`_                      | TheJulia, dtantsur                  |
+---------------------------------------+-------------------------------------+
| `Conductor role splitting`_           | jroll, dtantsur                     |
+---------------------------------------+-------------------------------------+
| `Neutron Event Processing`_           | vdrok, mgoddard, hjensas            |
+---------------------------------------+-------------------------------------+

Inter-Project Goals
-------------------

+---------------------------------------+-------------------------------------+
| `Deployment state callbacks to nova`_ | TheJulia, ?jroll?                   |
+---------------------------------------+-------------------------------------+
| `Smartnic Support`_                   | TheJulia, mkrai                     |
+---------------------------------------+-------------------------------------+


Details
~~~~~~~

Upgrade Checker
---------------

This is an OpenStack Community goal for the Stein Cycle. For ironic this will
mean a new command called ``ironic-status upgrade check``. This command is
intended to return an error for things that would be fatal for an upgrade
such as new required configuration missing, or schema/data upgrades not
yet performed.

Python3 First
-------------

This is an OpenStack Community goal for the Stein Cycle. Most of this work has
already been completed in ironic. Largely we need to change our tests so we
are explicitly testing on Python3. We can't do this for every test at the
moment, but we should be able to change most and still ensure the bulk of
the code paths are covered by tests labeled with ``python2``.

iPXE/PXE interface split
------------------------

This is an older effort that has been restarted in the interest of supporting
multiple architectures (such as AArch64, Power, and x86_64) in the same
deployment.

As it turns out, Power's architecture expects the older PXELinux style
templates that are written by our PXE boot interface. Additionally, while
AArch64 can be booted using iPXE, no pre-built binaries are available.

As such, we need to no longer make this global for the conductor, but
specific to the node, and splitting the interfaces apart begins to make
much more sense. The original specification can be found
`here <http://specs.openstack.org/openstack/ironic-specs/specs/not-implemented/ipxe-boot-interface.html>`.

UEFI First
----------

2020 is an important year for Baremetal Operators, as Legacy boot mode support
is anticipated to be removed from newer processors being shipped.

To ensure our success, we need to improve our testing and prepare for the time
when UEFI is the only boot mode available for newer hardware. As a result,
this will become a multi-cycle focus to enable the default boot mode to be
changed to ``uefi`` in a future cycle.

HTTPClient Booting
------------------

While the community is interested in supporting HTTPClient based booting,
we currently have a few steps to surpass first. Namely the iPXE/PXE interface
split and improved UEFI testing.

The nature of this work is to enable an explict HTTP booting scenario where
the booting node does not leverage PXE.

Nova conductor_group awareness
------------------------------

This work is exlusively in the ironic virt driver in the `openstack/nova`
repository. This would enable us to define a ``conductor_group`` to which
the nova-compute process leverages for the view of baremetal nodes it is
responsible for.

Enhanced Checksum Support
-------------------------

Ironic presently defaults to use of MD5 checksums for the ``image_checksum``
which is far from ideal. During the Rocky cycle, Glance has enhanced their
support for checksum storage, which means we should enhance ours as well.

DHCP-less/L3 virtual media boot
-------------------------------

Some operators and vendors wish to enable ironic to manage deployments where
DHCP is not something that is leveraged or utilized in the deployment process.
In order to do this, we need to enable some additional capabilities in terms of
enabling information to be attached to a deployment ramdisk. The
specification can be found
`here <http://specs.openstack.org/openstack/ironic-specs/specs/not-implemented/L3-based-deployment.html>`.

Deploy Templates
----------------

In the future, we want to take specific action based upon traits submitted to
ironic from Nova describing the instance's expected state or behavior.

This will allow us to take actions and influence the deployment steps, and
as such is a continuation of the Deploy Steps work from the Rocky cycle.

Graphical Console
-----------------

We need a way to expose graphical (e.g. VNC) consoles to users from drivers
that support it. We reached agreement on the specification in the Rocky cycle
and have started to work through the patches to enable this. Our goal being
to have a framework and preferably at least one vendor driver to support
Graphical console connectivity. The specification can be found
`here <http://specs.openstack.org/openstack/ironic-specs/specs/not-implemented/vnc-graphical-console.html>`_.

Federation Capabilities
-----------------------

Edge computing is bringing a variety of cases where support for federation
of ironic deployments can be useful and extremely powerful.

In order to better support this emerging use case, we want to try and agree
on a viable path forward that meets several different use cases and
requirements. The objective for this effort is an agreed upon specification.

Task execution improvements
---------------------------

We realize that our task execution and locking model is problematic, and while
it does scale in some ways, it does not scale in other ways. This work will
consist of worker execution improvments, an evaluation and possible
implementation of different worker thread execution models, and careful
improvement of locking.

No IPA to conductor communication
---------------------------------

Larger operators need much more strict security in their deployments,
where they wish to prevent all outbound network connectivity to the
control plane. Presently the design model requires nodes are able to
reach ironic's API in order to perform heartbeat and lookup operations.

The concept with this is to optionally enable the conductor to drive the
deployment by polling IPA using the already known IP address. That being
said, this is realistically going to require `Task execution improvements`_
to be complete to help ensure that operators are able to have performant
deployments. The specification can be found
`here <https://review.openstack.org/#/c/212206/>`.

Getting steps
-------------

One of the biggest frustrations that people have with our cleaning model
is the lack of visibility into what steps they can execute. This is further
compounded with ``deploy steps``. We have ideas on this and we need to begin
providing the mechanisms to raise that visibility.

This may also involve state machine states to enable the agent to sit in a
holding pattern pending operator action.

The goal is ultimately to provide a CLI user to be able to understand the
available steps that can be utilized.

Neutron Event Processing
------------------------

Currently ironic has no way to determine when certain asynchronous events
actually finish in neutron, and with what result. Nova, on the contrary, uses
a special neutron driver, which filters out notifications and posts some of
them to a special nova API endpoint. We should do the same.

Conductor role splitting
------------------------

The conductor presently does all of the work... But does it need to?

This is a question we should be asking ourselves as we evolve, if we
can optionally break the conductor into many pieces, to enable edge
conductors, or edge local boot management. The goal here is to try and
obtain a matrix of distinct actions taken, which will hopefully further
guide us as time moves on.

Smartnic Support
----------------

Smartnics complicates ironic as the NIC needs to be programmed with the
power in a state such that the configuration on the NIC can be changed.

While the effort to support this may ultimately result in enhancements
to neutron in the form of Super-Agents to apply the configuration, we
still need to understand the impact to our workflows and ensure that
sufficient security is still present. The primary objective is to have
a joint specification written in advance of the Berlin summit to reach
consensus with the Neutron team as to the mechanics, information passing,
and setting storage.

Deployment state callbacks to nova
----------------------------------

One of the issues in ironic's nova virt driver is that no concept of
callbacks exist. Due to this, the virt driver polls the ironic API
endpoint repeatedly, which increases overall system load. In an ideal
world, ironic would utilize a mechanism to indicate deployment state
similar to how neutron informs nova that networking has been configured.
