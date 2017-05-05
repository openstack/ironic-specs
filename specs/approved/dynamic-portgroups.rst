..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===================
Dynamic port groups
===================

https://bugs.launchpad.net/ironic/+bug/1652630

In the Ocata release, Ironic added support for grouping ports into port groups.
The administrator also has the ability to specify ``mode`` and ``properties``
of a port group by using appropriate port group fields. However
the administrator is still required to pre-create a port group on the
ToR (Top of Rack) switch manually. Or find some other way to sync
portgroup settings between Ironic and the ML2 driver.



Problem description
===================

While Ironic provides the ability to create port groups with different
configurations (mode and properties), port groups still have to be pre-created
on ToR manually as we do not pass port group details to ML2 drivers.
To make port groups creation ``dynamic`` Ironic should pass port group settings
to Neutron ML2 drivers. The ML2 driver is responsible for port group
configuration (creation/deletion) on ToR switch during deployment.

This spec does not cover end-user interface for specifying port group
configuration when doing ``nova boot`` at this moment. It can be extended
when community has some agreement on it.

Proposed change
===============

Start passing port group information to Neutron ML2 drivers via the Neutron
port ``binding:profile`` field. Appropriate Neutron ML2 drivers will use that
information to create port group dynamically on the ToR switch.

  .. note::
      We cannot use existing ``binding:profile`` ``local_link_information`` key
      as it is a list with port details, where ``switch_id`` and ``port_id`` are
      mandatory keys. For portgroup object those keys are not required as
      portgroup is virtual interface and might be spread across different
      switches. For example `MLAG <https://eos.arista.com/mlag-basic-configuration/>`__
      configuration.

The ``binding:profile`` data structures is yet in discussion. Possible options
are provided in the `Binding profile data structure`_

Binding profile data structure
------------------------------

Scenario 1 (Preferred)
~~~~~~~~~~~~~~~~~~~~~~

* Introduce new ``local_groups_information`` array that stores portgroups
  information.
* Reuse existing ``local_link_information`` for port objects only
* Setup links between ``local_groups_information`` and
  ``local_link_information`` objects.

A JSON example of ``binding:profile`` with ``local_link_information`` reuse:

  ::

    "binding:profile": {
        'local_link_information': [
            {
                'id': '13070d34-fcc6-46d9-ad45-fb8d489873bf',
                'switch_info': 'tor-switch0',
                'port_id': 'Gig0/1'
                'switch_id': 'aa:bb:cc:dd:ee:ff'
            },
            {
                'id': '62a4428a-3974-409d-9934-d88d0a815397',
                'switch_info': 'tor-switch0',
                'port_id': 'Gig0/2',
                'switch_id': 'aa:bb:cc:dd:ee:ff'
            }
        ],
        'local_groups_information': [
            {
                'id': '51a9642b-1414-4bd6-9a92-1320ddc55a63',
                'name': 'PortGroup0',
                'bond_mode': 'active-backup',
                'bond_ports': ['13070d34-fcc6-46d9-ad45-fb8d489873bf', '62a4428a-3974-409d-9934-d88d0a815397'],
                'bond_properties': {
                    'bond_xmit_hash_policy': 'layer3+4',
                    'bond_miimon': 100,
                }
            },
        ],
    }


Scenario 2
~~~~~~~~~~

* Introduce new ``links`` array that stores mixed group of objects (ports and
  portgroups). Where ``type`` of object is the only one mandatory key.
* Deprecate existing ``local_link_information``

A JSON example of ``binding:profile`` with ``links`` array:

  ::

    "binding:profile": {
        'links': [
            {
                'id': '51a9642b-1414-4bd6-9a92-1320ddc55a63',
                'name': 'PortGroup0',
                'type': 'bond',
                'bond_mode': 'active-backup',
                'bond_ports': ['13070d34-fcc6-46d9-ad45-fb8d489873bf', '62a4428a-3974-409d-9934-d88d0a815397'],
                'bond_properties': {
                    'bond_xmit_hash_policy': 'layer3+4',
                    'bond_miimon': 100,
                }
            },
            {
                'id': '13070d34-fcc6-46d9-ad45-fb8d489873bf',
                'type': 'phy',
                'switch_info': 'tor-switch0',
                'port_id': 'Gig0/1'
                'switch_id': 'aa:bb:cc:dd:ee:ff'
            },
            {
                'id': '62a4428a-3974-409d-9934-d88d0a815397',
                'type': 'phy',
                'switch_info': 'tor-switch0',
                'port_id': 'Gig0/2',
                'switch_id': 'aa:bb:cc:dd:ee:ff'
            }
        ],
    }

The data types:

+-----------------------+---------------------------------------------------+
| Field Name            | Description                                       |
+=======================+===================================================+
| id                    | The UUID of Ironic port/portgroup object          |
+-----------------------+---------------------------------------------------+
| name                  | The name of the ironic port group                 |
+-----------------------+---------------------------------------------------+
| bond_mode             | Ironic portgroup mode                             |
+-----------------------+---------------------------------------------------+
| bond_ports            | List with UUID of Ironic ports, that are members  |
|                       | of port group                                     |
+-----------------------+---------------------------------------------------+
| bond_properties       | Ironic portgroup properties                       |
+-----------------------+---------------------------------------------------+
| switch_info           | The hostname of the switch                        |
+-----------------------+---------------------------------------------------+
| port_id               | The identifier of the port on the switch          |
+-----------------------+---------------------------------------------------+
| switch_id             | The identifier of the switch, ie mac address      |
+-----------------------+---------------------------------------------------+

.. note::
    It is recommended to pick ``bond_mode`` and keys/values for
    ``bond_properties`` from the [1]_ as they will be used by
    user OS.

Alternatives
------------

* Use port groups in the static fashion when administrator pre-creates
  port group on ToR switch.
* If ML2 driver supports port group creation, make sure that port group
  properties in Ironic and ML2 are the same.

Data model impact
-----------------

None.

State Machine Impact
--------------------

None.

REST API impact
---------------

None.

Client (CLI) impact
-------------------

None.

RPC API impact
--------------

None.

Driver API impact
-----------------

None.

Nova driver impact
------------------

None.

Ramdisk impact
--------------

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

No need to pre-create port group at the ToR switch. Only need to specify
port group configuration at the Ironic portgroup object.

Developer impact
----------------

Out of tree network interfaces should be updated to pass ``portgroup.mode``
and ``portgroup.properties`` with ``links`` array in Neutron port
``binding:profile`` field.
Vendors are responsible to deal with ``links`` to support dynamic port groups.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  vsaienko <vsaienko@mirantis.com>

Work Items
----------

* Update ``neutron`` network interface to pass data structure described in
  `Binding profile data structure`_ to Neutron.
* Add dynamic port group support to networking-generic-switch
* Update tempest with appropriate tests.

Dependencies
============

Dynamic portgroup support is dependent on Neutron ML2 driver functionality
being developed to deal with ``links`` array in ``binding:profile`` field.

Testing
=======

* Add dynamic port group support to networking-generic-switch

* Update tempest with appropriate tests.

Upgrades and Backwards Compatibility
====================================

Backward compatibility is retained as Ironic will still pass
``local_link_information`` in Neutron port ``binding:profile`` field.

Documentation Impact
====================

This feature will be fully documented.

References
==========

.. [1] *Linux kernel bond*: https://www.kernel.org/doc/Documentation/networking/bonding.txt
