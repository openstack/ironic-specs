..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=====================
VNC Graphical console
=====================

https://bugs.launchpad.net/ironic/+bug/1567629

In addition to a serial console, allow ironic nodes to be accessed through a
graphical console. This proposal presents the work required to create a new
driver interface for accessing graphical console of a node.


Problem description
===================

End users often have to troubleshoot their instances because they might have
broken their boot configuration or locked themselves out with a firewall.
Keyboard-Video-Mouse (KVM) access is often required for troubleshooting these
types of issues as serial access is not always available or correctly
configured. Also, KVM provides a better user experience as compared to serial
console.

Currently, ironic does not expose a node's KVM capabilities. As such, admin
users and deployers have to find alternatives to provide KVM access to their
users. Also, Horizon's VNC console is not supported for the ironic nodes
provisioned by Nova.


Proposed change
===============

* A new interface ``GraphicalConsoleInterface`` will be added. This interface
  will essentially have the same class API as current ``ConsoleInterface``
  interface (with ``start_console``, ``stop_console`` and ``get_console``
  methods), but it will be possible to enable/disable/configure it
  independently from serial console access.
  As with other ironic driver interfaces and hardware types, operators
  are free to choose which implementation of a graphical console access to use
  by setting it to the one enabled and supported by corresponding hardware type
  implementations.
  The new interface will have following methods::

    class GraphicalConsoleInterface(BaseInterface):
        """Interface for graphical console-related actions."""
        interface_type = "graphical_console"

        @abc.abstractmethod
        def start_console(self, task):
            """Start a remote graphical console for the task's node.

            This method should not raise an exception if console already started.

            :param task: a TaskManager instance containing the node to act on.
            """

        @abc.abstractmethod
        def stop_console(self, task):
            """Stop the remote graphical console session for the task's node.

            :param task: a TaskManager instance containing the node to act on.
            """

        @abc.abstractmethod
        def get_console(self, task):
            """Get connection information about the graphical console.

            This method should return the necessary information for the
            client to access the graphical console.

            :param task: a TaskManager instance containing the node to act on.
            :returns: the graphical console connection information.
            """

* The following new hardware interface implementations of
  ``GraphicalConsoleInterface`` will be created.

  + ``ipmitool-vnc`` - For accessing graphical console using VNC.
  + ``no-graphical-console`` - For no graphical console.
  + ``fake`` - For accessing fake graphical console used for testing.

* New config options will be introduced for this interface which are as
  follows:

  + ``[DEFAULT]enabled_graphical_console_interfaces`` -  This config option
    represents the list of enabled graphical console interfaces in ironic.
    The default value is ``['no-graphical-console']``.

  + ``[DEFAULT]default_graphical_console_interface`` - This config option
    represents the default graphical console interface to be used with various
    drivers. The default value will be ``no-graphical-console``.

* Two new fields will be added to the Node object:

  + ``graphical_console_interface`` - This field represents the supported
    graphical  console interface for the node.

  + ``graphical_console_enabled`` - This field will a Boolean value that will
    represent the state of console. It will be set to True via request to start
    the graphical console.

* While a node unprovisioning, Ironic will stop all the graphical connections
  to the node.

Alternatives
------------

* Accept this limitation and only offer a serial console.

* Use out-of-band KVM access provided by administrator without Ironic support.

* Generalize and formalize concept of a ``console`` interface,
  and allow to have arbitrary number of console interfaces
  (from those declared as supported by a hardware type) to be active and
  enabled for a particular node.

Data model impact
-----------------

- A new node field ``graphical_console_enabled``, during upgrade/conversion
  will be populated from ``default_graphical_console_interface`` config option
  (``no-graphical-console`` by default).
- new node field ``graphical_console_interface`` will be added.

State Machine Impact
--------------------

None.


REST API impact
---------------

