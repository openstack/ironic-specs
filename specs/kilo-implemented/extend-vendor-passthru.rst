..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

======================
Extend Vendor Passthru
======================

https://blueprints.launchpad.net/ironic/+spec/extend-vendor-passthru

Make the VendorPassthru and DriverVendorPassthru more consistent
and extend it to support running vendor methods synchronously and
asynchronously as well as different HTTP methods apart from POST.

Problem description
===================

The VendorPassthru and DriverVendorPassthru are inconsistent. VendorPassthru
methods are asynchronous and DriverVendorPassthru methods are synchronous.

In addition, right now each driver is responsible for implementing
their own method that will invoke their vendor methods and they ended up
duplicating a lot of code and also doing things like raising different
exceptions for the same type of error. Also, some of them are logging the
errors raised by the vendor methods or converting non-Ironic exceptions
to Ironic exceptions and others are not.

Apart from that both endpoints only support one HTTP method: POST. It
would be good to extend it to support other HTTP method because some
drivers may want to use them. One example would be the iPXE driver where
supporting GET would be beneficial because the iPXE script could request
a GET in the Ironic API which would return what kernel and ramdisk should
be booted and the script can chainload it from there.

Another problem is that currently the vendor methods are not discoverable
via out API, there's no way to know what are the methods being currently
exposed by the drivers.

Proposed change
===============

The first change is to have a generic way to run the vendor methods, and
this should be responsible for logging and converting exceptions in case
a non-Ironic exception has been raised. The way this blueprint wants to
do that is by creating a decorator to decorate the vendor methods and
wrap it with a custom code that will take care of those.

The second part will extend the new decorator to add some metadata
about each vendor method and be able to create a generic mechanism to
invoke those methods. Vendors that want to expose some unique capability
in Ironic should not care about writing a custom code to invoke their
functions as part of the work to implement a vendor interface, they should
only care about implementing the vendor method itself. For this work
we also need to differentiate VendorPassthru from DriverVendorPassthru
methods so the decorator should be split in two, but they both can share
the same code base, it will be more a alias for each type.

The third part is about making VendorPassthru and DriverVendorPassthru
more consistent. We should make it configurable per-method if it should
run asynchronously or synchronously instead of having each endpoint
running things in a different way. A flag will be added to the decorators
to them express that.

The fourth will is about allowing vendor methods to support different
HTTP methods. Since it's a REST API vendors would benefit from being able
to expose methods to use all HTTP methods available. We should though
inform the vendors that things like having a synchronous GET method
talking to the BMC may not be a good idea since BMCs are flaky and it
may take a long time for the request to complete, so they don't shoot
themselves on the foot. But for things like the iPXE driver generating
configurations on-the-fly that would be beneficial.

Once we have the generic mechanism mapping all vendor methods, (the
second part of the proposal) we can then expose those via our API. By
issuing a GET on ../vendor_passhru/methods endpoint it will return the
available methods for that driver or node. For each method, it will
include a description, the supported HTTP methods and whether it is a
synchronous or asynchronous operation.

Another change would include a tutorial about how to write vendor
methods, and give tips just like the one about not talking to the BMC
in a synchronous way.

A backward compatible layer will also be added so we don't break
out-of-tree drivers that still use a custom vendor_passthru() and
driver_vendor_passthru() on their vendor interfaces. In case these
methods are present in the vendor interface they will be called just
like before. If not present, we are going to use the new mechanism to
invoke the vendor methods.

Alternatives
------------

* Modify the vendor_passthru() and driver_vendor_passthru() in the
  VendorInterface base class to run the vendor methods, basically
  substituting the decorator idea, that would impact on the backwards
  compatible plan that still need the conductor to know how it should invoke
  that vendor method, should it start a working thread (asynchronously)
  or call it directly (synchronously).

Data model impact
-----------------

None.

REST API impact
---------------

* /v1/nodes/<uuid>/vendor_passthru and /v1/drivers/<driver>/vendor_passthru
  will support different HTTP methods apart from POST, the list of methods
  are: GET, POST, PUT, PATCH and DELETE.

* /v1/nodes/<uuid>/vendor_passthru will continue to return HTTP 202
  (Accepted) for methods running in asynchronous mode, but will also
  return HTTP 200 (OK) for methods running synchronously.

* /v1/drivers/<driver>/vendor_passthru will continue to return HTTP 200
  (OK) for methods running in synchronous mode, but will also return
  HTTP 202 (Accepted) for methods running asynchronously.

* GET /v1/nodes/<uuid>/vendor_passthru/methods will return a list of
  vendor methods and its metadata supported by that node.

* GET /v1/drivers/<driver>/vendor_passthru/methods will return a list
  of vendor methods and its metadata supported by that driver.

Note: Both endpoints already support returning error HTTP codes like
HTTP 400 (BadRequest) and so on.


RPC API impact
--------------

* A new parameter ``http_method`` will be added to the vendor_passthru()
  and driver_vendor_passthru() methods in the RPC API.

* The return value from the vendor_passthru() and driver_vendor_passthru()
  methods in the RPC API will also change to include which mode
  (asynchronous or synchronous) the vendor method was invoked, that's
  needed so the API part can determine what HTTP code it should return in
  case of success.

* Two new RPC methods will be added to the RPC API:
  get_vendor_routes(<node id>) and get_driver_routes(<driver name>)
  which will return the list of available methods for that specific node
  or driver and will be used by the ``ironic-api`` services to expose this
  information via the REST API.

Driver API impact
-----------------

* Removal of vendor_passthru() and driver_vendor_passthru() from the
  VendorInterface. Prior to these changes each driver had to implement
  their own method to invoke their vendor methods and it was done via
  the vendor_passthru() and driver_vendor_passthru() methods from the
  VendorInterface. This is going to be replaced by a common method in the
  ConductorManager. This also allows us to test whether drivers continue
  to implement a custom vendor_passthru() or driver_vendor_passthru()
  method in the VendorInterface and if so we invoke them to make it
  backward compatible. When invoked using the backward compatible mode
  we are going to log a warning saying that having custom vendor's method
  has been deprecated.


Nova driver impact
------------------

None.

Security impact
---------------

None.

Other end user impact
---------------------

* Support for using different HTTP methods when calling the vendor
  endpoints will be added in the python-ironicclient, since today it
  assumes POST only.

Scalability impact
------------------

None.

Performance Impact
------------------

None.

Other deployer impact
---------------------

None.

Developer impact
----------------

Writing vendor methods is going to be easier and more flexible.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  lucasagomes

Other contributors:
  sambetts

Work Items
----------

* Create a decorator that will take care of logging and handling
  exceptions from the vendor methods.

* Extend the decorator to add metadata to the methods and be able to
  create a generic mechanism to invoke those without requiring vendors to
  write a custom code for that.

* Add support for running vendor methods synchronously and asynchronously.

* Add support for different HTTP methods on the vendors endpoints.

* Write a document explaining how to write vendor methods.

* Add client support for calling vendor methods using different HTTP methods.

Dependencies
============

None.


Testing
=======

* Unittests

* Tempest tests for the API changes

Upgrades and Backwards Compatibility
====================================

This change will be backwards compatible with existing clients,
so they could still run their custom vendor_passthru() and
driver_vendor_passthru() methods.

Documentation Impact
====================

* A new document will be added explaining how to write vendor methods.

* Update the Ironic documentation to mention that writing a custom
  vendor_passthru() and driver_vendor_passthru() methods in the vendor
  class has been deprecated and will be removed in the Liberty cycle.

References
==========

None.
