..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=============================================
NGS: Modern Switch Configuration Drivers
=============================================

https://bugs.launchpad.net/networking-generic-switch/+bug/2161019

The ``networking-generic-switch`` (NGS) project currently configures
switches by sending CLI commands over an interactive SSH session via
``netmiko`` and ``paramiko``. There are a number of reasons to move
toward a more modern configuration model — dependency constraints,
performance, FIPS compliance, and the broader industry convergence
on structured interfaces — and this specification proposes building
new per-vendor NETCONF drivers using ``ncclient`` to get there.

.. NOTE::
   This work does not remove the ``netmiko`` or ``paramiko``
   dependencies from NGS. Platforms that lack structured
   configuration APIs — such as Open vSwitch, which is used
   for CI — will continue using existing SSH CLI drivers, and
   operators on ``netmiko``-based drivers may continue to use
   them. The goal is forward-looking drivers that leverage
   ``libssh`` as the underlying transport, alongside the
   existing SSH CLI drivers for platforms where structured
   APIs are not available.


Problem description
===================

The current ``netmiko``/``paramiko`` CLI model has served NGS well,
but multiple factors motivate moving to structured configuration
interfaces:

* **Dependency constraints** -- ``netmiko`` pins ``paramiko`` below
  version 5.0 due to breakage (issues `#3856`_ and `#3858`_), and
  the ``netmiko`` maintainer has indicated that next-major-version
  work will not begin until fall/winter 2026. A compatible release
  may not be available as quickly as needed, particularly as the
  ecosystem moves toward post-quantum key exchange. Additionally,
  ``paramiko`` is a pure-Python SSH implementation, which
  downstream packagers view with some concern compared to bindings
  for system-level SSH libraries like ``libssh``.

* **Performance** -- Interactive SSH CLI sessions carry overhead from
  prompt detection, pagination handling, and timing-based output
  completion. Operators have reported this adds meaningful latency
  to switch configuration, particularly at scale.

* **CLI model fragility** -- Each driver maintains vendor-specific
  command templates sent as text strings over an interactive SSH
  session. ``netmiko`` must handle prompt detection, pagination
  suppression, enable mode, configuration mode entry/exit, and
  timing heuristics — a complex per-vendor state machine that is
  difficult to maintain and validate.

* **FIPS compliance** -- NGS currently monkey-patches ``paramiko``'s
  ``PKey.get_fingerprint`` to replace MD5 with SHA-256. ``libssh``
  delegates cryptography to OpenSSL and is FIPS compatible when
  OpenSSL runs in FIPS mode, eliminating this workaround.

* **Modern algorithm support** -- As switch vendors update firmware
  to prefer newer key exchange and cipher algorithms, the SSH client
  library should be able to negotiate them without friction.

* **Post-quantum readiness** -- ``libssh`` has post-quantum key
  exchange (ML-KEM) support in development. While there is effort to
  bring ML-KEM to ``paramiko`` as well, that work has not landed, and
  the ``netmiko`` version pin would block its consumption regardless.
  Building on ``libssh`` positions NGS to negotiate post-quantum
  algorithms as switch vendors begin shipping firmware that supports
  them.

Any one of these factors might not justify the effort on its own,
but together they present a clear case. And while some will reach
different points with time, there is increased value in operational
choice for our users.

Proposed change
===============

Build new per-vendor NGS drivers using NETCONF (via ``ncclient``)
as alternatives to the existing ``netmiko`` CLI drivers. Each new
driver explicitly documents its capabilities (VLAN, VXLAN, security
groups) so operators have clear expectations. Existing ``netmiko``
drivers remain available for operators who prefer or require the
SSH CLI model. Once new drivers gain feature parity and operator
traction, the project may choose to deprecate the corresponding
``netmiko`` equivalents in a future cycle.

Why NETCONF Instead of Replacing SSH Transport
-----------------------------------------------

The original approach considered in this specification was to replace
``netmiko``/``paramiko`` with a new ``libssh``-based SSH CLI
framework. That approach requires reimplementing ``netmiko``'s
interactive shell state machine — prompt detection, pagination, enable
mode, configuration mode, timing-based output completion — per vendor.
This is the hardest and riskiest part of ``netmiko`` to replicate.

