..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=============================================
Attestation Interface and Keylime Integration
=============================================

https://storyboard.openstack.org/#!/story/2002713

In order to help verify that baremetal nodes are in a trustworthy
state, we are in need of an interface that allows us to take certain
actions or verification steps while proceeding along the state machine.

Some of these steps may involve calling an external attestation server,
or executing a special step during cleaning in order to ensure that a
node is owned by the attestation server.

At a high level, we need an interface of hooks. And there is no better
way than to provide a facility to execute external tooling.


Problem description
===================

Terms Glossary
--------------

In trying to bring together two unrelated services, a bit of namespace
pollution was inevitable. So for those unfamiliar with Keylime terminology and
to avoid confusion with Openstack vocabulary, we will define all the terms
needed for this spec here.

"Trusted Platform Module (TPM)" - a microcontroller within a machine which can
create and store hashes securely. All nodes looking to use Keylime for
attestation will need to have TPM 2.0.

"Integrity Measurement Architecture (IMA)" - A security subsystem in Linux
which gathers hashes of files, file metadata, and process metadata as a
'measurement' of the system. Stores the measurement in the machine's TPM. In
the context of Ironic and Keylime integration, we will need to run IMA on the
node we are attesting.

"allowlist" - A hash representing the golden state of the node. In the context
of Keylime, an allowlist is compared with an IMA measurement to see if the node
has been tampered with in an unauthorized way.

"Keylime verifier" - A component of the Keylime suite which is responsible for
comparing the allowlist to the measurement gathered from the node we are
attesting. The verifier will run on a machine external to Ironic and the node
Ironic is controlling and looking to attest.

"Keylime registrar" - A component of the Keylime suite which Ironic will need
to talk to in order to initiate the attestation workflow for a node. The
registrar also runs on a machine external to Ironic and the node. The verifier
and registrar may run on the same machine, but it is not necessary and the
decision is left to the operator.

"Keylime agent" - A component of the Keylime suite which runs on the node we
are attesting. The agent will command IMA to collect measurements and
send the measurements to the verifier.

"Keylime tenant" - An API which the Ironic conductor will need to use to
communicate with the registrar and verifier. Not to be confused with Openstack
tenants.

Introduction
------------

Presently, we rely upon a certain level of trust for users that leverage
baremetal resources. While we do perform cleaning between deployments,
a malicious attacker could potentially modify firmware of attached devices
in ways that may or may not be readily detectable.

The solution that has been proposed for this is the use of a measured launch
environments with engagement of Trusted Platform Management (TPM) modules to
help ensure that the running system profile is exactly as desired or approved,
by the attestation service.

But from a security standpoint, security is not always about code.
Sometimes security is adherence to process. To leverage TPM's for
attestation, we propose Keylime, an open source remote boot attestation and
runtime integrity measurement system.

The first step requires a new interface type 'attestation_interface'
to be added as a subclass of 'BaseDriver'. This would then come with a
'attestation_interface' implementation which would use Keylime to learn about
the security state of a node and manage configurations. All calls to the
attestation interface would happen along existing clean and deployment
workflows and simply fail transition if a node is deemed to be compromised.

The second step is a set of enhancements for the ramdisk to support TPM 2.0,
and installation of the Keylime agent. From there the Keylime agent
would communicate with the registrar and verifier. The manager would
trigger attestations at certain points along the node's workflow ex) during
the boot process. Note that in order to perform attestation, the verifier
must be within the same network as the node.


Proposed change
===============

Attestation Interface
---------------------

The addition of a ``attestation_interface`` field in the ``nodes`` table,
which maps to a `task.node.driver.attestation` interface, along with the other
standard configuration parameters and defaults behavior that exists with
the driver composition model.

Accordingly the ``attestation_interface`` would be returned on the node object
when retrieved via the REST API, and will be able to be set as another
interface.

The attestation_interface will provide a means of configuring and orchestrating
a node's connection with a verifier machine.

