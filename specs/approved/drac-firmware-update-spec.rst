..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=================================
Dell EMC hardware firmware update
=================================

https://storyboard.openstack.org/#!/story/2003494

Operators and deployers (such as tripleo) need the ability to flash the
firmware on Dell EMC hardware to specific versions before provisioning
baremetal servers.


Problem description
===================

Use cases
---------

* An operator upgrades the firmware for certain hardware components on a
  server to newer versions to take advantage of new features or bug fixes in
  the firmware. This could be prior to or after provisioning.

* An operator rolls back the firmware for certain hardware components on a
  server to prior versions to avoid regressions introduced in newer firmware.
  This could be prior to or after provisioning.

* A deployer (such as tripleo) pins the firmware for certain hardware
  components to specified versions prior to initiating overcloud deployment.

The following use cases are considered outside the scope of this spec:

* An operator or software component uploads a firmware image to a firmware
  image repository.

* An operator or software component removes a firmware image from a firmware
  image repository.

Dell EMC WSMAN firmware management
----------------------------------

WSMAN firmware management is offered by the iDRAC.  Supported operations
are:

* List firmware on server: Enumerate DCIM_SoftwareIdentity

* Update firmware: Invoke
  DCIM_SoftwareInstallationService.InstallFromSoftwareIdentity

Dell EMC Redfish firmware management
------------------------------------

Redfish firmware management is offered by the iDRAC.  Supported operations
are:

* List firmware on server:
  https://$idrac_ip/redfish/v1/UpdateService/FirmwareInventory

* Update firmware:
  https://$idrac_ip/redfish/v1/UpdateService/Actions/UpdateService.SimpleUpdate

Support for firmware management in ``redfish`` hardware type
------------------------------------------------------------

A patch for firmware update in sushy has been merged:
https://review.opendev.org/#/c/613828/
There is no support for firmware update in the ``redfish`` hardware type yet.

Proposed change
===============

Since the Dell EMC ''redfish'' implementation of firmware update is fully
compliant with the DMTF spec, the decision has been made to go with a
``redfish`` implementation.

A manual clean step will be added to the RedfishManagement class to initiate
firmware update. The clean step will accept a list of dictionaries.  Each
dictionary will represent a single firmware update, and will contain a URI to
the firmware image.

As an example::

  "clean_steps": [{
      "interface": "management",
      "step": "update_firmware",
      "args": {
          "firmware_images":[
              {
                  "url": "file:///firmware_images/idrac/9/iDRAC-with-Lifecycle-Controller_Firmware_VRYKT_WN64_3.32.32.32_A00.EXE",
                  "checksum": "<sha1-checksum-of-this-file>"
              },
              {
                  "url": "swift://firmware_container/BIOS_W8Y0W_WN64_2.1.7.EXE",
                  "checksum": "<sha1-checksum-of-this-file>"
              }
          ]
      }
  }]

The implementation will apply the firmware updates in the given order.

The implementation will have no knowledge of dependencies of the supplied
firmware, or if the firmware is applicable to the hardware that it is being
installed on.  The implementation will rely on the firmware update failing
gracefully in these cases.

The updater will fail fast so that if one update fails, it will abort
and not apply the remaining updates. If a failure does occur midway through
applying the updates, successful updates prior to the failed update will not
be rolled back.

The cleaning step will be out-of-band. The firmware update cleaning step
will use Redfish to perform the update.  The intent is to use the
sushy library if possible, and if not, provide vendor extensions as necessary.

While the iDRAC supports rolling back to the last known good firmware, the
ability to do this will not be implemented as part of this spec.  Instead,
if a user wishes to roll back to an early version of the firmware, they will
just do a firmware update to an older version.

While the initial implementation of this will use the Redfish protocol,
it will be implemented in such a way that it will not preclude adding
support for the ``WSMAN`` protocol at a later date.

Alternatives
------------

One alternative would be to implement firmware update using ``WSMAN``.
Because ``WSMAN`` will eventually be deprecated in favor of Redfish, it
is preferred to avoid this option.

Another alternative would be to do firmware update in-band via an Ironic
Python Agent hardware manager for the iDRAC.

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
Users will be able to launch a cleaning step to update the firmware on Dell
EMC servers.

"openstack baremetal" CLI
~~~~~~~~~~~~~~~~~~~~~~~~~
Users will be able to launch a cleaning step to update the firmware on Dell
EMC servers.

RPC API impact
--------------

None

Driver API impact
-----------------

A cleaning step will be added to update the firmware on Dell EMC hardware
managed by the ``redfish`` hardware type.

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

None

Scalability impact
------------------

None

Performance Impact
------------------

None

Other deployer impact
---------------------
To use firmware update, the user will need to configure the selected hardware
type to use the ``redfish`` management interface and set ``redfish``
credentials in the node's driver_info.

Config options
~~~~~~~~~~~~~~

A new [firmware_update] group will be defined in the ironic configuration
file.  The following options  will be moved from the iLO section to that
group.

use_web_server_for_images
    Indicates if images should be uploaded to the conductor web server.
swift_container
    The swift container for firmware images.
swift_object_expiry_timeout
    The timeout in seconds after which the given swift URL should expire.

Developer impact
----------------

None


Implementation
==============

Assignee(s)
-----------

cdearborn

Work Items
----------

* Ironic RedfishManagement changes to add a cleaning step
* python-dracclient changes to implement firmware update
* Ironic iDRAC hardware type changes to add support for the Redfish management
  interface

Dependencies
============

None


Testing
=======

Addition of unit tests to test the firmware update cleaning step.

Upgrades and Backwards Compatibility
====================================

If a firmware update is attempted on a Dell EMC server that does not
support the Redfish UpdateService.SimpleUpdate firmware upgrade command, then
cleaning will be aborted and an appropriate error message logged.

Documentation Impact
====================

The documentation will be updated to cover this new feature.  The
documentation will be updated to include the generations of Dell EMC
hardware officially supported.

References
==========

* Manual cleaning - https://github.com/openstack/ironic-specs/blob/master/specs/approved/manual-cleaning.rst
* sushy - https://github.com/openstack/sushy
