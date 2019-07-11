..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==================================================
Client Caching Of Negotiated Version
==================================================

https://bugs.launchpad.net/ironic/+bug/1526411

This adds support for caching the version negotiated by the
ironicclient, between itself and the ironic server.  This is supplementary
to the 'api microversion' spec approved in the Kilo release[0].

Problem description
===================

When the ironicclient talks to the ironic server, there may be a mismatch
in supported API versions.  The client and server negotiate a version to be
used in communicating, but since the ironicclient can be used as a user
interactive client, this process of negotiation would be repeated for each
command line invocation.

It would be useful, for each ironic server that the ironicclient talks to,
to cache the version agreed upon for communication, so that each conversation
between client and server does not require renegotiation.

This version caching would need to be per user, for each ironic server (host,
network port pair specific) and would be time-bound (say 5 minutes), so any
future upgrade of the client or server would benefit from supporting newer
available versions.

Proposed change
===============

The proposed implementation consists of caching the negotiated version
information between an ironicclient and ironic server in local file storage
for use by future invocations of the ironicclient.

This information would be cached for a specific period of time, before
becoming stale and ignored.

Specifically, we are proposing:

* Using the dogpile.cache[1] caching system, a pre-existing library that is
  already included in global requirements[2]. It is currently used by
  os-client-config[3], which is used by openstackclient[4].

* Storing the cached information in local file storage, using appdirs[5] to
  provide the correct location

* Indexing the version information in an ironic-server:network-port pair
  (such as 'example.com:1234') so that multiple ironic servers running on
  the same IP address will be cached independently for each user invoking
  python-ironicclient

* Having a default period of 5 minutes for caching version information for
  each ironic server

Storing the version information in a well-known, standardised, local file
storage location means that, if the user wants to, they can remove the cached
version information manually triggering a renegotiation of the version to be
used in communication between the client and server.

Alternatives
------------

An alternative file-based solution was proposed[6], but rejected in favour of
using dogpile.cache.

The suggestion to move to dogpile.cache was made both in the code review[9]
and was discussed in IRC[8].

Reasons for using dogpile.cache included: commonality with existing file
caching libraries used elsewhere in OpenStack, and use of tested common
libraries typically means less bugs.

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

This spec only affects the python-ironicclient, not ironic server.

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

N/A

.. NOTE: This section was not present at the time this spec was approved.

Security impact
---------------

None

Other end user impact
---------------------

None

Scalability impact
------------------

This change potentially reduces network traffic between the client and server
and hence aids scalability.

Performance Impact
------------------

This change potentially reduces network traffic between the client and server
and hence improves latency between when a request is made to ironic and when
the response is received.

Other deployer impact
---------------------

None

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  mrda - Michael Davies <michael@the-davies.net>


Work Items
----------

* The implementation of this spec has already commenced - see [7]

Dependencies
============

None

Testing
=======

Unit tests will be provided to verify this solution

Upgrades and Backwards Compatibility
====================================

None

Documentation Impact
====================

None

References
==========

* [0] API Microversions Spec:
  http://specs.openstack.org/openstack/ironic-specs/specs/kilo/api-microversions.html
* [1] Documentation on dogpile.cache is found here: https://dogpilecache.readthedocs.org/en/latest/
* [2] dogpile.cache is already specified in
  https://github.com/openstack/requirements/blob/master/global-requirements.txt
* [3] https://github.com/openstack/os-client-config
* [4] https://github.com/openstack/python-openstackclient
* [5] Documentation on appdirs is found here: https://pypi.org/project/appdirs
* [6] Original custom file cache solution: https://review.opendev.org/#/c/173674/1/
* [7] Current state of the implementation at the time of this spec being
  raised: https://review.opendev.org/#/c/173674/19
* [8] http://eavesdrop.openstack.org/irclogs/%23openstack-ironic/%23openstack-ironic.2015-05-11.log.html#t2015-05-11T19:38:04
* [9] https://review.opendev.org/#/c/173674/9