The Ironic controller will work under the assumption that the
network used to communicate with the attestation service is secure and
that the attestation entity is also always trustworthy. Trying to concern
ourselves with issues like replay attacks or spoofed messages is beyond
the scope of IMA attestation workflows.

To accommodate operator workflows wherein an operator may not have
access to the attestation service, we cannot allow the attestation service
perform any orchestration. This requires all communication to an
attestation service to involve the Ironic controller polling an API for a
status or instructing the attestation service or node to take action, as
opposed to receiving information from the attestation service or node
itself. For example, Keylime offers revocation frameworks for taking
action immediately upon a node being compromised. However, from
Ironic's perspective, allowing another service to do any orchestration
could put Ironic in a state where it does not know what is happening
on the node.

Presently, we are mainly concerned with monitoring deployment and
cleaning of a node. The intended workflow will be to use the interface
during these steps to ensure the firmware of a node has not been
modified.

Keylime Interface
-----------------

The Keylime interface will inherit from the AttestationInterface class. The
purpose of the interface is to allow the controller to gather relevant
information about the security state of the node and take action based on
the results. Doing so will require methods which will make calls to the
Keylime verifier through the available REST API as well as calls to the IPA
to pass necessary configuration parameters. Keylime is anticipated to be
supported by generic hardware types.

Keylime Configuration
---------------------

The Keylime verifier and Keylime registrar are two components of the Keylime
suite which must be stood up by an operator. The verifier and registrar will
need TLS connections over https in order to communicate. The Keylime tenant CLI
is installed on ironic controller. The operator will be responsible for
securing any network the registrar and verifier are setup in.

Detailed communication requirements are list as following:

    Keylime tenant -> Keylime verifier: mutual TLS connection

    Keylime verifier/tenant -> node: unencrypted connection

    Keylime verifier/node/tenant -> registrar: mutual TLS connection for
    post/put requests; unencrypted connection for get/delete requests

Every Keylime agent must have a uuid associated with it in order to register
itself with the registrar. It generates its uuid using the Keylime config
file. The uuid defaults to a random id.

Allowlist and Excludelist
-------------------------

Allowlists and Excludelists will be generated beforehand and hosted on a
remote server or in the conductor's filesystem. A filepath for the conductor's
filesystem or url to a remote server to locate such files will be supplied to
Ironic before provisioning. Allowlists may also be signed with a checksum to
ensure they have not been tampered with. Such checksums would also be
supplied to Ironic with a path or url to the file. Supplying an allowlist is
required in order to perform attestation. Excludelists are not required but
are used in a majority of Keylime use cases.

The paths of the allowlist, checksum, and excludelist can be saved in
``driver_info\keylime_allowlist``,
``driver_info\keylime_allowlist_checksum``, and
``driver_info\keylime_excludelist``.

Linux's IMA submodule gathers measurement list signed with TPM quote. The
Ironic controller will send the allowlist to the verifier using the Keylime
tenant. The Keylime verifier obtains the measurement list and performs
attestation by comparing the measurement list against allowlist.

Alternatives
------------

We could add such functionality to various interfaces, but generally
attestation will be a specific model for a deployment or portion of a
deployment, and thus we may one day have need for "vendor" specific drivers
for particular attestation solutions and workflow. As such, not creating a
new interface for this seems less ideal.

Another alternative would be to perform certain checks along state transitions.
For example, at clean time we can check the firmware and fail if things have
been modified. However, this is undesirable in a scenario where we have strict
workflows and processes we want to adhere to. In the situation where an owner
lends a node to an untrustworthy lessee the owner might want to ensure the
lessee does not perform any unexpected actions. This is also less extensible
to other workflows such as a periodic monitoring.

Data model impact
-----------------

Addition of a ``attestation_interface`` field to the node object, and this
will require a database migration to create the field. The field will
default to ``None`` which will map to a no-attestation interface.

State Machine Impact
--------------------

