..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==============================================
Add Support for Retry on NodeLocked Exceptions
==============================================

https://blueprints.launchpad.net/ironic/+spec/add-nodelocked-retry

Let's reduce the pain of clients being presented errors due to
conflicts with locking a particular node (NodeLocked exceptions)
by adding multiple attempts to lock the node on the client's behalf.

As an added benefit, this would also help with tempest testing where
this error is seen on occasion [1].

Problem description
===================

Ironic clients may sometimes experience a NodeLocked exception/error
when making certain REST API calls. This is because the conductor(s)
will grab a lock on a node before performing any action that may
change that node's characteristics. Examples of where node locking
occurs are:

* Almost all of the RPC API calls (called to satisfy some REST API requests)
  lock the node in question except for: change_node_maintenance_mode,
  driver_vendor_passthru, get_console_information and
  validate_driver_interfaces.

* The conductor periodic task to synchronize power states.

* The conductor periodic task to check deploy timeouts.

The amount of time the node locks are held are typically not long.
We could eliminate many of these errors by simply retrying the lock
attempt. Admittedly, this would not *totally* eliminate the problem,
but it would make it much less likely to occur for clients, and thus
make for a much better experience.

Proposed change
===============

The TaskManager class is used to control when nodes are locked. The lock
itself is implemented by the database backend.

I propose we change the TaskManager.__init__() method to incorporate
the retry logic, leaving the implementation of the lock itself (the
database API layer) untouched. This lets us change the lock implementation
later, if we choose, without having to migrate the retry logic.

Alternatives
------------

A more permanent solution to this problem is being discussed in a spec that
is defining an asynchronous REST API [2]:

https://review.openstack.org/94923

It is unlikely that spec will be approved in Juno because of the work that
it entails to change the APIs. This proposal is simple and can be implemented
quickly.

A second alternative would be to implement the retry logic at the RPC level.
This has the disadvantage of increasing traffic on the RPC bus, and even
lengthier waits for lock attempts.

A third alternative is to change the locking layer itself and provide it
a value for timing out the attempt. This could potentially be a more complex
change, and would need to be duplicated if we changed the mechanism used
for locking.

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

This could create a DoS opportunity based on configuration values for
retry attempts and time between retries. This is eliminated by using
configuration values that will force only a single lock attempt.

Other end user impact
---------------------

The only impact this will have on the user is the reduced amount of node lock
errors from API requests and potential delays in HTTP responses. See the
Performance Impact section for more information on delays.

Scalability impact
------------------

This does have the possibility to negatively impact scalability. A spawned
worker thread within the conductor could potentially take longer to
process the work if a NodeLocked expection is thrown. This impact can be
mitigated by increasing the number of workers in the pool (the
workers_pool_size option).

Performance Impact
------------------

This will add additional processing time to REST API calls that happen
to encounter a node lock error. This is due to repeated calls to the
database API layer to attempt to successfully lock the node.

If the node is locked successfully on the first attempt, then performance
is not impacted at all.

Other deployer impact
---------------------

We should control the retry logic with configuration variables for
maximum retry attempts and time in between attempts. Using sane defaults
(setting the values such that no retry attempts are performed) should help
alleviate much of this impact.

The following new configuration variables are proposed (and their default
values) to be added to the conductor variable group:

* node_locked_retry_attempts = 3    (default to 3 retry attempts)
* node_locked_retry_interval = 1    (default to 1 second between attempts)

The default for node_locked_retry_attempts will be 3, which could potentially
affect existing installations (see Performance Impact section) when upgraded,
but should reduce NodeLocked errors encountered.

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  <dshrews>

Work Items
----------

None

Dependencies
============

The retrying [3] Python library would be of great use here, as it
encasulates all of the logic we would want. Version 1.2.2 (the latest
release as of this writing) would be the minimum version we would want
since it contains an important bug fix related to retrying on certain
exceptions.

NOTE: The global-requirements.txt value [4] for the retrying module will
need to be modified to meet this minimum version requirement.

Testing
=======

I don't see how to test this in tempest successfully (other than eliminating
the current errors from tempest due to this problem), but I imagine we can
add unit tests to verify it's working as we expect.

Documentation Impact
====================

None

References
==========

[1] https://bugs.launchpad.net/ironic/+bug/1321494
[2] https://review.openstack.org/94923
[3] https://pypi.python.org/pypi/retrying
[4] https://github.com/openstack/requirements
