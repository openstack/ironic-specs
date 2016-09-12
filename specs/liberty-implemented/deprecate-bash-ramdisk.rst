..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================
Deprecate the bash ramdisk
==========================

https://blueprints.launchpad.net/ironic/+spec/deprecate-bash-ramdisk

This spec is a continuation of the blueprint `ipa-as-default-ramdisk`_
implemented in the Kilo release. This spec intends to deprecate
deployments using the bash script ramdisk.

Problem description
===================

The bash ramdisk is still supported by the drivers prefixed with ``pxe_``
without any deprecation message. In the Kilo release it was agreed that
we should stop supporting the bash ramdisk in the future and we worked
on making the IPA_ ramdisk supported by all drivers in tree.

Also, the bash ramdisk is already lagging behind support for some
features, for example cleaning only works with IPA_.  So now we should
start dropping the support for that ramdisk.

Proposed change
===============

We can not simply delete the code that the bash ramdisk uses, therefore
we should start adding deprecation messages on the ``deploy-ironic``
element from `diskimage-builder`_ and in the vendor passthru methods
``pass_deploy_info`` and ``pass_bootloader_install_info`` which are used
by the bash ramdisk to pass the deployment information to Ironic.

Apart from the deprecation messages this spec also proposes freezing
the features for the bash ramdisk. No new features should be added to it
(like we did to include support for `local boot`_), only bug fixes will
be accepted.

Devstack and tempest jobs should also be updated to not use the bash
ramdisk anymore.

The element in `diskimage-builder`_ and the deprecated code in Ironic
should be removed in the Mitaka release cycle of OpenStack.

Alternatives
------------

Continue to support the bash ramdisk for a longer time.

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

Deployer should start replacing the bash ramdisk with the IPA_
ramdisk. There's no new configuration needed for it, it's a drop-in
replacement.

Developer impact
----------------

Developers won't be allowed to include any new features to the bash
ramdisk, only bug fixes.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  lucasagomes <lucasagomes@gmail.com>

Other contributors:
  everyone


Work Items
----------

* Update Devstack and tempest to use the IPA_ ramdisk instead of the
  bash ramdisk.

* Add deprecation messages on the `diskimage-builder`_ ``deploy-ironic``
  element and vendor passthrus ``pass_deploy_info`` and
  ``pass_bootloader_install_info``.

* Stop accepting new features for the bash ramdisk (code reviews and
  spec review).

* In the Mitaka release cycle remove the element from `diskimage-builder`
  and the code that supports the bash ramdisk in Ironic.

Dependencies
============

None

Testing
=======

Unittests will be added.

Upgrades and Backwards Compatibility
====================================

None

Documentation Impact
====================

The documentation should be updated to say that the bash ramdisk is
deprecated and the examples should now use IPA_ instead.

References
==========

.. _`ipa-as-default-ramdisk`: https://blueprints.launchpad.net/ironic/+spec/ipa-as-default-ramdisk
.. _IPA: https://wiki.openstack.org/wiki/Ironic-python-agent
.. _`local boot`: http://specs.openstack.org/openstack/ironic-specs/specs/kilo/local-boot-support-with-partition-images.html
.. _`diskimage-builder`: https://github.com/openstack/diskimage-builder
