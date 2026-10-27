..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=====================================
Add support for configdrive checksums
=====================================

https://bugs.launchpad.net/ironic/+bug/2168078

Problem description
===================

Recently a security report was filed with Ironic which could be summed
up as "your ansible deploy interface doesn't checksum configuration drives"!

Which is valid. Except... We don't have the framework to declare a checksum
when a pre-built configuration drive is sent to Ironic, nor do we have the
ability to then know what the checksum is that we need to enforce in later
steps.

Part of this is because configuration drive usage and modeling has evolved
over time. Which is fine, but it has gone from a binary blob, to a url, to a
JSON dictionary. We still present the base model and users do what they need.
Meaning the question is, how do we enable increased security and control,
without breaking the user experience.

Proposed change
===============

In order to provide options, we're proposing a new field which can be provided
at deploy time which allows for explicit declaration of the "checksum" of the
configuration drive contents, and that ironic will verify the result and store
that result for later verification if needed in the overall flow of deployment
sequence, or even if Ironic needs to amend the configuration drive to correct
contents.

In this model, we'll accept a new field value on the
``/v1/nodes/<node>/states/provision`` endpoint with a name of
``configdrive_checksum`` which is a length detected format pattern, typical
in other checksum handling, and then apply that to the data where applicable.

In Ironic's model, this requires that value to potentially be updated as time
progresses, but ideal cases where we would want this is when the configdrive
is supplied as a URL *or* as a blob transmitted into the field.

Optionally, we'll add a new configuration option,
``[deploy]require_configdrive_checksum`` which makes the lack of a checksum
an explicit failure deployment attempts are to fail upon.

The new checksum to be tracked will be stored in the node ``instance_info``
field, alongside the configdrive contents or reference.

Alternatively, when not explicitly enforced, Ironic will need to record and
enforce the checksum value identified and transferred over. This may force
the conductor to download the configuration drive shortly after the
deployment request is received in order to detect any chance of the config
drive changing.

This change *will* require a microversion increase of Ironic's API, and
will also require relatively minor changes in all deploy interfaces which
leverage configuration drives so checksums are verified prior to the instance
being handed over to the end user.

Alternatives
------------

Ultimately there is no other way to do this given our flexibility, this also
shifts the declaration to users, while balancing detection and surfacing
deployment errors and potential changes to the user so they can respond
accordingly.

Data model impact
-----------------

No new high level fields are required, however a node ``instance_info``
subfield will be required.

State Machine Impact
--------------------

None.

REST API impact
---------------

As noted, a new field will be added to the
``/v1/nodes/<node>/states/provision`` endpoint, which allows a
``configdrive_checksum`` to be declared by the user and recorded by
Ironic when supplied.

This will require a microversion handling, and Ironic to still record,
track, and enforce the resulting checksum even if the API user does not
supply a checksum with the deployment request. The precise microversion
number is not yet known and will be determined during implementation.

An invalid checksum value will result in a failed provision, but that is
not anticipated to be validated until after the initial request has been
validated. First pass content validation may also take place, with the
expectation that only SHA-256 (64 characters) or SHA-512 (128 characters)
checksums are supported, detected by length. Furthermore, this
field shall not permit a *remote* url, as that would require Ironic to
retrieve and enforce the checksum immediately, and would otherwise open
the door to a man-in-the-middle substitution of the configuration drive
contents between declaration and retrieval.

Client (CLI) impact
-------------------

"openstack baremetal" CLI
~~~~~~~~~~~~~~~~~~~~~~~~~

The CLI changes will be required to enable supplying a checksum when
deployments are requested.

"openstacksdk"
~~~~~~~~~~~~~~

This change will require an additional field to be added to the SDK
which a user can supply a value to if needed.

RPC API impact
--------------

This requires an additional value to be able to be passed over the RPC bus
which will require RPC changes. This is a known pattern to add an additional
value to RPC requests, and upgrades will need to navigate that as well.

Driver API impact
-----------------

None

Nova driver impact
------------------

Nova as of 2026.2 *does* still generate a configuration drive blob and post
the file to Ironic. This will likely need to be augmented, but the work is
intended to be disjointed and record the checksum when submitted directly
to the API anyhow.

Ramdisk impact
--------------

The ironic-python-agent project will need to be aware of the value,
and enforce it in it's workflow, which means a suddenly detected mismatch,
for example if a file on remote server somehow changes, then a deployment
may fail, but that is the desired behavior.

Security impact
---------------

This change improves the overall security posture of the system by
recording, checking, and enforcing the checksum value of a configuration
drive being worked with prior to being written to an instance's disk.

Other end user impact
---------------------

None anticipated.

Scalability impact
------------------

None.

Performance Impact
------------------

This change may result in a slightly slower API and/or conductor depending on
the precise location of checksum computation in a fallback case, but that is
anticipated to be relatively trivial.

Other deployer impact
---------------------

None.

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Julia "TheJulia" Kreger

Other contributors:
  Any volunteers?

Work Items
----------

* Implement support for a declared configuration drive in ironic-python-agent.
* Implement ironic-python-agent version handling for an enhanced IPA version.
* Implement auto-checksuming of configuration drive content, and passing to
  ironic-python-agent.
* Implement Rest API and RPC API changes to enable this functionality.
* Update the REST API reference documentation for the new field and
  configuration option.

Dependencies
============

None.

Testing
=======

Unit testing is expected, but this model is anticipated to functionally be on
and enforced by default unless the ironic-python-agent version cannot support
enforcement.

Upgrades and Backwards Compatibility
====================================

No issues anticipated here.

Documentation Impact
====================

The rest API reference will need to be updated.

References
==========

None.
