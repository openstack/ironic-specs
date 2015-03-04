..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

====================
Ironic Microversions
====================

https://blueprints.launchpad.net/ironic/+spec/api-microversions

The purpose of this spec is to call out the specific behaviour between
Ironic and python-ironicclient that is required now that we are using
microversions, and to provide guidance how other clients may wish to
interact with Ironic.

Problem description
===================
As a community we are really good at evolving interfaces and code over time
via incremental development. We've been less good at giant big bang drops of
code. The Ironic API is under heavy development, and we want to ensure that
consumers of Ironic's API are able to make use of new features as they become
available, while also ensuring they don't break due to incompatibilities.

Ironic isn't the only OpenStack project implementing microversions, ironically.
Nova[0] is also implementing microversions in parallel for the 'Kilo' release.

The implementation of microversions is currently underway in Ironic, based
around that Nova spec. The implementation in Ironic has already landed[1],
and is currently under implementation for Ironic's primary client,
python-ironicclient[2].

Microversions are implemented in the API through the addition of a new HTTP
header - specifically 'X-OpenStack-Ironic-API-Version'.  This header is
accepted by Ironic so a client can indicate which version of the API it wants
to use for communication, and likewise for Ironic to indicate which version
it is using for communication.

For Ironic, if no HTTP header is supplied, v1.0 (stable/juno) of the API is
used. If an invalid version is specified in the HTTP header, an HTTP 406 Not
Acceptable is returned with an indication of the supported range of
versions[4]. If the special 'latest' version is specified, Ironic will use
its most recent version.

During changes being made to python-ironicclient[2] to support Ironic's
microversions it was discovered that there isn't a formal specification of how
Ironic and a client should interact for varying cases of microversion mismatch
or for an unknown/unspecified microversion.

The need for this spec was discussed in IRC[3], to specifically address the
interaction between Ironic and a client (whether that be python-ironicclient or
any other client).

Proposed change
===============

To address the specific behaviour between Ironic and python-ironicclient, the
following Use Cases are listed to specify the expected functionality.  Please
see the IRC logs[3][5] and this code review[2] for further context for these
Use Cases.

For the purposes of definition, we will use the term "old Ironic" to refer to
a version of Ironic that predates microversions and has no knowledge of them.
Likewise, we will use the term "new Ironic" to refer to a version of Ironic
that includes support for microversions.

Similarly, we will apply such labelling to "old client" and "new client"
respectively.

New Client Default Microversion
-------------------------------
The python-ironicclient provides an option to specify which microversion to
attempt to use for communicating to Ironic. When this is specified, the
requested microversion should be used (unless of course the client cannot
support that version).  This includes 'latest' which is an indication to
Ironic that the latest microversion that ironic knows about should be used.

However if no microversion is specified to the client, it should use the
latest microversion that the client supports.

As part of the initial communication with Ironic it may need to revert to a
lower microversion due to Ironic's support for only older microversions
(as per Use Case 7).

The goal of this requirement is for python-ironicclient / Ironic communication
to "just work" for the user, and if possible, to use the most recent version
of the REST API possible, so that the user is able to make use of the latest
functionality.

Use Case 1: Old Client communicating with an Old Ironic
-------------------------------------------------------
This is exactly the same behaviour that was seen prior to the introduction
of microversions - no change to either the client or server is required
for this case.

* The client makes a connection to Ironic, not specifying the HTTP header
  X-OpenStack-Ironic-API-Version
* Ironic does not check for an X-OpenStackIronic-API-Version header, and
  processes all communication simply as v1.0 (stable/juno)

Use Case 2: Old Client communicating with a New Ironic
------------------------------------------------------
This is where Ironic is updated to a new version that support microversions,
but an old client is used to communicate to it.

* The client makes a connection to Ironic, not specifying the HTTP header
  X-OpenStack-Ironic-API-Version
* Ironic does not see the X-OpenStack-Ironic-API-Version HTTP header
* Ironic communicates using v1.0 (stable/juno) of the REST API, and
  all communication with the client uses that version of the interface.

Use Case 3A:  New Client communicating with a Old Ironic (not user-specified)
-----------------------------------------------------------------------------
This is the where the user does not request a particular microversion to a
new client that support microversions and tries to communicate with an old
Ironic.  The version that the new client uses is the maximum microversion
it supports.

* The user does not specify the microversion to use in communciation with
  the client.  Consequentally, the client attempts to use the latest
  microversion that the client knows about.
* The client makes a connection to an old Ironic, supplying a
  X-OpenStack-Ironic-API-Version HTTP header
* Ironic doesn't look for, or parse the HTTP header.  It communicates using
  the only API code path it knows about, that being v1.0
* The client does not receive a X-OpenStack-Ironic-API-Version header in
  the response, and from that is able to assume that the version of Ironic
  that it is talking to does not support microversions.  That is, it is using
  a version of the REST API that predates v1.0 (stable/juno).
* The client should transparently proceed now that it knows that it is
  commmunicating to an Ironic that can only support v1.0 of the REST API.