No impact to the state machine is expected. All calls to the new interface's
methods will take place in existing workflows driven by the state machine.
Action will be taken on a result immediately upon receiving the result.

REST API impact
---------------

The ``attestation_interface`` will be added to the node object and guarded by
an API microversion.

Client (CLI) impact
-------------------

"ironic" CLI
~~~~~~~~~~~~

None

"openstack baremetal" CLI
~~~~~~~~~~~~~~~~~~~~~~~~~

The OSC plugin will be changed accordingly to assist users in
changing the new ``attestation_interface`` field.

RPC API impact
--------------

This new ``attestation_interface`` field requires the RPC version to be
incremented.

Driver API impact
-----------------

The attestation interface methods that would be proposed would consist
of a ``no-attestation`` interface defined on a new base class
AttestationInterface.

These methods would consist of::

    def validate_security_status(self, task):
        """Grabs the latest information about the node's security state
        from the attestation machine. Returns nothing on success, raises
        an exception if status is not what we expect or unable to reach
        verifier to obtain a status.
        """

    def start_attestation(self, task):
        """Grabs the allowist, allowlist checksum, and excludelist from
        ``driver_info`` instructions. Verifies the integrity of the allowlist
        using the checksum. Attempts to send the allowlist and excludelist to
        the attestation service. Sending allowlist and excludelist allows the
        node to begin attesting itself. Returns nothing on success, raises an
        exception if checksum does not pass or is unable to reach the
        verifier to send allowlist/excludelist.
        """

    def unregister_node(self, task):
        """Unregisters the node from the verifier machine. Returns
        nothing on success, raises an exception if status is not what
        we expect.
        """

These methods can be used during the node's cleaning and
deployment time. The action taken on a particular security state
will be configurable. Whether or not we raise an error on attestation failure
will be configurable.

A few additional variables will need to be saved as part of ``driver_info``
in order to manage the node. These include:

    ``driver_info\keylime_allowlist`` the allowlist for a node.

    ``driver_info\keylime_allowlist_checksum`` a checksum for the allowlist
    to ensure the allowlist has not been tampered with.

    ``driver_info\keylime_excludelist`` the excludelist for a node.

    ``driver_info\keylime_agent_uuid`` the uuid for a Keylime agent. Needed
    for querying the verifier for a security status and associating an
    allowlist/excludelist pair with a node in the Keylime verifier.

Workflow
--------

With all this in mind, we have devised the following workflow for deployment/
cleaning using a Keylime implementation of the attestation interface.

Beforehand, the operator will stand up a machine with the Keylime verifier and
registrar. The user will generate their own allowlist, allowlist checksum,
and excludelist for the node. An admin may make these files available on the
same machine as the Ironic controller and pass in the filepath to
``driver_info`` or a non admin may make these files available to grab and
instead pass in a url to ``driver_info``. This step must be done before
provisioning. The operator will also pass in how to locate the Keylime
registrar and verifier to ``driver_info.``

During the image building process the node image will be set up with an
instance of the Keylime agent, as well as TPM, and IMA configurations which
will allow the Keylime agent to run. The Keylime agent will register itself
with the Keylime registrar automatically once started. At this point booting
has begun and the node may send its first heartbeat back to the Ironic
controller.

Next, start_attestation() will be called to send the allowlist and
excludelist to the verifier. The conductor will make an rpc call to the agent
to retrieve the Keylime agent's uuid, the Keylime agent's address, and the
port which the Keylime agent is listening on. The Ironic controller will save
these variables as ``driver_info\keylime_agent_uuid``,
``driver_info\keylime_agent_address``, and
``driver_info\keylime_agent_port`` for further use. If the conductor does not
receive these credentials cleaning will fail.

The allowlist and excludelist will be sent to the verifier by calling the
keylime_tenant cli programmatically. Once the verifier has received the
allowlist and excludelist, attestation will begin. The verifier will
periodically poll the Keylime agent for IMA measurements and compare them
with the allowlist and excludelist to determine if the node has been tampered
with. The verifier will record the status of the node, but take no action on
the status.

