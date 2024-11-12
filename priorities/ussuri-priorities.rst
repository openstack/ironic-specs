.. _ussuri-priorities:

=========================
Ussuri Project Priorities
=========================

This is a list of goals the Ironic team is prioritizing for
Ussuri development cycle, in order of relative size and dependency
addressing.

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
| `Scale / Performance`_                | TheJulia, arne_wiebalck             |
+---------------------------------------+-------------------------------------+
| `Bare metal program/SIG`_             | TheJulia, arne_wiebalck             |
+---------------------------------------+-------------------------------------+
| `Deploy Steps`_                       | dtantsur, mgoddard                  |
+---------------------------------------+-------------------------------------+
| `Replacing WSME`_                     | dtantsur                            |
+---------------------------------------+-------------------------------------+
| `Node retirement/quarantine`_         | arne_wiebalck, rpittau              |
+---------------------------------------+-------------------------------------+
| `Managed boot for inspection`_        | dtantsur                            |
+---------------------------------------+-------------------------------------+
| `Multitenancy/Machine Ownership`_     | tzumainn                            |
+---------------------------------------+-------------------------------------+
| `DHCP-less Deployments`_              | etingof                             |
+---------------------------------------+-------------------------------------+


Community Goals
~~~~~~~~~~~~~~~

+---------------------------------------+-------------------------------------+
| Goal                                  | Primary Contacts                    |
+=======================================+=====================================+
| `IPv6 support`_                       | TheJulia                            |
+---------------------------------------+-------------------------------------+
| `Drop Python 2.7 Support`_            | iurygregory, rpittau                |
+---------------------------------------+-------------------------------------+

Experiment for the Future
~~~~~~~~~~~~~~~~~~~~~~~~~

Ironic is stable, but it doesn't mean we should not experiment and find new
ways to solve the same problems. General consensus seems to be that this is an
important step forward to allow ourselves to further enable the future.

We give ourself the freedom to Innovate, Experiment, Evolve, and of utmost
importance the freedom to listen to our users.

Some of these things may be to just enable Software RAID 5/6, DHCP-less
deployment, boot-from-url for IPv4, or even kexec deployment. The idea being
that these are focused high-impact and tactical changes and we should
encourage such capabilities to merge.

The ultimate goal being to deliver and respond to the needs of our users
faster.

Details
~~~~~~~

Scale / Performance
-------------------

Ironic is being used all over the world. From small clusters to clusters which
may only be able to be described as "mind-boggling".

While scale brings a different class of problems, we have consumers and users
which can be impacted through even small minor changes. We *must* bring
visibility and awareness to this topic as well as ensuring we set
expectations and communicate ideal architectures.

* Implement some lightweight stress and performance testing
* Documentation oriented to scaling

It will be important to work with the `Bare Metal SIG`_ on this topic.

Deploy Steps
------------

While a theme that was included in the Train cycle, the overall effort for
deploy steps is ongoing. The Train cycle provided more interfaces capable of
being leveraged via deploy steps. The primary goal is to support in-band
execution of deploy steps with the focus being on leveraging Software RAID.

Bare metal program/SIG
----------------------

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

Node retirement/quarantine
--------------------------

Larger operators with Ironic have found themselves approaching a quandry of
"What is the proper way to retire a machine from ironic?". A nearly identical
topic has arisen from the Telecom world seeking to represent the state of the
node more accurately with-in ironic as to represent if a machine is in a fault
state or questionable state under-going investigation.

With that being said, we did not make progress on this issue in the past cycle
due to a fundamental disagreements in perception. The Project Teams Gathering
in Shanghai provided a forum for discussion where we realized that these are
actually similar but separate issues. One is for a separate logic path in what
could be three or six months, and the other is a change in present time.

Managed boot for inspection
---------------------------

In order to support edge architectures and on-demand inspection, we need to
enable managing the activation of inspection through ironic.

Multitenancy/Machine Ownership
------------------------------

The reality of hosting environments is that someone owns the hardware.
Sometimes this may be the tenant that needs to be on the hardware, and
we can't expect them to have administrative access to all hardware.

Thus we need to support a model where a tenant can be granted access
a piece of hardware.

DHCP-less Deployments
---------------------

Deployment of machines at the edge requires the case where we do not control
DHCP. Except there are cases where there might not be any DHCP server,
and in such cases, we must supply networking configuration in the
virtual media being attached to the physical machine being deployed.

IPv6 support
------------

The OpenStack Technical Committee had a goal for the Train cycle for projects
to implement IPv6 testing in order to declare IPv6 support. We as a community
are aware that our IPv6 support works, however the anticipated changes from
a community standpoint were incompatible with the settings required to
emulate physical baremetal.

Also, we have encountered some issues with testing IPv6 support where
existing default binary builds that are published in distributions lack
some of the required support to be enabled.

More information can be found in `change 657174 <https://review.opendev.org/#/c/657174>`_.

Drop Python 2.7 Support
-----------------------

Time has come to remove support for Python 2.7 as upstream security
support for Python 2.7 is being dropped early in the Ussuri development
cycle.