Use Case 3B:  New Client communicating with a Old Ironic (user-specified)
-------------------------------------------------------------------------
This is the where the user requests a particular microversion to a
new client that support microversions and tries to communicate with an old
Ironic.

* The user specifies a microversion that is valid for the client.
* The client makes a connection to an old Ironic, supplying a
  X-OpenStack-Ironic-API-Version HTTP header
* Ironic doesn't look for, or parse the HTTP header.  It communicates using
  the only API code path it knows about, that being v1.0
* The client does not receive a X-OpenStack-Ironic-API-Version header in
  the response, and from that is able to assume that the version of Ironic
  that it is talking to does not support microversions.  That is, it is using
  a version of the REST API that predates v1.0.
* The client informs the user that it cannot communicate to Ironic using that
  microversion and exits.

Use Case 4: New Client, user specifying an invalid version number
-----------------------------------------------------------------
This is the case where a user provides as input to a new client an invalid
microversion identifier, such as 'spam', 'l33t', or '1.2.3.4.5'.

* The user specifies a microversion to the client that is invalid.  The client
  should return an error to the user, i.e. the client should provide some
  validation that a valid microversion identifier is provided.

Use Case 5: New Client/New Ironic: Unsupported Ironic version
-------------------------------------------------------------
This is the case where a new client requests a version that is older than
the new Ironic can handle.  For example, the client supports microversions
1.1 to 1.6, and Ironic supports versions 1.8 to 1.15.

  * The client makes a connection to Ironic, supplying 1.6 as the requested
    microversion.
  * Ironic responds with a 406 Not Acceptable, along with the -Min- and -Max-
    headers that it can support (in this case 1.8 and 1.15)
  * As the client does not support a version supported by Ironic, it cannot
    continue and reports such to the user.
  * (An alternative path would be for the client to try and proceed using a
    version acceptable to Ironic. Note that in this case the client should be
    able to proceed since any change that would break basic compatibility
    would likely require a major version bump to v2)

Use Case 6: New Client/New Ironic: Unsupported Client version
-------------------------------------------------------------
This is the case where a new client requests a version that is newer than
the new Ironic can handle.  For example, the client supports microversions
1.10 to 1.15, and Ironic supports versions 1.1 to 1.5.

  * The client makes a connection to Ironic, supplying 1.10 as the requested
    microversion.
  * Ironic responds with a 406 Not Acceptable, along with the -Min- and -Max-
    headers that it can support (in this case 1.1 and 1.5)
  * The client reports this error to the user
  * (An alternative path would be for the client to try and proceed using a
    version acceptable to Ironic. Note that in this case the client should be
    able to proceed since any change that would break basic compatibility
    would likely require a major version bump to v2)

Note: This sceanrio should not occur in practice as the client should always
be able to talk to any version of Ironic.

Use Case 7A: New Client/New Ironic: Negotiated version (not user-specified)
---------------------------------------------------------------------------
This is the case where a new client requests a version that is newer than
the new Ironic can handle, but supports a version that Ironic supports.  For
example, the client supports microversions 1.8 to 1.15, and Ironic supports
versions 1.1 to 1.10.

  * The user has not specified a version to the client
  * The client makes a connection to Ironic, supplying 1.15 as the
    microversion since this is the latest microversion that the client
    supports.
  * Ironic responds with a 406 Not Acceptable, along with the -Min- and -Max-
    headers that it can support (in this case 1.1 and 1.10)
  * The client should transparently proceed, having negotiated that both
    client and server will use v1.10. The client should also cache this
    microversion, so that subsequent attempts do not need to renegotiate
    microversions.

Use Case 7B: New Client/New Ironic: Negotiated version (user-specified)
-----------------------------------------------------------------------
This is a slight variation on Use Case 7, where the user specifies a
specific version to use to communicate with Ironic.

  * The user specifies a particular microversion (e.g. 1.15) that the client
    should use
  * The client makes a connection to Ironic, supplying 1.15 as the
    microversion
  * Ironic responds with a 406 Not Acceptable, along with the -Min- and -Max-
    headers that it can support (in this case 1.1 and 1.10)
  * The client reports this to the user and exits

Use Case 8: New Client/New Ironic: Compatible Version
-----------------------------------------------------
This is the case where a new client requests a version that is supported
by the new Ironic.  For example, the client supports microversions 1.8 to
1.10, and Ironic supports versions 1.1 to 1.12.

  * The client makes a connection to Ironic, supplying 1.10 as the requested
    microversion.
  * As Ironic can support this microversion, it responds by sending back a
    response of 1.10 in the X-OpenStack-Ironic-API-Version HTTP header.

Use Case 9: New Client/New Ironic: Version request of 'latest'
--------------------------------------------------------------
This is the case where a new client requests a version of 'latest' from a
new Ironic.

* The client makes a connection to Ironic, supplying 'latest' as the version
  in the X-OpenStack-Ironic-API-Version HTTP header
