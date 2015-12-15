..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===================================================
HTTP(S) proxy support for agent images downloading
===================================================

https://bugs.launchpad.net/ironic/+bug/1526222

This adds support of proxy configuration for images downloading by
agent.

Problem description
===================

Currently Ironic Python Agent (IPA) is able to download images via direct
HTTP(S) links, but it does not support proxy configuration. If IPA will support
proxy configuration for image downloading user can place caching proxies in
the same physical network segments as nodes for reducing owerall network
traffic and deploying time.
There are two different types of image sources when Ironic does deploy with
IPA: Glance UUID and HTTP(S) URL. When HTTP(s) URLs are used so we can simply
utilize HTTP(S) proxy configuration parameter, additional Ironic features
are not needed. When we use Glance UUIDs there is a problem with Swift
temporary URLs, because current time is used for temporary URLs calculation.
In the proxy servers requests with query string parameters are cached
separately for each unique query string, therefore if Swift temp URL's are used
images can not be cached efficiently on the proxy server side.

Proposed change
===============

Three new optional parameters: ``image_http_proxy``, ``image_https_proxy`` and
``image_no_proxy`` will be added to agent deploy driver. First two parameters
are strings with format "PROTOCOL://PROXY_IP:PROXY_PORT". ``image_no_proxy``
is a list of comma-separated URLs that should be excluded from proxying.
New behavior of agent deploy driver methods:

* get_properties() - returns description of new parameters.

* validate() - validate new parameter(s) (if present).

* continue_deploy() - add "proxies" and "no_proxy" keys in the "image_info"
  dict if parameter(s) present::

    proxies = {'http': 'http://192.168.0.2:8080',
               'https': 'https://192.168.0.3:4444'}

    no_proxy='192.168.1.5,10.0.0.3'

If "proxies" key is present IPA adds a parameter to requests.get() method.
Requests library supports "no_proxy" only as environment variable, not as a
get() parameter. If "no_proxy" parameter is set agent should add it to Python's
"os.environ" before get() call.

Swift Temporary URL changes:

For caching proxies different URLs are mapped to different files in the cache.
Therefore caching of Swift Temporary URLs for images should be implemented on
the conductor. When a temporary URL for image is created agent driver stores it
into the cache with UUID of Glance image as a key. Agent driver uses URL from
cache for same UUIDs and checks expiration of temporary URLs.
New integer config parameter ``swift_temp_url_cachetime`` will be added to
``glance`` group. If it greater than zero agent driver enables caching
of URL's and use it's value for new temp URL duration.

Notes about proxy service:

* Proxy should support HTTP/1.1 chunked transfer encoding.

* For SSL image URLs proxy should be configured for termination of SSL
  connection from client on the proxy side.

* Caching of large files should be enabled on the proxy.

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

Decrypting of HTTPS data on the proxy server side is not recommended for images
which contain confidential information.

Other end user impact
---------------------

None

Scalability impact
------------------

Proxy support for image downloading by agent can improve scalability (reduce
network traffic and time of deploy) in proper configured environment.

Performance Impact
------------------

None

Other deployer impact
---------------------

* New optional parameters will be added for agent deploy driver in the
  node.driver_info: ``image_http_proxy``, ``image_https_proxy``,
  ``image_no_proxy``.

* A new config option ``swift_temp_url_cachetime`` will be added in ``glance``
  group.

* Deployer must install and configure proxy service(s).

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

* Implement proxy parameters for IPA deploy driver.

* Implement Swift Temporary URLs cache.

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

Usage of agent's proxy configuration will be documented.

References
==========

.. [#] http://docs.python-requests.org/en/latest/user/advanced/#proxies
