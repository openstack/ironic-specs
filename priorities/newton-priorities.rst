.. _newton-priorities:

=========================
Newton Project Priorities
=========================

This is a list of development priorities the Ironic team is prioritizing for
Newton development, in order of priority. The primary contact listed is
responsible for tracking the status of that work and herding cats to help get
that work done.

+-----------------------------------------+---------------------------------+
| Priority                                | Primary Contacts                |
+=========================================+=================================+
| `Upgrade testing`_                      | jlvillal, mgould                |
+-----------------------------------------+---------------------------------+
| `Network isolation`_                    | jroll, TheJulia, devananda      |
+-----------------------------------------+---------------------------------+
| `Gate improvements`_                    | jlvillal, lucasagomes, dtantsur |
+-----------------------------------------+---------------------------------+
| `Node search API`_                      | jroll, lintan, rloo             |
+-----------------------------------------+---------------------------------+
| `Node claims API`_                      | jroll, lintan                   |
+-----------------------------------------+---------------------------------+
| `Multiple compute hosts`_               | jroll                           |
+-----------------------------------------+---------------------------------+
| `Generic boot-from-volume`_             | TheJulia, dtantsur, lucasagomes |
+-----------------------------------------+---------------------------------+
| `Driver composition`_                   | dtantsur                        |
+-----------------------------------------+---------------------------------+

Upgrade testing
---------------

We claim to support upgrading Ironic from release to release (and cycle to
cycle), however we don't have testing to prove that. This item is specifically
to get cold upgrade testing working, which is necessary for some of the heavier
changes, like network isolation and multi-compute. As a note, we've agreed that
this is important enough to block other work.

Network isolation
-----------------

This feature was designed in Liberty, and much of the code was written. The
code was not ready in time to land in Mitaka. We need to complete this work in
Newton, along with the Nova side of the work. This is one of our biggest
feature asks from users. To be clear, the priority is to land the parts that
were already designed in Liberty/Mitaka, not the future work like
vlan-aware-instances.

Gate improvements
-----------------

There exist other gaps in our gate testing, as well as some refactoring we
wish to do. This includes:

* Switching to tinyipa instead of the CoreOS image.
* Switching to virtualbmc instead of the SSH driver.
* Testing local boot
* Testing agent driver with partition images
* Getting grenade-partial running to test live upgrades (even if it isn't
  stable yet)

Node search API
---------------

This lays the groundwork for the work being done in Nova to allow the Ironic
driver to utilize multiple compute hosts. The search API also helps users query
nodes much more intelligently.

Node claims API
---------------

This lays the groundwork for the work being done in Nova to allow the Ironic
driver to utilize multiple compute hosts. The claims endpoint will help clients
other than Nova schedule to nodes more easily.

Multiple compute hosts
----------------------

This is an effort to allow the Ironic virt driver in Nova scale across many
compute hosts. Currently only one compute host is supported. This shrinks the
failure domain of the nova-compute service in an Ironic deployment, and also
helps schedule Ironic resources more efficiently. Note that this work is in the
Nova codebase, but is an Ironic effort. This will likely depend on work
happening in Nova, specifically the generic resource pools work in the
scheduler.

Generic boot-from-volume
------------------------

This work allows generic hardware to boot from NFS or cinder volumes, allowing
diskless nodes to be managed by ironic. This also lays down the framework for
hardware-specific implementations to be built.

Driver composition
------------------

This work refactors the way that drivers are composed internally, as well as
allowing operators to mix and match drivers for each interface rather than
guessing at which driver is which combination. This allows us to stop
exploding our driver matrix with every interface addition.