NETCONF sidesteps this entirely. There is no interactive shell, no
prompt detection, no pagination. Configuration is sent as structured
XML and responses are parsed programmatically. This is both less
fragile and more maintainable.

``ncclient`` 0.7.0 (released August 2025) already ships a ``libssh``
transport via ``connect_libssh()``, so NETCONF drivers built on
``ncclient`` can operate without ``paramiko`` today.

Per-Vendor Driver Model
-----------------------

NGS already has a vendor-agnostic NETCONF/OpenConfig driver and a
``NetconfSwitch`` base class (649 lines) that handles NETCONF session
management, datastore locking, candidate/running auto-detection,
confirmed commits, and configuration persistence. New drivers will
build on this foundation.

However, per-vendor drivers will be needed rather than a single
vendor-neutral driver. OpenConfig YANG model coverage varies across
vendors, and some features central to NGS — particularly VXLAN L2VNI
configuration and security group ACLs — may require vendor-specific
YANG models or are not uniformly available. Some vendors may not
support VXLAN at all.

Each per-vendor driver will:

* Inherit from the existing ``NetconfSwitch`` base class.
* Implement the same device interface contract as existing drivers so
  the ML2 plugin layer requires no changes.
* Explicitly document which capabilities it supports (VLAN, trunk,
  VXLAN L2VNI, security groups, port enable/disable) so operators
  can make informed decisions.
* Be registered as a separate stevedore entry point following
  the naming convention ``netconf_<vendor>_<model>``, e.g.,
  ``netconf_juniper_junos``. The transport is an implementation
  detail. Alternate transport variants are not anticipated at
  this time, though a compelling need could change that stance.
  Existing ``netmiko_`` prefixed drivers remain available for
  operators who prefer or require the SSH CLI model.

.. NOTE::
   The ``libssh`` transport requires the remote device to support
   key-based or password authentication. Devices that require
   keyboard-interactive authentication are not compatible with
   ``libssh`` and will need to use a ``netmiko``-based driver.

Operators will be able to see at a glance what each driver supports
and choose between the structured-API driver and the legacy CLI
driver based on their environment's requirements.

Target Platforms
~~~~~~~~~~~~~~~~

The following platforms are targets for new NETCONF drivers.
Implementation order will be driven by contributor availability,
hardware or simulator access for validation, and community
demand. Contributors with access to specific platforms are
encouraged to drive implementation for those targets.

* Juniper Junos -- co-creators of NETCONF, excellent support
* Cisco NX-OS -- NETCONF supported on Nexus platforms
* SONiC -- NETCONF is architecturally supported in the SONiC
  Management Framework and enterprise vendors have begun shipping
  NETCONF support, though gNMI is more widely adopted in the
  SONiC ecosystem today
* Dell OS10 -- NETCONF supported
* Nokia SR Linux -- NETCONF supported
* Arista EOS -- a vendor-agnostic NETCONF/OpenConfig driver
  already exists in-tree; per-vendor work may focus on features
  not covered by OpenConfig models
* Cisco IOS -- NETCONF on IOS-XE; classic IOS has limited
  support

RBAC Considerations
~~~~~~~~~~~~~~~~~~~

NETCONF access may require different credentials or privilege levels
than SSH CLI access on some platforms. For example, NETCONF may
require a dedicated ``netconf`` subsystem user or specific RBAC
permissions for the NETCONF subsystem.

These are operational trade-offs that will be documented on a
per-driver basis. Operators should evaluate the credential and access
requirements for each driver as part of their migration planning.

Challenges
~~~~~~~~~~

* **YANG model coverage** -- Not all switch configuration is
  available through OpenConfig YANG models. VXLAN L2VNI and security
  group ACL configuration may require vendor-specific YANG modules,
  increasing per-driver complexity. Each driver must evaluate what is
  available through NETCONF on its target platform.

* **Feature gaps** -- Some switches do not support VXLAN at all (e.g.,
  Cisco IOS classic). The per-vendor driver model handles this by
  explicitly documenting supported capabilities rather than assuming
  uniform feature sets.

* **Distributed locking and request batching** -- The existing
  ``NetmikoSwitch`` base class provides distributed locking via
  ``tooz`` and request batching via ``SwitchBatch``. These exist
  largely because CLI-based configuration is not transactional —
  each command takes effect immediately, so concurrent sessions
  risk leaving switches in an inconsistent state. NETCONF's
  transactional model (candidate datastore, commit, confirmed
  commit) provides atomic configuration changes at the protocol
  level, which likely eliminates the need for application-level
  distributed locking. This assumption should be validated during
  implementation.

