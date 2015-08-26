..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===========================================
iRMC Virtual Media Deploy Driver for Ironic
===========================================

https://blueprints.launchpad.net/ironic/+spec/irmc-virtualmedia-deploy-driver

The proposal presents the work required to add support for deployment
features for FUJITSU PRIMERGY iRMC, integrated Remote Management
Controller, Drivers in Ironic.


Problem description
===================
FUJITSU PRIMERGY servers are capable of booting from virtual media,
but Ironic lacks a driver which can utilize this for PXE/TFTP less
deployment.

Proposed change
===============
Adding new iRMC Drivers, namely iscsi_irmc and agent_irmc, to enable
PXE/TFTP less deployment capability to provision PRIMERGY bare metal
nodes (having iRMC S4 and beyond) by booting the bare metal node with
virtual media using NFS or CIFS from a conductor node to deploy an
image.

iRMC virtual media deploy driver is basically same as iLO's. However
comparing iRMC deploy driver with iLO deploy driver, the only
significant change is the location of virtual media images,
specifically deploy ISO image, floppy FAT image and boot ISO image.
The location where iRMC deploy driver places the created floppy FAT
image and the boot ISO image is on an NFS or CIFS server, while the
location where iLO deploy driver creates is on Swift Object Storage
Service.
The location where iRMC mounts the three images is from an NFS or
CIFS server, while the location where iLO mounts is from the http
temp-url generated for the Swift object Service.
The other parts are common.

Before starting Ironic conductor, however, deployer has to set up
operating system properly so that Ironic conductor mounts the NFS or
CIFS shared file system on path "/remote_image_share_root" as default,
the path is configurable in the ironic configuration file.
This driver checks this mount at start up time.

The NFS or CIFS server can be located anywhere in the network as long
as iRMC and Ironic conductor can reach it.
The NFS or CIFS server and the network path should be redundant so
that a bare metal node won't fail to boot. For this reason, Ironic
conductor is not recommended to be used as the NFS or CIFS server for
high available environments.

The iRMC deploy module uses `python-scciclient package <https://pypi.python.org/pypi/python-scciclient>`_
to communicate with ServerView Common Command Interface (SCCI) via
HTTP/HTTPS POST protocol.

The details of ServerView Common Command Interface (SCCI) is described
in `FUJITSU Software ServerView Suite, Remote Management, iRMC S4 - integrated Remote Management Controller <http://manuals.ts.fujitsu.com/file/11470/irmc-s4-ug-en.pdf>`_

Alternatives
------------
Other drivers such as the following can be used, but there are no
drivers that can boot using virtual media.

* iRMC driver for PXE (pxe_irmc) which can boot in either Legacy mode
  or UEFI. The details of the boot mode control is described in
  `iRMC Management Driver for Ironic <http://specs.openstack.org/openstack/ironic-specs/specs/kilo/irmc-management-driver.html>`_.

* IPMI driver for PXE (pxe_ipmitool) which can boot only in Legacy mode.


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
None

RPC API impact
--------------
None

Driver API impact
-----------------
None

Nova driver impact
------------------
None

Security impact
---------------
* Admin credentials will be stored unencrypted in the Ironic
  configuration file, and the DB which will be visible in the
  driver_info field of the node when a node-show is issued.
  But only the ironic admin user will have access to the Ironic
  configuration file and the DB.