At this point, the conductor may perform a validate_security_status() call to
get the status of the node. If the status is what we expect, we may proceed.
If the status is something we do not expect, or the controller is unable to
access the verifier due to network issues, we will fail the deployment.

The Keylime agent will need to be unregistered with a call to unregister_node()
to instruct the Keylime verifier to end its connection and remove the node from
its database.

Here is a diagram for the anticipated workflow:

diagram {
Image; Node; Keylime-tenant; Keylime-verifier; Keylime-registrar;
activation = none; span_height = 1; edge_length = 250;
default_note_color = white; default_fontsize = 12;
Image -> Node [label = "The node is booted with an image generated by
diskimage-builder tool. Keylime and TPM environment is setup in the image"];
Node -> Keylime-registrar [label = "Makes a post request to register the
Keylime agent on the node"];
Keylime-registrar -> Node [label = "Responses the node with an encrypted AIK"];
Node -> Keylime-registrar [label = "Makes an activation request with an
ephemeral registrar key from TPM"];
Keylime-registrar -> Node[label = "200 OK"];
Node -> Keylime-tenant [label = "First heartbeat"];
Keylime-tenant -> Keylime-tenant [label = "The allowlist and excludelist are
provided by the user to the Keylime tenant command"];
Keylime-tenant -> Keylime-verifier [label = "Sends allowlist and excludelist
and adds the Keylime agent uuid to the verifier"];
Keylime-tenant -> Node [label ="Gets TPM quote from the node to check the
Keylime agent’s validity with the registrar"];
Keylime-verifier -> Node [label ="Starts polling the node for verification"];
Keylime-tenant -> Keylime-verifier [label = "Gets the current status of the
node"];
}

Workflows which allow node lessees to bring their own Keylime instance in to
attest a node is theoretically possible within the framework given in this
spec. However, Keylime currently lacks certain features needed to make this
fully automated in Ironic.


Nova driver impact
------------------

None

Ramdisk impact
--------------

To have the Keylime agent work with TPM 2.0, certain libraries and
configuration must be provided. These enhancements will come as part of the
ramdisk. This includes tpm2-tss software stack, tpm2-tools utilities,
and, although not required, the tpm2-abrmd resource manager.

Keylime-agent will be setup on the ramdisk. A new dib element will be created
to install keylime-agent and make it run as a system service.

A new IPA extension will be needed to collect and send back to the conductor
the keylime_agent_uuid, keylime_agent_address, and keylime_agent_port.

Security impact
---------------

It has a positive impact on security, since we can verify if the node is
trustworthy by the attestation service.

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

The ``attestation`` interface will not be enabled by default, since the default
will map to a ``no-attestation`` interface.

Config options
~~~~~~~~~~~~~~

Options for configuring whether or not cleaning and deployment
should fail in face of attestation failure will be part of the new
``[keylime]`` section

fail_clean_on_attestation_failure
  Boolean to determine whether to fail clean on attestation failure

fail_deploy_on_attestation_failure
  Boolean to determine whether to fail deploy on attestation failure


Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Leo McGann <ljmcgann> lmcgann@redhat.com
  Danni Shi <sdanni> sdanni@redhat.com

Other contributors:
  None

Work Items
----------

* Add ``attestation_interface`` database field.
* Implement base interface addition
* Implement ``no-attestation`` interface.
* Add node RPC object field
* Add API support and microversion.
* Implement Keylime attestation interface.

Dependencies
============

None

Testing
=======

Testing for this interface and basic functionality, as well as integration
testing using the ansible-keylime-tpm-emulator for TPM emulation.

Upgrades and Backwards Compatibility
====================================

No issues are anticipated.

Documentation Impact
====================

Documentation will be provided about how to use keylime-verifier and
keylime-registrar.

References
==========

https://github.com/keylime
