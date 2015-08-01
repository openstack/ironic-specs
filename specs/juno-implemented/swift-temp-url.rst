..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Swift Temporary URLs
==========================================

https://blueprints.launchpad.net/ironic/+spec/swift-temp-urls

Ironic needs an option to download images securely from
Swift without passing the admin auth token all over the place. Using
Swift temporary URLs, the conductor could create an expiring URL that has
full access to download only a specific image. This is very helpful for the
Ironic Python Agent, because we don't want to send admin auth tokens to all
the ramdisk agents, opening a potential security vulnerability,
but they still need a way to download images.

Problem description
===================

Today, Ironic downloads images to write out directly from Glance. In the
current PXE driver, there isn't a security concern because the images are
downloaded to the conductor and tokens do not have to be passed around. With
the Ironic Python Agent and other drivers like iLO,
images need to be downloaded into the ramdisk.
To download from Glance, an auth token would need to be sent with the
request. In Ironic's case, that would be an admin token, which would allow
the agent to have admin control of other services. Many other services/drivers
in Ironic may want the ability to download from Swift but limit what a
service has access to in a similar fashion.

There is also a scaling benefit to download directly from Swift,
rather than using Glance as an intermediary. The Swift cluster can be scaled
to deal with larger loads without much additional load on the Glance cluster.


Proposed change
===============

The ability to create a signed temporary URL for an image registered in
Glance and stored in Swift which can be downloaded without additional
credentials.

* Given the image info returned by Glance's show command and a previously
  set temporary URL key in Swift, a temporary URL will be created using the
  Swift client library and returned. It will either use the image info's
  direct_url property if set, or a set of config options in Ironic to
  generate the URL.

* The key is generated using a hash of the HTTP methods, the timeout,
  the image path, and the shared key, which is appended to the end of the
  Swift object URL, along with the timeout. No call to Swift or Glance is
  necessary, because it is signing the URL with a shared secret key. The
  actual create of the temp url is handled by python-swiftclient.
  Reference: [1]

* The method will support either constructing the URL from direct_url in the
  Glance image info or a set of config options set in Ironic.

* If direct_url is not enabled, the deployer will need to set config option
  for the scheme to talk to Swift with (http, https), the Swift endpoint URL,
  the path (which includes the API version and the tenant ID),
  and the container that the Glance images are stored in.


Alternatives
------------

* Enable passing admin auth tokens to agents or to host the images in a way
  that the agent would be able to download them.

* A deployer could pass Swift URLs with the username and password in the URL
  itself, which would be less insecure than admin auth tokens,
  but still insecure.

* The images could also be hosted by any web server,
  and that URL could be passed to the agent.

* Ideally, this code should live in keystone-client or oslo,
  so other projects could benefit from temporary URLs as well. We are
  proposing it in Ironic for now, because we need to use it sooner rather
  than later, but it should be moved later.

Data model impact
-----------------

None

REST API impact
---------------

None

Driver API impact
-----------------

None

Nova driver impact
------------------

None

Security impact
---------------

* This code requires a Swift temporary URL key to be set. If this key is
  leaked, it could allow a bad actor to allow public access to anything they
  have access to in Swift.

* A temporary URL gives complete public access to possibly private images
  until the expiration.

* The only allowed HTTP methods are GET and HEAD, so bad actors will not be
  able to modify the images themselves.

Other end user impact
---------------------

None

Scalability impact
------------------

This change should allow better scaling. Swift is highly scalable and
designed to allow you to download large images. This will
lessen the load on the Glance cluster. The main bottleneck would be the
Swift - nodes network links. They could easily be saturated if a large
number of nodes attempt to download an image at the same time.

Performance Impact
------------------

The code is relatively small and self contained.  It requires the result of
a Glance image-show command to make the temporary URL,
however that Glance call may already be required (in the agent driver,
for example). The Glance image-show call in Ironic is here: https://github.com/openstack/ironic/blob/master/ironic/common/glance_service/base_image_service.py#L176.
The temporary URL works via signing the direct-URL (from Glance image-show)
or a URL constructed with the proposed config options with a shared private
key, so apart from this one Glance command, the temporary URL can be
generated. There are no additional database calls required.


Other deployer impact
---------------------

* Deployers will need to set up a Swift cluster and configure Glance to use
  it if they want to take advantage of temporary URLs.

* Either direct_url needs to be enabled in the Glance cluster or
  a list of config options needs to be set to translate Glance image IDs to
  Swift URLs. To configure direct_url: [3]

Required config options:

* swift_temp_url_key: This is the shared private key. It needs to be set up
  on the Swift cluster prior to use. To set up a temporary URL key: [1]

* swift_temp_url_duration: How long the Swift temporary URL is good for. Should
  be set relatively low to prevent allowing images to become public. 5
  minutes should be enough time to start the download and minimize security
  concerns about the URL getting out. The duration will be specified in
  seconds.

Required if direct_url is not enabled in Glance, and the options have no
defaults:

* swift_endpoint_url: The scheme, hostname, and optional port of the
  Swift cluster. For example, "http://example.com:8080".

* swift_path: The API version and tenant ID of the cluster and container
  that Glance images are stored in. For example, "/v1/TENANT_USER_TENANT_UUID".

* swift_backend_container: The Swift container in which Glance stores its
  images.

Developer impact
----------------

This change will allow other driver developers to use Temporary URLs or at
least provide them as an option.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  JoshNang

Work Items
----------

* Address comments on the current patch.

* Add tempest tests

Dependencies
============

* Merging of the python-swiftclient tempurl patch [2]

* Adding python-swiftclient to Ironic's requirements.txt

Testing
=======

* Initially, only unit-testing will be conducted

* This change will also be tested as part of the Ironic Python Agent
  integration testing. It is challenging to test on it's own,
  as it does not present any external APIs for Tempest to test.

Documentation Impact
====================

To implement this feature, Glance using Swift as the image datastore is
required. Swift will also require the tempurl middleware to be configured
for the temporary URLs to work. Swift will need a tempurl key to be set
before this feature can be used, and it needs to be set in Ironic as
swift_temp_url_key. Glance either needs to be configured to
provide direct_url or the operator must set the following config options:

* swift_endpoint_url

* swift_path

* swift_backend_container

The actual signing code is proposed in python-swiftclient.

Detailing how to use Temporary URLs with a Swift cluster and how to
configure Glance to use direct_url would be helpful for deployers. Drivers
that utilize the change should link to these requirements.

References
==========

* Swift Temporary URLs: http://docs.openstack.org/trunk/config-reference/content/object-storage-tempurl.html

* Proposed patch in python-swiftclient: https://review.openstack.org/#/c/102632/

* Glance direct_url configuration: https://github.com/openstack/glance/blob/master/etc/glance-api.conf#L89