* **SSH parameter bridge** -- NETCONF drivers using ``ncclient``'s
  ``libssh`` transport will need a way to expose SSH connection
  parameters (timeouts, allowed algorithms, key types) that
  operators currently configure via NGS's ``ngs_ssh_*`` options.
  Bridging between NGS configuration and ``ncclient``'s ``libssh``
  transport API is tractable but represents additional integration
  work that must be done separately.

Expected effort
~~~~~~~~~~~~~~~

The NETCONF driver framework — base class, OpenConfig YANG model
library, session management, locking, retry, and confirmed commit
handling — already exists and is tested. One concrete NETCONF
driver (``NetconfOpenConfigSwitch``) is in production today. The
pattern for building a new driver is established.

For vendors with good OpenConfig YANG coverage, each new driver is
incremental work: evaluate available YANG models, map NGS
operations to model objects, write tests, and validate against a
simulator. The existing driver serves as a template.

However, the per-vendor work should not be underestimated:

* **YANG model evaluation** requires domain expertise in both
  the vendor's NETCONF implementation and the YANG models it
  exposes. Model coverage, naming conventions, and datastore
  behavior vary significantly across vendors.
* **Vendor-specific YANG models** are needed where OpenConfig
  coverage falls short — particularly for VXLAN L2VNI and
  security group ACL configuration. These require building new
  model classes that cannot follow the OpenConfig template.
* **Vendor NETCONF quirks** — each vendor's NETCONF
  implementation has idiosyncrasies in session handling,
  capability negotiation, error reporting, and commit behavior
  that must be discovered and handled per driver.
* **Each per-vendor driver is a long-term maintenance
  commitment.** Firmware updates can change YANG model
  behavior, and the project must be prepared to maintain
  drivers across vendor software versions.

Simulator availability also affects effort. Platforms with
readily available simulators can be validated directly; others
may require vendor relationships or rely on community testing.

Alternatives
------------

**Replace SSH transport only (libssh CLI drivers).** Build a new
``LibsshSwitch`` base class that reimplements ``netmiko``'s
interactive shell state machine using ``libssh`` instead of
``paramiko``, keeping the CLI command model. This avoids the need to
learn each vendor's NETCONF/YANG models but requires reimplementing
the hardest part of ``netmiko`` — the per-vendor prompt detection
and shell automation. This remains a fallback for any platform where
NETCONF is not viable.

**Use gNMI.** gNMI (gRPC Network Management Interface) uses the
same YANG data models as NETCONF but runs over gRPC/TLS instead
of SSH, eliminating the ``paramiko`` dependency entirely. Platforms
like SONiC and Cumulus NVUE that have limited NETCONF support do
support gNMI. Python libraries such as ``pyGNMI`` provide a mature
vendor-neutral client. gNMI could serve as a future transport for
platforms where NETCONF is not available, but adding a third driver
transport model is out of scope for the initial effort.

**Use scrapli.** The ``scrapli`` library provides network device CLI
automation without ``paramiko``. However, its build chain requires
Zig for compiling transport bridges, which poses packaging challenges
for downstream distributions.

**Do nothing and wait for netmiko.** This leaves NGS pinned to
``paramiko`` < 5.0 for the foreseeable future, deferring the ability
to adopt modern cryptographic capabilities.

Data model impact
-----------------

None

State Machine Impact
--------------------

None. NGS operates as an ML2 plugin outside of Ironic's state machine.

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

This change improves the security posture of NGS:

* For NETCONF drivers using ``ncclient``'s ``libssh`` transport:
  removes the ``paramiko`` dependency and the ``PKey.get_fingerprint``
  monkey-patch. ``libssh`` delegates all cryptographic operations to
  OpenSSL, so it inherits FIPS compliance when the underlying OpenSSL
  is running in FIPS mode. This is the same model used by RHEL.
* NETCONF access may require different credentials or privilege
  levels than SSH CLI. This is an operational trade-off documented
  per driver.

Other end user impact
---------------------

None

Scalability impact
------------------

No negative scalability impact is anticipated. NETCONF's
transactional model may reduce management-plane load compared
to interactive SSH sessions, though this will vary by platform.

