..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

================
Snapshot support
================

https://storyboard.openstack.org/#!/story/2008033


Problem description
===================

Snapshot is not a new thing, it was available for virtual machines for a
long time. Snapshot is useful for instance backup, image reusing, etc, but
there is no such support for bare metals as it's more complex than passing
the request to libvirt.

Bare metal snapshot may not match with virtual machines in speed and
efficiency, but it could address following requirements:

As an operator, I want to be able to back up a bare metal instance
periodically and when there is hardware failure, the same image can be
applied to another machine.

As an operator, I want to be able to build a master image from a post
customized instance, capture the system into an image and apply to other
similar machines.


Proposed change
===============

The proposal is to implement a similar process like deployment, when a node
is requested to do a snapshot, ironic prepares boot configuration then
triggers a netboot to the node, IPA lookups and ironic instructs IPA to
streaming the data of root disk to a remote storage.

The remote storage could be the host where the conductor is running if proper
service like NFS, HTTP, etc is configured. Or another host as long as both
conductor and IPA are able to access. The remote storage will act as an
intermediate storage, when the streaming is done, conductor will upload the
image to the image service and remove the image in the intermediate
storage.

The initial proposal is to utlilize HTTP WebDAV as remote storage, NFS and
other storage can be extended when this feature is implemented. When the
direct deploy interface is configured to download images from HTTP service,
it can be updated with WebDAV support.

Alternatives
------------

None

Data model impact
-----------------

A new hardware interface ``snapshot_interface`` will be added to support
different snapshot implementations.


State Machine Impact
--------------------

Add following states to the state machine:

* snapshot wait
* snapshotting
* snapshot failed

With following transitions:

* active -> snapshotting (on snapshot) Prepare boot and network
* snapshotting -> snapshot failed (on fail) On error
* snapshotting -> snapshot wait (on wait) Wait for ramdisk alive
* snapshot wait -> snapshotting (on resume) Image streaming and uploading
* snapshot wait -> snapshot failed (on fail) On timeout
* snapshot wait -> snapshot failed (on abort) On abort request
* snapshotting -> active (on done) Snapshot complete
* snapshot failed -> active (on abort) Abort a failed snapshot
* snapshot failed -> snapshotting (on snapshot) Retrigger a failed snapshot
* snapshot wait -> deleting (on deleted) Abort snapshot and undeploy
* snapshot failed -> deleting (on deleted) Abort and undeploy


REST API impact
---------------

The existing provision endpoint is used, a new verb ``snapshot`` will be
guarded by microversions.

* PUT /v1/nodes/{node_ident}/states/provision

  When the requested version is permitted, and node is in the active state,
  start to do a snapshot. An ``image_ref`` argument is required, which refers
  to a location where the snapshot image should be stored.

  If the ``image_ref`` is an UUID, it refers to the UUID of an image in the
  Image service, the image should be precreated before snapshot request and
  acts as a holder for receiving image data. When integrated with Compute
  service, the ``image_id`` is an argument passed to the driver interface
  ``snapshot()``.

  Example request::

    {
      "target": "snapshot",
      "image_ref": "66498c26-a9b5-496c-97a8-5bc08f256155"
    }

   The ``image_ref`` could be an URL in other forms for standalone usage,
   but not covered in this spec.

Other provision state transitions will use existing verbs.

Client (CLI) impact
-------------------

"openstack baremetal" CLI
~~~~~~~~~~~~~~~~~~~~~~~~~

The impact to CLI should be trivial, will have a new command:

* ``openstack baremetal node snapshot <node> ...``

"openstacksdk"
~~~~~~~~~~~~~~

openstacksdk will be enhanced to know the snapshot API version.

RPC API impact
--------------

Will introduce a new rpc interface ``do_node_snapshot``.


Driver API impact
-----------------

Adds an optional interface ``snapshot_interface``, initially implements
``fake``, ``no-snapshot``, and ``agent``.

