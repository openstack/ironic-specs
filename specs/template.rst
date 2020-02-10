..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=================
Title of the Spec
=================

Include the URL of your StoryBoard story (which should have an `rfe`` tag):

https://storyboard.openstack.org/#!/story/XXXXXXX

Introduction paragraph -- start here.

Why are we doing anything? This should be a single paragraph of prose that
operators can understand.

Some notes about using this template:

* Your spec should be in ReSTructured text, like this template.

* Please wrap text at 79 columns.

* Please do not delete any of the sections in this template.  If you have
  nothing to say for a whole section, just write: None

* For help with syntax, see http://sphinx-doc.org/rest.html

* To test out your formatting, build the docs using tox, or see:
  http://rst.ninjs.org

* If you would like to provide a diagram with your spec, ascii diagrams are
  required.  http://asciiflow.com/ is a very nice tool to assist with making
  ascii diagrams.  The reason for this is that the tool used to review specs is
  based purely on plain text.  Plain text will allow review to proceed without
  having to look at additional files which can not be viewed in gerrit.  It
  will also allow inline feedback on the diagram itself.

* If you are unsure whether this proposal is aligned with the project's
  mission and scope, you are encouraged to submit a minimal spec to get
  feedback early, before investing the effort in a complete specification.
  Do this by filling in the `Problem description` and `Proposed change`
  sections and delete the rest of the template. This will fail unit tests,
  but will still get attention from the review team.

* If you do not wish to submit a complete spec (for example, you do not plan
  to complete the spec during this cycle but would like to document the idea)
  you can submit a short spec. It must contain at least the `Problem
  description` and `Proposed change` sections, and may optionally contain any
  other valid sections. Propose this to the `specs/backlog` directory. This
  must follow all other rules of a regular spec (eg, it still requires a
  blueprint, good RST formatting, etc).


Problem description
===================

A detailed description of the problem:

* For a new feature this might be use cases. Ensure you are clear about the
  actors in each use case: End User, Admin User, Deployer, or another Service

* For a major reworking of something existing it would describe the
  problems in that feature that are being addressed.


Proposed change
===============

Here is where you cover the change you propose to make in detail. How do you
propose to solve this problem?

If this is one part of a larger effort make it clear where this piece ends.
In other words, what is the scope of this effort?

If you are unsure whether this proposal is aligned with the project's mission
and scope, stop here.

Alternatives
------------

What other ways could we do this thing? Has someone else done this thing in
another project? In another language? Why aren't we using those? This doesn't
have to be a full literature review, but it should demonstrate that thought has
been put into why the proposed solution is an appropriate one.

Data model impact
-----------------

Changes which require modifications to the data model often have a wider impact
on the system.  The community often has strong opinions on how the data model
should be evolved, from both a functional and performance perspective. It is
therefore important to capture and gain agreement as early as possible on any
proposed changes to the data model.

Questions which need to be addressed by this section include:

* What new data objects and/or database schema changes is this going to
  require?

* What database migrations will accompany this change?

* How will the initial set of new data objects be generated? For example, if
  you need to take into account existing instances, or modify other existing
  data, describe how that will work.

State Machine Impact
--------------------

Interaction between the proposed change and the Ironic state machine should be
documented here.

Questions which need to be addressed by this section include:

* Are you adding or removing any states or verbs?

* Are you changing any state transitions?

* What states are impacted by this change? This includes situations where
  an additional action is being performed on nodes in a given state.

Any change to the state machine is also a REST API change, and should also be
documented accordingly in the next section.

REST API impact
---------------

Each API method which is either added or changed should have the following

* Specification for the method

  * A description of what the method does, suitable for use in user
    documentation.

  * Method type (POST/PUT/GET/DELETE/PATCH)

  * Normal http response code(s)

  * Expected error http response code(s)

    * A description for each possible error code should be included.
      Describe semantic errors which can cause it, such as
      inconsistent parameters supplied to the method, or when a
      resource is not in an appropriate state for the request to
      succeed. Errors caused by syntactic problems covered by the JSON
      schema definition do not need to be included.

  * URL for the resource

  * Parameters which can be passed via the url, including data types

  * JSON schema definition for the body data if allowed

  * JSON schema definition for the response data if any

* Does the API microversion need to increment?

* Example use case including typical API samples for both data supplied
  by the caller and the response

* Discuss any policy changes, and discuss what things a deployer needs to
  think about when defining their policy.

* Is a corresponding change in the client library and CLI necessary?

* Is this change discoverable by clients? Not all clients will upgrade at the
  same time, so this change must work with older clients without breaking them.

Note that the schema should be defined as restrictively as possible. Parameters
which are required should be marked as such and only under exceptional
circumstances should additional parameters which are not defined in the schema
be permitted.

Use of free-form JSON dicts should only be permitted where necessary to allow
divergence in the drivers. In such case, the drivers must expose the expected
content of the JSON dict and an ability to validate it.

Reuse of existing predefined parameter types is highly encouraged.

Client (CLI) impact
-------------------
Typically, but not always, if there are any REST API changes, there are
corresponding changes to python-ironicclient. If so, what does the user
interface look like. If not, describe why there are REST API changes but
no changes to the client.

"openstack baremetal" CLI
~~~~~~~~~~~~~~~~~~~~~~~~~
Changes, if any, to the OpenStackClient plugin, "openstack baremetal" CLI.

"openstacksdk"
~~~~~~~~~~~~~~
Changes, if any, to the `OpenStack SDK
<https://docs.openstack.org/openstacksdk/latest/>`_, `baremetal
<https://opendev.org/openstack/openstacksdk/src/branch/master/openstack/baremetal>`_
methods.

RPC API impact
--------------

Changes which affect the RPC API should be listed here. For example:

* What are the changes, if any, to existing API calls?

* What new API calls are being added? Will these be using cast() or call()?

* ironic-api and ironic-conductor services must be upgradable independently.
  What is the upgrade process for rolling this change out to an existing
  deployment?

Driver API impact
-----------------

Changes which affect the driver API have a direct effect on all drivers, and
often have a wider impact on the system. There are several things to consider
in this section.

* Is it a change to a "core" or "common" API?

* Can all drivers support it initially, or is it specific to a particular
  vendor's hardware?

* How will it be tested in the gate and in third-party CI systems?

* If adding a new interface, explain the intended scope of the proposed
  interface, what functionality it enables, why it is needed, and whether it is
  supported by current drivers.

* If adding or changing a method on an existing interface, the impact on
  existing drivers should be explored.

* Will the new interface or method need to be invoked when the hash ring
  rebalances, for example to rebuild local state on a new conductor service?

* How does this affect upgrades? Third-party drivers could be updated
  independently from this change, and care must be taken not to break
  backwards-compatibility within our Driver API.

Nova driver impact
------------------

Chances are, if this change affects the REST or Driver APIs, it will also
affect the Nova driver in some way. If this requires a functional change in
Nova, chances are the Nova team will require a spec to discuss the changes to
their project as well. Provide a link to that here, or a justification for why
that is not needed.

Questions which need to be addressed in this section include:

* What is the impact on Nova?

* If this change is enabling new functionality exposed via Nova, this section
  should cite the relevant components within other Nova drivers that already
  implement this.

* Ironic and Nova services must be upgradable independently. If the change
  affects existing functionality of the nova.virt.ironic driver, how will an
  upgrade be performed? How will it be tested?

Ramdisk impact
--------------

The ``ironic-python-agent`` project has become an integral component in nearly
every Ironic deployment, and is used throughout the life cycle of each Node
from inspection to deployment and cleaning. There are multiple ways to build a
ramdisk containing this agent which cater to different environments, and
operators are encouraged to build their own ramdisks as well.

In this section, please describe any changes you expect to make to the
``ironic-python-agent`` or its member classes, to the ramdisk build process, or
that otherwise affect the resulting ramdisk and its contents. Be mindful of
the downstream impact this may have, and to the impact on compatibility.

If your change to the ramdisk will also require a change in Ironic, and you
think they should be upgraded together, then you should approach the problem
differently. Forward and backward compatibility, within at least one release,
must be maintained between Ironic and the IPA ramdisk.

This could include changes in any of the following:

* Are you proposing a change to the ironic-python-agent API, or adding an
  extension to it?

* Are you adding a new ironic-python-agent HardwareManager? This is like adding
  a new driver and should be documented, but will probably be easy to accept.

* Are you changing the HardwareManager base class or interface definitions?
  This is considered an API change and needs to be considered closely for
  potential impact on downstream users.

* Are you adding a new extension to IPA? This will require support in Ironic,
  and care will need to be taken to retain compatibility with ramdisks that
  lack this extension.

* Are you adding or changing a method on an existing IPA extension? This is
  likely to break compatibility.

* Are you changing the build process, or proposing a new one?

* If you are adding any new dependencies, explicitly call them out, and
  indicate any expected change in the size of the resulting ramdisk. This may
  affect performance in some environments.

* Are you proposing a change to the hardware inventory returned by
  list_hardware_info? This is part of the interface, and a change here will
  affect out of tree drivers.

* Are you proposing changes to ironic-inspector, or changes that will affect
  it? This is now packaged with the default ramdisk capabilities.

Security impact
---------------

Describe any potential security impact on the system.  Some of the items to
consider include:

* Does this change touch sensitive data such as tokens, keys, or credentials?

* Does this change affect the accessibility of hardware managed by Ironic?

* Does this change alter the API in a way that may impact security, such as
  a new way to access sensitive information or a new way to login?

* Does this change involve cryptography or hashing?

* Does this change require the use of sudo or any elevated privileges?

* Does this change involve using or parsing user-provided data? This could
  be directly at the API level or indirectly such as changes to a cache layer.

* Can this change enable a resource exhaustion attack, such as allowing a
  single API interaction to consume significant server resources? Some examples
  of this include launching subprocesses for each connection, or entity
  expansion attacks in XML.

For more detailed guidance, please see the OpenStack Security Guidelines as
a reference (https://wiki.openstack.org/wiki/Security/Guidelines).  These
guidelines are a work in progress and are designed to help you identify
security best practices.  For further information, feel free to reach out
to the OpenStack Security Group at openstack-security@lists.openstack.org.

Other end user impact
---------------------

Aside from the API and client, are there other ways a user will interact with
this feature?

* Will this require changes in the Horizon panel, or any other OpenStack
  project?

Scalability impact
------------------

Describe any potential scalability impact on the system, for example any
increase in network, RPC, or database traffic, or whether the feature
requires synchronization across multiple services.

Examples of things to consider here include:

* Additional network calls to internal or external services.

* Additional disk or network traffic that will be required by the feature.

* Any change in the number of physical nodes which can be managed by each
  conductor service.

A question an author may wish to ask themselves is what about scales beyond
their current context. We shouldn't afraid to ask "What about in a deployment
10x or 100x larger than any we know of?", or what if the nodes are on the Mars,
and the conductor is running on a satellite in orbit?

Performance Impact
------------------

Describe any potential performance impact on the system, for example
how often will new code be called, and is there a major change to the calling
pattern of existing code.

Examples of things to consider here include:

* A periodic task might look like a small addition, but all periodic tasks run
  in a single thread so a periodic task that takes a long time to run will have
  an effect on the timing of other periodic tasks.

* A small change in a utility function or a commonly used decorator can have a
  large impact on performance.

* Calls which result in one or more database queries (whether in the api or
  conductor services) can have a profound impact on performance when called in
  critical sections of the code.

* Will the change include any TaskManager locking, and if so what
  considerations are there on holding the lock?

* How will the new code be affected if the hash ring rebalances while it is
  running?

Other deployer impact
---------------------

Discuss things that will affect how you deploy and configure OpenStack
that have not already been mentioned, such as:

* What config options are being added? Should they be more generic than
  proposed (for example, a flag that other hardware drivers might want to
  implement as well)? Are the default values appropriate for production?
  Provide an explanation of why these defaults are reasonable.

* Is this a change that takes immediate effect after it's merged, or is it
  something that has to be explicitly enabled?

* If this change adds a new service that deployers will be required to run,
  how would it be deployed? Describe the expected topology, for example,
  what network connectivity the new service would need, what service(s) it
  would interact with, how many should run relative to the size of the
  deployment, and so on.

* Please state anything that those doing continuous deployment, or those
  upgrading from the previous release, need to be aware of. Also describe
  any plans to deprecate configuration values or features.  For example, if we
  were to change the directory that PXE boot files were stored in, how would we
  update existing boot files created before the change landed? Would we require
  deployers to manually move them? Is there a special case in the code, which
  would be removed after some deprecation period? Would we require operators
  to delete and recreate all instances in order to perform the upgrade?

Developer impact
----------------

Discuss things that will affect other developers working on OpenStack,
such as:

* If the blueprint proposes a change to the driver API, discussion of how
  other drivers would implement the feature is required.


Implementation
==============

Assignee(s)
-----------

Who is leading the writing of the code? Or is this a blueprint where you're
throwing it out there to see who picks it up?

If more than one person is working on the implementation, please designate the
primary author and contact.

Primary assignee:
  <IRC handle, email address, or None>

Other contributors:
  <IRC handle, email address, None>

Work Items
----------

Work items or tasks -- break the feature up into the things that need to be
done to implement it. Those parts might end up being done by different people,
but we're mostly trying to understand the timeline for implementation.


Dependencies
============

* Include specific references to specs and/or blueprints in Ironic, or in other
  projects, that this one either depends on or is related to.

* If this requires functionality of another project that is not currently used
  by Ironic, document that fact.

* Does this feature require any new library dependencies or code otherwise not
  included in OpenStack? Or does it depend on a specific version of library?

* Does this feature target specific hardware? If so, is it a common standard
  (eg IPMI) or a vendor-specific implementation (eg iLO)?


Testing
=======

Please discuss how the change will be tested. We especially want to know what
tempest tests will be added. It is assumed that unit test coverage will be
added so that doesn't need to be mentioned explicitly, but discussion of why
you think unit tests are sufficient and we don't need to add more tempest
tests would need to be included.

Is this untestable in gate given current limitations (specific hardware /
software configurations available)? If so, are there mitigation plans (3rd
party testing, gate enhancements, etc)?


Upgrades and Backwards Compatibility
====================================

Care must be taken to support our users by not breaking backwards compatibility
with either REST API or Driver API changes.

* If your proposal includes any changes to the REST API, describe how existing
  clients will continue to function when interacting with an upgraded API
  server.

* If your proposal includes any changes to the Driver API, describe how
  existing driver implementations will continue to function when loaded by a
  conductor running with the new driver base class.

* Describe what testing you will be adding to ensure that backwards
  compatibility is maintained.

* If deprecating an existing feature or API, describe the deprecation plan, and
  for how long compatibility will be maintained.


Documentation Impact
====================

What is the impact on the docs team of this change? Some changes might require
donating resources to the docs team to have the documentation updated. Don't
repeat details discussed above, but please reference them here.


References
==========

Please add any useful references here. You are not required to have any
reference. Moreover, this specification should still make sense when your
references are unavailable. Examples of what you could include are:

* Links to mailing list or IRC discussions

* Links to notes from a summit session

* Links to relevant research, if appropriate

* Related specifications as appropriate (e.g.  if it's an EC2 thing, link the
  EC2 docs)

* Anything else you feel it is worthwhile to refer to
