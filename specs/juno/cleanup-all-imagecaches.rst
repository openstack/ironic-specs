..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

====================================
Mechanism to cleanup all ImageCaches
====================================

https://blueprints.launchpad.net/ironic/+spec/cleanup-all-imagecaches

This spec talks about creating a mechanism to cleanup all the image caches
(leveraging most of the code that is already in pxe driver)

Problem description
===================
The cleanup method for cleaning up ImageCache (or its subclasses)
``_cleanup_caches_if_required`` is situated inside pxe driver.  Hence, any
other subclass of ImageCache situated in any other file, cannot use this
cleanup method.

This code was introduced in this commit:
https://review.openstack.org/#/c/92625

Proposed change
===============
The reason why the cleanup method is placed in pxe driver is because it needs
to know other subclasses of ImageCache to do efficient cleaning to make up for
the required space in the cache.  Other ImageCaches which are situated in the
same filesystem are also cleaned up if enough space is not available after
cleaning up the current cache. This method hardcodes ``InstanceImageCache``
and ``TFTPImageCache`` to be cleaned up for any cache cleanup.

The problem could be solved as follows:

* Each of the subclasses of ImageCache that wishes to be used in cleanup of
  other caches (currently ``InstanceImageCache`` and ``TFTPImageCache``) add
  a decorator ``@image_cache.cleanup(priority=N)``.  N should be a positive
  integer which signifies the priority in which the cache should be cleaned up
  when extra free space is required after cleaning up the provided cache.
  Higher value of N means higher priority. If two caches have same value of N
  (probably at different places in code), then the order of cleanup of those
  two caches is not predictable (it will depend on which of the two module is
  loaded first).

  Currently ``InstanceImageCache`` being large, should be cleaned up before
  ``TFTPImageCache``. Hence they will have it as below:

  ::

   @image_cache.cleanup(priority=50)
   class InstanceImageCache(...)
   ...


   @image_cache.cleanup(priority=25)
   class TFTPImageCache(...)
   ...


* There would be list ``cache_cleanup_list`` in image_cache.py which would
  contain a sorted list of instances of ``ImageCache`` to be considered for
  cleanup. The decorator function ``cleanup`` adds an instance of the
  subclass of ``ImageCache`` into list. This list will be
  kept sorted in non-increasing order of ``priority`` after adding the entry.

* The method ``_cleanup_caches_if_required`` will be moved to
  ironic.common.image_cache and renamed to ``clean_up_caches``.  The
  method ``_cleanup_caches_if_required`` currently uses a hardcoded list of
  caches to be cleaned for extra space.  Instead of that, the newly proposed
  method will just use the list ``cache_cleanup_list``.

* ``PXEImageCache`` will not have decorator ``@image_cache.cleanup``.

Alternatives
------------
The code to cleanup can continue to exist in the pxe driver and pxe driver can
import and maintain the hardcoded list of all the caches across the source
tree.  This is hard to maintain and not logical.

Another alternative is that the method can be moved to a common place, but
the cleanup may be initiated on the caches that the module would know about.
This would not be as efficient as the proposed solution, as proposed solution
can consider more caches for cleaning up and making up the required space.

Data model impact
-----------------
None.

REST API impact
---------------
None.

Driver API impact
-----------------
None.

Nova driver impact
------------------
None.

Security impact
---------------
None.

Other end user impact
---------------------
None.

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

* Developers wishing to introduce a new subclass of ``ImageCache`` can add the
  decorator ``@image_cache.cleanup`` and assign an ``priority`` in
  interest of overall ironic.

* The subclass of ImageCache that wishes to be cleaned up should not
  take any parameters in the constructor.

Implementation
==============

Assignee(s)
-----------
rameshg87

Work Items
----------

* Refactor ``_cleanup_caches_if_required`` from ironic.drivers.modules.pxe
  to ironic.common.image_cache.
* Modify the unit tests for fetch_images() method in
  ironic.tests.drivers.test_pxe

Dependencies
============
None.

Testing
=======
Currently existing unit tests will be modified in accordance with the
proposed behavior.

Documentation Impact
====================
None.

References
==========
None.
