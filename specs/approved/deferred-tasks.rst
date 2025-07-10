..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

============================
Deferred (resumable) Actions
============================

https://bugs.launchpad.net/ironic/+bug/2137571

While working on the migration away from eventlet, contributors
have raised concern over a change in the overall performance and
behavior pattern which was "glossed" over with eventlet. Where
"sleep" was not *really* blocking to the overall process, where now
"sleep" is now blocking to a thread. Some of this is tolerable, if
a thread is driving a whole workflow, but ultimately Ironic's goal
should be to minimize the amount of time a single thread is focused
on a specific node.

Some really good examples of this pattern and need are around
workflow operations which need to occur with Baseboard Management
Controllers where actions within the BMC take time, and we don't
want a firmware upgrade to consume a single thread for a node for
15-20 minutes. We want to do the needful, of which the vast
majority of the time would normally be waiting for the BMC to reach
the next desired state.

Combining with the other major workflow needs, the concept of a
"deferred" action surfaced in the Ironic community and is
resonating as a generalized path forward.

Problem description
===================

When dealing with hardware, our biggest problem with holding a
thread is the long wait. For example, when we're waiting for a host
to reboot or to power cycle. Or, when we realize there is a
problem, and we need to resume later.

This is compounded by users asking for more work, be it synchronous
or future asynchronous work via some sort of future bulk action.
Also from requests from other services where some fields may need
to be cleared entirely before exiting a state change, or to hint to
Ironic that a future action can proceed as part of a cross-service
workflow.

Ironic's traditional model is to leverage periodic worker tasks to
spawn some intermediate and follow-up actions, but we have limited
insight into what is ahead of us in the task pool, and we don't
really have the ability to wait and "check in five minutes". Much
less do we have any ability to say "I need to achieve this, but it
only needs to happen 'eventually'".

In substantial discussion over the 2025.2, and 2026.1 development
cycles, and now 2026.1 PTG we believe the best path forward is to
build a model where we can request an action be executed, later on,
to enable some of the existing code paths to be simplified.

For example, today the code is modeled as:

 * action_1
 * action_2
 * sleep or looping follow-up check action which blocks the thread.
 * action_3
 * set a state for a periodic to pickup which requires reading the
   whole of a node from the nodes table
 * periodic job triggers occasionally, and attempts to determine if
   it *can* proceed with a side effect of amplifying database load.
 * action_4

And in this model, we would conceptually reach a model of:

 * action_1
 * action_2
 * action_3 completed, telling the next action to do action_4
 * action_4

While this is not a perfect illustration, the key is simple. Shift
work tracking from the nodes table into a dedicated action table,
which improves database interactions, while *also* improving the
overall capabilities for users and unlocking advanced features other
project contributors are interested in and need the same basic
foundational building block.

.. NOTE:: Bulk actions, such as applying a change across many nodes
   simultaneously, are a future capability enabled by this
   foundation. The design and API surface for bulk actions will be
   addressed in a separate specification.

Proposed change
===============

To achieve the goal of reducing our database load, simplifying our
periodic interactions, and having the needful foundation for other
desired capabilities in Ironic, we need to build a basic framework
to identify who, what, when, and how to resume execution on an
Item.

This requires intentional decomposition of larger workflows, and
that work of decomposition is expected to be able to occur
independently of this specification once landed.

At the simplest level this work consists of

* An action, or "deferred action" item state model which also
  serves as a basic locking model.

  * CREATED - The record was created in the database. These actions
    always transition to RUNNING.
  * RUNNING - A conductor has started work on this item, and the
    overall action may be moved to RESCHEDULE if the action needs
    to be re-triggered but perhaps with different arguments or
    state. If done and successful, actions move to COMPLETED. If
    the action fails, and can be retried, the action moves to
    PENDING_RETRY. If there are no available retries, the action
    moves to FAILED.
  * RESCHEDULE - An action has requested to be called again, for
    example if an action has updated itself to call a next step
    with arguments and to reuse the same high level action. This
    is to allow operations like "power state change requests" to
    go from "Please change power state" to "Are we sure the power
    state actually changed?". State moves to RUNNING once the
    conductor has started work again.
  * PENDING_RETRY - This work item failed and needs to be
    retried. Action moves back to RUNNING once picked back up.
  * FAILED - A final stable state indicating we cannot retry
    anymore and continues to fail.
  * COMPLETED - A final stable state indicating work has been
    completed.

