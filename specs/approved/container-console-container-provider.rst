..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

====================================
Container console container provider
====================================

https://bugs.launchpad.net/ironic/+bug/2154494

Ironic's graphical console support runs one container per active console
session, managed through a pluggable console container provider. The
existing ``systemd`` and ``kubernetes`` providers are unusable when
``ironic-conductor`` itself runs in a Docker or Podman container. This
spec adds a ``container`` provider which manages console containers directly
through a Docker compatible container engine.

Problem description
===================

The graphical console framework added by the `Graphical Console Support`_
spec starts a console container for each node with an enabled graphical
console. The container runs a headless X11 session, a browser logged into
the BMC's HTML5 console, and a VNC server which ``ironic-novncproxy``
proxies to the end user. The conductor delegates container lifecycle to a
provider selected by ``[vnc]container_provider`` and loaded from the
``ironic.console.container`` entry point. A provider subclasses
``ironic.console.container.base.BaseConsoleContainer`` and implements:

* ``start_container(task, app_name, app_info)``: start a container for the
  node, blocking until a consumable VNC endpoint exists, and return a
  ``(host, port)`` tuple.
* ``stop_container(task)``: stop any container running for the node.
* ``stop_all_containers()``: stop every container managed by this
  conductor; called on conductor startup and graceful shutdown.

Two real providers exist in-tree:

* ``systemd`` writes podman Quadlet ``.container`` units to
  ``/etc/containers/systemd/users/{uid}/containers/systemd`` and drives
  them with ``systemctl --user``. This requires a host systemd instance, a
  logind user session, a user D-Bus bus and write access to host
  configuration directories. None of these are normally available inside
  a conductor container, and bind-mounting enough of the host to make
  them available adds considerable complexity and fragility.
* ``kubernetes`` creates pods with ``kubectl`` and assumes the conductor,
  ``ironic-novncproxy`` and the console pods run in the same Kubernetes
  cluster (it returns the pod IP, which is normally only routable
  in-cluster).

Deployments which run the Ironic services themselves in Docker or Podman
containers use neither host-level systemd unit management nor Kubernetes,
so neither provider is usable for them. The installation documentation
currently tells such deployments to write a custom out-of-tree provider.
Yet the container engine already running the conductor is the natural
place to run console containers, and driving it directly is a small,
generic provider that belongs in-tree rather than something each
deployment maintains itself.

The actor for this feature is the Deployer. End users see no change: the
console API, drivers and the noVNC user experience are untouched.

Proposed change
===============

Add a ``container`` console container provider,
``ironic.console.container.container:ContainerConsoleContainer``, registered
under the ``ironic.console.container`` entry point. The provider talks to
a Docker compatible engine by invoking the Docker CLI through
``ironic.common.utils.execute`` with an argument vector (no shell). This
matches the in-tree precedent of the ``systemd`` provider (``systemctl``,
``podman``) and the ``kubernetes`` provider (``kubectl``), and introduces
no new Python dependencies.

::

  +----------------------------------------------------------------+
  | host                                                           |
  |                                                                |
  |  +---------------------+       +----------------------------+  |
  |  | ironic-conductor    |       | Docker / Podman engine     |  |
  |  | container           | API   |                            |  |
  |  |                     | socket| +------------------------+ |  |
  |  | container provider -+-------->| ironic-console-<uuid>  | |  |
  |  +---------------------+       | | APP, APP_INFO,         | |  |
  |                                | | READ_ONLY env          | |  |
  |  +---------------------+       | | VNC 5900 -> host port  | |  |
  |  | ironic-novncproxy   |       | +-----------+------------+ |  |
  |  | container           |       +-------------|--------------+  |
  |  +----------+----------+                     |                 |
  +-------------|--------------------------------|-----------------+
                | VNC over TCP                   |
                +--------------------------------+

The console container additionally connects out to the BMC web interface
over the management network, exactly as with the existing providers.

