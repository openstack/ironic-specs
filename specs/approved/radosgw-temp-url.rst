..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=====================================
Ceph Object Gateway Temp URL support
=====================================

https://blueprints.launchpad.net/ironic/+spec/radosgw-temp-url

This blueprint adds support of Ceph Object Gateway (RADOS Gateway) temporary
URL format.

Problem description
===================

Ceph project is a powerful distributed storage system. It contains object store
with OpenStack Swift compatible API. Glance image service can use Ceph storage
via RADOS Gateway Swift API.
Ironic does not currently support deploy configuration with Glance and RADOS
Gateway. The reason is different format of temporary URL. First part of
temporary URL for RADOS Gateway with Glance frontend is
"endpoint_url/api_version/container/object_id", where

* "endpoint_url" contains scheme, hostname, optional port and mandatory
  "/swift" suffix.

* "api_version" is "v1" currently.

* "container" is the name of Glance container.

* "object_id" is Glance object id.

Calculation of parameters "temp_url_sig" and "temp_url_expires" is mostly the
same as in Swift, so full URL looks like

"https://radosgw.my.host/swift/v1/glance/22aee8e5-cba3-4554-92c4aadde5e38f28?
temp_url_sig=e75d1d6facb53d795547b1fc60eca4e8836bd503
&temp_url_expires=1443518434"

"temp_url_sig" calculation should not use "/swift" in the path.

OpenStack Swift temporary URL contains extra account parameter, it's account
that Glance uses to communicate with Swift. "swift_account" parameter is
mandatory for Ironic.

.. note::
    Do not use Python code as reference from
    http://docs.ceph.com/docs/master/radosgw/swift/tempurl/
    it does not create valid URL's, for Firefly release at least.

Proposed change
===============

A new configuration parameter ``temp_url_endpoint_type`` will be added to
the ``glance`` group. It can be set to values "swift" or "radosgw", "swift" is
default.
Code of image service in Ironic will be changed for supporting both of
endpoints (parameters set, mandatory suffix for RADOS Gateway).

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

* A new config option ``temp_url_endpoint_type`` will be added in ``glance``
  group.

* Deployer should configure Glance with RADOS Gateway beckend (via Swift API)
  and Ceph storage.

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  yuriyz


Work Items
----------

* Implement Rados GW support.

* Add unit tests.

Dependencies
============

None

Testing
=======

Unittests will be added.

Upgrades and Backwards Compatibility
====================================

None

Documentation Impact
====================

Usage of Ironic with Rados Gateway as Glance backend will be documented.

References
==========

* http://docs.openstack.org/kilo/config-reference/content/object-storage-tempurl.html
