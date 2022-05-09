.. _zed-themes:

==================
Zed Project Themes
==================

Themes
======


.. list-table:: Zed Themes
   :widths: 50 40 10
   :header-rows: 1

   * - Theme
     - Primary Contacts
     - Target
   * - `CI Health`_
     - iurygregory, rpittau, TheJulia
     -  1,2,3
   * - `Ironic Safeguards`_
     - TheJulia, arne_wiebalck
     - 2,3
   * - `RBAC Phase 2`_
     - TheJulia
     - 2,3
   * - `OpenConfig support in net-baremetal`_
     - hjensas
     - 2,3


Schedule Structure
------------------

`Zed Release Schedule <https://releases.openstack.org/zed/schedule.html>`_.

Sprint 1
++++++++

The release for this sprint will happen on May (02-06)

Sprint 2
++++++++

The second release is scheduled to happen on Aug 15 - Aug 19

Sprint 3
++++++++

This is the release that will create the stable/zed branch,
according to the release team schedule we have:

* non-client libraries: Aug 22 - Aug 26 (R-6)
* client libraries: Aug 29 - Sep 02 (R-5)
* Final RCs and intermediary releases: Sep 26 - Sep 30 (R-1)


Goals Details
=============


CI Health
---------

During the PTG we notice that we need to enable CI testing for some
features that were included in other releases, and also enable upgrade
testing following the new release cadence adjustment.

Ironic Safeguards
-----------------

We will introduce the ability to safeguard ironic deployments when running
cleaning operations. It will be possible to limit the maximum number of
concurrent cleaning operations for nodes in the infrastructure and also be
able to specify a list of disks that should/shouldn't be cleaned for each node.


RBAC Phase 2
------------

Following the TC goal `Consistent and Secure RBAC <https://governance.openstack.org/tc/goals/selected/consistent-and-secure-rbac.html>`_
we will be working on the Phase 2 described during this cycle.


OpenConfig support in net-baremetal
-----------------------------------

We will be adding device configuration capabilities for networking-baremetal,
since in multi-tenant BMaaS there is a need to configure the ToR network
devices (Access/Edge Switches) and many vendors have abandoned their ML2
mechanism plug-ins to support this.