.. code-block::python

    class SnapshotInterface(BaseInterface):
        """Interface for snapshot-related actions."""
        interface_type = "snapshot"

        @abc.abstractmethod
        def snapshot(self, task):
            """Perform a snapshot to the task's node.

            :param task: A TaskManager instance containing the node to act on.
            :returns: states.SNAPSHOTWAIT if snapshot is in progress asynchronously
                      or states.ACTIVE if it is complete.
            """

        @abc.abstractmethod
        def continue_snapshot(self, task):
            """Continue snapshot for async operation.

            :param task: A TaskManager instance containing the node to act on.
            """

        @abc.abstractmethod
        def clean_up(self, task):
            """Clean up the snapshot environment for the task's node.

            :param task: A TaskManager instance containing the node to act on.
            """


For the ``agent`` implementation, conductor host needs a WebDAV service to
receive image data from the IPA. When the first heartbeat is received,
ironic conductor sends command ``snapshot.stream_image`` with an URL to the
IPA to start the snapshotting. IPA find the root device and use proper methods
to dump disk data to the remote storage. The criterial for choosing the root
device is same with deployment, on the time of this writing, the root device
is the first available block device not less than 4GiB, or the first matched
device if the root device hint is specified.

There are two methods to utilize the WebDAV service:

* The WebDAV directory is mounted to the ramdisk, IPA uses ``qemu-img`` for
  snapshot, empty blocks will be bypassed so it provides better performance.
* IPA uses ``dd`` to dump the disk data to the WebDAV URL, when finished,
  ironic conductor needs to convert the raw image into proper format.

As the root device could be quite large and even larger than the available
space of conductor host, ``dd`` is not considered practical in the spec.

After the disk data is successfully retrieved, the conductor is responsible
to upload the image to the Image Service using the specified ``image_id`` and
remove the intermediate image.


Nova driver impact
------------------

Nova driver will need to implement the driver interface ``snapshot`` to
integrate with ironic. But before the integration the feature can be consumed
by ironic as long as the Image Service is available.


Ramdisk impact
--------------

For the ``agent`` implementation, a ``snapshot`` extension will be added to
the ironic-python-agent, when the WebDAV directory could be mounted,
``qemu-img`` is used for streaming disk data to the URL.

The snapshot extension will be defined as:

.. code-block::python

    class SnapshotExtension(base.BaseAgentExtension):
        @base.async_command('stream_image')
        def stream_image(self, url, image_name):
            """Stream disk data to the storage using provided information.

            :param url: string, the remote storage in URL format.
            :param image_name: string, the name of the image.
            """

Example arguments for an HTTP WebDAV connection:

* url: "http://10.10.1.1:8080/snapshots"
* image_name: "a830ebe1-67d4-448f-aa10-5bb33f3f3c02-snapshot.qcow2"

IPA will generate an URL to mount::

    mount -t davfs http://10.10.1.1:8080/snapshots /tmp/tmp5fjchif0

.. note::

   NFS connection is not covered but can be implemented after this feature
   is implemented. It will look like::

     mount -t nfs 10.10.1.1:/var/lib/ironic/snapshots /tmp/tmp5fjchif0


Security impact
---------------

The transfer of instance image from the target bare metal to image service
could have security risk since the data could be tampered or retrieved during
this process.


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

None

Developer impact
----------------

None


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  <kaifeng, kaifeng.w@gmail.com>

Other contributors:
  <TheJulia, juliaashleykreger@gmail.com>

Work Items
----------

* Equiping IPA with the ability of streaming disk data
* Spawning states and transitions to Ironic
* DB, RPC and API change
* Make Client/SDK aware of the feature
* Plug in with nova

Dependencies
============

None


Testing
=======

Will be covered by unit tests and tempest.


Upgrades and Backwards Compatibility
====================================

Should be backwards compatible.


Documentation Impact
====================

Documentation will be updated on this feature.


References
==========

* https://etherpad.opendev.org/p/PVG-ironic-snapshot-support
