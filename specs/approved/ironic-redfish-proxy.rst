..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

============================================
Redfish Proxy for Ironic Node Power Controls
============================================

https://storyboard.openstack.org/#!/story/2009184

One important aspect of our goal of improving support for node multi-tenancy
is to provide a seamless user experience for node lessees. This includes
enabling lessees to use their existing provisioning workflows on leased nodes
and to have these tools work as expected. Ironic policy does allow for lessees
to access basic power controls through either the Ironic REST API or the
``openstack baremetal`` CLI; however, if such tools lack instructions for
communicating with the Ironic API, the only way for them to function is by
making requests directly to the BMC of the node they wish to provision. This
would require giving the lessee BMC power credentials, which is especially
problematic considering that one of the goals of node multi-tenancy is to
enable this sort of functionality without giving the user such low-level
access. [NMTSTORY]_ [NODELEAS]_

Because such a solution is undesirable, to enable the use of existing
provisioning tools, we instead intend to emulate a standards-based interface
(Redfish, in this case) for use by node lessees. This interface will receive
Redfish API calls such as those made by provisioning tools, perform the
corresponding action within Ironic, and return a response in the format defined
by the Redfish schema. Redfish clients will be able to authenticate in the way
they expect to and these requests will be handled using the same authentication
strategy as the rest of the existing Ironic infrastructure. If all goes
according to plan, this feature will solve the compatibility problem previously
described, and will do so without giving any special permissions to the lessee.

Problem description
===================

The main concern here is compatibility-- the problem in which a lessee has
tools that expect to communicate via an inaccessible interface has two
undesirable solutions.

The first is for the lessee's workflow to be refactored to instead make use of
the Ironic API. For the user this is both time and resource-consuming,
especially considering these lessees will often have access to bare metal nodes
for a limited timeframe.

The second is to provide the lessee with BMC credentials, which aside from
going against the principles of node multi-tenancy, is a huge security risk.
If these credentials are not limited in access scope, lessees could possibly
damage or otherwise compromise the bare metal node. Additionally, if the
provided credentials are not immediately revoked when the lessee is supposed to
lose access to the node, they would retain access to the node's power controls
(and potentially more) until the credentials are changed.

These solutions potentially address the compatibility issue, but in turn, they
create either a major efficiency issue or a major security issue. This feature
intends to address compatibility without significantly compromising security or
efficiency.

Proposed change
===============

We will create a new WSGI service within the main Ironic repo which will serve
a REST API at ``/redfish`` that to the end user, will function like a
legitimate v1 Redfish endpoint, albeit with a limited feature set. This
interface will provide minimal functionality, just enough to allow Redfish
provisioning tools to set the power state of an Ironic node. In the future,
this service could be extended to provide additional features, such as boot
devices, boot modes, and virtual media; however, this is beyond the scope of
what we aim to achieve in this spec.

Implementation details
----------------------

The three key components necessary to achieve this goal are:

1. a means by which users can be authenticated
2. a way to determine the user's identity (roles, projects, privileges, etc.)
3. interfaces for performing operations on the nodes the user wishes to
   provision.

Broadly, the workflow for making use of this feature shall be as follows:

1. Acquire credentials to be used for authenticating with the Ironic Redfish
   intermediary.

   * If the Ironic system in question uses Keystone for authentication, the
     user must create a set of application credentials scoped to the
     appropriate project(s) and domain.
   * If not, the user will authenticate via HTTP basic authentication, which
     will be handled using Ironic's basic auth middleware. Configuring the
     backend where credentials are stored will be left up to individual Ironic
     system operators.

2. (Keystone users only) Authenticate using the Redfish SessionService
   interface.

   * Keystone users will authenticate through the Redfish SessionService
     interface using the UUID of their newly created application credential as
     a username and the credential's secret as a password. In response, they
     will receive a Redfish schema-compliant Session object in the body, as
     well as an authorization token and the URL of the newly created Session's
     interface in the header.

3. Perform the necessary provisioning operations.

   * All requests to Systems endpoints will require authentication; users who
     authenticated with the SessionService in step 2 must provide the
     ``X-Auth-Token`` they received in each request header, and users working
     with HTTP Basic Auth must provide base64-encoded credentials in each
     request header (as specified in [RFC7617]_).

4. (Keystone users only) End the Session created in step 2.

   * Keystone users will send a DELETE request to the URL of the Session
     object returned to them previously, internally revoking the created
     Keystone authentication token (note: not the application credential). If
     the user wishes to perform further actions, they will need to repeat the
     authentication process from step 2 again.

Authentication
~~~~~~~~~~~~~~