Performance Impact
------------------

Both NETCONF and CLI-based configuration run over SSH, so
underlying transport performance is comparable. NETCONF
eliminates the prompt-detection delays and pagination handling
inherent in interactive CLI sessions. Per-platform management
plane behavior varies — switch firmware quality and hardware
resources affect both configuration interfaces — so per-driver
performance characteristics will be documented as drivers are
validated.

Other deployer impact
---------------------

* Operators will need to update their NGS configuration to reference
  new driver entry points (e.g., ``netconf_juniper_junos``
  instead of ``netmiko_juniper_junos``) when migrating.
* NETCONF drivers using ``ncclient``'s ``libssh`` transport require
  the ``libssh`` system library. Most modern distributions package
  it.
* Each new driver documents its supported capabilities, so operators
  can verify feature parity before migrating.
* During the coexistence period, both driver sets are functional.
  Operators can migrate switches individually.

Developer impact
----------------

Third-party driver developers targeting NGS are encouraged to build
new drivers on the ``NetconfSwitch`` base class. Existing
``netmiko``-based drivers continue to work during the migration
period.


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

1. Update ``NetconfSwitch`` base class to support ``ncclient``'s
   ``connect_libssh()`` transport as the default, with ``paramiko``
   transport as a fallback.
2. Evaluate NETCONF YANG model coverage for VLAN, VXLAN L2VNI, and
   security group configuration on each target platform.
3. Implement per-vendor NETCONF drivers, starting with platforms
   where contributors have hardware or simulator access for
   validation.
4. Implement a ``fake`` driver on the NETCONF base class to
   maintain CI test coverage.
5. Update documentation with per-driver capability matrix and
   migration guide.

**Stretch goal:**

6. Move ``netmiko`` and ``ncclient`` to optional dependencies in
   ``pyproject.toml`` (``[project.optional-dependencies]``) and
   ensure imports fail gracefully when a driver's backing library
   is not installed.


Dependencies
============

* ``ncclient`` >= 0.7.0 -- Required for ``connect_libssh()`` NETCONF
  transport. ``ncclient`` 0.7.0 uses ``ssh-python`` (Cython bindings
  for the ``libssh`` C library) as its ``libssh`` backend. This is
  the same binding library used by Ansible's ``netcommon`` collection,
  giving it two significant downstream consumers validating it in
  production.
* ``libssh`` system library -- Available in Fedora, Ubuntu, Debian,
  RHEL/CentOS, and SUSE package repositories.
* Any future gNMI or RESTCONF drivers would use additional
  libraries (e.g., ``pyGNMI``, ``requests``) already available or
  easily packaged; this is out of scope for the initial effort.


Testing
=======

Unit tests will mock the ``ncclient`` manager, following the same
pattern as existing tests which mock ``netmiko.ConnectHandler``
and ``ncclient.manager.connect``.

The existing OVS-based multinode CI job provides the primary
integration test coverage for NGS today. Since OVS does not support
NETCONF, the OVS driver will remain SSH-based for CI
purposes. A ``fake`` driver built on the new base classes will be
needed for unit testing the structured-API path.

Validation against vendor platforms will rely on unit tests and
community testing by operators with access to the hardware or
simulators.


Upgrades and Backwards Compatibility
====================================

Both ``netmiko`` and NETCONF driver sets will coexist. Operators
choose which driver to use via the entry point name in their NGS
configuration. No automatic migration occurs — operators
explicitly switch entry points when ready.

The device interface contract is unchanged, so the ML2 plugin and
Neutron integration require no modifications.


Documentation Impact
====================

* Per-driver capability matrix documenting which features each
  driver supports (VLAN, trunk, VXLAN L2VNI, security groups, port
  enable/disable).
* Migration guide mapping old entry points to new ones.
* Per-driver RBAC and credential requirements.
* Updated driver documentation for each new driver.


References
==========

.. _#3856: https://github.com/ktbyers/netmiko/issues/3856
.. _#3858: https://github.com/ktbyers/netmiko/issues/3858

* netmiko paramiko<5.0 pin: `#3858`_
* netmiko maintainer acknowledgement: `#3856`_
* ncclient 0.7.0 libssh transport:
  https://github.com/ncclient/ncclient/releases/tag/v0.7.0
* ssh-python: https://pypi.org/project/ssh-python/
