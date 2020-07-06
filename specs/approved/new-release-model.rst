..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

============================
New Release Model for Ironic
============================

This specification describes the new model of releasing deliverables under the
ironic umbrella, including the Bare Metal service itself.

.. lint: norfe

Problem description
===================

Currently ironic follows the `OpenStack release model`_
*cycle-with-intermediary* that permits us to produce one or more releases per
OpenStack cycle, with the last one in a cycle used as a final release as part
of the OpenStack integrated release (called *named release* in this document,
as it receives a code name). A stable branch is created from this final release
for long-term bug fix support.

As the ironic community is exploring an increasing number of standalone
applications, including ones outside of OpenStack (such as Metal3_), one
problem has become apparent: the stand-alone usage requires not just frequent
feature releases, but rather **supported** frequent feature releases. To be
precise, we would like to produce supported releases every 1-3 months
(2 months is what this spec proposes), where *supported* involves:

* Addressing at least critical issues with a point release. Currently we
  require consumers to switch to the next release, even if it is major.

* A supported upgrade path between releases. Currently only upgrades between
  OpenStack named releases are tested and supported, we need to support
  upgrades between intermediate releases as well.

* Documentation for each release. Currently only documentation for named
  releases (and master) is published.

* An obvious way to consume such releases. Currently deployment tools,
  including even Bifrost, are oriented on named releases or git master.

The proposed model aims to implement these requirements while keeping the
existing commitments around the integrated release.

Proposed change
===============

Terminology
-----------

The following concepts are used throughout this document:

*named release*
    is an integrated OpenStack release that receives a code name and a *named
    stable branch*.
*intermediate release*
    is a release of an ironic deliverable that happens as part of the master
    development (purposely excluding stable releases here) that does not
    correspond to a named release.

    .. note::
        This definition differs from the official OpenStack definition of an
        intermediary release. This is done on purpose to make the wording of
        this document clearer.
*stable branch*
    a branch created from a named release where bug fixes are applied and
    periodically released as *stable releases*.
*stable release*
    is a release created as part of stable support of a *named* release.
*bugfix branch*
    a branch created from an intermediate release that did NOT result in
    a stable branch.

Releasing
---------

* Releases for all deliverables are created on a loose bi-monthly basis, i.e.
  roughly every 2 months. Here *roughly* means that the team may decide to
  release a few days earlier (if the desired scope is already implemented) or
  later (if last minute merges are required).

  This gives 6 releases a year, 3 per each OpenStack cycle.

* Two releases a year correspond to OpenStack named releases, other 4 happen
  between named releases. The former two happens always, the latter 4 can be
  skipped if a deliverable does not see notable changes within 2 months.

* One week of soft feature freeze is observed before every release. *Soft*
  implies that feature can still merge if they are considered low-risk or
  critical for the scope of the upcoming release.

  This leaves merge windows of roughly 7-9 weeks for most features. Plans for
  them should be made during the feature freeze of the previous release.

* Ironic deliverables follow SemVer_ with one clarification: *patch* releases
  are always issued from a stable or bugfix branch (see `Stable branches and
  upgrades`_).  Releases from master always receive a minor or major version
  bump.

  .. note::
    This limitation is required to be able to find a suitable version for a
    branch release. E.g. imagine we cut 21.2.0 from master, then 21.2.1 also
    from master. If then we need to make a release from ``stable/21.2`` (the
    support branch for 21.2.0), there is no SemVer version to use (21.2.0.1
    is still an option, of course, but may conflict with pbr).

* Intermediary (non-named) releases will target standalone users. OpenStack
  deployers will be recommended to use named releases.

Stable branches and upgrades
----------------------------

Service projects and bifrost
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The following procedure will be applied to service projects (ironic and
ironic-inspector), ironic-python-agent and bifrost:

* A stable branch is created from each release:

  * A traditional ``stable/<code name>`` branch for releases that coincide with
    named ones.

  * A ``bugfix/<major.minor>`` branch for other releases.

  The naming difference highlights the difference of intents:

  * *Stable* branches are designed for long-term consumption by downstreams
    (such as RDO) and for users to follow them.

  * *Bugfix* branches are a technical measure to allow patch releases after a
    certain release. Users and downstreams are not expected to follow them
    over a long period of time and are recommended to update to the next
    feature release as soon as it is out.

* Three upgrade paths are supported and tested in the CI for each commit:

  #. Between two subsequent named releases (e.g. *Train* to *Ussuri*).
  #. Between two subsequent intermediate releases.

     .. note:: It's unlikely that we'll be able to use Grenade for that.
               We'll probably use Bifrost instead.

  #. From a named release to any intermediate release in the next release
     cycle.

     .. note:: Supporting this path is technically required to implement CI
               for the other two paths).

.. note::
   Operating CI on the non-named branches may require pinning devstack, tempest
   and ironic-tempest-plugin versions to avoid breakages. It will be determined
   on the case-by-case basis.

Other projects
~~~~~~~~~~~~~~

Library projects (metalsmith, sushy, python-ironicclient and
python-ironic-inspector-client) and networking plugins (networking-baremetal
and networking-generic-switch) will be released and branched as before:

* Releases will be created on demand based on how many useful changes are
  available.

* Only named stable branches will be created, intermediate releases will not
  result in branching.

This procedure matches how libraries are usually released in the Python world.

The CI tools (virtualbmc and sushy-tools) and ironic-tempest-plugin will not
be branched.

Support phases
--------------

* A named stable branch is supported according to the OpenStack policies, which
  is currently 1.5 years of full support followed by extended maintenance.

