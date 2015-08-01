..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

============================================
Add instance_info field to Node model
============================================

https://blueprints.launchpad.net/ironic/+spec/add-node-instance-info

This blueprint will introduce a new field to the Nodes resource that
will be used to store instance-specific data, which will be used by the
driver when provisioning or managing that instance.

Problem description
===================

The metadata which describes a particular instance being deployed is
being passed from the client to the deploy driver via the node.driver_info
field. That field is intended to store only the driver-specific metadata
needed by that driver for the purpose of managing and provisioning that
specific node (such as IPMI credentials). Such metadata should be constant
across multiple deployments to the node, and updating the driver_info
often corresponds to an operator action (such as rotating passwords).

The instance-specific metadata, which changes during every deploy,
should not be stored alongside the driver-specific metadata.

Proposed change
===============

* create a new instance_info attribute to the Nodes resource where all
  the instance-level related data should live.

* modify the Nova Ironic driver to populate the instance_info instead
  of the driver_info when deploying a node.

* deploy ramdisk and deploy kernel to not be part of the Flavor's
  extra_data and live in the Node's driver_info instead.

* Remove all the data stored in the instance_info field as part of
  the node's tear down process (Since all the data stored there will be
  related to the instance).

Alternatives
------------

Continue to use the driver_info field?

Data model impact
-----------------

The instance_info field will be added to the nodes table.

REST API impact
---------------

A new instance_info attribute will be added to the Node resource.

Driver API impact
-----------------

None

Nova driver impact
------------------

When preparing the node to be deployed the Nova driver was adding the
instance information to the nodes driver_info field, with this change
the fields 'root_gb', 'swap_gb', 'ephemeral_gb', 'ephemeral_format',
'image_source' will now be added to the instance_info field instead.

The nova driver also needs to be changed to not look at the flavor's
extra spec to get the deploy ramdisk and deploy kernel, such fields
will be part of the process of enrolling a node and should be present
at the node before triggering it to be deployed (otherwise it will fail
in the validation).

Security impact
---------------

As a side effect, this change enables a later improvement in security
by allowing the driver_info field to be hidden from the REST API, if
policies were added and enforced in the API layer. This would allow the
management credentials to be hidden from users.

Other end user impact
---------------------

Instead of setting the deploy ramdisk and deploy kernel as part of
the flavor in Nova, this fields if required (depending on the driver)
should be set by the operator in the driver_info field of the Nodes when
enrolling it.

A migration script will be created to demonstrate how to extract the
deploy ramdisk and deploy kernel from the Nova flavor and update the
Ironic Node's driver_info field appropriately.

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
  lucasagomes

Other contributors:
  jroll

Work Items
----------

* create instance_info field in the nodes table in the database.

* create a new instance_info attribute in the Nodes object.

* modify the PXE driver to look at the new instance_info field to get
  the instance-level data when deploying a node.

* modify the Nova Ironic Driver to populate the Node's instance_info
  field instead of the driver_info.

* modify the Nova Ironic Driver to not get the deploy ramdisk and deploy
  kernel from the flavor and populate in the Node before the deployment,
  those fields should be present in the Node already once it's enrolled,
  validation should fail otherwise.


Dependencies
============

None

Testing
=======

Unit tests and DevStack needs to be changed to cover the new changes.

The DevStack change will need to be staggered in three changes:

* have DevStack add the deploy kernel and deploy ramdisk to driver_info
  (while still also adding on flavor).

* land patch in Ironic.

* have DevStack stop writing deploy kernel and deploy ramdisk to flavor.


Documentation Impact
====================

Documentation should be modified to instruct operators not to add
the deploy kernel and ramdisk glance image UUIDs to the Nova flavor.
Instead, the documentation will indicate that operators must pass this
information to Ironic when enrolling nodes.

References
==========

None
