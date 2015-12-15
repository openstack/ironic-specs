..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

================================================
Add pluggable metrics backend for Ironic and IPA
================================================

https://bugs.launchpad.net/ironic/+bug/1526219

This proposes the addition of metric data reporting features to
Ironic, and Ironic Python Agent (IPA). Initially, this will include a statsd
reference implementation, but will be sufficiently generic to permit the
creation of alternative backends.

Problem description
===================

Software metrics are extremely useful to operators for recognizing and
diagnosing problems in running software, and can be used to monitor the
real time and historical performance of Ironic and IPA in a production
environment.

Metrics can be used to determine how quickly (or slowly) parts of the system
are running, how often errors (such as API error responses or BMC failures)
occur, or the performance impact of a given change.

Currently, neither Ironic nor IPA report any application metrics.

Proposed change
===============

* Design a shared pluggable metric reporting system.
* Implement a generic MetricsLogger which includes:

  * Gauges (generic numerical data).
  * Counters (increment/decrement a counter).
  * Timers (time something).
  * Decorators, and context managers for same.

* Implement a StatsdMetricsLogger as the reference backend [1].
* Instrument Ironic to report metric data including:

  * Counting and timing of API requests.  This may be accomplished by hooking
    into Pecan.
  * Counting and timing of RPCs.
  * Counting and timing of most worker functions in ConductorManager.
  * Counting and timing of important driver functions.
  * Count and time node state changes.  By inspecting provision_updated_at
    during a state change, the time the node spent in that state can be
    calculated.

* Instrument IPA to report metric data including, but not limited to:

  * Image download/write counts and times.
  * Deploy/cleaning counts and times.

Example code follows (based on Python logging module naming conventions):

.. code:: python

  METRICS = metrics.getLogger(__name__)

  class Foo(object):
    def func1(self):
      # Emit gauge metric with value 1
      METRICS.gauge("one.fish", 1)

      # Increment counter metric by two
      METRICS.counter("two.fish", 2)

      # Decrement counter metric by one
      METRICS.counter("red.fish", -1)

      # Randomly sample the data (emit metric 10% of the time)
      METRICS.counter("blue.fish", 42, sample_rate=0.1)

      # Emit a timer metric with value of 125 (milliseconds)
      METRICS.timer("black.fish", 125)

      # Randomly sample the data (emit metric 1% of the time)
      METRICS.timer("blue.fish", 125, sample_rate=0.01)

    @METRICS.counter_d("func2.count")
    @METRICS.timer_d("func2.time", sample_rate=0.1)
    def func2(self):
      pass

    # Context managers for counting and timing code blocks
    def func3(self):

      with METRICS.counter_c("func3.thing_one.count", sample_rate=0.25):
        thing_one()

      with METRICS.timer_c("func3.thing_two.time"):
        thing_two()


Metric names follow this convention (optional parts indicated by []):

``[global_prefix.][host_name.]prefix.metric_name``

If `--metrics-agent-prepend-host-reverse` is set, then ``host.example.com``
becomes ``com.example.host`` to assist with hierarchical data
representation.

For example, using the Statsd backend, and relevant config options,
``METRICS.timer("blue.fish", 125, sample_rate=0.25)`` is emitted to statsd as
``globalprefix.com.example.host.moduleprefix.blue.fish:1|ms@0.25``.

Alternatives
------------

Alternatively, we could implement a Ceilometer backend.  Although Ironic
already reports some measurements (such as IPMI sensor data) to Ceilometer,
the metrics that are proposed in this spec do not fit with the Ceilometer
project mission, which is to "...collect measurements of the utilization of
the physical and virtual resources comprising deployed clouds..." [2]

Instead, this spec proposes that we instrument parts of the Ironic/IPA
codebase itself to report metrics and statistics about how/when the code is
run, and the performance of the code thereof.  This data is not directly
related to "physical and virtual resources comprising deployed clouds."
Therefore, we do not propose the addition of a Ceilometer backend, nor do we
propose that the existing Ceilometer measurements be converted to this
system, as they represent fundamentally different types of data.

