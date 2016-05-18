..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

============================================
Move Ironic to a feature-based release model
============================================

https://blueprints.launchpad.net/ironic/+spec/feature-based-releases

At the Liberty design summit in Vancouver, the Ironic team generally agreed
to move the Ironic project to a feature-based release model.[0] This is an
informational spec to lay out why we are doing this and how it will work.


Problem description
===================

Ironic currently uses the traditional OpenStack release model.[1]
This involves:

* One release every six months.

* A feature freeze prior to cutting this release, typically for a duration
  of six weeks. Only bug fix work and docs work should be done in this period.

* An optional spec freeze a few weeks prior to the feature freeze.

* After the feature freeze period, a stable branch is forked from master and a
  release candidate period begins. Critical bugs fixed on master during this
  period may be backported to the stable branch for the final release.

* After about four weeks of iterating on release candidates, the final version
  is released. This stable release may receive critical bug fixes for a longer
  period of 9-15 months.

This model creates a few problems. The primary problem created is that
development happens in peaks and valleys. Developers and vendors realize that
the feature freeze is coming up, and attempt to merge features quickly before
the freeze. This creates a flurry of both patches and reviews, which has the
tendency to burn out core reviewers. Then feature freeze begins. Features
cannot be landed and development slows, almost to a halt. This typically takes
six weeks. Once the next cycle opens for feature development, code starts to
trickle through but most folks are working on summit planning and taking a
break from the stress of the last release. This essentially causes *10 weeks*
of developer downtime *per cycle*, or 20/52 weeks per year.


Proposed change
===============

We should release Ironic (roughly) following the independent release model
defined by the OpenStack governance.[2]

.. note::
    As of July 15, 2015 [10], ironic follows the cycle-with-intermediary
    release model [11]. This model, which better matches this specification,
    was created by the OpenStack governance after this specification had been
    approved.

There are a few things of note here.

* We should release Ironic when major features or bug fixes are complete on
  the master branch. This will be at the discretion of Ironic's PTL or a
  designated release manager.

* We should continue to release a "final" release every six months,
  to continue to be part of the coordinated release.[3]

* In lieu of a feature freeze, Ironic's "stable" release should come from a
  "normal" Ironic release that happens around the same time that other
  integrated projects begin the release candidate period. For example, for
  Liberty[4], Ironic should aim to make a release in the second half of
  September. This will become equivalent to the stable/liberty branch.
  Release candidates should be built from this branch and may receive bug
  fixes. Stable releases should be eligible for receiving backports following
  the current process.

* Ironic releases should roughly follow SemVer[5] -- the difference being that
  the major version should be bumped for significant changes in Ironic's
  functionality or code. Ironic should never do a release without an upgrade
  path from a prior release, so in traditional SemVer the major version would
  never change. We should bump minor and patch versions as needed for
  minor feature and bug fix releases.

* Ironic releases should be published to PyPI.

* Specs should be no longer be targeted to a particular release -- folks
  should just work on specs and code continuously. Features will be released
  as they land. The ironic-specs repo should change to:

    * One "approved" directory where all specs live initially.

    * Separate $version-implemented directories that house the specs that were
      implemented in $version of Ironic. Specs are moved to this directory when
      the work is completed.

    * Create a placeholder in the old location which indicates which release
      of Ironic the work was completed in, with a link to the new location.
      This will keep older links from breaking.

* Leading up to all releases, reviewers should honor a "soft freeze" period of
  a few days to a week. Code that is risky in terms of breakage should probably
  not land at this time; quick bug fixes, driver changes, and other less risky
  changes should be okay to land in most cases. The PTL or designated release
  manager must be sure to communicate upcoming releases and these freezes well.

* Ironic may need to decouple from global requirements during Dep Freeze[7].
  During OpenStack's feature freeze, the master branch of global-requirements
  is locked. It should be okay to accept changes to Ironic's requirements.txt
  on the master branch that are blocked in global-requirements by the Dep
  Freeze, as the stable branch has already been cut by this point.
  This should only happen on an as-needed basis as the problem arises; not
  by default. We also may need to temporarily drop the
  "gate-ironic-requirements" job during this time. Finally, any patches to
  Ironic changing requirements.txt should also have a patch to
  global-requirements with a general "looks good" from a global-requirements
  core reviewer.

* Folks have discussed using feature branches for larger chunks of work. While
  these can be useful, we must be sure to only use them when absolutely
  necessary as feature branches can carry a large amount of pain. We should
  prefer feature flags[9] over feature branches where possible.

Alternatives
------------

Continue on the status quo. :(

Data model impact
-----------------

None.

State Machine Impact
--------------------

None.

REST API impact
---------------

None.

Client (CLI) impact
-------------------

None. The client will continue to release independently, and likely more often
than the server.

RPC API impact
--------------

None.

Driver API impact
-----------------

None.

Nova driver impact
------------------

As the Nova driver is released with Nova, it will not change in terms of the
way it is released.

Security impact
---------------

As only stable releases will receive backports, security bugs in other releases
should be fixed and released ASAP. An advisory should be published that
encourages users to upgrade to the new release.

Stable branches should continue to receive backports for security bug fixes.

Intermediate releases will not receive backports for security patches. Any
security bug in an intermediate release should be fixed and released with
the appropriate version bump. Whether the version change is major/minor/patch
may depend on what else has landed on master and will be released with the
patch.

Other end user impact
---------------------

End users will get features shipped to them more quickly.

Scalability impact
------------------

None.

Performance Impact
------------------

None.

Other deployer impact
---------------------

Deployers will receive changes and features more quickly. Those that do not
wish to do so may continue to consume the six-month integrated release.

Developer impact
----------------

All the productivity.


Implementation
==============

Assignee(s)
-----------

PTL, designated release manager (if one exists), and core reviewers.

Work Items
----------

* Switch to semver.

* Start releasing independently.

* Document the process in the developer docs.[8]


Dependencies
============

None.


Testing
=======

None.


Upgrades and Backwards Compatibility
====================================

This should cause upgrades to be smaller and thus less impactful.


Documentation Impact
====================

We should write a page in our developer docs about the process, including the
changes to the specs process.


References
==========

[0] https://etherpad.openstack.org/p/liberty-ironic-scaling-the-dev-team

[1] http://governance.openstack.org/reference/tags/release_at-6mo-cycle-end.html

[2] http://governance.openstack.org/reference/tags/release_independent.html

[3] http://governance.openstack.org/reference/tags/integrated-release.html

[4] https://wiki.openstack.org/wiki/Liberty_Release_Schedule

[5] http://semver.org/

[6] http://lists.openstack.org/pipermail/openstack-dev/2015-May/065211.html

[7] https://wiki.openstack.org/wiki/DepFreeze

[8] http://docs.openstack.org/developer/ironic/

[9] https://en.wikipedia.org/wiki/Feature_toggle

[10] https://review.openstack.org/#/c/202208/

[11] http://governance.openstack.org/reference/tags/release_cycle-with-intermediary.html
