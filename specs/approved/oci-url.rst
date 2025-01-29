..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

====================================
OCI (Container Registry) URL Support
====================================

https://bugs.launchpad.net/ironic/+bug/2085565

Problem description
===================

One of the expected patterns in the Ironic standalone user base is
to utilize a container image as a means to transport an image or bundle of
images between one location and another. Others in the Metal3 community
have expressed interest in doing the same.

Typically this takes the model of a file, inside of a container, which is
available once the container has been launched or if the filesystem layer
contents of the container has been accessed. While a pattern we may one day
support, it is an abstracted interaction model which actually makes it more
complicated to obtain access to the desired file.

That complexity is because in a container model, the file we want, which is a
qcow2 or raw image file, is inside of a filesystem layer file (gz-compressed,
tar format files) which then have to be mapped, extracted into a usable
structure, and then navigated to extract the file. The major downside to
this approach is that each time the *file* in the container is updated into
a new container version, the overall size of the container grows. This may
not be an issue for some, but it means ever increasing overhead for others.

A better, and more efficient path is to utilize the underlying data model to
attach separate "layer" files, which are actually whole binary artifacts, such
as a raw, vhd, or qcow2 image representing the contents of an image.

This presents an interesting path where you match the file contents in layers
up with a binary artifact which could be deployed, which is fundamentally how
multi-architecture container support is handled for other host and hypervisor
types by Podman.

Podman does this by using annotations in the metadata, which allows a client
to identify and extract what is required. For example, if you go to launch a
container on OSX, podman tooling is actually retrieving a disk image.

An example of this data and structure can be found by examining the metadata
available for the machine-os container.

.. code-block:: bash

   skopeo inspect --raw docker://quay.io/podman/machine-os:5.3

The overall positive of this approach is the underlying "layer" file matching
the user required annotations can be updated directly after a single file in
the overall layer has been updated. Effectively "compressing" complexity into
a single shipping and reference format with some minor additional complexity
as a result of the container build process. Please note, we'll dig into the
overall structure modeling of the container after the high level change
proposal below.

In order to streamline the overall flow and interaction, we propose
supporting the model of interaction where we are able to support a container
which has an associated matching disk image by enhancing our image handling
logic to enable access to the relevant artifact based upon annotations with
the goal of simplyfing the overall user experience for operators moving
images which are also containers.

Proposed change
===============

This change proposes adaptation of core Ironic service code to enable
retrieval of artifacts attached to OCI containers.

The first change is to modify Ironic's Image Service code to enable an
OCI protocol mapping, with an associated class which
understands how to authenticate, retrieve metadata, and ultimately download
the required content to a file just like any other image service in Ironic.

.. NOTE::
   There may be need to support declaration of additional annotations, but
   that is outside the intent of this specific specification at this time.

A second change *may* be needed for Ironic-Python-Agent to understand
how to authenticate to an image registry to retrieve the *final* artifact,
but ultimately our hope is the conductor performs all actions related to
identifying the disk image artifact.

Specifically, a pattern exists to artifacts to also be compressed using
Zstandard. This is not feasible for us to support out of the gate with
the Ironic-Python-Agent, so we expect this feature to mainly be used with
the ``image_download_source`` setting to be set to ``local``, to enable
the conductor to perform any decompression. We don't expect to exclude
an ``image_download_source`` of ``http`` though. If an artifact is
*not* compressed with additional compression, this should be entirely
feasible with the existing flow model mirroring what is done when
Swift image downloads are performed.

For example, when the ``image_download_source`` is set to ``local``, then the
conductor would be responsible for retrieval of the requested ``image_source``
from the registry, and providing the safety checked artifact to the
ironic-python-agent. All that the Ironic-Python-Agent would be
aware of when the ``image_download_source`` is set to ``http`` is the URL
which was resolved utilizing the client code to interact with the
container registry.

The overall goal being for a user to be able to set an
``instance_info/image_source`` value to
"oci://fqdn:port/container:version-label", which would result in the required
"raw" or "qcow2" artifact being retrieved and extracted.

The protocol portion of the URL, specifically "oci://" shall be stripped
from the URL provided to the underlying artifact retrieval tool or code path
as it will only be used for the higher level match into the Image Service.