Data model impact
-----------------

None

State Machine Impact
--------------------

None.

REST API impact
---------------

To support agent drivers, a config field will be added to the response for
the ``/drivers/<drivername>/vendor_passthru/lookup`` endpoint in the Ironic
API.

This field will contain the agent-related config options that an agent can
use to configure itself to report metric data.  For example: statsd host and
statsd port.

Client (CLI) impact
-------------------

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

Security impact
---------------

The statsd daemon [3] has no authentication, and consequently anyone who is
able to send UDP datagrams to the daemon can send arbitrary metric data.
However, the statsd daemon is typically configured to listen only on a local
interface, which partially mitigates security concerns.

Other end user impact
---------------------

None.

Scalability impact
------------------

Deployers must ensure that their statsd infrastructure is scaled correctly
relative to the size of their deployment.  However, even if the statsd daemon
is overloaded, Ironic will not be negatively affected (statsd UDP datagrams
are non-blocking, and will simply not be processed).

Performance Impact
------------------

By default, metrics reporting will be disabled, reducing, but not totally
eliminating, the performance impact for users who do not wish to collect
metrics.  At the very least, a conditional must be checked at each place where
a metric could be reported. Furthermore, depending on exactly how and where
the conditional checking occurs, arguments may be evaluated even if the metric
data aren't actually sent.

Reporting metrics via statsd affects performance minimally.  The overhead
of sending a single piece of metric data is very small--in particular, statsd
metrics are sent via UDP (non-blocking) to a  daemon [2] that aggregates the
metrics before forwarding them to one of its supported backends.  Should this
backend become unresponsive or overloaded, then metric data will be lost, but
without other performance effects.

After the metric data are aggregated by a local statsd daemon, they are
periodically flushed to one of statsd's configured backends, usually Graphite
[4].

Other deployer impact
---------------------

Default config options:

.. code::

  [metrics]

  # Backend options are "statsd" and "noop"
  backend="noop"
  statsd_host="localhost"
  statsd_port=8125

  # See proposed changes section for detailed description of how these are used
  prepend_host=false
  prepend_host_reverse=false
  global_prefix=""

  # Backend options are "statsd" and "noop"
  agent_backend="noop"
  agent_statsd_host="localhost"
  agent_statsd_port=8125

  # See proposed changes section for detailed description of how these are used
  agent_prepend_host=false
  agent_prepend_host_reverse=false
  agent_prepend_uuid=false
  agent_global_prefix=""


If the statsd metrics backend is enabled, then deployers must install and
configure statsd, as well as any other metrics software that they wish to use
(such as Graphite [3]).

Developer impact
----------------

None.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  aweeks

Other contributors:
  None

Work Items
----------

* Design/implement shared metric reporting library. (In progress [5])

* Implement statsd backend.

* Instrument Ironic code to report metrics.

* Instrument IPA code to report metrics.

Dependencies
============

This change will introduce a dependency on a shared metrics reporting library
in ironic-lib.  The statsd protocol is simple enough to justify implementing
it ourselves in order to avoid introducing external dependencies.

Testing
=======

Additional care may be required to test the statsd network code.

Upgrades and Backwards Compatibility
====================================

None.

Documentation Impact
====================

Appropriate documentation must be written.

References
==========

For more on why metrics are useful to operators, and why the statsd project
began: https://codeascraft.com/2011/02/15/measure-anything-measure-everything/

[1] https://github.com/etsy/statsd/blob/master/docs/metric_types.md

[2] https://wiki.openstack.org/wiki/Ceilometer

[3] https://github.com/etsy/statsd/

[4] https://graphite.readthedocs.org/en/latest/faq.html

[5] https://github.com/rackerlabs/metricslogger