* Add a new optional ``console_type`` parameter to
  ``GET /v1/nodes/{node_ident}/states/console`` and
  ``PUT /v1/nodes/{node_ident}/states/console`` APIs. This
  parameter defines which type of console the Ironic users want to access.
  The default value will be ``serial``. The possible values are as follows:

  + ``serial`` - For accessing the serial console.
  + ``graphical`` - For accessing the graphical console.

  This parameter will be included in the query string.

Example::

    GET /v1/nodes/{node_ident}/states/console?console_type=graphical

The response would be same as the console interface. A new 400 HTTP response
will be returned if user provides a invalid ``console_type``.

The API microversion will need to be bumped.


Client (CLI) impact
-------------------

* A new option ``--type`` will be added to OSC command
  ``openstack baremetal node console enable`` and
  ``openstack baremetal node console disable``.

* A new option ``--type`` will be added to OSC command
  ``openstack baremetal node console show``.


RPC API impact
--------------

* Add a new ``console_type`` parameter to ``get_console_information``

* Add a new ``console_type`` parameter to ``set_console_mode``

The RPC API microversion will need to be bumped.


Driver API impact
-----------------

* The new ``GraphicalConsoleInterface`` will be included in the standardized
  interfaces group. It is not a mandatory interface.

Nova driver impact
------------------

Nova impacts are fully described in the VNC console support for Ironic
driver [#]_ blueprint in Nova.

Essentially, the Ironic virt driver will have to implement ``get_vnc_console``
and call Ironic's get/set-console-mode with the ``graphical`` type.

As per policy in Nova, changes cannot land until ironic and python-ironicclient
changes have landed. The changes on the Nova side are fairly straightforward.


Ramdisk impact
--------------

None.


Security impact
---------------

* The VNC connection to the nodes are secured by a token generated while
  creating the console in Nova.

* With standalone Ironic deployment, this will return a URL and a user
  could directly connect with it. The connection to the baremetal node
  will not be secure.

Other end user impact
---------------------

* The number of maximum connections per console, specifically VNC consoles is
  implementation specific. Some servers are capable of multiple connections and
  others aren't.


Scalability impact
------------------

* As mentioned in the last section, the number of connections varies based on
  the hardware.

* TODO(mkrai): Update the number of connections a conductor can handle to
  address Ruby's comment on PS7.


Performance Impact
------------------

None.


Other deployer impact
---------------------

* Adds ``enabled_graphical_console_interfaces`` config option.

* Adds ``default_graphical_console_interface`` config option.

Developer impact
----------------

Driver developers can now offer multiple console interfaces rather than
sticking to a single one. This actually maps much better to the reality
of servers often offering a Serial-on-LAN access along with a
Keyboard-Video-Mouse access.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  * mkrai

Other contributors:
  * anupn

Work Items
----------

* Introduce ``ipmitool.IPMIVNCConsole(BaseInterface)``

* Add ``console_type`` support to the console REST API.

* Add ``console_type`` support to the RPC methods.

* Add ``console_type`` support to the OSC plugin.

* Add graphical console support to VirtualBMC

* Implement basic enable-disable + connect testing within devstack

* Update documents to explain how graphical console can be used


Dependencies
============

None.


Testing
=======

* Unit tests

* CI testing of ``ipmitool.IPMIVNCConsole`` with a basic enable-disable
  connect test.

* Add support for graphical console support in virtual BMC for gate test.


Upgrades and Backwards Compatibility
====================================

Proper compatibility with Nova will be ensured. A newer Nova will continue to
behave as it currently does when running with an older ironic. A newer ironic
will expose features that Nova will simply not use.

Backwards compatibility within ironic is assured through RPC versions.
Additional care is taken to ensure out-of-tree drivers are still compatible
because the code will specifically handle drivers not switched to the new
hardware types. Specific tests covering this part will be added. Finally,
compatibility with older API clients is assured through REST API microversions.


Documentation Impact
====================

* Documentation will be updated.


References
==========

.. [#] https://blueprints.launchpad.net/nova/+spec/ironic-vnc-console