.. NOTE::
   Back-end tools which authenticate and interact with container registries,
   for example podman and spokeo utilize the containers image common library,
   and the man page containers-transports_ is dated 2019 with some specific
   updates being more recent. However, the more recently updated
   OpenContainers distribution-spec_ version 1.1.0 is dated in 2024, and
   explicitly calls out that it's protocol is based upon the docker v2
   protocol with some additions covered in the specification. It may be
   concievable for the project to explicitly strip the leading URL protocol
   format from the user supplied URL and allow the tool to make appropriate
   determination from there, meaning an "oci://" style URL is possible as
   well as or "docker://" style URL. This makes the most sense to do.
   It should also be recognized that the containers-transports
   common code and related documentation simply have *not* been updated
   for a newer consensus.

.. NOTE::
   The use of an explicit, user supplied checksum is not required in
   this model. When digest manifests are referred to directly,
   the manifest's checksum is part of the url. Furthermore, the
   contents of the manifest include the digest value of the binary
   artifact we will retrieve.

.. NOTE::
   It is likely this capability will be implemented via pure python with
   an invocation of an HTTP client library. The base protocol is well
   detailed and examples exist. Furthermore, native python object usage
   will enable appropriate authentication handling for mutli-user
   environments, where doing the same with CLI tools may prove overly
   complex.

Furthermore, many registries, for example like one hosted on OpenShift,
explicitly require authentication for users to access contents in the
remote container registry. Additionally, some public image registries
have fairly restrictive rate limits in place for unauthenticated users.

The best course of action is to support submission of a "pull secret" to
enable image retrieval by the user in the form of an
``instance_info/image_pull_secret`` value for *user* artifact authentication.
The existing secret protection code in the API surface should guard this
value from being API visible, but this value can be utilized to establish
the appropriate temporary user environment or simply to authenticate to the
registry to enable metadata and artifact access

For *service* artifact, and ultimately user artifact collection as a fallback
in secure environment contexts, it is necessary for the service to support
use of the docker auths configuration format. This will be introduced as
a new OCI client configuration option which allows conductor configuration
to hold a pre-shared secret. This will leverage the existing standard
format for container auth.json files. For more details please refer to
container-auth_.

To help enable management of capabilities, a new configuration option will
also be introduced to allow operators to disable this capability.

Overall file retrieval flow will likely take the following path:

1) URL will be processed to remove the protocol portion of the URL.
2) Credentials will be utilized to facilitate a remote registry login.
3) Basic image metadata will be retrieved which allows for translation of
   metadata annotations to identify the specific required blob.
4) The specific required blob will then be retrieved, for example getting
   translated to an HTTP "GET /v2/<name>/blobs/<digest>" command where the
   ``name`` value is the container name, and the ``digest`` is the sha256
   checksum representing the blob, as referenced through the metadata.
   The act of retrieval for ironic-python-agent (IPA) would be through
   IPA to be provided the direct URL to download.
5) The artifact will likely need to be checked for compression *prior* to
   being decompressed. This can be handled as a minor magic byte check and
   opportunistic uncompression separate from the overall flow.

While not distinctly part of this change, another possible future change
is the deployment of containers as an bootable container image.
In such a case, we would just expect the whole container to be set as an
``image_source`` parameter, and ultimately the ``deploy_interface`` would
understand the needful actions required, much like the ``anaconda``
deployment interface works today.

.. WARNING::

   The examples of container artifact modeling for disk images does not
   solve the underlying challenge of a kernel/ramdisk artifact. The proposed
   code does support retrieval of artifacts as long as they are referred to
   utilizing the manifest digest URL, i.e.
   ``example.io/user/image@sha256:manifest_hash``. Additional tagging may
   be an option to enable other artifacts to be retrieved and extracted,
   but those are outside the scope of this specification.

A structural deep-dive
----------------------

It is important to note that the multi-arch artifact linking style takes a
different modeling of containers, in that a top level supplemental artifact
linkage exists. This deep-dive is present to help relate the overall data
structure and modeling to aid readers in the understanding of the OCI
container structural model we're looking at in the additional context to aid
us in creation of our own client code to support artifact retrieval.

For example, the top level index data has a second mapping entry, where the
first is the traditional container file layout, and the second index links to
the required mapping data for multi-architecture.

.. note::
   The examples in this deep dive are from an oci://path copy output from a
   remote registry inspired by Podman's multi-arch support. The file contents
   and structure thus mirror what is API accessible for the container.
   The goal of this is to help paint an illustration of what the data
   structures look like and how they relate.

.. code-block:: bash

  # cat index.json | jq
  {
    "schemaVersion": 2,
    "manifests": [
      {
        "mediaType": "application/vnd.oci.image.manifest.v1+json",
        "digest": "sha256:a4460c00d2244ed88eb44be9f3ffd1a3da4a4594690cc314f5b2de6cc427ed3b",
        "size": 11537
      },
      {
        "mediaType": "application/vnd.oci.image.index.v1+json",
        "digest": "sha256:63fb09d03efaa20f10cacd285f08befb98ae5b4decb3125d6704ca912b99f7eb",
        "size": 1930
      }
    ]
  }

