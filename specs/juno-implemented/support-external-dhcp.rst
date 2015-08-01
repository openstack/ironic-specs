..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===============================
Support external DHCP providers
===============================

https://blueprints.launchpad.net/ironic/+spec/support-external-dhcp

Ironic should allow operators to use an external DHCP server, rather than
Neutron's DHCP server.


Problem description
===================

There are a number of reasons a deployer may wish to use an external DHCP
server. These include:

* Neutron is not available in the deployer's environment.

* The deployer may believe Neutron's DHCP server is not scalable. Neutron's
  DHCP server uses dnsmasq under the hood, which is known to be unsuitable
  for large-scale deployments (see links in references section).


Proposed change
===============

Ironic should have a configuration option `dhcp_provider` that specifies which
provider to use.  All DHCP providers will implement a DHCP provider interface,
which exposes a method to update a port's DHCP attributes.

Drivers will no longer call the DHCP provider directly, but instead request a
DHCP provider from a factory, which will return the provider specified in the
configuration options.

The two initial provider implementations will be "neutron" and "none".

Neutron functioality that does not relate to DHCP (ie. updating a port's MAC
address) will not be moved.

Alternatives
------------

It would be simpler in the short term to have a boolean `use_neutron_for_dhcp`
config that would tell Ironic to either use Neutron or do nothing.  This would
duplicate the initial functionality of the proposed change.  However, new DHCP
providers would be difficult to add, and there would also be more work for the
deploy driver.

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

This will only make Ironic more scalable, as it will expose a configuration
in which Ironic no longer interacts with Neutron.

Performance Impact
------------------

None.

Other deployer impact
---------------------

A config option `dhcp_provider` will be added that starts with two options,
"neutron" and "none".

There will be no immediate impact on deployers, as `dhcp_provider` will default
to "neutron", which does not change behavior.

However, deployers that wish to use an external DHCP provider must set the
config option and also deploy a DHCP service.

Developer impact
----------------

None.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  jroll

Other contributors:
  JoshNang
  ellenh

Work Items
----------

* Add `dhcp_provider` config option.

* Move Neutron API behind a DHCP provider interface.

* Implement "none" DHCP provider.

* Implement a DHCP provider factory.

* Add Tempest tests


Dependencies
============

None.

Testing
=======

Tempest tests should be written that use an external DHCP provider. dnsmasq
is already installed in devstack, so this could be accomplished by running
dnsmasq standalone, rather than via Neutron.


Documentation Impact
====================

Documentation will need to be written for this config option. This should
include:

* What the config option does.

* How to configure an external DHCP server to work with Ironic.

* A diagram of what the control plane looks like for both dhcp_provider
  options.


References
==========

* "Dnsmasq provides network infrastructure for small networks":
  http://www.thekelleys.org.uk/dnsmasq/doc.html
