..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==================================================
Boot and network management for in-band inspection
==================================================

https://storyboard.openstack.org/#!/story/1584830
https://storyboard.openstack.org/#!/story/1528920

This spec suggests making Ironic Inspector play well with the tenant network
separation and non-PXE boot interfaces.

Problem description
===================

With the ``neutron`` network interface nodes are no longer constantly connected
to the provisioning network. We need to connect them manually before in-band
inspection, which is inconvenient and error-prone.

This change covers integration with both boot and network interfaces.

Proposed change
===============

The proposed flow will work as follows:

#. Inspection with the ``inspector`` inspect interface is started via the API.

#. The ``inspector`` inspect interface:

   #. Calls ``task.driver.network.validate_inspection``.

      If it raises ``UnsupportedDriverExtension``, fall back to the code path.

   #. Calls ``task.driver.boot.validate_inspection``.

      If it raises ``UnsupportedDriverExtension``, fall back to the code path.

   #. Calls ``task.driver.network.add_inspection_network``. It creates a port
      on the ``inspection_network``.

   #. Calls ``task.driver.boot.prepare_ramdisk`` providing kernel parameters
      from the option ``[inspector]extra_kernel_params``.

   #. Calls the ironic-inspector introspection API with ``manage_boot=False``.

   #. Powers on the machine via ``task.driver.power``.

#. Now inspection proceeds as previously.

Boot and network interfaces
---------------------------

* Add a new call ``validate_inspection``. It will be implemented the same way
  as ``validate_rescue``, but instead of raising ``MissingParameterValue`` on
  absent parameters it will raise ``UnsupportedDriverExtension`` to indicate
  fall back to the old approach.

  * Implement ``validate_inspection`` for the PXE and iPXE boot interfaces.

* Add a new ``driver_info`` parameter ``driver_info[inspection_network]`` and
  a new configuration option ``[neutron]inspection_network``.

* Extend the ``NetworkInterface`` to provide ``add_inspection_network``,
  ``remove_inspection_network`` and ``validate_inspection`` similarly to
  rescue networks. However, ``validate_inspection`` will raise
  ``UnsupportedDriverExtension`` if the inspection network is not specified.

Inspector inspect interface
---------------------------

Modify the ``Inspector`` inspect interface to follow the flow outlined above.

* Call ``boot.validate_inspection`` and ``network.validate_inspection`` in the
  beginning of the introspection process. If either raises
  ``UnsupportedDriverExtension``, follow the same procedure as previously.

* Call ``network.add_inspection_network`` before and
  ``network.remove_inspection_network`` after inspection.

* Add a new ``driver_info`` parameter
  ``driver_info[inspector_extra_kernel_params]`` and a new configuration option
  ``[inspector]extra_kernel_params``.

* Call ``boot.prepare_ramdisk`` before introspection, providing the
  ironic-inspector URL (fetched from the service catalog) and
  ``extra_kernel_params`` to the ``ramdisk_params`` argument. Call
  ``boot.cleanup_ramdisk`` afterwards.

* Call ironic-inspector passing ``manage_boot=False``.

Inspecting ports
----------------

Currently Ironic Inspector does not require ports, port groups or local
link information to be present to conduct inspection. However, to use network
flipping we will need this information, which can be:

* entered manually by an operator (using out-of-band inspection if possible) OR

* inspected initially with a node manually put on the right network.

Alternatives
------------

* Do not support network separation.

* Expose the network and boot interfaces in Ironic API and make Inspector
  use it.

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

Extend the ``NetworkInterface`` with:

.. code-block:: python

    def validate_inspection(self, task):
        """Validates the network interface for inspection operation.

        :param task: A TaskManager instance.
        :raises: InvalidParameterValue, if the network interface configuration
            is invalid.
        :raises: MissingParameterValue, if some parameters are missing.
        """
        raise exception.UnsupportedDriverExtension(
            driver=task.node.driver, extension='validate_inspection')

    def add_inspection_network(self, task):
        """Add the inspection network to a node.

        :param task: A TaskManager instance.
        :raises: NetworkError
        """
        pass

    def remove_inspection_network(self, task):
        """Remove the inspection network from a node.

        :param task: A TaskManager instance.
        """
        pass

Extend the ``BootInterface`` with:

.. code-block:: python

    def validate_inspection(self, task):
        """Validate that the node has required properties for inspection.

        :param task: A TaskManager instance with the node being checked
        :raises: MissingParameterValue if node is missing one or more required
            parameters
        :raises: UnsupportedDriverExtension
        """
        raise exception.UnsupportedDriverExtension(
            driver=task.node.driver, extension='validate_inspection')

Nova driver impact
------------------

None

Ramdisk impact
--------------

None

Security impact
---------------

This change will also allow using in-band inspection with tenant network
separation increasing security.

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

New configuration options:

* ``[neutron]inspection_network`` the default inspection network (no default).

* ``[inspector]extra_kernel_params`` the default kernel parameters to pass
  to introspection (empty by default).

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Dmitry Tantsur (lp: divius, irc: dtantsur)

Work Items
----------

#. Add new methods to the network and boot interfaces.

#. Update the ``inspector`` inspect interface to use them.

Dependencies
============

None

Testing
=======

Coverage by unit tests.

Upgrades and Backwards Compatibility
====================================

The default behavior will not change because the ``inspection_network`` will be
left unpopulated initially. After it gets populated, nodes with ports will
follow the new flow for introspection. This feature can be enabled per node by
setting ``inspection_network`` on nodes, not globally.

This work does not anyhow affect introspection that is started using the
ironic-inspector's own CLI or API.

Documentation Impact
====================

The Ironic documentation should be updated to explain using network separation
with in-band inspection.

References
==========