The container image, the ``APP``/``APP_INFO``/``READ_ONLY`` environment
contract and the in-container VNC port 5900 are unchanged: the provider
runs the same image referenced by ``[vnc]console_image`` that the
``systemd`` and ``kubernetes`` providers run.

Provider behaviour
------------------

On load (``__init__``) the provider runs ``docker version`` to verify both
the CLI and engine connectivity, requires ``[vnc]console_image`` to be
set, and pre-renders ``[vnc]container_command_template`` once to catch
template errors, raising ``ConsoleContainerError`` otherwise. This mirrors
the CLI probing done by both existing providers and the ``console_image``
check and template validation done by the ``kubernetes`` provider, and
fails fast at conductor startup.

``start_container(task, app_name, app_info)``:

#. Remove any stale container for the node (``docker rm --force``, a
   missing container is tolerated), so a retried start cannot collide with
   a leftover name.
#. Render ``[vnc]container_command_template`` and run the container. The
   rendered text is split into an argument vector with ``shlex`` (``#``
   starts a comment), the provider prepends ``[vnc]container_executable``,
   and the whole is run through ``utils.execute`` with no shell. The
   default template renders::

     # Arguments for [vnc]container_executable. Rendered with Jinja2,
     # then split with shlex; '#' starts a comment.
     run --detach --rm
     --name ironic-console-{{ uuid }}
     --label org.openstack.ironic.console=true
     --label org.openstack.ironic.conductor={{ conductor }}
     --label org.openstack.ironic.node={{ uuid }}
     --publish {{ publish_port }}
     --pull missing
     --env APP={{ app }}
     --env APP_INFO
     --env READ_ONLY={{ read_only }}
     {{ image }}

   ``APP_INFO`` contains BMC addresses and credentials, so the default
   template passes it value-less: the provider supplies the value
   (``json.dumps(app_info)``) through the CLI's process environment via
   ``utils.execute``. The credentials therefore never appear on a command
   line (world-readable ``/proc/<pid>/cmdline``) or in debug-logged
   commands. Template variables are ``uuid``, ``image``
   (``[vnc]console_image``), ``app``, ``read_only``, ``conductor``
   (``CONF.host``), ``publish_port`` (``[vnc]container_publish_port``) and
   ``my_ip`` (``CONF.my_ip``). A custom template must preserve the
   load-bearing parts of the default template, listed under
   `Configuration`_. With the default
   template's ``--pull missing`` (or ``always``) this step may include an
   image pull, which is not bounded by ``[vnc]wait_for_ready_timeout``;
   see `Performance Impact`_.
#. Discover the published endpoint with
   ``docker port ironic-console-<node uuid> 5900/tcp`` and parse the
   ``host:port`` output by splitting on the last colon and stripping
   brackets, handling IPv4, bracketed IPv6 (Docker 23.0+) and unbracketed
   IPv6 (older Docker, all Podman releases) forms. If multiple bindings
   are published (e.g. a dual-stack publish specification) the first IPv4
   binding is preferred. If the bind address is unspecified (``0.0.0.0``
   or ``::``), substitute ``CONF.my_ip``, since an unspecified address is
   not consumable by ``ironic-novncproxy`` or Nova.
#. Wait until the endpoint returns 12 bytes of data (the length of an RFB
   ProtocolVersion greeting), bounded by the existing
   ``[vnc]wait_for_ready_timeout`` option with its existing retry-count
   semantics. This check already exists as
   ``SystemdConsoleContainer._wait_for_listen`` and will be moved to
   shared code (see `Shared readiness check`_).
#. On any failure, capture ``docker logs`` output for the container at
   debug level (best-effort: under the default template's ``--rm`` a
   crashed container may already have removed itself), remove the
   container, and raise ``ConsoleContainerError``.
#. Return the ``(host, port)`` tuple.

``stop_container(task)`` captures ``docker logs`` at debug level (as the
``systemd`` provider captures the unit's journal) and then runs
``docker rm --force`` on the node's container name. An already-absent
container is treated as success by the provider itself rather than by
relying on the engine's exit code, which differs between engines (Podman
before 4.2 exits non-zero). Console containers are stateless (X11,
browser, VNC server), so no graceful stop period is needed.

