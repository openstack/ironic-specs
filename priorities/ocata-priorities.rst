.. _ocata-priorities:

========================
Ocata Project Priorities
========================

This is a list of development priorities the Ironic team is prioritizing for
Ocata development, in order of priority. The primary contact listed is
responsible for tracking the status of that work and herding cats to help get
that work done.

+-----------------------------------------+---------------------------------+
| Priority                                | Primary Contacts                |
+=========================================+=================================+
| `Portgroups support`_                   | sambetts, vdrok                 |
+-----------------------------------------+---------------------------------+
| `CI refactoring`_                       | dtantsur, lucasagomes           |
+-----------------------------------------+---------------------------------+
| `Rolling upgrades`_                     | rloo, jlvillal                  |
+-----------------------------------------+---------------------------------+
| `Security groups`_                      | jroll                           |
+-----------------------------------------+---------------------------------+
| `Interface attach/detach API`_          | sambetts                        |
+-----------------------------------------+---------------------------------+
| `Generic boot-from-volume`_             | TheJulia                        |
+-----------------------------------------+---------------------------------+
| `Driver composition`_                   | dtantsur                        |
+-----------------------------------------+---------------------------------+
| `Rescue mode`_                          | JayF                            |
+-----------------------------------------+---------------------------------+
| `Smaller things`_                       | jroll/all                       |
+-----------------------------------------+---------------------------------+

Portgroups support
------------------

This has been in progress for a couple cycles now and is almost complete. It
allows for using bonding to support a single connection over multiple NICs.
Let's get it done in Ocata.

Rolling upgrades
----------------

Many OpenStack projects are beginning to support rolling upgrades - we should
too. Let's do our part to make downtimes a thing of the past. This involves
code changes, new multi-node CI jobs, and reviewer/developer documentation.

Security groups
---------------

This covers security groups on the provisioning network(s). It barely missed
the Newton release and is essentially done, let's finish it in Ocata.

Interface attach/detach API
---------------------------

This makes our API to attach a Neutron port to an Ironic port object a
first-class API, rather than pushing data into a JSON blob. It also refactors
how Nova attaches these ports together. This is a pre-requisite for VLAN-aware
instances, so let's get it done and unblock that for Pike.

Generic boot-from-volume
------------------------

This work allows generic hardware to boot from cinder volumes or NFS, allowing
diskless nodes to be managed by ironic. This also lays down the framework for
hardware-specific implementations to be built.

Driver composition
------------------

This work refactors the way that drivers are composed internally, as well as
allowing operators to mix and match drivers for each interface rather than
guessing at which driver is which combination. This allows us to stop
exploding our driver matrix with every interface addition.

Rescue mode
-----------

This is necessary for users that lose regular access to their machine (e.g.
lost passwords). The spec was merged in Newton, the code is partially done,
let's put some effort into making progress here in Ocata.

CI refactoring
--------------

We have too many jobs, and we have a plan to consolidate those jobs. We need
to do that ASAP, as infra isn't interested in adding more jobs for us until
then.

Smaller things
--------------

There's a number of smaller changes we'd like to accomplish in Ocata, or larger
things that are nearly code-complete. These include:

* etags in the REST API
* spec for ironic-python-agent's REST API versioning
* spec for deploy steps
* spec for specific fault support
* adding more notifications
* soft power off and NMI support
* node tags
