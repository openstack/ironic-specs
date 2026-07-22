..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

============================================================
NGS: Structured CLI Drivers for Linux-Based Switch Platforms
============================================================

https://bugs.launchpad.net/networking-generic-switch/+bug/2161019

SONiC and Cumulus Linux 5.x (NVUE) are Linux-based switch platforms
whose CLI tools behave like ordinary Linux commands — non-interactive,
deterministic, and reporting success or failure via exit codes. The
existing NGS drivers for these platforms already connect as Linux SSH
sessions (``NETMIKO_DEVICE_TYPE = "linux"``), but they still route
through ``netmiko`` and ``paramiko`` to do so — even though
``netmiko``'s value lies in its interactive shell state machine,
which these platforms do not need.

This specification proposes replacing ``netmiko`` for these two
platforms with direct SSH command execution via ``libssh`` (through
``ssh-python``). Rather than opening an interactive shell and
sending commands through it (as ``netmiko`` does, even for the
``linux`` device type), the new drivers execute each command
directly over an SSH exec channel — the same mechanism as
``ssh user@host command``. The resulting drivers reuse the proven
CLI command patterns from the existing drivers while removing the
``netmiko``/``paramiko`` dependency for these platforms.

This is a companion to the NETCONF migration specification, which
covers platforms that support structured configuration via NETCONF.


Problem description
===================

SONiC and Cumulus NVUE do not support NETCONF, which means the
NETCONF migration specification cannot cover them. However, both
platforms differ fundamentally from the traditional network device
CLI model that makes ``netmiko`` valuable:

* **No interactive shell state machine.** Traditional network device
  CLIs require prompt detection, pagination suppression, enable mode,
  configuration mode entry/exit, and timing-based output completion.
  This is the complex per-vendor state machine that ``netmiko``
  provides. SONiC and Cumulus NVUE do not need any of it — their
  CLI tools (``config`` for SONiC, ``nv`` for Cumulus NVUE) are
  non-interactive Linux commands that execute and return.

* **Exit codes instead of output parsing for errors.** Linux commands
  report success or failure via exit codes. While the existing
  drivers also scan output for error patterns as a safety net, the
  primary error signal is the command's return code — not regex
  matching against an interactive terminal session's text output.

* **Structured output available.** Cumulus NVUE supports JSON output
  via the ``-o json`` flag, enabling programmatic parsing without
  fragile text-table scraping. SONiC's ``show`` commands produce
  text tables that the existing drivers parse, but configuration
  commands use exit codes for status.