* A new database table with the following fields:

  * An action Id column, serving as primary key, but not expecting
    to be utilized directly.
  * An action UUID
  * A node reference, to keep it lightweight, but have enough
    information to access a Node table record when needed,
    specifically to perform join queries for hash ring
    application.
  * A "state" field where a new simple state machine will
    represent the state of the action for the conductor. The
    state field will also be the *primary* guard from a conductor
    attempting to launch an action multiple times.
  * A "parent_action" field, for future use which allows for
    structural expansion in future bulk actions.
  * A future "start after" time.
  * A time added field.
  * A "call" field which relates to the method to be executed.
  * An "arguments" field which contains arguments in JSON form.
  * A "retry_remaining" integer field.
  * A ``created_by`` string field, nullable. When ``None``, the
    action was created by Ironic internally as part of normal
    operations. When populated, the value contains the creating
    project identifier, signaling the action originated from an
    external request. This field provides informational context
    for operators and future use.
  * A "result" field which is a string field. Results to this
    field are for convenience, but also expected to be written to
    a node's history.
  * This table is *expected* to have entries which exist for 30
    seconds to several minutes, depending on the exact flow and
    case in which it is being utilized. Some future use may cause
    entries to remain for longer, such as where a bulk action has
    been enumerated.

  Overall, this database is expected to be indexed on the columns
  which are queried against. Furthermore, there is no expectation
  that this table will be de-duplicated at any point in time,
  records should be relatively short-lived as well. Furthermore,
  updates to this table should utilize row level locks so that
  the underlying state field can be leveraged as a lock to head
  off potential conditions where multiple conductors may believe
  they are responsible for a node during a conductor rebalance.

.. NOTE::
   Field names in this specification are **NOT** final field
   names, and may be subject to change as the community evolves
   this feature.

* A new high level "action" object for each database row to be
  loaded in from.

* A "launcher" periodic task which queries the new database table
  to collect and fill the thread pool with new items up to a
  configurable maximum number of threads to be consumed. This
  periodic runs on a configurable interval. The launcher centers
  around the following conditions:

  * Does the node apply to this conductor with the state of the
    hash ring?
  * State is CREATED, RESCHEDULE, or PENDING_RETRY.
  * Actions are launched in order of the ``start_after`` time.
    Actions with a ``start_after`` value that has elapsed are
    prioritized over lazy actions (those with no ``start_after``).
    Lazy actions are picked up when thread pool capacity is
    available after timed actions.
  * In order to start an action, the underlying node lock must be
    able to be obtained. Ultimately locked nodes may be
    explicitly excluded from consideration as an optimization.
    If a lock is encountered at the last moment, the action
    state is reverted to its prior state and the invocation
    will be retried *without* negative impact to the action,
    i.e. retry counter being decremented.
  * The actual act of launching the action involves retrieving an
    entire Node object and spawning the conductor TaskManager
    object on a worker thread which then calls the requested
    method with the saved arguments from the new action database
    entry.
  * Upon Exception or Error, if the retry field is a positive
    integer, then this action is retried by the retry value
    being lowered and the state field being updated to
    PENDING_RETRY so the conductor picks the work up again.
    Furthermore, any methods leveraging this retry logic could
    request and set the required retry count if necessary.
  * When an action exhausts all retries and transitions to
    FAILED, the failure is recorded to the node's history using
    the existing ``node_history_record()`` helper with
    ``error=True``, which also populates ``last_error`` on the
    node. The event message includes the action that failed, the
    error encountered, and the ``request_id`` from the original
    request context so users can provide this identifier to
    operators for troubleshooting. The ``user`` parameter is
    populated from ``task.context.user_id`` to enable
    correlation with the originating request.
  * Upon successful exit, state machine field and result fields
    are updated, if applicable.

.. NOTE:: The exact database query pattern for the "launcher"
   is to be determined, in that it may not make sense to load
   the entire row into an intermediary object, but it would be
   helpful to utilize an object to house related key logic
   around the action's workflow.

* A helper to create the entry which triggers appropriate save()
  actions on the attached objects, and injects the record into
  the ``deferred_actions`` table.

