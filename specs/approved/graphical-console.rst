..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=========================
Graphical Console Support
=========================

https://bugs.launchpad.net/ironic/+bug/2086715


Hardware vendors are adding support for remote graphical consoles via
non-standardised Redfish interfaces. End users would like to have a consistent
way of accessing these consoles via Ironic using command-line, the Nova
driver, or the Horizon web interface.

Problem description
===================

Nova has for a long time provided VNC graphical console support via a NoVNC
proxy for virtual machines. Ironic end users would like to access bare metal
graphical consoles in the same way. There is currently no Redfish standardised
method for managing bare metal consoles and each vendor exposes different
methods and capabilities:

* Dell iDRAC: VNC fully manageable via oem Attributes supported by
  sushy-oem-idrac, including changing password.
  Also provides a BMC web interface which displays an html5 based console.
* HPE iLO: Requires html5/java/.net/windows client, not VNC related.
  No password management.
  Also provides a BMC web interface which displays an html5 based console.
* Supermicro: Invocable via IPMI, VNC base but with a custom colorspace and
  other additional opcodes so incompatible with standard VNC clients. Requires
  html5/java or a fork of NoVNC[1]. KVMIP port 5900 is listed in
  ``redfish/v1/Managers/1/NetworkProtocol`` but it is otherwise not manageable
  via Redfish.
  Also provides a BMC web interface which displays an html5 based console.

There is also a requirement from infrastructure operators for an optional
read-only view of graphical consoles.

Proposed change
===============

NoVNC proxy
-----------

Nova has a separate novnc-proxy service which serves the NoVNC web assets and
also opens a websocket to the browser which is proxied to the VNC server TCP
connection. This allows a VNC session to be displayed in a web browser without
a direct network connection to the VNC server. This code is fairly self
contained so it is practical to forklift directly out of nova into the ironic
codebase, only requiring these changes:

* replacing the token lookup with a simple node lookup and token verification
* adapting the process launch to use ``ironic.common.service``. This increases
  the likelihood that the novnc-proxy service can be integrated into the
  all-in-one ``singleprocess`` launcher.
* consolidating the ``nova.conf`` options from three groups to a single
  ``ironic.conf`` ``[vnc]`` group.

For some drivers, novnc-proxy will be connecting directly to a VNC server
exposed by the BMC. This means that it needs to run both with access to the
BMC network, and with the ability to expose an HTTP service to the end user.

For other drivers there will need to be an intermediate VNC server running in
a container for each connection. Either the driver or novnc-proxy will need to
initiate (but not directly manage) these containers.


Read-only support
-----------------

An ``ironic.conf`` ``[vnc]`` option will default connections to be read-only.
Operators can change this default informed by what non-console operations a
browser based console might expose.

Container based driver proposal
-------------------------------

The only common implementation of all vendors is a browser based BMC
interface which includes an html5 based console.

The approach suggested is to start a container for each graphical console
session which runs the following stack:

* A headless X11 session provided by Xvfb
* A VNC server displaying the session, such as x11vnc
* A chromium browser in app mode (full screen, one site)
* An entrypoint script which runs a (python) Selenium script to log into the
  BMC and load the html5 based console.

A template driven approach can be taken where a file is written out for each
active console which provides enough information for an external tool to start
and stop containers as appropriate. The driver can be responsible for writing
out files based on these templates and waiting for another file to be written
which contains the VNC endpoint address and port. novnc-proxy can then connect
to this VNC server and start proxying traffic.

An optional service will be written which will be started by devstack which
will manage the lifecycle of these VNC containers via podman. This service may
be appropriate for some deployment architectures but not all. For example,
Ironic managed by kubernetes would need something like an operator to monitor
for changes to these files and manage the VNC pods. This file based interface
will be documented with the intention of supporting other container management
implementations.

If a vendor has a Redfish API to provide a browser based console as its KVMIP
function, then that can be used to generate the URL which is loaded in the
browser container. This may be possible for Dell[3] and Supermicro[4]. In
other cases, a full Selenium script is required which enters BMC credentials
into a login form and navigates to the console.

The initial priority for having working drivers for vendors will be:

HPE iLO
~~~~~~~

The ``/irc.html`` page is loaded to show the console. In iLO 6 an inline login
form is displayed. In iLO 5 an "Invalid session key" message is shown. The
Selenium script can handle this difference and take the fast login for iLO 6
and load the main login page for iLO 5.

Dell iDRAC
~~~~~~~~~~

The ``/console`` page is loaded which shows the login page. Logging in loads
the virtual console configuration page which immediately triggers a pop-up
which shows the actual console. In Chromium app mode pop-ups appear on top
so this can be scripted with Selenium.

It is possible that doing a POST to [3] provides use-once credentials to build
a URL to load the pop-up URL directly, more research is required.

Supermicro
~~~~~~~~~~

A Redfish GET call to ``/redfish/v1/Managers/1/Oem/Supermicro/IKVM`` [4] will
return a temporary URL directly to an html5 console, which can be used as the
initial browser loading page.

Session management
------------------

ironic-novncproxy session management
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Nova implements a simple bearer token for each graphical console session with
a configured expiry. It has a dedicated token database table and the token is
part of the NoVNC URL query string which is passed through to the websocket.
The instance is discovered by looking up the token entry which has an
associated instance.

