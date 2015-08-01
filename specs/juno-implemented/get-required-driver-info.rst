..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=======================================================
API to Get driver_info Properties
=======================================================

https://blueprints.launchpad.net/ironic/+spec/get-required-driver-info

This blueprint proposes an API that returns all the driver_info properties,
along with a description for each property.


Problem description
===================

It is possible to create a node without specifying any driver_info properties
in the initial POST -- this is reasonable and fine. However, the API does not
expose the list of driver_info properties, nor which are  required for the
node's driver. The client cannot know what fields/properties to send in
subsequent PATCH requests without reading Ironic's developer docs (or source
code!).

To address the above, an API is proposed, that returns the driver_info
properties, along with a description for each property. The description will
include whether the property is required or not.

Being an API, it may be consumed by humans and applications.

Proposed change
===============

.. _rest_api:

RESTful web API
---------------

The RESTful web API will be enhanced with:

    GET /v1/drivers/<driver>/properties

where <driver> is the name of the driver.

If unsuccessful, eg an invalid driver name was specified, it returns HTTP
status 404 and an error message.

If successful, it returns HTTP status 200 and the response (in Json format)
is a list of ::

    <property name>: <property description>

where <property description> is a description of the property, including
whether it is required or optional or any other special circumstances.

Eg: ``GET /v1/drivers/pxe_ssh/properties`` might return::

  {"pxe_deploy_ramdisk": "UUID... Required.",
   "ssh_address": "IP address or hostname of the node to ssh into. Required.",
   "ssh_virt_type": "virtualization software... Required.",
   "ssh_user_name": "username to authenticate as. Required.",
   "ssh_key_contents": "private key(s). One of this, ssh_key_filename,
        or ssh_password must be specified."
   "ssh_key_filename": "filename ... One of this, ssh_key_contents,
        or ssh_password must be specified."
   "ssh_password": "password... One of this, ssh_key_contents, or
        ssh_key_filename must be specified."
   "pxe_deploy_kernel": "UUID... Required."}
  }


.. _cli_subcommand:

CLI subcommand
--------------

The ``driver-properties`` subcommand will be added::

    ironic driver-properties <driver_name>

It returns a table with the driver_info properties of the specified driver.
For each property, this information is displayed:

- name of the driver_info property
- description

Eg::

  $ ironic driver-properties fake_ipminative
  +---------------+---------------------------------+
  | Property      | Description                     |
  +---------------+----------+----------------------+
  | ipmi_address  | IP of the node's BMC. Required. |
  | ipmi_password | IPMI password. Required.        |
  | ipmi_username | IPMI username. Required.        |
  +---------------+---------------------------------+

For invalid driver names, it returns::

    The driver '<invalid-driver-name>' is unknown. (HTTP 404)


Required vs optional properties
-------------------------------

The driver properties are specific to each driver, and depend on the interfaces
(power, deploy, console, rescue, management) of a driver.  It is at the
interface implementation where we identify which properties are required and
which are optional. Having said that, it isn't all black and white. For
example, a driver with the ``SHPower power`` interface requires one of
``ssh_key_contents``, ``ssh_key_filename``, or ``ssh_password`` properties to
be specified. Handling this "exactly one of these must be specified" case might
be reasonable, but what happens if there is a desire for "one or more of these
must be specified", "exactly X of these must be specified", "B must be
specified if A is specified", or "if A is specified, B or C must be specified"?

After :ref:`discussing this <irc_discussion>`, we decided to take the approach
of indicating, as part of the description, whether a property is required or
not along with any constraints on that. No explicit 'required' field will be
returned.


How the API service gets the information
----------------------------------------

A conductor service can handle one or more different drivers.
There could be different versions of conductor services running,
different versions of the API service running, and different versions of
drivers available via the different conductor services.
Ironic currently has a mechanism for versioning the
conductor service and api service (via the RPC_API_VERSION). However,
there is no mechanism yet for versioning of drivers.

When/if Ironic has a mechanism for versioning the drivers,
the API (and code) can be updated to use the driver version to get the driver
properties specific to that version.

Driver upgrades (resulting in one or more conductor services being restarted)
need to be considered, since driver upgrades could include changes to their
properties.  There will be upgrade windows, during which different conductor
services may be handling different drivers due to an upgrade. This
specification assumes that the upgrade window is small, and that
after an upgrade, all conductor services will be handling the same driver
versions. (The right solution is to have explicit driver versioning; an
intermediate solution might be to allow the user to explicitly specify a
conductor service when querying for driver information, but that doesn't seem
to be the right approach to take.)