The actions that this feature shall provide access to should only be accessed
by certain users. The question of authentication is one of "is the person that
is requesting access really who they claim to be?" How we are to answer this
question depends on the authenticaton strategy in place on the Ironic system
in question.

In the context of Keystone (v3), the question of "who is this person?" requires
a few pieces of information-- the user's identifier, the identifier of the
project they're working on, and the identifier of the domain in which the user
and project exist. However, Redfish expects only the identifier of the user
(UUID or username) to determine identity and as such, authentication would end
up requiring the Redfish user to provide more information than they would
otherwise expect to provide, which poses a potential problem.

We intend to solve this problem through the use of application credentials,
which specify the user, project, and domain they are scoped to. Since each
application credential possesses a UUID, we can use this identifier in place of
all the information that would otherwise be required by Keystone. [APPCREDS]_
This approach is also beneficial from a security standpoint, as it reduces the
number of times raw user credentials are handled directly.

The user will pass the credential's UUID and secret to the SessionService,
where it will internally be passed along to Keystone for verification. If
the information provided is valid, an authorization token will be created and
sent back to the user in a format emulating that of a Redfish Session. Since
Redfish Sessions are required to have a UUID, we will use the audit ID of the
newly created Keystone auth token to satisfy this requirement. According to the
Keystone API reference, "You can use these audit IDs to track the use of a
token ... without exposing the token ID to non-privileged users." [KSTNEAPI]_
We want to make sure this proxy does not unintentionally expose sensitive
information, and the decision to use audit IDs seems like a sensible one in
the context of this problem.

Once the user is finished performing the provisioning actions they intend to
carry out, they will send a DELETE request to the Session URL, as per the
Redfish spec. Internally, this will revoke the Keystone authorization token,
essentially "logging the user out." This is the intended method for ending a
user session, however it is important to note the difference between how
Keystone and Redfish handle session expiration.

Redfish Sessions are designed to expire after a period of inactivity, while
Keystone authorization tokens are designed to expire at a specific time (e.g.
an hour or two after creation). We do not intend to mimic Redfish Session
expiration, since we feel the added overhead and code complexity is not worth
the minimal benefit this detail would provide. Auth tokens are ephemeral in
nature, and it is up to the user to recognize this and account for the case of
unexpected expiration, whether we implement this detail or not.

The authentication process for users of HTTP Basic Auth will be simple, as
this strategy is standards-based (see [RFC7617]_). The user will provide
base64-encoded credentials with every request to a Redfish endpoint that
expects a user to be authorized. Since Ironic supports basic authentication,
implementing this will simply be a matter of passing the user's credentials
through the pre-existing basic auth middleware. Additionally, if basic auth is
in use, the SessionService will be disabled and unusable.

Identity
~~~~~~~~

Since application credentials are scoped upon creation, obtaining the pieces
of information that constitute a user's identity should be a straightforward
process using the existing Ironic policy code and the Keystone middleware. We
will use this information to determine what data, actions, etc. the user has
access to via the same rules and methods as the existing Ironic API.

It is important to note that with basic auth, such policy-based access
restrictions are essentially non-existent. If a user can log in, they will
have access to all available data. However, since our basic auth strategy *is*
Ironic's basic auth, any extension to Ironic's basic auth capability would in
turn be an extension to the capability of this feature.

Provisioning Tools
~~~~~~~~~~~~~~~~~~

The node provisioning tools that will be implemented here shall be
functionally identical to existing Bare Metal endpoints, as shown here. The
internal logic for achieving this functionality shall mirror that of the
actual Ironic API as closely as possible; in theory the only difference should
be in how requests by the user and responses to the user are formatted.

+--------------------------------------------------+-------------------------+
| Emulated Redfish URI                             | Equivalent Ironic URI   |
+==================================================+=========================+
| [GET]  /redfish/v1/SystemService/Systems         | [GET] /v1/nodes         |
+--------------------------------------------------+-------------------------+
| [GET]  /redfish/v1/SystemService/Systems/{uuid}  | [GET] /v1/nodes/{uuid}  |
+--------------------------------------------------+-------------------------+
| [POST] /redfish/v1/SystemService/Systems/{uuid}\ | [PUT] /v1/nodes/{uuid}\ |
|        /Actions/ComputerSystem.Reset             |       /states/power     |
+--------------------------------------------------+-------------------------+

This intermediary will abide by version 1.0.0 of the Redfish spec [RFSHSPEC]_
and schema [RFSHSCHM]_ for maximum backwards compatibility with existing tools.
More details regarding the planned functionality of these endpoints will be
elaborated upon below in the `REST API Impact`_ section.

