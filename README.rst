===============================================
OpenStack Baremetal Provisioning Specifications
===============================================

This git repository is used to hold approved design specifications for
additions to the Baremetal Provisioning program, and in particular, the Ironic
project.  Reviews of the specs are done in gerrit, using a similar workflow to
how we review and merge changes to the code itself.

The layout of this repository is::

  specs/approved/
  specs/backlog/
  specs/not-implemented/
  specs/<release>/
  specs/<juno|kilo|liberty>-implemented/

There are also placeholder directories for old links that have been moved.

Specifications must follow the template which can be found at
`doc/source/specs/template.rst`.

Specifications are proposed by adding them to the `specs/approved` directory,
adding a soft link to it from the `specs/not-implemented` directory, and
posting it for review. When a specification is fully implemented, the link in
`specs/not-implemented` directory should be moved to the appropriate
`specs/<release>` directory. Not all approved specifications will get
fully implemented.

Starting with the Mitaka development cycle, all approved specifications
(implemented and not-implemented) will reside in the `specs/approved`
directory.

Prior to the Juno development cycle, this repository was not used for spec
reviews.  Reviews prior to Juno were completed entirely through Launchpad
blueprints::

  http://blueprints.launchpad.net/ironic

Please note, Launchpad blueprints are still used for tracking the
current status of blueprints. For more information, see::

  https://wiki.openstack.org/wiki/Blueprints

For more information about working with gerrit, see::

  http://docs.openstack.org/infra/manual/developers.html#development-workflow

To validate that the specification is syntactically correct (i.e. get more
confidence in the Jenkins result), please execute the following command::

  $ tox

After running ``tox``, the documentation will be available for viewing in HTML
format in the ``doc/build/`` directory.