* A periodic task which cleans up "older" items from the action
  table in order to prune it from growing forever. Actions in
  terminal states (COMPLETED, FAILED) are soft-deleted. The
  retention window is configurable with a default of 15 minutes
  after reaching a terminal state, and a maximum configurable
  ceiling of one day. Records will not be retained beyond this
  maximum regardless of configuration, and this limit will be
  explicitly documented for operators. The cleanup periodic
  purges soft-deleted records using batched deletes to avoid
  holding table locks for extended periods, consistent with the
  existing node history cleanup patterns. When the conductor's
  thread pool is relatively idle, the cleanup periodic may run
  more aggressively to take advantage of quiet periods such as
  overnight windows where fewer active deployments are running.
  Failed actions are recorded to node history before being pruned
  to ensure no failure information is lost.

.. NOTE::
   The exceptions-based signaling mechanism for retry and
   hold-off is now addressed by the action state model. The
   RESCHEDULE state handles cases where an action needs to be
   called again (e.g. to check on a BMC operation), and
   PENDING_RETRY handles failure cases with remaining retries.
   Implementation details for how specific interactions map to
   these states are left to the individual change proposals.

**Operator Visibility: Logging, Metrics, and Notifications**

This specification intentionally introduces no REST API surface.
Operator visibility into deferred actions is instead provided
through logging, metrics, and notifications, leveraging Ironic's
existing frameworks.

*Logging*

The launcher periodic provides two distinct log points per
iteration cycle at DEBUG level, consistent with how existing
periodic tasks such as ``_sync_power_states`` log their
operational summaries:

1. **Launch log**: At the start of each iteration, log the
   iteration number (a monotonic counter incrementing each time
   the action worker fires), the number of actions being launched
   in this cycle, and the percentage of conductor thread pool
   capacity being consumed. This allows operators to see that
   the conductor is actively launching work and to gauge
   utilization.

2. **Completion log**: At the end of each iteration, log the
   iteration number and counts of actions that completed, failed,
   or were rescheduled during this cycle. The matching iteration
   numbers between launch and completion logs aid debugging by
   allowing operators to correlate what was launched with what
   resulted.

The iteration counter is a generally useful metric for operators
because it provides a clear signal that the conductor is
functioning and making progress.

*Metrics*

Ironic's existing metrics framework (``ironic.common.metrics``)
is used to emit gauge and timer metrics, following established
patterns such as those in ``_sync_power_states``:

* ``@METRICS.timer()`` decorators on the launcher periodic and
  cleanup periodic for execution time tracking.
* ``METRICS.send_gauge()`` for action counts:

  * ``DeferredActionsLaunchedCount`` - actions launched this
    cycle.
  * ``DeferredActionsPendingCount`` - actions still pending.
  * ``DeferredActionsFailedCount`` - failed actions.
  * ``DeferredActionsRetryCount`` - actions pending retry.
  * ``DeferredActionsCompletedCount`` - completed actions.

*Notifications*

Versioned notifications are emitted on terminal state transitions
only, following Ironic's existing notification framework. A
``DeferredActionNotification`` with a corresponding
``DeferredActionPayload`` is defined following the pattern
established by ``NodeSetPowerStateNotification``. Notifications
are emitted when an action reaches COMPLETED or FAILED state.
Intermediate state transitions (RUNNING, RESCHEDULE,
PENDING_RETRY) do not emit notifications to avoid excessive
volume given the short-lived nature of most actions.

The notification payload includes the action UUID, node UUID,
terminal state, result, and ``created_by`` field. Notification
emission respects the configured notification level, allowing
operators to filter as needed.

The overall goal of this visibility strategy is conductor health
monitoring: helping operators answer "is my conductor working and
making progress?" rather than providing per-action introspection
into individual action internals.

With this overall flow, the launcher periodic consults the
executor status and picks up items from the list and leverages a
helper to facilitate the action record update in our table of
pending actions, and then handles the spawn into the ThreadPool.
The cleanup periodic task will separately clean up items and
address items which have been sitting in the RUNNING state for
too long where it will move the action to PENDING_RETRY based
upon the "retry" field on the action database table.

Overall, this basic model builds a foundation for decomposing
multi-step synchronous actions. Future specifications may build
upon this foundation for bulk actions, asynchronous updates from
other services, and other advanced capabilities that need this
same basic building block.