``stop_all_containers()`` lists containers with
``docker ps --all --quiet --filter
label=org.openstack.ironic.conductor=<CONF.host>`` and force-removes
them. Scoping the filter to the conductor's own label mirrors the
``kubernetes`` provider's ``conductor`` label selector, so the bulk
cleanup of one conductor never affects another's containers when an
engine is shared; the removal by name in the start sequence intentionally
reclaims a node's container when the node has moved between conductors.
The ``--all`` flag also collects containers that have exited, which
matters when a custom template omits ``--rm``.

The default template runs containers with ``--rm``, so a container that
exits for any reason removes itself, and exited containers cannot
accumulate writable layers and logs on a long-running conductor host.
The provider captures ``docker logs`` at debug level before each
explicit removal, so diagnostics for provider-initiated stops are
preserved; what ``--rm`` gives up is the post-mortem of a container
that exited on its own. Operators debugging such exits can remove
``--rm`` from the template, in which case exited containers are cleaned
up by the explicit removals above and by ``stop_all_containers()`` at
conductor startup, and can additionally be purged on a TTL with the
engine's own tooling — the engine records each container's creation
time, so no extra timestamp label is needed (e.g. ``docker container
prune --filter until=24h --filter
label=org.openstack.ironic.console=true``).

Image cleanup is deliberately left to the engine. Ironic never removes
images, so every pull of an updated ``console_image`` (for instance a
weekly rebuild with security updates) leaves the superseded image
behind, and over a long conductor uptime these add up to real disk
consumption. Bounding it is an operator task with existing engine
tooling (``docker image prune``). The documentation will include a
disk-usage callout covering image accumulation, the ``--rm`` default and
TTL-scoped pruning above, and log rotation: Docker's default
``json-file`` log driver does not rotate logs, so deployments expecting
long-lived, heavily used consoles should set ``--log-opt max-size`` in
the template or configure log rotation engine-wide — that, not ``--rm``,
is what bounds log growth (including deliberate log flooding from a
console session) while a container is still running.

No ``--restart`` policy is set: an engine or container restart would
republish a new random host port that no longer matches the ``vnc_port``
recorded for the node, so automatic restart cannot restore a working
session. As with the existing providers, a console whose container has
died stays unavailable until the session expires or the console is
disabled and re-enabled, and containers belonging to a conductor that
died without running its shutdown cleanup persist until that conductor
restarts; the ``org.openstack.ironic.console`` label gives operators a
documented way to locate and purge orphans. Teaching the session-expiry
periodic to also end sessions whose container has stopped — reconciling
state in both directions — is tracked for all providers in `bug
2158578`_ and is out of scope here; this provider gives such a check
everything it needs through the deterministic per-node container name
and labels. Per-node serialization of
start and stop is provided by the conductor's exclusive node lock, as for
the existing providers; the provider itself holds no state.

Engine selection and Podman support
-----------------------------------