Alternatives
------------

The type of BMC interface emulation we're looking to implement here does
already exist in sushy-tools [SUSHY]_ and VirtualBMC [VIRTBMC]_, which emulate
Redfish and IPMI respectively. A previous spec was submitted by Tzu-Mainn Chen
(tzumainn) which proposed the idea of a sushy-tools driver in Ironic to enable
this functionality, but concerns about security, along with the potential value
of this existing in Ironic proper have led to the proposal of this spec.
[PREVSPEC]_

We currently plan on implementing this as a separate WSGI service within the
Ironic repository, however it is possible to have both the Ironic API and this
Redfish proxy run under the same service. Since both are separate, independent
WSGI apps, a WSGI dispatcher, such as the Werkzeug application dispatcher
middleware [WSGIDISP]_ could be used to achieve this.

Data model impact
-----------------
None.

State Machine Impact
--------------------
None.

REST API impact
---------------

No changes will be made to the Ironic API proper, rather, a new WSGI service
hosting a new API will be created as described below. End-users shall be able
to interact with this API as if it were a v1.0.0 Redfish endpoint (see
[RFSHSPEC]_ and [RFSHSCHM]_).

Since this is a new service, Ironic operators will need to account for the
fact that it will need its own port and (if using Keystone) will need to be
added as a new endpoint within Keystone. If this proves to be a significant
enough inconvenience, however, it could be possible to launch both the Ironic
API and this proxy within one service as described above under `Alternatives`_.

Redfish API Versions:
~~~~~~~~~~~~~~~~~~~~~

* GET /redfish

  * Returns the Redfish protocol version (v1). This will always return the same
    response shown below, as per the Redfish API spec. (section 6.2 of
    [RFSHSPEC]_)
  * Normal response code: 200 OK
  * Example response::

      {
          "v1": "/redfish/v1/"
      }

    +------+--------+----------------------------------------+
    | Name | Type   | Description                            |
    +======+========+========================================+
    | v1   | string | The URL of the Redfish v1 ServiceRoot. |
    +------+--------+----------------------------------------+

* GET /redfish/v1/

  * The Redfish service root URL, will return a Redfish ServiceRoot object
    containing information about what is available on the Redfish system.
  * Normal response code: 200 OK
  * Example response::

      {
          "@odata.type": "#ServiceRoot.v1_0_0.ServiceRoot",
          "Id": "IronicProxy",
          "Name": "Ironic Redfish Proxy",
          "RedfishVersion": "1.0.0",
          "Links": {
              "Sessions": {
                  "@odata.id": "/redfish/v1/SessionService/Sessions"
              }
          },
          "Systems": {
              "@odata.id": "/redfish/v1/Systems"
          },
          "SessionService": {
              "@odata.id": "/redfish/v1/SessionService"
          },
          "@odata.id": "/redfish/v1/"
      }

    +------------------+--------+---------------------------------------------+
    | Name             | Type   | Description                                 |
    +==================+========+=============================================+
    | @odata.type      | string | The type of the emulated Redfish resource.  |
    +------------------+--------+---------------------------------------------+
    | @odata.id        | string | A resource link.                            |
    +------------------+--------+---------------------------------------------+
    | Id               | string | The identifier for this specific resource.  |
    +------------------+--------+---------------------------------------------+
    | Name             | string | The name of this specific ServiceRoot.      |
    +------------------+--------+---------------------------------------------+
    | Links            | object | Contains objects that contain links to      |
    |                  |        | relevant resource collections.              |
    +------------------+--------+---------------------------------------------+
    | Systems          | object | Contains a link to a collection of Systems  |
    |                  |        | resources.                                  |
    +------------------+--------+---------------------------------------------+
    | SessionService   | object | Contains a link to the SessionsService      |
    |                  |        | resource.                                   |
    +------------------+--------+---------------------------------------------+
    | Sessions         | object | Contains a link to a collection of Sessions |
    |                  |        | resources.                                  |
    +------------------+--------+---------------------------------------------+
    | RedfishVersion   | string | The version of this Redfish service.        |
    +------------------+--------+---------------------------------------------+

Sessions
~~~~~~~~