.. NOTE:: API surface for querying or managing deferred actions is
   explicitly deferred to a future specification. If operational
   experience demonstrates the need for direct API visibility, it
   will be designed with the benefit of real-world usage patterns.

Alternatives
------------

The clear alternative is to have periodics which can serve as the
delineation points, and then have enough logic to figure out what
to trigger, but this could quickly create a similar situation to
what we have now, a number of periodic runners which are threads
in the post-eventlet model as well.

The downside with that model is the need to hydrate and then
extract the data on a next step, and potentially concealing future
work to act upon.

Data model impact
-----------------

A new table, ``deferred_actions``:

* ``id`` - Integer, primary key. Internal identifier, not
  expected to be utilized directly.
* ``uuid`` - String(36). Unique identifier for the action.
* ``node_id`` - Integer, foreign key to ``nodes.id``. Links the
  action to a node, enabling join queries for hash ring
  application without duplicating node data.
* ``state`` - String(15). The action state machine value: one of
  CREATED, RUNNING, RESCHEDULE, PENDING_RETRY, FAILED, or
  COMPLETED. This field is the primary guard against a conductor
  launching an action multiple times. Indexed.
* ``parent_action`` - Integer, nullable, foreign key to
  ``deferred_actions.id``. For future use, allowing structural
  expansion for bulk actions.
* ``start_after`` - DateTime, nullable. A future time after which
  the action should be picked up. Actions with no value are
  treated as "lazy" items. Indexed.
* ``call`` - String(255). The method to be executed, in the form
  ``task.driver.interface.method``.
* ``arguments`` - Text (JSON). Additional context for the call.
  This field may contain operational context; it should not
  contain credentials. See `Security impact`_.
* ``retry_remaining`` - Integer. Number of retries remaining
  before the action moves to FAILED on error.
* ``created_by`` - String, nullable. When ``None``, the action
  was created internally by Ironic. When populated, contains the
  creating project identifier, indicating the action originated
  from an external request. This field provides operational
  context for distinguishing internal actions from those
  initiated by external projects.
* ``result`` - Text, nullable. Result information, also expected
  to be written to a node's history.
* ``created_at`` - DateTime, from base database schema.
* ``updated_at`` - DateTime, from base database schema.

Indexes: ``state``, ``start_after``, ``node_id``.

The table will be joined against the ``nodes`` table using
``node_id`` so that hash ring fields are available without
duplicating data. Row-level locking will be used on updates to
the ``state`` field to prevent race conditions where multiple
conductors believe they are responsible for a node during a
conductor rebalance.

A corresponding ``DeferredAction`` ironic object will be created
to house related key logic around the action's workflow.

The new table and any subsequent schema changes will be handled
through Alembic migrations.

This table is anticipated to have short-lived entries (30 seconds
to several minutes), though future bulk action use cases may
cause entries to remain longer.

.. NOTE:: While an arguments column is proposed, the original
   request context will not be preserved. Deferred actions are
   intended to allow us to avoid and remove "sleep" invocations
   in the code on individual threads which are waiting for
   actions like BMCs to reboot, or where we have gotten a
   notification from another service and need to resume a
   workflow which would have only had the conductor's internal
   RequestContext already.

State Machine Impact
--------------------

This specification introduces a new action state machine for
deferred actions. This state machine is independent of the
existing node provision state machine and has no impact on it.

Action states:

* ``CREATED`` - The action record has been created in the
  database.
* ``RUNNING`` - A conductor has picked up the action and is
  executing it.
* ``RESCHEDULE`` - The action has requested to be called again,
  potentially with different arguments or to check a subsequent
  step.
* ``PENDING_RETRY`` - The action failed but has retries remaining.
* ``FAILED`` - Terminal state. The action has exhausted all
  retries and cannot be completed.
* ``COMPLETED`` - Terminal state. The action finished
  successfully.

State transitions::

    CREATED ---------> RUNNING
    RUNNING ---------> COMPLETED     (success)
    RUNNING ---------> RESCHEDULE    (needs re-invocation)
    RUNNING ---------> PENDING_RETRY (failure, retries remain)
    RUNNING ---------> FAILED        (failure, no retries)
    RESCHEDULE ------> RUNNING       (picked up again)
    PENDING_RETRY ---> RUNNING       (picked up again)

