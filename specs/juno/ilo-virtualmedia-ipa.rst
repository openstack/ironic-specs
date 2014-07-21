..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=====================
iLO IPA Deploy Driver
=====================

https://blueprints.launchpad.net/ironic/+spec/ilo-virtualmedia-ipa

Add ability to provision proliant baremetal nodes (having iLO4 and beyond)
by booting the baremetal node with virtual media and using IPA to deploy the
image.

Problem description
===================
IPA project provides a more powerful ramdisk for doing deploy from the
conductor node.  But IPA has the following issues:

- Some customers don't prefer PXE protocol in their environment because of
  the following issues:

  + PXE uses TFTP to transfer the files which is unreliable because it uses
    UDP.
  + PXE is not suited for some network topologies where the relaying of PXE
    requests might be required in routers to enable PXE working for the whole
    network.
- Deployers require an extra tftp service to be running on the conductor node.
- Currently the admin token required to call node's vendorpassthru cannot be
  transmitted securely to the baremetal node.

Proposed change
===============
The below review introduced a new mechanism for booting proliant machines with
virtual media.
http://specs.openstack.org/openstack/ironic-specs/specs/juno/ironic-ilo-virtualmedia-driver.html

The methods ``setup_virtual_media_boot`` introduced in the above review can be
used to boot up a baremetal node with the deploy ISO image.  A new class
``IloVirtualMediaAgentDeploy`` can be added which will setup the machine to
be booted with virtual media instead of PXE.

The vendor interface ``AgentVendorInterface`` can be reused to continue the
deploy and complete it.

This change will also enable the admin token to be handed off securely to the
baremetal node through OOB channel over virtual media.

Alternatives
------------
The proliant machines can continue to work booting the agent ramdisk with PXE.

Data model impact
-----------------
One new parameter ``deploy_iso`` will be used in driver_info to boot up the
node for deploy.  ``deploy_iso`` will contain the glance UUID of bootable
ISO built with agent ramdisk.

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
This method of deploy no longer requires an extra service (like tftp service
in case of pxe driver) to be running on the conductor node.

Developer impact
----------------
None.

Implementation
==============

Assignee(s)
-----------
Primary assignee:
  rameshg87

Work Items
----------
* Add ``IloVirtualMediaAgentDeploy`` which implements base.DeployInterface.

Dependencies
============
None.

Testing
=======
Unit tests will be added for all the code.  Tempest tests for this will be
considered later.

Documentation Impact
====================
The procedure for configuring the proliant baremetal node will need to be
documented. This will be documented in rst format in doc/ directory in ironic
source tree.  The contents of this file can be put in ironic wiki as well.

References
==========
None.