* Since this proposal significantly increases the number of branches in
  support, we'll tighten the rules around backports to named branches:

  * The first 6 months or until the next named release (whatever comes later)
    any bug fixes are acceptable.

    Low-risk features **may** be accepted if they're believed to substantially
    improve the operator or user experience.

  * The last year and during the extended maintenance phase only high and
    critical bug fixes are accepted.

* Bugfix branches (for deliverables that have them) are supported for 6 months.
  Only high and critical bug fixes are accepted during the whole support time.

  .. note::
    It may mean that a stable branch created earlier will receive more fixes
    than a bugfix branch created later. This is a reflection of the fact that
    consumers are not expected to follow bugfix branches.

* As before, high and critical bug fixes **should** be backported to all
  supported branches once merged to master.

Dependencies
------------

Dependencies handling for named releases and branches does not change. For
example, we keep consuming upper-constraints of a corresponding branch.

For intermediate releases we will consume upper-constraints from a future named
branch. E.g. for Victoria we would consume
https://releases.openstack.org/constraints/upper/victoria.

The inter-service dependencies for both named and intermediate releases must be
expressed separately, both via microversioning or via documentation. We already
provide support for a broad set of versions of projects we can integrate with.

Deprecation policy
------------------

The deprecation policy remains intact: any deprecated functionality can only be
removed after 6 months pass and a **named** release is done.

Alternatives
------------

* Keep the current model, ask intermediate releases consumers to always upgrade
  to the latest one.

Data model impact
-----------------

None

State Machine Impact
--------------------

None

REST API impact
---------------

None

Microversioning is already used as a way to ensure cross-releases API
compatibility.

Client (CLI) impact
-------------------

None

"openstack baremetal" CLI
~~~~~~~~~~~~~~~~~~~~~~~~~

None

"openstacksdk"
~~~~~~~~~~~~~~

None

RPC API impact
--------------

None

Driver API impact
-----------------

None

Nova driver impact
------------------

None

We expect the Nova driver released as part of a certain OpenStack release
series to be compatible *at least* with all Ironic releases from the same
series and with the last release from the previous series.

Ramdisk impact
--------------

Under the proposed model, ironic, ironic-inspector and ironic-python-agent will
get released at roughly the same time. The compatibility rules will be:

Each release of ironic/ironic-inspector is compatible with

* the release of ironic-python-agent that happens at the same time
* the last named release of ironic-python-agent

.. note::
   Supporting releases between these two is very likely but is not officially
   guaranteed nor tested in the CI.

Each release of ironic-python-agent is compatible with

* the releases of ironic and ironic-inspector that happen at the same time
* the last named releases of ironic and ironic-inspector

.. note::
    The first 3 rules are already enforced in the CI, the last will require
    a new job on ironic-python-agent, supposedly based on Bifrost.

The compatibility matrix will be provided through the documentation as part of
the pre-release documentation update and via the future web site.

We will publish ironic-python-agent images corresponding to all stable
branches, named and intermediate (currently images are only published for named
branches) and provide instructions on how to build customized images based on
a certain branch or release.

Security impact
---------------

Supported intermediate releases will also receive security bug fixes.

Other end user impact
---------------------

See `Other deployer impact`_.

Scalability impact
------------------

None

Performance Impact
------------------

None

Other deployer impact
---------------------

Deployers will have faster access to new features if they opt for using
intermediate releases.

Developer impact
----------------

No direct impact. The `Deprecation policy`_ is not changed.

Implementation
==============

Assignee(s)
-----------

The whole team is expected to be responsible for executing this plan, the
primary assignee(s) will coordinate it.

Primary assignee:
  Dmitry Tantsur (@dtantsur, dtantsur@protonmail.com)

Work Items
----------

* Discuss this document with the release team and the TC. Make necessary
  adjustments to our deliverables in the release repository.

* Update the `releasing documentation`_ and publish our release schedule.

* Create new CI jobs as described in Testing_.

* Start publishing ironic-python-agent images from non-named stable branches
  (may work out-of-box).

* Update Bifrost to support installing components from latest published
  releases.

Dependencies
============

None

Testing
=======

Two new family of the CI jobs will be introduced:

* Intermediary upgrade jobs on ironic and ironic-inspector, testing upgrade
  from the last intermediate release branch.

* Backwards compatibility job on ironic-python-agent to test every commit
  against the previous named releases of ironic and ironic-inspector (e.g.
  during the Victoria cycle ironic-python-agent is tested against stable/ussuri
  of ironic and ironic-inspector).

Third party CI jobs are expected to run on the intermediate branches the same
way as they would on master. As soon as support for a specific branch is over,
the 3rd party CI jobs may be turned off for it. Since we are only going to
accept high and critical bug fixes to new branches, only minor load increase
is expected on 3rd party CI systems.

Upgrades and Backwards Compatibility
====================================

See `Stable branches and upgrades`_ and Testing_.

Documentation Impact
====================

To make intermediate releases obviously consumable, we will need a new web
site focused around standalone ironic. It will display the latest versions of
the components and ironic-python-agent images, point at the way to consume them
and provide documentation for each minor or major release.

The `releasing documentation`_ will be updated to follow this model.

References
==========

.. _OpenStack release model: https://releases.openstack.org/reference/release_models.html
.. _Bifrost: https://docs.openstack.org/bifrost/latest/
.. _Metal3: http://metal3.io/
.. _SemVer: https://semver.org/
.. _releasing documentation: https://docs.openstack.org/ironic/latest/contributor/releasing.html