.. NOTE:: Implementations should enforce a maximum reschedule
   count or timeout for the RESCHEDULE state to prevent infinite
   loops where an action repeatedly reschedules without making
   progress.

REST API impact
---------------

None. This specification intentionally introduces no API surface.
Operator visibility is provided through logging, metrics, and
notifications as described in the `Proposed change`_ section. A
future specification may introduce API endpoints if operational
experience demonstrates the need.

Client (CLI) impact
-------------------

"openstack baremetal" CLI
~~~~~~~~~~~~~~~~~~~~~~~~~

None.

"openstacksdk"
~~~~~~~~~~~~~~

None.

RPC API impact
--------------

None

Driver API impact
-----------------

None anticipated, however there is a distinct possibility some of
the methods may be evaluated to be split along the lines of the
Driver API interface, where feasible.

Nova driver impact
------------------

None

Ramdisk impact
--------------

None anticipated.

Security impact
---------------

The ``arguments`` JSON field may contain operational context
related to the action being executed. While this field should not
contain credentials, implementers should be mindful of what is
stored.

Other end user impact
---------------------

None. There is no user-facing API or CLI surface in this
specification.

Scalability impact
------------------

This overall idea should allow for better thread management for
the Ironic conductor process where ultimately Ironic should be
able to maintain a lower memory footprint for the conductor
service runtime.

The trade-off is slight increase in database activity, but as
time progresses we foresee the ability to begin to retool some of
the existing periodics which should ultimately also provide a
path to reduce the database load and related thundering herd
issues which can result in large deployments where the conductor
service is restarted.

Performance Impact
------------------

The anticipated performance impact is an ability to enable
greater deployment parallelism per-conductor, by removing
thread consumption where explicit sleep or wait actions are
required when working with hardware.

As mentioned in the prior section, we anticipate this impact to
require an additional periodic task, but we expect to be able to
remove other periodic tasks in the long run which is viewed as an
overall improvement.

This *may* allow locking to be freed up and ultimately also
remove some gaps which would normally exist during long running
locked tasks, but this is a likely positive.

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
  Julia "TheJulia" Kreger <juliaashleykreger@gmail.com>

Other contributors:
  Dmitry "dtantsur" Tantsur <dtantsur@protonmail.com>

Work Items
----------

* Create database table and objects.
* Create specialised queries and periodic task to query the data
  set.
* Create tooling to record a new future action.
* Implement launcher periodic logging (iteration counter, launch
  and completion counts, thread pool utilization percentage).
* Implement metrics gauge emission for action state counts.
* Implement versioned notifications for terminal state
  transitions (COMPLETED, FAILED).
* Implement failure propagation to node history and last_error,
  including request_id for operator troubleshooting.
* Implement cleanup periodic with soft delete, configurable
  retention (default 15 minutes, max 1 day), and batched purge.
* Create some basic unit tests around the creation and execution
  of actions.
* Fix the BMC firmware support sleep usage as a *first*
  user of this change.
* Tackle the excessively long sleeps in the BMC firmware update
  handling feature to utilize this path.

Dependencies
============

None

Testing
=======

This functionality is expected to be unit tested. As this is a
fundamental change in overall task flow, integration testing
coverage will naturally follow as existing workflows are
decomposed to use the deferred action model.

Upgrades and Backwards Compatibility
====================================

Because the mapping of a node and this action will be mapped by
the conductor hash ring, no upgrade or compatibility issues are
anticipated.

Furthermore, this may actually allow for some intermediate
actions to enable a minimal interruption for restarts/upgrades
for long running actions in the long term.

Documentation Impact
====================

Operator documentation will be augmented to describe the logging
and metrics emitted by the deferred action launcher, including
how to interpret iteration counters, action state counts, and
thread pool utilization percentages. Troubleshooting
documentation will cover how to correlate failed action
request_ids with originating user requests.

References
==========

* `IRC discussion on 2026-05-11
  <https://meetings.opendev.org/irclogs/%23openstack-ironic/
  %23openstack-ironic.2026-05-11.log.html
  #t2026-05-11T22:04:27>`_
  establishing consensus on scope, naming, and operator
  visibility approach.