After the conductor services are upgraded, all the API services should be
restarted. So during the upgrade window, the API services may return
incorrect/different driver property information, but after the upgrade is
done, the information should be correct again.

Although an API service could access/instantiate the drivers directly,
that would only give the service access to local drivers. These
drivers may not be the actual drivers that the conductor services use.
Furthermore, since the drivers talk to hardware, the API service shouldn't
be allowed to access them directly.

The conductor service, then, is the gateway to getting driver properties.
Two approaches were considered:

1. the API service queries, via RPC, a conductor service, to get the driver
   properties. It picks the first conductor service (any one will do if
   we assume that all the conductors are handling the same version of the
   driver). **This is the approach we will take.**
2. the API service queries the DB to get driver properties that the
   conductor services have placed there. When a conductor service starts,
   it adds the property
   information for each of the drivers it can handle, to a DB table.
   Since more than one conductor could be handling the same driver,
   the driver information would be added to a new DB table, different from
   the "conductor" table.

For both of these approaches, making an RPC or DB call for each user
request may become a performance issue; especially if the user requests are
generated by some automated system.
Since the information is static for the lifetime of the conductor services
(or longer), it makes sense for the API services to cache the information
locally.

If an upgrade (where a conductor driver is updated) occurs, all
the API services must be restarted after the conductor service upgrades
are completed. This will clear out the caches, to make sure that the API
services get the most recent drivers' information.

A cache-refresh mechanism could be added, but the information is
relatively static and only changes when a driver changes.
Driver changes should be infrequent enough that
having the API services restarted after conductor services are upgraded
should suffice.

Since there doesn't seem to be much gain with storing the driver information
in the database since caching will be done, having the API service query a
conductor service for the driver information (approach #1) will be implemented.


Alternatives
------------

The driver_info information could be made available in a non-API fashion:

- document the information.

  - pros: no code changes at all, no need to write this specification
  - cons: user needs to know where to find the documentation;
    documentation needs to be kept up-to-date;
    more difficult to write automation tools to extract this information

- read the code.

  - pros: no additional code changes required; no need to write this spec;
    will always be *the source of truth*
  - cons: very user-unfriendly; user needs to know python and know where to
    find the appropriate code.

Given that we think having an API is a GOOD THING, these approaches were
ruled out.

This doesn't describe alternative RESTful web API, CLI commands or response
outputs, because the proposed API is consistent with the existing API, but
clearly there are alternatives.


Data model impact
-----------------

This will add an internal cache to each API service. The database is not
affected.


REST API impact
---------------

See :ref:`RESTful web API <rest_api>` section above for a
description of the new request.

Driver API impact
-----------------

All the driver interfaces (DeployInterface, PowerInterface, ConsoleInterface,
RescueInterface, VendorInterface, ManagementInterface) will/must have a new
method::

    @abc.abstractmethod
    def get_properties(self):
        """Return the properties of the interface.

        :returns: a dictionary with <property name>:<property description>
                  entries
        """

Nova driver impact
------------------

None

Security impact
---------------

None

Other end user impact
---------------------

See :ref:`CLI subcommand <cli_subcommand>` section above for the CLI
subcommand.


Scalability impact
------------------

None

Performance Impact
------------------

Negligible.

Other deployer impact
---------------------

Requirement that all the API services must be restarted after an upgrade
of the conductor services.

Developer impact
----------------

None except for doing reviews. Well, making sure the list of properties is
updated in the code.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  rloo

Other contributors:
  None

Work Items
----------

Bug:

- API does not expose required driver_info
  (https://bugs.launchpad.net/ironic/+bug/1261915)

Patches:

- Implement API to get driver properties
  (https://review.openstack.org/#/c/73005/)
- Add driver-properties command
  (https://review.openstack.org/#/c/76338/)


Dependencies
============

None

Testing
=======

Since the information is static, Ironic unit tests are sufficient.

Tempest testing should be added if the QA team feels it is in the best
interest of Tempest to check the output of common drivers.


Documentation Impact
====================

The CLI subcommand will need to be documented, but the docs team have a script
that generates the documentation via issuing ironic commands.

One or more guides (operators and/or deployment) will need to mention that
all the API services need to be restarted after an upgrade of all conductor
services.

References
==========

.. _irc_discussion:

discussion about how to handle required vs optional properties. Starting from
2014-07-08T14:18:06:
http://eavesdrop.openstack.org/irclogs/%23openstack-ironic/%23openstack-ironic.2014-07-08.log
