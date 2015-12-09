..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=================================================
Third Party Driver Continuous Integration Testing
=================================================

https://blueprints.launchpad.net/ironic/+spec/third-party-ci

This spec is to define the deadlines, requirements and process of bringing
third party continuous integration testing to ironic.

Problem description
===================

The ironic project wants to make sure that all the drivers in tree are
maintained and of high quality. In order to do this, it has become necessary
to require that all drivers have a continuous integration test system to test
the driver against every code change proposed for ironic, unless that change
is to code or documentation that can not impact the driver. Required tests
to be run by each driver test system will be documented in the ironic CI
requirements documentation. Not all drivers are provided or maintained by
third party vendors.

Third party vendors must provide and maintain this CI for drivers they
maintain. Any driver whose maintainer is not able to implement a reliable CI
system to test will be removed from the ironic tree.

A driver test system will be deemed reliable if it runs the expected tests and
reports the results of those tests consistently over a period of time. Tests
will be expected to complete and report back to gerrit within 8 hours of the
patch submission until the end of N release and within 4 hours by the end of O
development cycle.

A driver test system will be deemed reliable if:

* It runs the expected tests for every patch set that is not excluded. Reasons
  for this exclusion will be documented and approved by the ironic team.

* It reports the results within the expected time frame, see above.

* All required test artfacts are posted in a standard format and made available
  to the community following the infrastructure requirements.[3]

* Test results (pass or fail) are accurate.

Proposed change
===============

The ironic team has decided to require all driver maintainers to run and
maintain CI test systems in order to have their driver code remain in the
ironic source tree. When there are problems with the CI system, the driver test
team will make a best effort to respond to questions about their system and to
fix the system quickly. If the driver test team is not responsive, any voting
privileges for the test system may be removed, and may eventually result in the
driver being removed from the source tree.

Timeline
--------

The process to implement and start enforcing third party driver CI is to be
completed by the end of the N development cycle.

Deliverable milestones:

* Immediately: Driver teams contacted and notified of expectations.

* Mitaka-2 milestone: Driver teams will have registered their intent to run CI
  by creating system accounts and identifying a point of contact for their CI
  team.

* Mitaka Feature Freeze: All driver systems show the ability to receive
  events and post comments in the third party CI sandbox.

* N Feature Freeze: Per patch testing and posting comments.

Please refer to the Mitaka release schedule[5] for specific dates. Note that
the ironic project does not strictly follow the official OpenStack release
cycle deadlines, but we are using the official deadlines as a reference point.

Infra CI will continue to test the ssh drivers already being used in the gate.

Third party driver teams that do not implement a reliable reporting CI test
system by the N release feature freeze (see Deliverable milestones above) will
be removed from the ironic source tree. Driver test systems that miss any of
the milestones may be subject to immediate removal from the source tree.

Driver test systems will be required to initially run a test similar to the
`gate-tempest-dsvm-ironic-pxe_ipa` test, with the only difference being
changes to drivers loaded, etc, to make ironic work with the driver under
test.

More information about this and other required tests will need further
documentation.

Initial driver test systems will not be allowed to vote on changes to ironic.
A driver test team may ask that their CI system be allowed to vote only if the
ironic team approves based on the test team's participation, availability and
history of reliable operation.

Driver test systems will be expected to follow the Infrastructure Third Party
test requirements[3], unless overridden here or in the ironic third party
driver testing documentation produced as a result of this spec.

Community-maintained drivers that do not have CI testing will also be removed
from the ironic source tree.

Alternatives
------------

None

Data model impact
-----------------

None

State Machine Impact
--------------------

None

REST API impact
---------------

None

Client (CLI) impact
-------------------

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

Security impact
---------------

None

Other end user impact
---------------------

None

Scalability impact
------------------

None

Performance Impact
------------------

None

Other deployer impact
---------------------

When upgrading to the release that drops untested drivers, if a deployer is
using a driver that is removed from the tree, they will need to change to an
in-tree driver or install the removed driver from a new location, if one
exists.

The Ironic team must communicate which drivers are being removed, and when. We
should note that these drivers *may* be available at a new location, and that
driver authors *may* be communicating that information.

Authors of a driver removed from tree may communicate the new location, if one
exists, and document how to install the driver into an ironic environment.

Developer impact
----------------

Developer impacts may include core reviewers needing to wait until testing
for a system completes before approving a patch for merge. Developers that
had a test fail will need to review the test artifacts for their patch linked
to the comment left in the patch comment log. If necessary, the developer may
need to coordinate with the driver test team for help with debugging the
problem. See Infra requirements in the References section below.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  krtaylor

Other contributors:
  jroll, thingee

Work Items
----------

1. Communicate intention to vendors with existing drivers in tree - make a
   reasonable effort to contact the entity responsible for the driver and
   inform them of the timeline to require driver third party CI.

2. Set incremental timeline milestones for vendors to implement CI testing.

3. A deprecation process will need to be documented.

4. Document process, requirements - this spec is not meant to exhaustively
   enumerate all requirements, just to define that they need to be documented.

5. The documentation will also need to describe the way in which a test system
   proves they are adequately testing their driver.

6. Assemble and maintain list of contacts for all in-tree drivers.

7. Remove third party drivers that do not implement a CI test system as per the
   schedule listed above.

8. Document impacts to ironic deployers and developers that the driver they may
   have been using was removed from tree, as per the deployer impact section.

Dependencies
============

None

Testing
=======

As described in this spec.

Upgrades and Backwards Compatibility
====================================

There will be a major upgrade impact on deployers using drivers that are
removed from tree; see the "Deployer impact" section for more info.

A deprecation process will be documented including timeline.

Documentation Impact
====================

There will be several areas impacted:

1. Document drivers in tree and their expected functionality.

2. Document requirements for the third party drivers systems, expectations,
   time thresholds, tests required to be run, and other topics as needed.

3. Document an example implementation of the third party test system
   infrastructure.

4. Document the process to notify the community and users that a driver
   will be removed from tree.

5. Document more information about the required tests

References
==========

[1] Third Party CI working group
https://wiki.openstack.org/wiki/ThirdPartyCIWorkingGroup

[2] Third party CI meetings
https://wiki.openstack.org/wiki/Meetings/ThirdParty

[3] Infra requirements documentation for implementing a third party system
http://docs.openstack.org/infra/system-config/third_party.html#requirements

[4] Discussion at Mitaka summit
https://etherpad.openstack.org/p/summit-mitaka-ironic-third-party-ci

[5] Mitaka release schedule:
https://wiki.openstack.org/wiki/Mitaka_Release_Schedule
