..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

================================
Add Intel® Speed Select Support
================================

https://storyboard.openstack.org/#!/story/2005390

Multiple types of servers are needed to handle diverse workloads. Purchasing
and managing these servers introduces complexity and increases total cost of
ownership(TCO).
Intel Speed Select Technology(SST)[1] is a collection of features that improves
performance and optimizes TCO by providing more control over CPU performance.
With Intel SST, one server can do more which means the same server can be used
to run different workloads. One of the feature is Intel Speed Select
Technology-Performance Profile (SST-PP) which allows configuring the CPU to run
at 3 distinct operating points or profiles.

With Intel SST-PP, one can set the desired core count and their base and turbo
frequencies which can help to tune the server to specific workload performance.

Problem description
===================
This spec proposes to support Intel SST-PP feature in Ironic. With Intel
SST-PP, Ironic users can:

* Run their servers at different configuration level.
* Each configuration level supports different number of active cores and
  frequency.
* Same server can be used to run multiple different workloads thus decreasing
  TCO.

Intel SST-PP Speed Select supports three configuration levels:

* 0 - Intel SST-PP Base Config
* 1 - Intel SST-PP Config 1
* 2 - Intel SST-PP Config 2

Following table shows the list of active cores and their base frequency at
different SST-PP config levels::

 ---------------------------------------------
 |   Config    |  Cores  |  Base Freq (GHz)  |
 ---------------------------------------------
 | Base        | 24      | 2.4               |
 | Config 1    | 20      | 2.5               |
 | Config 2    | 16      | 2.7               |
 ---------------------------------------------

Proposed change
===============

Intel SST-PP can be set over IPMI. Each configuration level has its
own hexa raw code that the server understands. Ironic sends this code to the
server via IPMI to set the desired SST-PP level.

We will map these configurations to traits that Ironic understands.

* 0 - ``CUSTOM_INTEL_SPEED_SELECT_CONFIG_BASE``
* 1 - ``CUSTOM_INTEL_SPEED_SELECT_CONFIG_1``
* 2 - ``CUSTOM_INTEL_SPEED_SELECT_CONFIG_2``

The solution works at two stages:

Scheduling
----------

The solution to support Intel SST-PP is first enable scheduling the request
for baremetal instance deployment on the nodes that supports it. We set the
desired configuration as the trait in our flavor::

  $ openstack flavor set --property \
    trait:CUSTOM_INTEL_SPEED_SELECT_CONFIG_2=required baremetal

Now, we also need to update the Ironic node's trait with the supported
configuration levels::

  $ openstack baremetal node add trait node-0 \
    CUSTOM_INTEL_SPEED_SELECT_CONFIG_BASE CUSTOM_INTEL_SPEED_SELECT_CONFIG_1 \
    CUSTOM_INTEL_SPEED_SELECT_CONFIG_2


Now, when user sends a request to boot a node with the ``baremetal`` flavor,
placement API service will select the Ironic node that supports Intel SST-PP.

Provisioning
------------

The Intel SST-PP needs to be set via IPMI before powering on the node
in the process of provisioning. Ironic API service receives the desired
configuration in ``node.instance_info.traits`` in the boot request. Ironic will
then run the deploy template's step matching the trait. The deploy template
will specify the new ``configure_intel_speedselect`` step which configures
the Intel SST-PP configuration level and then powers on the node.

Ironic will need below details to configure Intel SST-PP on the node:

* Intel SST-PP configuration level: This is the required configuration level
  on the node. Possible values are the traits listed above. This information
  is set by admins in the  flavor's trait they want to boot the baremetal node
  with. Nova in turn updates the Ironic's node information with the trait.

* Number of sockets: This is the number of sockets per CPU. Setting Intel
  SST-PP needs to be done for every socket.

Both these information can be provided as an argument to the
``configure_intel_speedselect`` deploy step.



Alternatives
------------

Continue to not support Intel SST-PP or users can manually configure
it independent of Ironic.

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

None

"openstack baremetal" CLI
~~~~~~~~~~~~~~~~~~~~~~~~~

None

RPC API impact
--------------

None

Driver API impact
-----------------

* Add a new hardware type ``IntelIPMIHardware`` to support Intel SST-PP
  enabled servers.

  .. code-block:: python

      class IntelIPMIHardware(IPMIHardware):

* Add a new management interface ``IntelIPMIManagement`` to manage the
  configuration of Intel SST-PP on the servers. This class will have a new
  deploy step ``configure_intel_speedselect`` to configure Intel SST-PP on
  the nodes. This will also be enabled as a clean step so that it can be used
  to reset the configuration while node cleaning.


  .. code-block:: python

      class IntelIPMIManagement(ipmitool.IPMIManagement):
          @base.deploy_step(priority=200, argsinfo={
              'intel_speedselect_config': {
                  'description': (
                       "Intel SST-PP configuration."
                  ),
                  'required': True
              },
              'socket_count': {
                  'description': (
                      "No. of sockets."
                  )
              }
          })
          def configure_intel_speedselect(self, task, **kwargs):
              return None

  The following table contains the ``intel_speedselect_config`` values
  for the proposed deploy templates::

   -----------------------------------------------------------------------
   |   Deploy Template                      |  intel_speedselect_config  |
   -----------------------------------------------------------------------
   | CUSTOM_INTEL_SPEED_SELECT_CONFIG_BASE  |  0x00                      |
   | CUSTOM_INTEL_SPEED_SELECT_CONFIG_1     |  0x01                      |
   | CUSTOM_INTEL_SPEED_SELECT_CONFIG_2     |  0x02                      |
   -----------------------------------------------------------------------

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

Users will have to update the traits with the desired Intel SST-PP
configuration level in the corresponding flavors.

Scalability impact
------------------

None

Performance Impact
------------------

None

Other deployer impact
---------------------

Deployers wishing to use feature will have to add the Intel SST-PP
configuration in Node's trait and also have to create corresponding deploy
templates.

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  mkrai

Work Items
----------

* Implement Intel SST-PP support code in Ironic.

* Write the test code.

* Write a document explaining how to use Intel SST-PP.


Dependencies
============

None

Testing
=======

* Unit tests

Upgrades and Backwards Compatibility
====================================

None

Documentation Impact
====================

New document will be added to explain the support of new Intel SST-PP feature
in Ironic and how to use it.

References
==========

[1] https://www.intel.com/content/www/us/en/architecture-and-technology/speed-select-technology-article.html
