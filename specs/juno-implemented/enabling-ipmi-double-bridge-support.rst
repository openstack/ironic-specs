..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Enabling IPMI double bridge support
==========================================

https://blueprints.launchpad.net/ironic/+spec/enabling-ipmi-double-bridge-support

This blueprint proposes ipmi double bridging support in ironic.


Problem description
===================

Currently, ironic IPMI driver(ipmitool) does not support bridging.

Many of the recent server architecture is based on distributed management.
For a chassis that has "n" number of servers, the management is delegated
from the core controller to many satellite controllers, which mandates the
need for bridging.


Proposed change
===============

- When registering an baremetal node which requires bridging, the appropriate
  parameters should be specified to ironic IPMI power driver as follows:

  * -i ipmi_bridging=<single/dual/no>
  * -i ipmi_local_address=<VALUE>
  * -i ipmi_transit_local_address=<VALUE>
  * -i ipmi_transit_channel=<VALUE>
  * -i ipmi_transit_address=<VALUE>
  * -i ipmi_target_channel=<VALUE>
  * -i ipmi_target_address=<VALUE>

    The parameters can be specified based on the hardware being registered.
    i.e, In order to perform an double-bridge, an user can just specify
    'transit_address' and 'target_address', rest is taken care by ipmi.
    But some hardware will mandate to specify transit_channel and
    target_channel, if they are using different channels.

    The parameter 'ipmi_bridging' should specify the type of bridging
    required(single/dual) to access the baremetal node.
    If the parameter is not specified, the default value will be set to "no"


      **Single Bridging:**

      ironic node-create -d pxe_ipmitool
      [-i ipmi_local_address=VALUE]  <-i ipmi_bridging=single>
      <-i ipmi_target_channel=VALUE>  <-i ipmi_target_address=VALUE>  ...

      The parameter 'ipmi_local_address' is optional. If the parameter
      is not specified, it is auto discovered by ipmitool


      **Double Bridging:**

      ironic node-create -d pxe_ipmitool
      [-i ipmi_local_address=VALUE]  [-i ipmi_transit_local_address=VALUE]
      <-i ipmi_bridging=dual>  <-i ipmi_transit_channel=VALUE>
      <-i ipmi_transit_address=VALUE>  <-i ipmi_target_channel=VALUE>
      <-i ipmi_target_address=VALUE>  ...

      The parameters 'ipmi_local_address' and 'ipmi_transit_local_address'
      are optional. If the parameters are not specified,
      it is auto discovered by ipmitool


- Ironic IPMI driver should be modified to parse the above information
  and perform ipmi operations with appropriate parameters.

Alternatives
------------

None

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

None

Other end user impact
---------------------
None

Scalability impact
------------------

Depends on the number of parallel IPMI sessions that can be supported by the
underlying BMC. When the sessions are exhausted, IPMI retry option can be
used to get the handle of a session.

Performance Impact
------------------

If the underlying BMC is designed for federated management, where there
might be one main controller and many sub controllers, there will not be any
impact.
However if only one controller exists in the BMC that manages all the nodes,
then the sessions might be slower when it reaches its threshold.

Other deployer impact
---------------------

When an node which mandates bridging is being registered, provide the
appropriate parameters:

* -i ipmi_bridging=<single/dual/no>
* -i ipmi_local_address=<VALUE>
* -i ipmi_transit_local_address=<VALUE>
* -i ipmi_transit_channel=<VALUE>
* -i ipmi_transit_address=<VALUE>
* -i ipmi_target_channel=<VALUE>
* -i ipmi_target_address=<VALUE>

Developer impact
----------------

None


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  rh-s

Other contributors:
  bmahalakshmi

Work Items
----------

* Include functionality to IPMI driver(ipmitool) to check if the underlying
  ipmitool utility supports bridging.
* Changes to IPMI driver to parse the bridging parameters.
* When a node being provisioned has bridging configuration specified,
  perform all ipmi operations with appropriate parameters.


Dependencies
============

IPMITOOL_1_8_12


Testing
=======

Unit test cases to test IPMI driver with bridging enabled and disabled


Documentation Impact
====================

Documentation should reflect the parameters that can be provided during
registering an node to enable bridging operation.


References
==========

- http://manpages.ubuntu.com/manpages/trusty/man1/ipmitool.1.html
- http://sourceforge.net/p/ipmitool/mailman/ipmitool-cvs/?viewmonth=201001

