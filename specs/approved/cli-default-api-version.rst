..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=================================================================
Change CLI default API version to latest known ironic API version
=================================================================

https://bugs.launchpad.net/python-ironicclient/+bug/1671145

When using ironic CLI or the OpenStack CLI (OSC), ironic API version 1.9 is
used by default. This spec proposes raising the default ironic API version used
in both CLIs to the latest compatible API version.

Problem description
===================

Currently, ironic CLI and the baremetal OSC plugin default to using an API
version that dates to the Liberty release. [#]_

This means that any new user using the CLI who doesn't specify the version
can only use features that are almost 2 years old as of the time of this
writing. This limits discoverability and usability of new features.

Also, if we ever bump up the minimum supported API version in the API, we will
have to deal with raising the minimum CLI version anyway.

Proposed change
===============

* For the Pike cycle, a warning message will be printed when a user runs
  either CLI without specifying the version, indicating that the CLI will
  soon default to using the latest compatible API version. The proposed wording
  for the OSC plugin is as follows:

    You are using the default API version of the OpenStack CLI baremetal
    (ironic) plugin. This is currently API version 1.9. In the future,
    the default will be the latest API version understood by both API and CLI.
    You can preserve the current behavior by passing the
    --os-baremetal-api-version argument with the desired version or using
    the OS_BAREMETAL_API_VERSION environment variable.

  A similar wording will be used for the ``ironic`` tool:

    You are using the default API version of the ``ironic`` CLI tool.
    This is currently API version 1.9. In the future, the default will be
    the latest API version understood by both API and CLI.
    You can preserve the current behavior by passing the
    --ironic-api-version argument with the desired version or using
    the IRONIC_API_VERSION environment variable.

  If the user wishes to continue using API version 1.9, they should specify so
  on the command line.

* During the Queens cycle, the default API version used by the CLI will change
  to the latest version of the API compatible with the CLI. If only the major
  version is specified (for example, ``--os-baremetal-api-version=1``), the
  latest compatible version of that major version will be used (e.g. 1.32 if
  that's the latest 1.XX version).

  The latest compatible version will be determined via version negotiation
  between the CLI and ironic. The CLI will first make a request to the root
  endpoint of the ironic API, which returns the version of the ironic API. [#]_
  If the ironic API version is lower than the maximum version the client is
  compatible with, the CLI will use the version running on the API service to
  ensure compatibility. Otherwise, the maximum ironic API version that can be
  handled by the client will be used.

  .. note::
     We may deprecate the ``ironic`` tool in the Queens cycle. If this happens,
     we may decide to skip applying this change to this tool, and proceed with
     the deprecation instead. This is subject to a separate spec.

Changes to the client library are out of scope for this spec.

This change was discussed in detail at the Pike PTG. [#]_

Alternatives
------------

* We could periodically bump the default API version used by the CLI. This
  has the disadvantage of being unpredictable from a user standpoint and
  doesn't solve the discoverability issue for the latest features. It's also
  not ideal for maintainability of the CLI codebase.

* We could keep the default as 1.9 and always log a warning, without ever
  changing the default to the latest version. This doesn't solve the ease of
  use or discoverability issues, and it permanently adds an extra annoyance to
  users who don't wish to specify a version every time the CLI is invoked.

* We could just pass ``latest`` to the API when no version is provided.
  However, this approach would lead to potentially broken behavior if we ever
  land a breaking change to our API.

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

"ironic" CLI
~~~~~~~~~~~~

A warning will be logged when ironic CLI is invoked without specifying
``--ironic-api-version``, indicating that the default will soon be the latest
compatible API version.

After the deprecation period, the default will be changed accordingly, assuming
that ironic CLI itself is not deprecated beforehand.

"openstack baremetal" CLI
~~~~~~~~~~~~~~~~~~~~~~~~~

A warning will be logged when the OSC baremetal plugin is invoked without
specifying ``--os-baremetal-api-version``, indicating that the default will
soon be the latest compatible API version.

After the deprecation period, the default will be changed accordingly.

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

None

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  dtantsur

Other contributors:
  mariojv

Work Items
----------

* Add the warning message
* After the standard deprecation period (release boundary or 3 months,
  whichever is longer), change the default API version used by the CLI.

Dependencies
============

None

Testing
=======

Appropriate unit and functional testing will be added.

Upgrades and Backwards Compatibility
====================================

If a user has scripts or tooling that use the CLI without specifying the
version, those will need to be updated to specify the version.

Documentation Impact
====================

None. Appropriate release notes will be added.

References
==========

.. [#] https://docs.openstack.org/developer/ironic/dev/webapi-version-history.html
.. [#] https://etherpad.openstack.org/p/ironic-pike-ptg-operations
.. [#] https://developer.openstack.org/api-ref/baremetal/#list-api-versions