* Ironic responds by using the latest API version it supports, and includes
  this in the X-OpenStack-Ironic-API-Version header, along with the -Min- and
  -Max- headers.

Note: It's possible that Ironic provides a response that the client is not able
to correctly interpret.  This is unavoidable, however it enables a client that
is older than the deployed version of Ironic to potentially access all of the
functionality available in that Ironic version.  In this instance, the client
may choose to report to the user the version that Ironic included in the
response, along with the min and max microversions that the client is known to
be able to support. Any parts of the response from Ironic that the client is
not programmed to handle will simply be discarded.

Alternatives
------------
One alternative to microversions is to not have them at all.  What this would
result in would be a group of large changes happening simultaneously, resulting
in unpaired server/client versions not being compatible at all.  It would also
result in less frequent, but larger incompatible API changes.  And nobody wants
that.

Data model impact
-----------------
None.  This change is isolated to the API code.

REST API impact
---------------
As described above, a new HTTP header would be accepted, and returned by
Ironic.

If a client chose to use that header to request a specific version, Ironic
would respond, either accepting the requested version for future communication,
or rejecting that version request as not being supportable.

If a client chose not to use that header, Ironic would assume that the REST API
to be used would be v1.0 (that is, the same API that was present in the 'Juno'
release[6]). This is how the REST API works today.

RPC API impact
--------------
None

Driver API impact
-----------------
None

Nova driver impact
------------------
The current behaviour of python-ironicclient (pass no version header) results
in the Nova driver using v1.0 of our API. The proposed changes to
python-ironicclient will cause the Nova driver to use the latest microversion
that the client supports.  This will make available to Nova any new
functionality we add to Ironic at the point in time when we tag a new client
release.

A future enhancement would be to modify the Nova Ironic driver to specify a
specified microversion to use when communicating to Ironic. This would provide
exact control over which REST API version to consume.

This behaviour should be documented in how Nova and Ironic are gate tested.

There is the potential here to break the nova driver if the incorrect version
is requested.  Consequently, it is important to manage the Nova driver, Ironic
and python-ironicclient version changes.

Security impact
---------------
None

Other end user impact
---------------------
Clients that wish to use new features available over the REST API added since
the 'Juno' release will need to start using this HTTP header.  The fact that
new features will only be added in new versions will encourage them to do so.

Scalability impact
------------------
None

Performance Impact
------------------
None

Other deployer impact
---------------------
None

Developer impact
----------------
Any future changes to Ironic's REST API (whether that be in the request or
any response) *must* result in a microversion update, and guarded in the code
appropriately.

Upgrades and Backwards Compatibility
====================================
As described above.

Implementation
==============

Assignee(s)
-----------

Primary assignees:
::

  lintan - Tan Lin <tan.lin.good@gmail.com>

Secondary assignees:
::

  devananda - Devananda van der Veen <devananda.vdv@gmail.com>
  rloo - Ruby Loo <rloo@yahoo-inc.com>
  mrda - Michael Davies <michael@the-davies.net>
  plus many others

Work Items
----------
Complete the python-ironicclient microversion implementation by:
    #. Add in the highest Ironic microversion that the python-ironicclient can
       support.
    #. If the User does not pass a version, the client should automatically
       try the highest version it supports.  That is, send the
       X-OpenStack-Ironic-API-Version HTTP header with the highest Ironic
       microversion that it supports.
    #. The python-ironicclient should support X.Y and 'latest' as valid API
       versions.

Dependencies
============
None

Testing
=======
It is not feasible for tempest to test all possible combinations of the API
supported by microversions. We will have to pick specific versions which are
representative of what is implemented. The existing tempest tests will be used
as the baseline for future API version testing.

The following combinations should be tested:

* Old client (eg, juno-era client release) against current master branch of
  Ironic
* Latest client (eg, proposed changes to master) against current master branch
  of Ironic
* Latest client (eg, proposed changes to master) against stable/juno Ironic

And we should continue such forwards-and-backwards testing for as long as we
claim to support a given release.

Documentation Impact
====================
No specific documentation impact is identified that is not covered by existing
API change processes.

References
==========

* [0] https://github.com/openstack/nova-specs/blob/master/specs/kilo/approved/api-microversions.rst for details on Nova's microversioning.  Note that this document borrows heavily from that spec. (Thanks cyeoh!)

* [1] https://review.openstack.org/#/c/150821/ and https://review.openstack.org/#/c/158601/

* [2] https://review.openstack.org/#/c/155624/

* [3] http://eavesdrop.openstack.org/irclogs/%23openstack-ironic/%23openstack-ironic.2015-03-03.log#2015-03-03T22:17:26-2015-03-03T23:00:42

* [4] https://review.openstack.org/#/c/160758/

* [5] http://eavesdrop.openstack.org/meetings/ironic/2015/ironic.2015-03-09-17.00.log.txt#17:17:33-17:50:20

* [6] While this is broadly true, at least one change - the addition of the
  'maintenance_reason' field - has been made since the 'Juno' release of
  Ironic