When we evaluate the contents of the second file, we see something
along the following lines. Please note this is being edited down from the
the actual example to focus clarity for context exchange, by removing
artifacts with ``disktype`` annotation ``applehv`` and ``hyperv``.

These contents below are best viewed as a list of artifacts which point
to manifests.

.. code-block:: bash

  cat ./blobs/sha256/63fb09d03efaa20f10cacd285f08befb98ae5b4decb3125d6704ca912b99f7eb | jq
  {
    "schemaVersion": 2,
    "mediaType": "application/vnd.oci.image.index.v1+json",
    "manifests": [
      {
        "mediaType": "application/vnd.oci.image.manifest.v1+json",
        "digest": "sha256:026602a096974b80497e4afba3c8cff8397dbdf46a70197e698011d338491611",
        "size": 474,
        "annotations": {
          "disktype": "qemu"
        },
        "platform": {
          "architecture": "x86_64",
          "os": "linux"
        }
      },
      {
        "mediaType": "application/vnd.oci.image.manifest.v1+json",
        "digest": "sha256:6dda6fec71d06cc3d19460a4228e28aad2c9fc48ce0f7f1c4052f6c97c78b0dd",
        "size": 475,
        "annotations": {
          "disktype": "qemu"
        },
        "platform": {
          "architecture": "aarch64",
          "os": "linux"
        }
      },
      {
        "mediaType": "application/vnd.oci.image.manifest.v1+json",
        "digest": "sha256:a4460c00d2244ed88eb44be9f3ffd1a3da4a4594690cc314f5b2de6cc427ed3b",
        "size": 11537,
        "platform": {
          "architecture": "amd64",
          "os": "linux"
        }
      },
      {
        "mediaType": "application/vnd.oci.image.manifest.v1+json",
        "digest": "sha256:1ad1af838a5d3cb228288f4c0dc8d95617734d10f1c9f46eae871ecf05aaed94",
        "size": 11535,
        "platform": {
          "architecture": "arm64",
          "os": "linux"
        }
      }
    ]
  }

In the above context, these are intermediate pointer files, which help link
the ``platform``, ``os``, and ``disktype`` annocation together. Below is an
example of the disk image. The references lacking a ``disktype`` annotation
are simply just another container filesystem layer reference.

When you utilize the format ``oci://host/container@sha256:hash``,
your referring *directly* to a manifest such as the file below. It is also
important to note that this file has *no* pointer pointing to the previous
data structure.

.. code-block:: shell

  cat blobs/sha256/026602a096974b80497e4afba3c8cff8397dbdf46a70197e698011d338491611 |jq
  {
    "schemaVersion": 2,
    "mediaType": "application/vnd.oci.image.manifest.v1+json",
    "config": {
      "mediaType": "application/vnd.oci.empty.v1+json",
      "digest": "sha256:44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a",
      "size": 2,
      "data": "e30="
    },
    "layers": [
      {
        "mediaType": "application/zstd",
        "digest": "sha256:0bd0cc6a9a7a1656011cd813615124e44ee0fcd63ab71000ec541e1c0502c7cc",
        "size": 1059378224,
        "annotations": {
          "org.opencontainers.image.title": "podman-machine.x86_64.qemu.qcow2.zst"
        }
      }
    ]
  }

Following up on the note regarding layers being compressed blocks of data, the
underlying files are as well, as demonstrated below.

.. code-block:: shell

  $ file ./blobs/sha256/0bd0cc6a9a7a1656011cd813615124e44ee0fcd63ab71000ec541e1c0502c7cc
  ./blobs/sha256/0bd0cc6a9a7a1656011cd813615124e44ee0fcd63ab71000ec541e1c0502c7cc: Zstandard compressed data (v0.8+), Dictionary ID: None
  $ zstdcat ./blobs/sha256/0bd0cc6a9a7a1656011cd813615124e44ee0fcd63ab71000ec541e1c0502c7cc |file -
  /dev/stdin: QEMU QCOW Image (v3), 10737418240 bytes (v3), 10737418240 bytes
  $

In other words, the actual program code should evaluate all top level data,
seeking out an entry with annotations, and an annotation for a ``disktype`` of
``qemu``, and then select the file based upon the ``platform`` dictionary's
``architecture`` field matching the architecture to be deployed.

