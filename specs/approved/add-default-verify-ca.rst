..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

================================================
Add a field to accept the default verify_ca path
================================================

https://bugs.launchpad.net/ironic/+bug/2040236

This spec adds an option for setting [driver]verify_ca for each driver.
This value would then be used by Ironic for certificate validation instead of
the default system CA bundle for that driver. Each driver may use a different
CA certificate for this purpose if desired.


Problem description
===================

Currently, Ironic utilizes a system-wide CA certificate bundle to validate
HTTPS connections. However, there are scenarios where this default behavior may
not align with the specific requirements or policies of an organization.
Particularly, when a user specifies that certificate validation is required,
administrators may prefer not to rely on the system's default certificate path
for authentication with BMCs. Instead, they might need to utilize custom CA
certificates, which are tailored to their organizational security policies or
specific use cases.

At present, if the operator desires to configure a custom CA certificate for
communications between Ironic and the BMCs of managed bare-metal servers,
they have the ability to configure the <driver>_verify_ca option on the node or
nodes in question.
This option can be configured to be either true, false, or set to a specific
certificate path. When '<driver>_verify-ca' is set to true, Ironic defaults to
using the system's CA bundle for certificate validation. Furthermore, in cases
where the operator desires to specify a CA certificate outside system CA
bundle, this approach has a serious shortcoming: it requires the operator to
know the exact location of the pre-existing CA certificate in the filesystem.
While this configuration option is set on per-node level through Ironic APIs,
there is no way for the operator to either upload the CA certificate through
those APIs or to determine the filesystem path of such certificate. This is not
a desirable situation. This option is also unsuitable for the use cases where
the operator is only able to interact with Ironic through writing configuration
file and making API calls (which is the case in metal3).

To overcome this limitation, we propose a new configuration option scoped on a
driver level (as opposed to the node level): [driver]verify_ca. This way the
required CA certificates can be deployed to known locations at the deploy time
and Ironic configuration for each driver can be written referencing those
paths.


Proposed change
===============

1. Adding a new option verify_ca for each driver

  * Adding a verify_ca option to each driver's conf to accept the specified
    value. Making this option configurable on a per-driver level is
    consistent with existing configuration options (e.g. kernel_append_params).
    It is also very clear what purpose this specific CA certificate serves.

2. Retrieving the path before node verification

  * Before performing the node verification, retrieve the certificate path, and
    pass it to verify_ca for validation. This implementation vary based on
    different vendors.

Alternatives
------------

* Administrators may need to log in to the system where ironic is located and
  manually add the desired certificate. Note: this requires modifications of
  the trusted CA certificate collection on the machine running Ironic, which
  may or may not be desired; there may be use cases where an operator wishes to
  trust a certain CA for connections to BMC but not other encrypted
  communications involving the server running Ironic.
* Instead of [driver]verify_ca, a global configuration option similar to
  [conductor]verify_ca could be considered, however this could lead to
  confusion about the impact of setting it (does it apply to all conductor
  connections? BMC connections? else?) and would be inconsistent with other,
  similar options (e.g. kernel_append_params).
* Using the existing <driver>_verify_ca setting is another alternative,
  however it requires prior existence of the desired CA certificate in the
  filesystem where Ironic is running as well as operator’s knowledge of the
  exact path, which should not be relied upon and as such is not desired.

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

Ramdisk impact
--------------

None

Security impact
---------------

The introduction of the verify_ca configuration option in
Ironic's driver could have several security implications:

1. Handling of Sensitive Data:

  * This change involves the path to CA certificates, which are critical for
    secure communications. While the option itself doesn't handle sensitive
    data like tokens or keys, it directs Ironic to the location of sensitive
    cryptographic material. Proper management and permissions of this path
    are essential to prevent unauthorized access.

2. Accessibility of Managed Hardware:

  * By allowing a custom CA path, this change could affect the security of the
    hardware managed by Ironic. If an incorrect or untrusted CA path is
    specified, it could potentially compromise the integrity of the SSL/TLS
    connections with the BMCs, impacting the secure management of the
    hardware.

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
* At deploy time, one or more custom CA certificates may be installed on the
  machine running Ironic under a known path.
* Ironic configuration created at the deploy time will assign the custom
  CA certificate to the driver(s) that are expected to be using it.
* Each driver can use a different CA certificate, or the same CA certificate
  may be used by multiple drivers if desired.
* The default None value for verify_ca ensures backward
  compatibility, using the system's default CA bundle unless overridden.
  This approach maintains operational stability for existing deployments
  while offering flexibility for custom configurations.
* Ironic will be enhanced to dynamically retrieve the value of
  verify_ca for each hardware driver and pass it to the verify_ca
  function. This mechanism ensures that SSL/TLS communications with BMCs
  across different hardware types can leverage the specified custom CA
  certificates.
* The feature requires explicit enablement by deployers. This change will not
  automatically activate.

Developer impact
----------------

* Developers will need to ensure that their drivers correctly interpret and
  utilize the specified CA path.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Zhou Hao <zhouhao@fujitsu.com>

Other contributors:
  Zou Yu <zouy.fnst@fujitsu.com>
  Feng GuangWen <fenggw-fnst@fujitsu.com>

Work Items
----------

* Implement option verify_ca for each vendor.
* Update documentation.


Dependencies
============

None


Testing
=======

* Test the driver to verify that the set path is used when performing
  certificate validation.

Upgrades and Backwards Compatibility
====================================

None


Documentation Impact
====================

* The documentation should be updated for each hardware vendor as features are
  implemented.


References
==========

None