* **Already treated as Linux by netmiko.** Both drivers set
  ``NETMIKO_DEVICE_TYPE = "linux"`` — they were never using
  ``netmiko``'s network-device-specific shell automation.
  However, ``netmiko`` still opens an interactive PTY shell
  (via ``paramiko``'s ``invoke_shell()``) and writes commands
  into it character-by-character with timing-based reads. Even
  for the ``linux`` device type, ``netmiko`` never uses SSH
  exec channels. The drivers are paying the full cost of
  interactive shell management for platforms that do not need it.

Given these characteristics, direct SSH command execution is
sufficient — and more appropriate than an interactive shell.
Replacing the ``netmiko`` layer also advances the broader goal
of migrating away from the ``netmiko``/``paramiko`` combination,
with the same motivations described in the companion NETCONF
specification: FIPS compliance without monkey-patching,
packager preference for system-level SSH over pure-Python
implementations, and modern SSH algorithm support including
post-quantum readiness via ``libssh``.


Proposed change
===============

Build a lightweight ``SshCommandSwitch`` base class that provides
SSH command execution via ``libssh`` (through ``ssh-python``)
without interactive shell handling. Then migrate the SONiC and
Cumulus NVUE drivers to use it. The base class is generic enough
that other Linux-based platforms — including OVS — could adopt it
in the future.

SshCommandSwitch Base Class
---------------------------

The base class provides:

* Persistent SSH sessions via ``libssh`` — a connection is
  established once and held open for the duration of a driver
  operation. Each command opens a new SSH exec channel on the
  existing session (standard SSH channel multiplexing per
  RFC 4254), so multiple commands execute without repeated
  SSH handshakes or re-authentication. Connection pooling
  allows sessions to be reused across operations.
* Support for the same NGS configuration options where applicable
  (``ngs_ssh_connect_timeout``, ``ngs_max_connections``,
  ``ngs_ssh_allowed_algorithms``).
* A ``run_command(command)`` method that executes a single command
  over the active session, returning its output and exit code.
* A ``run_commands(commands)`` method that executes a sequence of
  commands over the same session, failing on the first non-zero
  exit code.
* Error handling based on exit codes, with optional output-pattern
  matching as a secondary check for platforms that return exit
  code 0 on some error conditions.

This base class does not implement:

* Prompt detection or pagination handling.
* Interactive shell session management.
* Enable mode or configuration mode transitions.
* Timing-based output completion heuristics.

None of these are needed for Linux-based command execution.

.. NOTE::
   ``SshCommandSwitch`` is independent from the ``NetconfSwitch``
   base class. While both use ``libssh`` for SSH transport, the
   NETCONF class delegates session management to ``ncclient``,
   which manages its own SSH connections internally. The two base
   classes have different connection lifecycles and do not share
   a transport layer.

Per-Platform Drivers
--------------------

**SONiC driver** (``libssh_sonic``):

Reuses the same CLI command patterns as the existing
``netmiko_sonic`` driver:

* VLAN management: ``config vlan add/del``
* Port membership: ``config vlan member add/del``
* VXLAN/L2VNI: ``config vxlan map add/del`` plus FRR ``vtysh``
  commands for BGP EVPN
* Security groups: ACL JSON files written via shell pipeline,
  loaded with ``acl-loader``
* Configuration save: ``config save -y``

A ``libssh_dell_enterprise_sonic`` variant handles Dell-specific
ACL command differences, mirroring the existing driver structure.

**Cumulus NVUE driver** (``libssh_cumulus_nvue``):

Reuses the same CLI command patterns as the existing
``netmiko_cumulus_nvue`` driver:

* VLAN management: ``nv set/unset bridge domain br_default vlan``
* Port membership: ``nv set/unset interface ... bridge domain``
* Trunk ports: tagged VLAN membership via ``nv set``
* VXLAN/L2VNI: ``nv set bridge domain ... vlan ... vni`` with
  ingress-replication, head-end-replication, and multicast BUM
  modes
* Port enable/disable: ``nv set interface ... link state up/down``
* Configuration apply: ``nv config apply --assume-yes``
* Configuration save: ``nv config save``
* JSON output parsing via ``-o json`` flag on show commands

.. NOTE::
   Cumulus Linux 4.x (NCLU) is deprecated by NVIDIA in favor of
   NVUE and is not in scope for a new driver. The existing
   ``netmiko_cumulus`` driver remains available for operators still
   running Cumulus 4.x.

Deprecation
-----------

The existing ``netmiko_sonic``, ``netmiko_dell_enterprise_sonic``,
and ``netmiko_cumulus_nvue`` drivers will be deprecated after their
``libssh`` replacements reach feature parity, following the same
deprecation model as the NETCONF specification: no deprecation
warnings until the replacement is proven and documented.

Challenges
~~~~~~~~~~

* **Privilege escalation** -- The existing SONiC driver uses
  ``netmiko``'s ``enable()`` method, which for the ``linux``
  device type runs ``sudo su`` to enter a persistent root shell.
  Since the new drivers use exec channels rather than an
  interactive shell, they cannot maintain a persistent
  escalated context. Instead, commands will be prefixed with
  ``sudo`` (e.g., ``sudo config vlan add 100``). Whether
  ``sudo`` is required will be configurable, since some
  deployments authenticate directly as root.

* **Command restructuring** -- Some existing command patterns
  rely on shell features (pipes, redirections) that assume an
  interactive shell context. For example, the SONiC ACL write
  uses a pipeline: ``echo | base64 -d | gunzip > file``. SSH
  exec channels execute commands without a login shell, but
  pipelines and redirections can be preserved by wrapping them
  with ``sh -c "..."`` — the exec channel invokes ``sh``,
  which then interprets the pipeline normally. Commands that
  cannot be handled this way can be restructured into discrete
  steps (e.g., write a file, then load it). This is expected
  to be straightforward but requires per-command review during
  implementation.

* **FRR vtysh commands** -- Both SONiC and Cumulus NVUE use
  ``vtysh -c`` for BGP EVPN configuration. While ``vtysh -c``
  accepts commands as arguments (non-interactive), it has its
  own error reporting patterns that the drivers must handle.

* **SONiC output parsing** -- SONiC's ``show`` commands produce
  text tables in multiple formats across versions. The existing
  driver handles three different output formats with regex
  parsing. The new driver inherits this complexity. Most of
  this parsing involves single-line value hunting to determine
  whether configuration needs to be re-applied, rather than
  full table reconstruction. If richer parsing is needed in
  the future, libraries such as TTP (Template Text Parser)
  could be considered.

Distributed Locking
~~~~~~~~~~~~~~~~~~~

The existing ``NetmikoSwitch`` base class uses ``tooz``-based
distributed locking to serialize configuration operations against
each switch. This was motivated by traditional network devices
that support only a limited number of concurrent configuration
sessions — often just one — where a second session would either
be rejected or cause conflicts.

SONiC and Cumulus NVUE are Linux systems that support multiple
independent concurrent SSH sessions without session-count
constraints. Each NGS operation targets a specific port binding,
and the switch applies each command independently. The risk of
conflicting concurrent operations is low: two Neutron requests
would need to operate on overlapping VLAN membership for the
same port simultaneously, which normal scheduling makes unlikely.

For these reasons, the ``SshCommandSwitch`` base class does not
implement distributed locking. If operational experience reveals
concurrency issues, locking can be added later without changing
the driver interface.


Alternatives
------------

**Use gNMI for SONiC.** SONiC supports the gNMI Set RPC for
configuration, including transactional semantics with
checkpoint/rollback. However, gNMI adoption for configuration
management (as opposed to telemetry) remains limited across the
industry — most vendors implement only Get, Subscribe, and
Capabilities, not Set. Building a gNMI driver framework for a
single platform provides limited reuse value. gNMI remains an
option if the structured-CLI approach proves insufficient for
SONiC, or if broader vendor adoption of gNMI Set materializes.

**Use RESTCONF for SONiC.** SONiC's Management Framework
includes a RESTCONF interface with some OpenConfig YANG model
support. While this provides a standards-based configuration
path, the OpenConfig coverage in SONiC has been found to be
limited in practice — not all configuration relevant to NGS
operations is exposed through the available YANG models. NGS
is also pursuing RESTCONF support as an alternative to NETCONF
for platforms with broader RESTCONF coverage. If SONiC's
RESTCONF implementation matures, a RESTCONF-based driver could
complement or replace the structured-CLI driver. The
structured-CLI approach is preferred for initial delivery
because it reuses proven command patterns from the existing
drivers and provides a known-working baseline.

**Use the Cumulus NVUE REST API.** Cumulus NVUE exposes a REST API
on port 8765 using OpenAPI (not YANG/RESTCONF). This is a
vendor-proprietary interface with no standards-based equivalent.
A REST driver would work but provides no reuse across platforms
and introduces an HTTP dependency. The structured-CLI approach
reuses proven command patterns and shares a base class with SONiC.

**Leave both on netmiko.** This is viable — the drivers work
today. However, SONiC in particular is a high-demand platform in
bare metal deployments, and leaving it on a pinned ``paramiko``
while the rest of the fleet migrates away creates an inconsistency
that operators will notice.

Data model impact
-----------------

None

State Machine Impact
--------------------

None. NGS operates as an ML2 plugin outside of Ironic's state
machine.

REST API impact
---------------

None

Client (CLI) impact
-------------------

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

None. The new drivers implement the same device interface contract.
No changes to Ironic's network interface or driver API are required.

Nova driver impact
------------------

None

Ramdisk impact
--------------

None

Security impact
---------------

* Removes the ``paramiko`` dependency for SONiC and Cumulus NVUE
  configurations. ``libssh`` delegates all cryptographic operations
  to OpenSSL, inheriting FIPS compliance when OpenSSL runs in FIPS
  mode.
* Removes the need for the ``paramiko`` ``PKey.get_fingerprint``
  monkey-patch on these platforms.

Other end user impact
---------------------

None

Scalability impact
------------------

None anticipated. Command execution patterns remain the same.

Performance Impact
------------------

May improve over the current ``netmiko`` drivers. The existing
drivers route through ``netmiko``'s interactive shell handling
even though these platforms do not need it. Direct command
execution via ``libssh`` eliminates that overhead, which
operators have identified as a source of latency in switch
configuration at scale.

Other deployer impact
---------------------

* Operators will need to update their NGS configuration to
  reference new driver entry points (e.g., ``libssh_sonic``
  instead of ``netmiko_sonic``) when migrating.
* The ``libssh`` system library must be available on the host.
  Most modern distributions package it.
* During the coexistence period, both driver sets are functional.
  Operators can migrate switches individually.

Developer impact
----------------

None. The ``SshCommandSwitch`` base class is specific to
Linux-based platforms with non-interactive CLIs.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Julia (TheJulia) Kreger

Other contributors:
  Harald (hjensas) Jensas

Work Items
----------

1. Implement ``SshCommandSwitch`` base class with ``libssh``-based
   SSH command execution, connection management, and exit-code
   error handling.
2. Implement ``libssh_sonic`` and ``libssh_dell_enterprise_sonic``
   drivers using the existing CLI command patterns.
3. Implement ``libssh_cumulus_nvue`` driver using the existing CLI
   command patterns.
4. Implement a ``libssh_fake`` driver for unit testing the new
   base class.
5. Add deprecation warnings to the corresponding ``netmiko``
   drivers after replacements reach feature parity.
6. Update documentation with migration guide.


Dependencies
============

* ``ssh-python`` -- Cython bindings for the ``libssh`` C library.
  The same binding library used by ``ncclient`` 0.7.0 and
  Ansible's ``netcommon`` collection.
* ``libssh`` system library -- Available in Fedora, Ubuntu,
  Debian, RHEL/CentOS, and SUSE package repositories.


Testing
=======

Unit tests will mock the ``libssh`` session layer, following the
same pattern as existing tests which mock
``netmiko.ConnectHandler``. The existing test suites for SONiC
(1085 lines) and Cumulus NVUE (1158 lines across two files) define
the expected command sequences; the new tests will verify the same
sequences through the ``SshCommandSwitch`` interface.

The existing OVS-based multinode CI job exercises NGS end-to-end
but uses OVS, not SONiC or Cumulus. Validation against SONiC and
Cumulus NVUE will rely on unit tests and community testing by
operators with access to the hardware or simulators (SONiC-VS,
Cumulus VX).


Upgrades and Backwards Compatibility
=====================================

Both ``netmiko`` and ``libssh`` driver sets will coexist during
the migration period. Operators choose which driver to use via the
entry point name in their NGS configuration.

Individual ``netmiko`` drivers will emit deprecation warnings only
after their ``libssh`` replacement has reached feature parity.
They remain fully functional until removal. No automatic migration
occurs — operators explicitly switch entry points when ready.

The device interface contract is unchanged, so the ML2 plugin and
Neutron integration require no modifications.


Documentation Impact
====================

* Migration guide mapping old entry points to new ones.
* Updated driver documentation for SONiC and Cumulus NVUE.
* Deprecation notices on the ``netmiko`` driver documentation
  pages for these platforms.


References
==========

* Companion NETCONF spec: ngs-libssh-migration
* SONiC Management Framework:
  https://github.com/sonic-net/SONiC/blob/master/doc/mgmt/
  Management%20Framework.md
* Cumulus NVUE documentation:
  https://docs.nvidia.com/networking-ethernet-software/
  cumulus-linux-516/System-Configuration/
  NVIDIA-User-Experience-NVUE/
* ssh-python: https://pypi.org/project/ssh-python/