.. note::
   It must be noted that the ``applehv`` disk types appear, at a glance, to
   be raw disk images, which may be ideal for streaming if available,
   otherwise qemu compatible qcow2 images may instead need to be transferred.

Alternatives
------------

The alternative to supporting such a pattern, is a set expectation that all
users must supply all tooling and process to place images available at HTTP(S)
URLs, however that is illogical when considering we support Glance as an image
source today.

Data model impact
-----------------

No data model impact is anticipated as part of this change.

State Machine Impact
--------------------

None

REST API impact
---------------

None anticipated, although a question should be asked among the project
if we should bump the version as a capability signifier to API consumers,
which is a habit the project has made when substantial capabilities have
been added that would not be otherwise easily discoverable.

Client (CLI) impact
-------------------

None

"openstack baremetal" CLI
~~~~~~~~~~~~~~~~~~~~~~~~~

None

"openstacksdk"
~~~~~~~~~~~~~~

None

RPC API impact
--------------

None

Driver API impact
-----------------

This functionality is anticipated in ironic "common" code available to
all drivers and modules which utilizes the common code for url or object
retrieval. As such, in this model, it is not anticipated to be breaking,
only additive in the overall capabilities.

Nova driver impact
------------------

None

Ramdisk impact
--------------

Overall, no impact to the ramdisk composition or structure is anticipated.

One detail which we will need to address at some point is passing a pull
secert or other bearer token to the agent to enable support for authenticated
container registry artifact access when ``image_download_source`` is set to
``http``.

Security impact
---------------

As part of this change, the overall contract around image checksums shall be
maintained. No other security impact is anticipated, but the implementation in
the Ironic-Python-Agent will need to be mindful that checksum operations
will be required. Checksum resolution, at least in terms of identification
of the proper checksum will be the responsibility of the conductor process.

The proposed model of interaction with Ironic should enable checksums to
occur transparently as they are executed outside of the lowest levels of
artifact retrieval. The underlying protocol is built upon the model of
file transfers over HTTP, which natively may be decompressed if the
client is capable, and is disctinctly different from security issues
in 2024 with ``qemu-img`` where disk images were interacted and streamed
through memory with multiple ``qemu`` plugins attempting to access data
in the user supplied disk image for data transformation. The overall act
of copying from an OCI compliant registry will largely take the shape of
HTTP interactions, possibly including just a transfer of the desirable
artifact file. Once that file is in a state ready for file inspection,
such as qcow2 file, then we anticipate the file to be checked.

Another aspect is any user supplied pull secret which may be required to
access the container registry. At present, if set in the existing
``instance_info`` field with an appropriate name, should result in the value
from being visible to an API consumer. Special care should be taken by the
implementer to purge this value upon the completion of operations.

Other end user impact
---------------------

A user requested ``image_download_source`` of ``swift`` will need to be
explicitly rejected as an incompatible configuration.

Scalability impact
------------------

None anticipated.

Performance Impact
------------------

Use of tools, unless (until) they support direct manifest artifact
retrieval, presently may leverage locations like /var/tmp to cache
pieces of containers, and may require additional artifacts/copies to
be retrieved in an upfront copy operation.

Other deployer impact
---------------------

None.

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Julia Kreger - TheJulia on IRC

Other contributors:
  Steve Baker - sbaker on IRC

Work Items
----------

* Creation of new image retrieval class in Ironic
* Addition of support to potentially supply a pull secret
  and clean up of the pull secret.
* Addition of unit testing in Ironic
* Exploration and work in ironic-python-agent to support this
  capability.

Dependencies
============

At present, no dependencies have been identified.

Testing
=======

An unknown which exists at this point in time is "how" we might be able to
execute CI on such a change. The best possible avenue will be to work with
Metal3 to enable their testing to take this path, however Ironic may
separately need to add additional CI jobs to facilitate this testing.

Upgrades and Backwards Compatibility
====================================

Not Applicable.

Documentation Impact
====================

Documentation will be updated as a result of this feature. We anticipate this
taking the form more of "how to deploy an image from an OCI container" example
documentation, as opposed to "how might you do this" which is the project's
historical style of documentation.

References
==========

* https://etherpad.opendev.org/p/ironic-ptg-october-2024
* https://github.com/opencontainers/image-spec

.. _containers-transports: https://github.com/containers/image/blob/main/docs/containers-transports.5.md
.. _distribution-spec: https://github.com/opencontainers/distribution-spec/blob/main/spec.md?plain=1
.. _container-auth: https://github.com/containers/image/blob/main/docs/containers-auth.json.5.md