* NFS and CIFS have very similar functionality, but have different
  security model.
  NFS server authenticates NFS client based on NFS client host IP
  address, while CIFS server authenticates CIFS client based on user
  identity.
  For this reason, this driver deals with CIFS as default, and NFS as
  alternative.
  Advanced deployer could use NFSv4 and Kerberos to authenticate NFS
  client based on user identity. Detail information is available in
  each linux distribution manual ([#]_, [#]_)

  .. [#] https://help.ubuntu.com/community/NFSv4Howto
  .. [#] http://docs.fedoraproject.org/en-US/Fedora/17/html/FreeIPA_Guide/kerb-nfs.html


Other end user impact
---------------------
None

Scalability impact
------------------
NFS or CIFS server would become performance bottleneck in case of
managing a large number of bare metal nodes such as more than 1,000
nodes. In that case, the load needs to be distributed and balanced among
multiple of NFS or CIFS server settings (([#]_, [#]_, [#]_)

.. [#] https://help.ubuntu.com/community/HighlyAvailableNFS
.. [#] https://wiki.samba.org/index.php/Samba_CTDB_GPFS_Cluster_HowTo
.. [#] https://access.redhat.com/documentation/en-US/Red_Hat_Enterprise_Linux/6/html/Cluster_Administration/ch-clustered-samba-CA.html


Performance Impact
------------------
None

Other deployer impact
---------------------
* The following parameters are required in the [irmc] section of
  the ironic configuration file which is typically located at
  /etc/ironic/ironic.conf in addition to the parameters defined in
  `iRMC Power Driver for Ironic <http://specs.openstack.org/openstack/ironic-specs/specs/kilo/irmc-power-driver.html>`_

  * remote_image_share_root: Ironic compute node's NFS or CIFS root
    path (string value). The default value is
    "/remote_image_share_root".
  * remote_image_server: IP of remote image server
  * remote_image_share_type: The share type (NFS or CIFS) of virtual
    media. The default value is "CIFS".
  * remote_image_share_name: The share name of
    remote_image_server. The default value is "share".
  * remote_image_user_name: user name of remote_image_server
  * remote_image_user_password: password of remote_image_user_name
  * remote_image_user_domain: domain name of
    remote_image_user_name. The default value is "".

* The following driver_info field is required to support iRMC virtual
  media in addition to the fields defined in
  `iRMC Power Driver for Ironic <http://specs.openstack.org/openstack/ironic-specs/specs/kilo/irmc-power-driver.html>`_.

  * irmc_deploy_iso: deploy ISO image which is either a file name
    relative to remote_image_share_root, Glance UUID, Glance URL or
    Image Service URL.

* The following instance_info field is optional.

  * irmc_boot_iso: boot ISO image file name relative to
    remote_image_share_root, Glance UUID, Glance URL or Image Service
    URL. If it is not specified, the boot ISO is created automatically
    from registered images in Glance.

* In order to use iRMC virtual media deploy driver, iRMC S4 and beyond
  with iRMC a valid license is required. Deployer is notified by error
  message if the iRMC version and/or the license is not valid.

* In order to deploy and boot ISO image via virtual media, an NFS or
  CIFS server is required. The NFS or CIFS server has to be reachable
  from both iRMC and Ironic conductor.

Developer impact
----------------
None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Naohiro Tamura (naohirot)

Other contributors:
  None

Work Items
----------
* Add iRMC Drivers (iscsi_irmc, agent_irmc)

* Implement iRMC virtual media deploy module for the iRMC Drivers by
  reusing and refactoring some part of the code from the current iLO
  deploy driver.

Dependencies
============
* This feature requires iRMC S4 and beyond that is at least BX S4 or
  RX S8 generation of FUJITSU PRIMERGY servers.

* This feature uses `python-scciclient package <https://pypi.python.org/pypi/python-scciclient>`_.

* This feature depends on `iRMC Power Driver for Ironic <http://specs.openstack.org/openstack/ironic-specs/specs/kilo/irmc-power-driver.html>`_
  and `iRMC Management Driver for Ironic <http://specs.openstack.org/openstack/ironic-specs/specs/kilo/irmc-management-driver.html>`_.


Testing
=======
* Unit Tests

* Fujitsu plans Third-party CI Tests

Upgrades and Backwards Compatibility
====================================
None

Documentation Impact
====================
The required driver_info fields and [irmc] section parameters in the
ironic configuration file need be included in the documentation to
instruct operators how to use Ironic with iRMC.

References
==========
* `FUJITSU Software ServerView Suite, Remote Management, iRMC S4 -   integrated Remote Management Controller <http://manuals.ts.fujitsu.com/file/11470/irmc-s4-ug-en.pdf>`_

* `iRMC Power Driver for Ironic <http://specs.openstack.org/openstack/ironic-specs/specs/kilo/irmc-power-driver.html>`_

* `iRMC Management Driver for Ironic <http://specs.openstack.org/openstack/ironic-specs/specs/kilo/irmc-management-driver.html>`_

* `python-scciclient package <https://pypi.python.org/pypi/python-scciclient>`_

* `iLO Virtual Media iSCSI Deploy Driver <http://specs.openstack.org/openstack/ironic-specs/specs/juno/ironic-ilo-virtualmedia-driver.html>`_

* `iLO IPA Deploy Driver <http://specs.openstack.org/openstack/ironic-specs/specs/juno/ilo-virtualmedia-ipa.html>`_

* `Automate UEFI-BIOS Iso Creation <http://specs.openstack.org/openstack/ironic-specs/specs/kilo/automate-uefi-bios-iso-creation.html>`_

* `Support for non-glance image references <http://specs.openstack.org/openstack/ironic-specs/specs/kilo/non-glance-image-refs.html>`_