This approach is not suggested for Ironic as the aim is to avoid data model
changes. NoVNC passes all query parameters through to the URL of the
websocket, so it will be possible to include a query parameter for the node
UUID, and another for the token. The token and expiry are set in the node
``driver_internal_info`` by the driver with the help of novnc session utility
functions. When a session is started, other utility functions verify the
token. Nova also has an option to terminate existing sessions when the token
expires. This could be implemented in the future if there is a demonstrated
need.

Browser console session management
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

BMC web interfaces have their own session timeouts and there is potential for
these to interact poorly with Ironic's console session management. Ideally the
running container will be aware of new VNC connections and defer browser login
until a connection is made, then log out when the last connection is
terminated. However the initial implementation may need to be much simpler,
requiring that the user access the console soon after it is enabled.

Alternatives
------------

Instead of having an intermediate browser container for all drivers, some
could connect novncproxy to BMC VNC endpoints directly, specifically:

* iDRAC fully exposes a VNC endpoint that can be managed via OEM extension
* Supermicro exposes a non-compliant VNC endpoint which could be supported by
  NoVNC if this stale PR[5] is supported to be merged.

This is not the suggested approach as it makes read-only support harder, and
it also complicates network connectivity from nova-novncproxy to BMC VNC
endpoints.

Overall approach
~~~~~~~~~~~~~~~~

Previously a dedicated API and model was proposed, which was close to Nova's
implementation. But it was decided during the PTG[2] that this was overkill
and the existing serial console driver and API interfaces were sufficient to
provide this functionality.

Data model impact
-----------------

None. All state is stored in the node's ``driver_internal_info``. NoVNC token
information will be stored consistently across all graphical console drivers.
Also each driver will store it's own state as required for the vendor specific
implementations.

State Machine Impact
--------------------

None

REST API impact
---------------

None, the existing console API is used.

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

None

Nova driver impact
------------------

Implementing the ``ComputeDriver.get_vnc_console`` method in the Ironic driver
should be sufficient for available graphical consoles to be used as for any
other nova driver. This requires that the Ironic driver provide an actual VNC
host and port rather than a NoVNC URL. The Ironic driver can read the
``driver_internal_info`` directly to fetch ``vnc_host`` and ``vnc_port``
values. These will become part of an internal API contract.

Ramdisk impact
--------------

None

Security impact
---------------

This opens a new way to get privileged access to the running bare metal,
so consideration is required at all levels including:

* The RFP protocol authentication forklifted from Nova
* The bearer token implementation for starting a graphical console session
* The isolation of the headless VNC containers
* The implementation of any read-only mode
* The management of credentials to access the bare metal VNC/KVMIP
* Limiting access to any non console functionality exposed by a browser
  based console

Other end user impact
---------------------

Horizon will show a graphical console when the bare metal is managed via Nova,
but it would also be desirable to modify the ironic-ui to show the graphical
console in Horizon for Ironic managed nodes.

Scalability impact
------------------

The novncproxy service can be scaled as a stateless service like ironic-api,
and its resource usage will be minimal. Each console session requires a
container running an embedded browser. Each container will consume
approximately the following on the host which is running it:

* ~300MB of memory
* 1 TCP port
* some processing overhead

Performance Impact
------------------

None

Other deployer impact
---------------------

Deployment tooling will need to manage the novnc-proxy service and
the tool which manages headless VNC containers.

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Steve Baker <sbaker@redhat.com>

Other contributors:
  Volunteers welcome!

Work Items
----------
* Forklift novnc-proxy from Nova to Ironic and adapt to proposed model
* Write iDRAC driver and supporting utility functions
* Start novnc-proxy in devstack
* Write template based driver class for iLO driver
* Write a iLO driver and associated headless VNC server container
* Write a devstack-appropriate service to manage headless VNC containers
* Pick up the upstream NoVNC contribution to enable the Supermicro variant
* Modify the ironic driver in Nova to enable the graphical console
* Modify ironic-ui to show the graphical console, as for nova instances

Dependencies
============

None

Testing
=======

Full unit test coverage. Functional coverage with a fake driver.

Automated integration testing of vendor specific drivers will be interesting
challenge, it may be necessary to start with manual testing only.

Upgrades and Backwards Compatibility
====================================

No backward compatibility issues. Upgrade tooling will need to manage the
new novnc-proxy service and whatever tool is used to manage headless VNC
containers.

Documentation Impact
====================

The following will need to be documented:

* configuration options for enabling and configuring novnc-proxy
* infrastructure instructions for starting novnc-proxy
* instructions for configuring drivers which require a headless VNC container
  management component
* requirements for enabling specific drivers for a node

References
==========

[1] https://github.com/kelleyk/noVNC
[2] https://etherpad.opendev.org/p/ironic-ptg-october-2024#L252
[3] https://developer.dell.com/apis/2978/versions/7.xx/openapi.yaml/paths/~1redfish~1v1~1Managers~1%7BManagerId%7D~1Oem~1Dell~1DelliDRACCardService~1Actions~1DelliDRACCardService.GetKVMSession/post
[4] https://www.supermicro.com/manuals/other/redfish-user-guide-4-0/Content/general-content/bmc-configuration-examples.htm#ikvm
[5] https://github.com/novnc/noVNC/pull/614