The provider executes the binary named by ``[vnc]container_executable``
(default ``docker``). When ``[vnc]container_host`` is set, it is exported to
the CLI as both ``DOCKER_HOST`` and ``CONTAINER_HOST`` — the latter is
honoured by the Podman CLI since Podman 4.0, where it also enables remote
mode; the Podman CLI ignores ``DOCKER_HOST``. When unset, the CLI's
default socket resolution applies (typically
``unix:///var/run/docker.sock``). The engine is assumed to run on the
conductor host: the default publish binding and the ``CONF.my_ip``
substitution are only correct for a local engine, so a remote
``container_host`` requires ``container_publish_port`` to bind an address that
is valid and routable on the engine host.

Podman provides a Docker-compatible CLI and a Docker-compatible API
service (``podman system service``), so the same provider is expected to
work against Podman by setting ``container_executable = podman`` (Podman 4.0
or later recommended) or by pointing ``container_host`` at a Podman socket
with the ``docker`` CLI or ``podman-docker`` shim. Per the RFE, initial
development and testing target Docker; Podman support via the
compatibility interface is best-effort initially and will be hardened as
it sees use. No separate ``podman`` provider is proposed; one would only
be added later if real compatibility divergence demands it
(podman-on-host deployments are already served by the ``systemd``
provider).

The provider never invokes ``sudo`` or any other privilege escalation.
Access to the engine is governed entirely by socket permissions, which the
deployment controls — for a containerized conductor, by mounting the
engine socket into its container. A deployment that insists on
sudo-mediated access can point ``container_executable`` at a wrapper script.

Configuration
-------------

New options, all in the existing ``[vnc]`` group, following the
provider-prefix convention of the ``systemd_*`` and ``kubernetes_*``
options:

``container_executable`` (string, default ``docker``)
  Name or absolute path of the Docker-compatible CLI binary. Set to
  ``podman`` to use Podman's Docker-compatible CLI.

``container_host`` (string, default unset)
  Engine endpoint URL, e.g. ``unix:///var/run/docker.sock`` or
  ``tcp://...``. Exported as ``DOCKER_HOST``/``CONTAINER_HOST`` when set;
  otherwise the CLI default applies.

``container_publish_port`` (string, default ``$my_ip::5900``)
  Value for ``docker run --publish``, mapping container VNC port 5900 to
  the host. Identical semantics and default to
  ``systemd_container_publish_port``: bind to ``$my_ip`` and let the
  engine allocate a random high host port. An IPv6 bind address must be
  bracketed (e.g. ``[2001:db8::1]::5900``), so deployments where
  ``my_ip`` is IPv6 must set this option explicitly.

``container_command_template`` (string)
  Path to the Jinja2 template that renders the argument vector for
  ``container_executable`` (shown above); defaults to
  ``$pybasedir/console/container/ironic-console-container.template``.
  Operators edit it for deployment-specific needs — removing ``--rm`` to
  keep crashed containers for inspection, ``--pull`` policy,
  ``--network``, resource limits (``--memory``/``--cpus``), log rotation
  (``--log-opt``) or extra labels. A custom template must keep, as
  rendered by the default: the container ``--name`` and the
  ``org.openstack.ironic.*`` labels (per-node stop, bulk cleanup and the
  documented prune and orphan-location commands find containers by
  them), ``--detach`` (the provider's blocking ``run`` invocation would
  otherwise not return until the container exits), the publish of
  container port 5900 (endpoint discovery depends on it) and the
  value-less ``--env APP_INFO`` entry (the credentials are supplied
  through the CLI's process environment). Startup validation only
  renders the template, so omissions surface at the first console start
  rather than at conductor startup.

The help text of ``[vnc]container_provider`` and ``[vnc]console_image``
will be updated to document the ``container`` provider. The existing
``console_image``, ``read_only`` and ``wait_for_ready_timeout`` options
are reused unchanged.

Shared readiness check
----------------------

``SystemdConsoleContainer._wait_for_listen``, which polls the published
endpoint until it returns 12 bytes of data (the length of an RFB
ProtocolVersion greeting), is generic. It will be moved to
``BaseConsoleContainer`` (or a small shared helper module) with behaviour
unchanged, and reused by both the ``systemd`` and ``container`` providers.
Nothing in the check is engine- or systemd-specific, so the
``kubernetes`` provider could later adopt it in place of (or in addition
to) its pod-status wait; that change is out of scope here, but the
shared placement enables it.

Scope
-----

This spec only adds a provider behind the existing abstraction. The
console drivers, ``ironic-novncproxy``, the REST API, the
``BaseConsoleContainer`` abstract interface and the console container
image are not changed.

Alternatives
------------

* Use the ``docker-py``/``podman-py`` Python SDKs instead of the CLI.
  Rejected: it adds a Python dependency for an optional feature, couples
  Ironic to engine API versioning, and breaks with the in-tree precedent
  of shelling out (``kubectl``, ``systemctl``, ``podman``). The CLI is
  also the interface deployments can most easily constrain and audit.
* Add a dedicated ``podman`` provider now. Rejected for the initial
  implementation: Podman's Docker compatibility makes it redundant, and
  the RFE explicitly suggests supporting Docker first.
* Make the ``systemd`` provider work from inside a container. Rejected:
  it would require exposing the host's systemd, user D-Bus, journal and
  quadlet directories into the conductor container — exactly the
  complexity this RFE seeks to avoid.
* Render a ``docker compose`` file instead of templating the ``docker
  run`` command. Rejected: ``docker compose`` is an extra plugin
  dependency and a templated ``docker run`` invocation needs no
  orchestration file.
* Keep requiring an out-of-tree provider. This works by design today, but
  running the conductor in a container next to a Docker compatible engine
  is common enough to warrant an in-tree, gate-tested provider.

Data model impact
-----------------

None

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

None. The ``BaseConsoleContainer`` abstract interface is unchanged; the
readiness-check refactoring only adds a concrete helper, so out-of-tree
providers continue to load and run unmodified.

Nova driver impact
------------------

None. The provider returns a host and port stored in
``driver_internal_info`` as ``vnc_host``/``vnc_port``, the same contract
the Nova driver already consumes.

Ramdisk impact
--------------

None

Security impact
---------------

* Access to a rootful container engine socket is root-equivalent on the
  host: anyone who can talk to the engine can start privileged containers
  and mount host paths. Mounting such a socket into the
  ``ironic-conductor`` container therefore extends a conductor compromise
  to host root. This is a deliberate deployment trade-off that the
  documentation will state plainly, along with mitigations: use a
  dedicated engine or a rootless Podman socket where possible (a rootless
  socket grants only the owning user's privileges), and consider engine
  authorization plugins. Ironic itself performs no privilege escalation
  and does not use ``sudo``.
* ``app_info`` contains BMC addresses and credentials and is passed to
  the container as the ``APP_INFO`` environment variable, where it is
  visible via ``docker inspect`` and the container's process environment
  to anyone with socket access. This matches the exposure of the
  ``systemd`` provider (environment in a quadlet unit file) and the
  ``kubernetes`` provider (Secret consumed as an environment variable),
  and socket access already implies greater privilege than these
  credentials grant. The value is supplied through the CLI's process
  environment, never on a command line, so it does not leak through
  ``/proc/<pid>/cmdline`` or debug-logged command lines.
* The VNC server in the console container is unauthenticated and
  unencrypted, as with all providers. The default publish specification
  binds to ``$my_ip``; documentation will warn against binding to
  ``0.0.0.0`` and require that published ports be reachable only from
  networks hosting ``ironic-novncproxy``/``nova-novncproxy``.
* If ``container_host`` points at a TCP endpoint, it must be protected with
  TLS, configured through the standard Docker client mechanisms
  (``DOCKER_TLS_VERIFY``, ``DOCKER_CERT_PATH``) in the conductor's
  environment. These apply to the ``docker`` CLI only: the Podman CLI's
  remote transport has no TLS option, so with Podman use a Unix socket or
  an ``ssh://`` endpoint. Unix sockets are the recommended deployment.
* ``container_command_template`` can alter container privilege (e.g.
  ``--privileged``). It is operator-controlled configuration file content,
  carrying the same trust level as the existing providers' template
  options.

Other end user impact
---------------------

None

Scalability impact
------------------

Per-session cost is identical to the existing providers: one container
and one host TCP port per active console. Each console start/stop adds a
handful of short-lived CLI invocations against a local engine socket.
``stop_all_containers()`` performs one label-filtered list
plus removals at conductor startup and shutdown. The engine daemon is
infrastructure such deployments already run.

Performance Impact
------------------

``start_container`` blocks its conductor thread until the VNC endpoint is
ready, as the ``systemd`` provider does. The readiness wait is bounded by
``[vnc]wait_for_ready_timeout``, but the ``docker run`` step is not: with
the default template's ``--pull missing`` (or ``always``) it can include
an image pull of unbounded duration. Deployments should pre-pull
``console_image`` (or set the template's ``--pull`` to ``never``) to keep
console start times predictable. Console start/stop are infrequent,
user-triggered operations.

Other deployer impact
---------------------

* The feature is opt-in: ``[vnc]container_provider`` defaults to ``fake``
  and nothing changes for existing deployments. Enabling it requires
  ``[vnc]enabled = True``, ``container_provider = container``,
  ``console_image``, and a running ``ironic-novncproxy``, as already
  documented for graphical consoles.
* The conductor's environment (or container image) must include the
  Docker or Podman CLI, and the engine socket must be reachable — for a
  containerized conductor, mounted into its container. Docker CLI 20.10
  or later is required (``docker run --pull``); Podman 4.0 or later is
  recommended when using the Podman CLI (``CONTAINER_HOST`` support).
* Registry authentication for pulling ``console_image`` is out of band,
  using the CLI's standard credential store (``docker login``,
  ``REGISTRY_AUTH_FILE``) in the conductor's environment; no Ironic
  options are added for it.
* Defaults are production-appropriate: publishing binds ``$my_ip`` with a
  random high port, matching the ``systemd`` provider.
* Changes to deployment tooling that wish to take advantage of this
  provider (socket mounts, CLI installation, configuration) belong to the
  respective tooling and are out of scope here.

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  cid <afonnepaulc@gmail.com>

Other contributors:
  None.

Work Items
----------

* Move the RFB readiness wait from ``SystemdConsoleContainer`` into
  shared code.
* Implement ``ContainerConsoleContainer`` in
  ``ironic/console/container/container.py`` and register the ``container``
  entry point.
* Add the ``[vnc]container_*`` options; update ``container_provider`` and
  ``console_image`` help text.
* Unit tests mocking ``utils.execute``, following the existing provider
  tests.
* Devstack support for selecting the ``container`` provider for graphical
  console testing.
* Documentation in ``doc/source/install/graphical-console.rst`` and a
  release note.

Dependencies
============

None. No new Python dependencies are introduced; the Docker or Podman
engine is provided by the deployment. This builds on the implemented
`Graphical Console Support`_ spec.

Testing
=======

Full unit test coverage with ``utils.execute`` mocked, following the
pattern of the existing provider tests in
``ironic/tests/unit/console/container/``.

End-to-end devstack testing of graphical consoles is currently disabled
pending re-enablement of the ``ir-novnc`` devstack service. When it is
re-enabled, a job variant can install Docker and exercise the ``container``
provider with the ``fake-graphical`` console interface, validating
container start/stop, port discovery and proxying without real hardware.
Until then, coverage is manual verification against real BMCs.

Upgrades and Backwards Compatibility
====================================

None. The provider is new and opt-in; existing providers, configuration
defaults and the provider abstract interface are unchanged.

Documentation Impact
====================

* A new "container provider" section in
  ``doc/source/install/graphical-console.rst`` covering configuration,
  socket access (including the containerized-conductor pattern), Podman
  compatibility and the security considerations above.
* A disk-usage callout for long-running conductor hosts: accumulation of
  superseded ``console_image`` images, log rotation for long-lived
  console sessions, and label- and TTL-scoped ``prune`` commands for
  deployments that remove ``--rm`` from the template.
* Soften the current guidance that containerized deployments must write a
  custom out-of-tree provider.
* A release note announcing the provider.

References
==========

.. _Graphical Console Support:
   https://specs.openstack.org/openstack/ironic-specs/specs/approved/graphical-console.html

.. _bug 2158578: https://bugs.launchpad.net/ironic/+bug/2158578

* RFE: https://bugs.launchpad.net/ironic/+bug/2154494
* Container providers documentation:
  https://docs.openstack.org/ironic/latest/install/graphical-console.html#container-providers
* Podman Docker-compatible API:
  https://docs.podman.io/en/latest/markdown/podman-system-service.1.html
* Docker daemon socket security:
  https://docs.docker.com/engine/security/#docker-daemon-attack-surface