* GET /redfish/v1/SessionService

  * Returns a Redfish SessionService object, containing information about how
    the SessionService and Session objects are configured.

    * If the underlying Ironic system is using HTTP basic auth, the
      SessionService will report itself to be disabled, and all Session-
      related functionality will be non-functional.

  * Normal response code: 200 OK
  * Error response codes: 404 Not Found, 500 Internal Server Error

    * 404 Not Found will be returned if the underlying Ironic system is not
      using Keystone authentication.
    * 500 Internal Server Error will be returned if the internal request to
      authenticate could not be fulfilled.

  * Example response::

      {
          "@odata.type": "#SessionService.v1_0_0.SessionService",
          "Id": "KeystoneAuthProxy",
          "Name": "Redfish Proxy for Keystone Authentication",
          "Status": {
              "State": "Enabled",
              "Health": "OK"
          },
          "ServiceEnabled": true,
          "SessionTimeout": 86400,
          "Sessions": {
              "@odata.id": "/redfish/v1/SessionService/Sessions"
          },
          "@odata.id": "/redfish/v1/SessionService"
      }

    +----------------+--------+----------------------------------------------+
    | Name           | Type   | Description                                  |
    +================+========+==============================================+
    | @odata.type    | string | The type of the emulated Redfish resource.   |
    +----------------+--------+----------------------------------------------+
    | @odata.id      | string | A resource link.                             |
    +----------------+--------+----------------------------------------------+
    | Id             | string | The identifier for this specific resource.   |
    +----------------+--------+----------------------------------------------+
    | Name           | string | The name of this specific resource.          |
    +----------------+--------+----------------------------------------------+
    | Status         | object | An object containing service status info.    |
    +----------------+--------+----------------------------------------------+
    | State          | string | The state of the service, one of either      |
    |                |        | "Enabled" or "Disabled".                     |
    +----------------+--------+----------------------------------------------+
    | Health         | string | The health of the service, typically "OK".   |
    |                |        | [#]_                                         |
    +----------------+--------+----------------------------------------------+
    | ServiceEnabled | bool   | Indicates whether the SessionService is      |
    |                |        | enabled or not.                              |
    +----------------+--------+----------------------------------------------+
    | SessionTimeout | number | The amount of time, in seconds, before a     |
    |                |        | session expires due to inactivity. [#]_      |
    +----------------+--------+----------------------------------------------+
    | Sessions       | object | Contains a link to a collection of Session   |
    |                |        | resources.                                   |
    +----------------+--------+----------------------------------------------+

* GET /redfish/v1/SessionService/Sessions

  * Returns a Redfish SessionCollection, containing a link to the Session
    being used to authenticate the request. Requires the user to provide valid
    authentication in the request header.
  * Normal response code: 200 OK
  * Error response codes: 401 Unauthorized, 404 Not Found, 500 Internal Server
    Error

    * 401 Unauthorized will be returned if authentication in the header field
      is either absent or invalid.
    * 404 Not Found will be returned if the underlying Ironic system is not
      using Keystone authentication.
    * 500 Internal Server Error will be returned if the internal request to
      authenticate could not be fulfilled.

  * Example response::

      {
          "@odata.type": "#SessionCollection.SessionCollection",
          "Name": "Ironic Proxy Session Collection",
          "Members@odata.count": 1,
          "Members": [
              {
                  "@odata.id": "/redfish/v1/SessionService/Sessions/ABC"
              }
          ],
          "@odata.id": "/redfish/v1/SessionService/Sessions"
      }

    +---------------------+--------+------------------------------------------+
    | Name                | Type   | Description                              |
    +=====================+========+==========================================+
    | @odata.type         | string | The type of the emulated Redfish         |
    |                     |        | resource.                                |
    +---------------------+--------+------------------------------------------+
    | @odata.id           | string | A resource link.                         |
    +---------------------+--------+------------------------------------------+
    | Name                | string | The name of this specific resource.      |
    +---------------------+--------+------------------------------------------+
    | Members@odata.count | number | The number of Session interfaces present |
    |                     |        | in the collection.                       |
    +---------------------+--------+------------------------------------------+
    | Members             | array  | An array of objects that contain links   |
    |                     |        | to individual Session interfaces.        |
    +---------------------+--------+------------------------------------------+

* POST /redfish/v1/SessionService/Sessions

  * Requests Session authentication. A username and password is to be passed in
    the body, and upon success, the created Session object will be returned.
    Included in the headers of this response will be the authentication token
    in the ``X-Auth-Token`` header, and the link to the Session object in the
    ``Location`` header.
  * Normal response code: 201 Created
  * Error response codes: 400 Bad Request, 401 Unauthorized, 404 Not Found, 500
    Internal Server Error

    * 400 Bad Request will be returned if the username/password fields are not
      present in the message body.
    * 401 Unauthorized will be returned if the credentials provided are
      invalid.
    * 404 Not Found will be returned if the underlying Ironic system is not
      using Keystone authentication.
    * 500 Internal Server Error will be returned if the internal request to
      authenticate could not be fulfilled.

  * Example Request::

      {
          "UserName": "85775665-c110-4b85-8989-e6162170b3ec",
          "Password": "its-a-secret-shhhhh"
      }

    +----------+--------+----------------------------------------------------+
    | Name     | Type   | Description                                        |
    +==========+========+====================================================+
    | UserName | string | The UUID of the Keystone application credential to |
    |          |        | be used for authentication.                        |
    +----------+--------+----------------------------------------------------+
    | Password | string | The secret of said application credential.         |
    +----------+--------+----------------------------------------------------+

  * Example Response::

      Location: /redfish/v1/SessionService/Sessions/identifier
      X-Auth-Token: super-duper-secret-aaaaaaaaaaaa

      {
          "@odata.id": "/redfish/v1/SessionService/Sessions/identifier",
          "@odata.type": "#Session.1.0.0.Session",
          "Id": "identifier",
          "Name": "user session",
          "UserName": "85775665-c110-4b85-8989-e6162170b3ec"
      }

    +-------------+--------+--------------------------------------------+
    | Name        | Type   | Description                                |
    +=============+========+============================================+
    | @odata.type | string | The type of the emulated Redfish resource. |
    +-------------+--------+--------------------------------------------+
    | @odata.id   | string | A resource link.                           |
    +-------------+--------+--------------------------------------------+
    | Id          | string | The identifier for this specific resource. |
    +-------------+--------+--------------------------------------------+
    | Name        | string | The name of this specific resource.        |
    +-------------+--------+--------------------------------------------+
    | UserName    | string | The UUID of the application credential     |
    |             |        | used for authentication.                   |
    +-------------+--------+--------------------------------------------+

* GET /redfish/v1/SessionService/Sessions/{identifier}

  * Returns the Session with the identifier specified in the URL. Requires the
    user to provide valid authentication in the request header for the session
    they're attempting to access.
  * Normal response code: 200 OK
  * Error response codes: 401 Unauthorized, 403 Forbidden, 404 Not Found, 500
    Internal Server Error

    * 401 Unauthorized will be returned if authentication in the header field
      is either absent or invalid.
    * 403 Forbidden will be returned if authentication in the header field is
      valid but lacking proper authorization for the Session being accessed.
    * 404 Not Found will be returned if the identifier specified does not
      correspond to a legitimate Session ID or if the underlying Ironic system
      is not using Keystone authentication.
    * 500 Internal Server Error will be returned if the internal request to
      authenticate could not be fulfilled.

  * Example Response::

      {
          "@odata.id": "/redfish/v1/SessionService/Sessions/identifier",
          "@odata.type": "#Session.1.0.0.Session",
          "Id": "identifier",
          "Name": "user session",
          "UserName": "85775665-c110-4b85-8989-e6162170b3ec"
      }

    +-------------+--------+--------------------------------------------+
    | Name        | Type   | Description                                |
    +=============+========+============================================+
    | @odata.type | string | The type of the emulated Redfish resource. |
    +-------------+--------+--------------------------------------------+
    | @odata.id   | string | A resource link.                           |
    +-------------+--------+--------------------------------------------+
    | Id          | string | The identifier for this specific resource. |
    +-------------+--------+--------------------------------------------+
    | Name        | string | The name of this specific resource.        |
    +-------------+--------+--------------------------------------------+
    | UserName    | string | The application credential used for        |
    |             |        | authentication                             |
    +-------------+--------+--------------------------------------------+

* DELETE /redfish/v1/SessionService/Sessions/{identifier}

  * Ends the session identified in the URL. Requires the user to provide valid
    authentication in the request header for the session they're trying to end.
  * Normal response code: 204 No Content
  * Error response codes: 401 Unauthorized, 403 Forbidden, 404 Not Found, 500
    Internal Server Error

    * 401 Unauthorized will be returned if authentication in the header field
      is either absent or invalid.
    * 403 Forbidden will be returned if authentication in the header field is
      valid but lacking proper authorization for the Session being accessed.
    * 404 Not Found will be returned if the identifier specified does not
      correspond to a legitimate Session ID or if the underlying Ironic system
      is not using Keystone authentication.
    * 500 Internal Server Error will be returned if the internal request to
      authenticate could not be fulfilled.

Node Management
~~~~~~~~~~~~~~~

* GET /redfish/v1/Systems

  * Equivalent to ``baremetal node list``, will return a collection of Redfish
    ComputerSystem interfaces that correspond to Ironic nodes. Requires the
    user to provide valid authentication in the request header for the
    resource they are trying to access.
  * Normal response code: 200 OK
  * Error response codes: 401 Unauthorized, 403 Forbidden, 500 Internal Server
    Error

    * 401 Unauthorized will be returned if the authentication in the header
      field is either absent or invalid.
    * 403 Forbidden will be returned if authentication in the header field is
      valid but lacking proper privileges for listing Bare Metal nodes.
    * 500 Internal Server Error will be returned if the internal request to the
      Bare Metal service could not be fulfilled.

  * Example Response::

      {
          "@odata.type": "#ComputerSystemCollection.ComputerSystemCollection",
          "Name": "Ironic Node Collection",
          "Members@odata.count": 2,
          "Members": [
              {
                  "@odata.id": "/redfish/v1/Systems/ABCDEFG"
              },
              {
                  "@odata.id": "/redfish/v1/Systems/HIJKLMNOP"
              }
          ],
          "@odata.id": "/redfish/v1/Systems"
      }

    +---------------------+--------+------------------------------------------+
    | Name                | Type   | Description                              |
    +=====================+========+==========================================+
    | @odata.type         | string | The type of the emulated Redfish         |
    |                     |        | resource.                                |
    +---------------------+--------+------------------------------------------+
    | @odata.id           | string | A resource link.                         |
    +---------------------+--------+------------------------------------------+
    | Name                | string | The name of this specific resource.      |
    +---------------------+--------+------------------------------------------+
    | Members@odata.count | number | The number of System interfaces present  |
    |                     |        | in the collection.                       |
    +---------------------+--------+------------------------------------------+
    | Members             | array  | An array of objects that contain links   |
    |                     |        | to individual System interfaces.         |
    +---------------------+--------+------------------------------------------+

* GET /redfish/v1/Systems/{node_ident}

  * Equivalent to ``baremetal node show``, albeit with fewer details. Will
    return a Redfish System resource containing basic info, power info, and the
    location of the power control interface. Requires the user to provide valid
    authentication for the resource they are trying to access.
  * Normal response code: 200 OK
  * Error response codes: 401 Unauthorized, 403 Forbidden, 404 Not Found, 500
    Internal Server Error

    * 401 Unauthorized will be returned if the authentication in the header
      field is either absent or invalid.
    * 403 Forbidden will be returned if authentication in the header field is
      valid but lacking proper privileges for the Bare Metal node being
      accessed.
    * 404 Not Found will be returned if the identifier specified does not
      correspond to a legitimate node UUID.
    * 500 Internal Server Error will be returned if the internal request to the
      Bare Metal service could not be fulfilled.

  * Example Response::

      {
          "@odata.type": "#ComputerSystem.v1.0.0.ComputerSystem",
          "Id": "ABCDEFG",
          "Name": "Baremetal Host ABC",
          "Description": "It's a computer",
          "UUID": "ABCDEFG",
          "PowerState": "On",
          "Actions": {
              "#ComputerSystem.Reset": {
                  "target": "/redfish/v1/Systems/ABCDEFG/Actions/ComputerSystem.Reset",
                  "ResetType@Redfish.AllowableValues": [
                      "On",
                      "ForceOn",
                      "ForceOff",
                      "ForceRestart",
                      "GracefulRestart",
                      "GracefulShutdown"
                  ]
              }
          },
          "@odata.id": "/redfish/v1/Systems/ABCDEFG"
      }

    +--------------------+--------+-------------------------------------------+
    | Name               | Type   | Description                               |
    +====================+========+===========================================+
    | @odata.type        | string | The type of the emulated Redfish          |
    |                    |        | resource.                                 |
    +--------------------+--------+-------------------------------------------+
    | @odata.id          | string | A resource link.                          |
    +--------------------+--------+-------------------------------------------+
    | Id                 | string | The identifier for this specific          |
    |                    |        | resource. Equal to the corresponding      |
    |                    |        | Ironic node UUID.                         |
    +--------------------+--------+-------------------------------------------+
    | Name               | string | The name of this specific resource.       |
    |                    |        | Equal to the name of the corresponding    |
    |                    |        | Ironic node if set, otherwise equal to    |
    |                    |        | the node UUID.                            |
    +--------------------+--------+-------------------------------------------+
    | Description        | string | If the Ironic node has a description set, |
    |                    |        | it will be returned here. If not, this    |
    |                    |        | field will not be returned.               |
    +--------------------+--------+-------------------------------------------+
    | UUID               | string | The UUID of this resource.                |
    +--------------------+--------+-------------------------------------------+
    | PowerState         | string | The current state of the node/System in   |
    |                    |        | question, one of either "On", "Off",      |
    |                    |        | "Powering On", or "Powering Off".         |
    +--------------------+--------+-------------------------------------------+
    | Actions            | object | Contains the defined actions that can be  |
    |                    |        | executed on this system.                  |
    +--------------------+--------+-------------------------------------------+
    | #ComputerSystem.   | object | Contains information about the "Reset"    |
    | Reset              |        | action.                                   |
    +--------------------+--------+-------------------------------------------+
    | target             | string | The URI of the Reset action interface.    |
    +--------------------+--------+-------------------------------------------+
    | ResetType@Redfish. | array  | An array of strings containing all the    |
    | AllowableValues    |        | valid options this action provides.       |
    +--------------------+--------+-------------------------------------------+

* POST /redfish/v1/Systems/{node_ident}/Actions/ComputerSystem.Reset

  * Invokes a Reset action to change the power state of the node/System. The
    type of Reset action to take should be specified in the request body.
    Requires the user to provide valid authentication in the request header
    for the resource they are attempting to access.
  * Accepts the following values for ResetType in the body [#]_:

    * "On" (soft power on)
    * "ForceOn" (hard power on)
    * "GracefulShutdown" (soft power off)
    * "ForceOff" (hard power off)
    * "GracefulRestart" (soft reboot)
    * "ForceRestart" (hard reboot)

  * Normal response code: 202 Accepted
  * Error response codes: 400 Bad Request, 401 Unauthorized, 403 Forbidden, 404
    Not Found, 409 NodeLocked/ClientError, 500 Internal Server Error, 503
    NoFreeConductorWorkers (for more on codes 409 and 503, see the details for
    PUT requests to ``/v1/nodes/{ident}/states/power`` in [IRONCAPI]_):

    * 400 Bad Request will be returned if the "ResetType" field is not found in
      the message body, or if the field has an invalid value.
    * 401 Unauthorized will be returned if the authentication in the header
      field is either absent or invalid.
    * 403 Forbidden will be returned if authentication in the header field is
      valid but lacking proper privileges to perform the specified action on
      the Bare Metal node being accessed.
    * 404 Not Found will be returned if the identifier specified does not
      correspond to a legitimate node UUID.
    * 409 NodeLocked/ClientError is an error code specified in the Bare Metal
      API call this request is proxied to. The body of a 409 response will be
      the same as that which was received from the Bare Metal API.
    * 500 Internal Server Error will be returned if the internal request to the
      Bare Metal service could not be fulfilled.
    * 503 NoFreeConductorWorkers is an error code specified in the Bare Metal
      API call this request is proxied to. The body of a 503 response will be
      the same as that which was received from the Bare Metal API.

  * Example Request::

      X-Auth-Token: super-duper-secret-aaaaaaaaaaaa

      {
          "ResetType": "ForceOff"
      }

  +-----------+--------+----------------------------------------------+
  | Name      | Type   | Description                                  |
  +===========+========+==============================================+
  | ResetType | string | The type of Reset action to take (see above) |
  +-----------+--------+----------------------------------------------+

Client (CLI) impact
-------------------
None.

"openstack baremetal" CLI
~~~~~~~~~~~~~~~~~~~~~~~~~

Though this addition would include new REST API endpoints, this feature merely
provides another way for users to access already existing features within the
Ironic API, which are already accessible from the ``openstack baremetal`` CLI.

"openstacksdk"
~~~~~~~~~~~~~~
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

The main consideration when it comes to the security of this feature is the
addition of a new means of accessing Ironic hardware. However, this should not
pose much of a new concern when it comes to security, since authentication
shall be implemented in the same way and using the same midddlewares as the
existing Ironic API. Nevertheless, great care will be taken to make sure that
said integration with the existing auth middleware is safe and secure.

To mitigate further risk, generated application credentials can and should be
limited in scope to only allow access to the parts of the Ironic API required
by this intermediary. We will also require all requests to be performed over
HTTPS, since session tokens, application credential secrets, and (base64-
encoded) HTTP basic auth credentials will be sent in plain text.

Other end user impact
---------------------

This will give end users an alternative way of accessing power controls, one
compatible with existing Redfish provisioning tools. This means in theory,
the majority of users won't be making API calls directly, instead utilizing
pre-existing Redfish-compatible software, such as
`Redfishtool <https://github.com/DMTF/Redfishtool>`_.

Scalability impact
------------------
None.

Performance Impact
------------------

Since this shall be implemented as a separate WSGI service, some additional
overhead will be required, although the impact should be minor, as it will
not require the running of any periodic tasks nor the execution of any
extraneous database queries.

Additionally, it should be noted that running this proxy service is completely
optional on the part of the Ironic system operator; if one does not wish to use
it, its existence can simply be ignored.

Other deployer impact
---------------------

This feature should have no impact on those who do not wish to use it, as it
must be ran separately and can be ignored. To prevent it from being started
accidentally, operators shall be able to explicitly disable it in the Ironic
configuration file.

Those who wish to make use of this feature must keep in mind that since it is
currently being implemented as a separate WSGI service, it shall require at
minimum its own port to be ran on. This can be useful if one wishes to have
the Redfish proxy service bound to a different port or a different host IP
from the Ironic API; however, it will require a new endpoint to be added via
Keystone (if using Keystone), and may potentially require extra network
configuration on the part of the system administrator.

Developer impact
----------------

This new service shall be implemented in Flask, as opposed to Pecan, which is
what the Ironic API currently uses. As such, all code written for this new
feature shall be well-documented in order to maximize its readability to any
Ironic devs unfamiliar with Flask.

It has been mentioned by TheJulia that in future, the Ironic dev team may want
to look into migrating the Ironic API to use Flask, and this addition to the
codebase may prove useful to those tasked with said migration.

Finally, the Sessions feature does not exist in sushy-tools; since this spec
includes a planned implementation of it, it could possibly be a useful addition
there. This basic Redfish proxy can also be extended in future to provide
access to even more parts of an Ironic system through a Redfish-like interface
to those who would find such functionality useful.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  | Sam Zuk (sam_z / szuk) <szuk@redhat.com>

Other contributors:
  | Tzu-Mainn Chen (tzumainn) <tzumainn@redhat.com>

Work Items
----------

* Create the necessary API endpoints

  * Implement the Redfish System -> Ironic Node proxy
  * Implement the Redfish Session -> Keystone authentication proxy
  * Write unit tests and functional tests to ensure proper functionality

* Write documentation for how to use and configure this functionality, for
  users, administrators, and developers.
* Test this feature on real hardware in a way that mimics expected use cases.

Dependencies
============

None.

Testing
=======

Functional testing will be required to ensure requests made to these new proxy
endpoints result in the correct behavior when ran on an actual Ironic setup.
Furthermore, rigorous test cases should be written to make extremely sure that
no unauthorized access to node APIs is possible.

Upgrades and Backwards Compatibility
====================================

N/A


Documentation Impact
====================

Documentation will need to be provided for the new API endpoints, along with
the necessary instructions for how to enable and configure this feature (for
operators), along with additional information end users may require, such as
how to work with authentication tokens.

References
==========

.. [NMTSTORY] https://storyboard.openstack.org/#!/story/2006506
.. [NODELEAS] https://opendev.org/openstack/ironic-specs/src/commit/6699db48d78b7a42f90cb5c06ba18a72f94b6667/specs/approved/node-lessee.rst
.. [APPCREDS] https://docs.openstack.org/keystone/latest/user/application_credentials.html
.. [SUSHY]    https://docs.openstack.org/sushy-tools/latest/
.. [VIRTBMC]  https://docs.openstack.org/project-deploy-guide/tripleo-docs/latest/environments/virtualbmc.html
.. [PREVSPEC] https://review.opendev.org/c/openstack/ironic-specs/+/764801/3/specs/approved/power-control-passthrough.rst
.. [RFSHSPEC] https://www.dmtf.org/sites/default/files/standards/documents/DSP0266_1.0.0.pdf
.. [RFSHSCHM] https://www.dmtf.org/sites/default/files/standards/documents/DSP8010_1.0.0.zip
.. [RFC7617]  https://datatracker.ietf.org/doc/html/rfc7617
.. [IRONCAPI] https://docs.openstack.org/api-ref/baremetal
.. [KSTNEAPI] https://docs.openstack.org/api-ref/identity/v3/index.html
.. [WSGIDISP] https://werkzeug.palletsprojects.com/en/2.0.x/middleware/dispatcher/

.. [#] This is included for compatibility and should always be "OK", although
       the Redfish schema allows for "Warning" and "Critical" as well.
.. [#] This is a placeholder value. Since sessions are just Keystone auth
       tokens, they will behave as any other Keystone token, as opposed to
       behaving like a Redfish Session. (see _`Authentication`)
.. [#] The Redfish schema for ResetType also includes "Nmi" (diagnostic
       interrupt) and "PushPowerButton" (simulates a physical power button
       press event). However, neither of these actions are part of Ironic's
       node power state workflow and support for these actions varies greatly
       depending on the driver and hardware.
