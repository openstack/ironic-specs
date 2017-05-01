..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==================================================
ironic-python-agent API Versioning and Negotiation
==================================================

https://bugs.launchpad.net/ironic/+bug/1602265

It was decided at the ironic newton midcycle that we need some form of API
version negotiation between ironic and IPA. This is required to allow ironic to
recognise that it is talking to an older ramdisk, and that newer features will
not be available.

Problem description
===================

During ironic upgrade it's possible that you will end up with node which uses
an version of the ironic-python-agent (IPA) older than the version of ironic.
In this case newer features that have been added to ironic and IPA will be
expected to exist by ironic however because the ramdisk used on a node has not
been upgraded yet, those features do not exist in that version of IPA. This
leads to failures because ironic tries to use these features during
deployment/cleaning and resulting in unexpected responses from IPA.

Proposed change
===============

The proposed change is that when IPA does its heartbeat to ironic it will
include an IPA version number that will be cached by ironic in the node's
``driver_internal_info`` in the same way as the Agent URL is stored. ironic
will then use this version information to gracefully degrade the feature set
that it uses from the ironic-python-agent. For example::

  def do_something_using_IPA(self)
    # Make sure to refresh the node object in case agent_version has changed
    # via a heartbeat since we first fetched the node.
    node = self.node.refresh()
    if node.driver_internal_info.get('agent_version', '0.0.0') >= '1.2':
      do_new_additional_thing_only_supported_in_1.2()
    do_thing_using_IPA()

Alternatives
------------

A couple of alternatives exist:

* Require that operators update every node's ramdisk to the newer version of
  the ramdisk with the new features before upgrading their ironic installation.

* Handle the cases where IPA doesn't support a particular feature by catching a
  set of expected errors on a case by case basis and gracefully fall back to
  another method. However in cases where this occurs it will result in more
  complex error handling in Ironic and extra API calls to IPA.

Data model impact
-----------------

New ``agent_version`` field will be be stored in ``node.driver_internal_info``
on agent heartbeat.

State Machine Impact
--------------------

In the existing code the cleaning step checks the IPA hardware manager version
and if it changes for any reason during the cleaning process, then cleaning is
aborted and will need to be restarted. The agent version being added by this
spec should be treated in the same way to ensure the most stable environment
for cleaning.

REST API impact
---------------

A new field ``agent_version`` will we included in the body of the heartbeat API
request alongside the existing ``agent_url`` field.

Client (CLI) impact
-------------------

None

"ironic" CLI
~~~~~~~~~~~~

None

"openstack baremetal" CLI
~~~~~~~~~~~~~~~~~~~~~~~~~

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

Ramdisk impact
--------------

IPA will need updating to include its current version in the ``agent_version``
field when it makes a heartbeat request.

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

This change will allow for deployers upgrading their ironic installs to upgrade
their node's ironic-python-agent ramdisk's asynchronously from the rest of
ironic.

Developer impact
----------------

Developers of ironic drivers that interact with the ironic-python-agent will
need to ensure their code takes into account the agent version that they might
be talking to. Making sure that if talking to an IPA that does not support a
feature it disables that feature in ironic.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  sambetts

Work Items
----------

- Add code to IPA to send its version to ironic in the heartbeat request
- Add code to ironic to accept and store the ``agent_version`` when it receives
  a heartbeat
- Add developer documentation on the correct way to add support for an IPA
  feature in ironic, such that it will gracefully degrade if it is not
  available.

Dependencies
============

None

Testing
=======

- ironic grenade tests already test ironic master with the last named release
  IPA
- Normal ironic/IPA tests will test ironic master + IPA master builds
- Need to add a grenade test to IPA to test last ironic named release + master
  IPA

Upgrades and Backwards Compatibility
====================================

- This spec adds the ability to better support Ironic version N+1 with IPA
  version N or older as Ironic will gracefully degrade which features it will
  request if they aren't available
- Ironic version N works with IPA version N+1 and should continue to work

Documentation Impact
====================

- Need to add the developer documentation mention in the work items section
- Need to document which versions of IPA are supported with which versions of
  ironic.

References
==========

- https://etherpad.openstack.org/p/ironic-newton-midcycle
