"""Deterministic agent history: the catalog, seven days of goals, and outcomes.

The freight seed makes the board look live; this seed makes the *fleet* look
lived-in. Every goal here is a real row with a real event trace ending in a
recorded outcome from the PRD taxonomy, so the Goals queue, the agent catalog
counters, and the outcome analytics are all reads, never fixtures.

Like the other seeds it is an upsert keyed on stable ids and offsets from one
``now`` anchor: re-running it re-anchors the history in place, and it never
touches a goal it did not create (the racing-scanner demo's goals use a
different trigger fingerprint and survive untouched).
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import Connection, text

from relayops.domain.identity import stable_id
from relayops.seed_freight import ALL_LOADS, ATLAS, MERIDIAN, LoadSpec

# ---------------------------------------------------------------------------
# The agent catalog. One agent is live; the rest are specified, and the API
# says so instead of pretending.
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AgentSpec:
    agent_type: str
    version: str
    trigger_kind: str
    display_name: str
    description: str
    live: bool


AGENT_DEFINITIONS: tuple[AgentSpec, ...] = (
    AgentSpec(
        agent_type="late_pickup",
        version="1.0.0",
        trigger_kind="scanner",
        display_name="Late Pickup Alert",
        description=(
            "Scans active loads, computes a deterministic pickup ETA, and alerts "
            "the account manager once lateness clears the tenant threshold."
        ),
        live=True,
    ),
    AgentSpec(
        agent_type="reactive_status_email",
        version="0.1.0",
        trigger_kind="inbound",
        display_name="Reactive Status Email",
        description=(
            "Answers a verified customer's status email with facts the engine "
            "can prove, through a twelve-step safety gate ladder."
        ),
        live=False,
    ),
    AgentSpec(
        agent_type="pod_collection",
        version="0.1.0",
        trigger_kind="scanner",
        display_name="POD Collection",
        description=(
            "Chases the proof-of-delivery document after a completed delivery, "
            "driver SMS first, escalating on a tenant schedule."
        ),
        live=False,
    ),
    AgentSpec(
        agent_type="eta_confirmation",
        version="0.1.0",
        trigger_kind="scanner",
        display_name="ETA Confirmation",
        description=(
            "Confirms tomorrow's delivery appointments against computed ETAs "
            "and warns the receiver before the dock does."
        ),
        live=False,
    ),
    AgentSpec(
        agent_type="detention_risk",
        version="0.1.0",
        trigger_kind="scanner",
        display_name="Detention Risk",
        description=(
            "Watches dwell time at the dock and opens a detention claim window "
            "before the free time expires."
        ),
        live=False,
    ),
)

LIVE_AGENT_TYPES: frozenset[str] = frozenset(
    spec.agent_type for spec in AGENT_DEFINITIONS if spec.live
)

LATE_PICKUP_CONFIG: dict[str, Any] = {
    "late_threshold_minutes": 30,
    "max_tracking_age_minutes": 30,
    "schedule": "06:00-22:00 America/Chicago",
}

# ---------------------------------------------------------------------------
# The trailing-week outcome distribution. Names are the PRD 8.5 taxonomy,
# verbatim; counts are pinned by tests so the analytics screen cannot drift
# from what the seed wrote.
# ---------------------------------------------------------------------------

ATLAS_TERMINAL_OUTCOMES: tuple[tuple[str, int], ...] = (
    ("acted_successfully", 14),
    ("below_threshold", 8),
    ("tracking_stale", 6),
    ("already_notified", 4),
    ("outside_schedule", 3),
    ("operator_suppressed", 2),
    ("facts_incomplete", 2),
    ("expired_without_action", 1),
)

MERIDIAN_TERMINAL_OUTCOMES: tuple[tuple[str, int], ...] = (
    ("tenant_disabled", 7),
    ("below_threshold", 3),
)

#: Open Atlas work, one goal in each live intermediate state.
OPEN_GOAL_STATES: tuple[str, ...] = ("evaluating", "action_pending", "waiting", "needs_review")

_OUTCOME_STATE: dict[str, str] = {
    "acted_successfully": "succeeded",
    "below_threshold": "suppressed",
    "tracking_stale": "suppressed",
    "already_notified": "suppressed",
    "outside_schedule": "suppressed",
    "operator_suppressed": "suppressed",
    "facts_incomplete": "suppressed",
    "expired_without_action": "expired",
    "tenant_disabled": "suppressed",
}

_AM_EMAIL = "dana.reyes@atlasbrokerage.demo"


@dataclass(frozen=True, slots=True)
class _Step:
    event_type: str
    to_state: str
    detail: dict[str, Any]


def _facts_step(spec: LoadSpec, minutes_late: int | None) -> _Step:
    detail: dict[str, Any] = {
        "facts_version": 1,
        "tracking_age_minutes": spec.tracking_age,
        "appointment_revision": 3 if spec.reference == "LD-1048" else 1,
    }
    if minutes_late is not None:
        detail["minutes_late"] = minutes_late
    return _Step("collecting_facts", "collecting_facts", detail)


def _evaluating_step(minutes_late: int, eligible: bool) -> _Step:
    return _Step(
        "evaluating",
        "evaluating",
        {
            "minutes_late": minutes_late,
            "threshold_minutes": LATE_PICKUP_CONFIG["late_threshold_minutes"],
            "eligible": eligible,
        },
    )


def _story(outcome: str | None, state: str, spec: LoadSpec, index: int) -> list[_Step]:
    """The event sequence for one goal, after its opened event.

    Each list ends at ``state``; terminal stories end with the recorded
    outcome. Numbers are derived from ``index`` so the trace reads specific
    without being random.
    """
    late = 31 + (index * 7) % 25  # over the 30-minute threshold
    under = 9 + (index * 5) % 20  # under it
    threshold = LATE_PICKUP_CONFIG["late_threshold_minutes"]

    if outcome == "acted_successfully":
        return [
            _facts_step(spec, late),
            _evaluating_step(late, True),
            _Step(
                "action_enqueued",
                "action_pending",
                {"action_kind": "email", "recipient": _AM_EMAIL},
            ),
            _Step(
                "action_executing",
                "executing",
                {"provider": "smtp-sandbox", "template": "late_pickup_alert:v1"},
            ),
            _Step(
                "outcome_recorded",
                "succeeded",
                {
                    "outcome": outcome,
                    "action_kind": "email",
                    "recipient": _AM_EMAIL,
                    "provider_message_id": f"sandbox-{index:04d}",
                },
            ),
        ]
    if outcome == "below_threshold":
        return [
            _facts_step(spec, under),
            _evaluating_step(under, False),
            _Step(
                "outcome_recorded",
                "suppressed",
                {"outcome": outcome, "minutes_late": under, "threshold_minutes": threshold},
            ),
        ]
    if outcome == "tracking_stale":
        stale_age = 34 + (index * 3) % 40
        return [
            _facts_step(spec, None),
            _Step(
                "outcome_recorded",
                "suppressed",
                {
                    "outcome": outcome,
                    "tracking_age_minutes": stale_age,
                    "max_tracking_age_minutes": LATE_PICKUP_CONFIG["max_tracking_age_minutes"],
                },
            ),
        ]
    if outcome == "already_notified":
        return [
            _facts_step(spec, late),
            _evaluating_step(late, False),
            _Step(
                "outcome_recorded",
                "suppressed",
                {"outcome": outcome, "prior_alert": "this appointment window was already alerted"},
            ),
        ]
    if outcome == "outside_schedule":
        return [
            _evaluating_step(late, False),
            _Step(
                "outcome_recorded",
                "suppressed",
                {"outcome": outcome, "schedule": LATE_PICKUP_CONFIG["schedule"]},
            ),
        ]
    if outcome == "operator_suppressed":
        return [
            _facts_step(spec, late),
            _evaluating_step(late, True),
            _Step(
                "needs_review",
                "needs_review",
                {"reason": "facts_contradictory", "conflict": "driver ETA vs computed ETA"},
            ),
            _Step(
                "outcome_recorded",
                "suppressed",
                {"outcome": outcome, "operator": "admin@atlas.demo"},
            ),
        ]
    if outcome == "facts_incomplete":
        return [
            _facts_step(spec, None),
            _Step(
                "outcome_recorded",
                "suppressed",
                {"outcome": outcome, "missing": ["appointment_window"]},
            ),
        ]
    if outcome == "expired_without_action":
        return [
            _facts_step(spec, late),
            _evaluating_step(late, True),
            _Step("waiting", "waiting", {"waiting_for": "fresh tracking fix"}),
            _Step(
                "outcome_recorded",
                "expired",
                {"outcome": outcome, "deadline": "appointment window closed"},
            ),
        ]
    if outcome == "tenant_disabled":
        return [
            _Step(
                "outcome_recorded",
                "suppressed",
                {"outcome": outcome, "config": "late_pickup disabled for this tenant"},
            ),
        ]

    # Open goals: the story so far, ending in the live state.
    if state == "evaluating":
        return [_facts_step(spec, late), _evaluating_step(late, True)]
    if state == "action_pending":
        return [
            _facts_step(spec, late),
            _evaluating_step(late, True),
            _Step(
                "action_enqueued",
                "action_pending",
                {"action_kind": "email", "recipient": _AM_EMAIL},
            ),
        ]
    if state == "waiting":
        return [
            _facts_step(spec, None),
            _Step("waiting", "waiting", {"waiting_for": "fresh tracking fix"}),
        ]
    # needs_review
    return [
        _facts_step(spec, late),
        _evaluating_step(late, True),
        _Step(
            "needs_review",
            "needs_review",
            {"reason": "facts_contradictory", "conflict": "driver ETA vs computed ETA"},
        ),
    ]


@dataclass(frozen=True, slots=True)
class _GoalSeed:
    tenant_id: uuid.UUID
    spec: LoadSpec
    outcome: str | None
    state: str
    fingerprint_suffix: str
    opened_at: datetime
    next_tick_at: datetime | None
    index: int


def _atlas_seeds(moment: datetime) -> list[_GoalSeed]:
    filler = [
        spec
        for spec in ALL_LOADS
        if spec.tenant_id == ATLAS and spec.reference.startswith("LD-2")
    ]
    seeds: list[_GoalSeed] = []

    outcomes = [name for name, count in ATLAS_TERMINAL_OUTCOMES for _ in range(count)]
    for index, outcome in enumerate(outcomes):
        day = index % 7
        opened = moment - timedelta(days=day, minutes=5 + (index * 47) % 400)
        seeds.append(
            _GoalSeed(
                tenant_id=ATLAS,
                spec=filler[index],
                outcome=outcome,
                state=_OUTCOME_STATE[outcome],
                fingerprint_suffix=f"d{day}",
                opened_at=opened,
                next_tick_at=None,
                index=index,
            )
        )

    # Open work uses the tail of the filler set: refs 37-40 carry at most one
    # terminal goal each, on a day other than today, so the d0 episode below
    # never collides with it on the idempotency key.
    for offset, state in enumerate(OPEN_GOAL_STATES):
        index = len(outcomes) + offset
        seeds.append(
            _GoalSeed(
                tenant_id=ATLAS,
                spec=filler[37 + offset],
                outcome=None,
                state=state,
                fingerprint_suffix="d0",
                opened_at=moment - timedelta(minutes=12 + offset * 9),
                next_tick_at=moment + timedelta(minutes=5 + offset * 10),
                index=index,
            )
        )
    return seeds


def _meridian_seeds(moment: datetime) -> list[_GoalSeed]:
    spec = next(load for load in ALL_LOADS if load.tenant_id == MERIDIAN)
    outcomes = [name for name, count in MERIDIAN_TERMINAL_OUTCOMES for _ in range(count)]
    seeds: list[_GoalSeed] = []
    for episode, outcome in enumerate(outcomes):
        # One pickup stop exists in this tenant, so the suffix is the episode
        # number rather than the day; the day is derived from it.
        day = episode % 7
        seeds.append(
            _GoalSeed(
                tenant_id=MERIDIAN,
                spec=spec,
                outcome=outcome,
                state=_OUTCOME_STATE[outcome],
                fingerprint_suffix=f"d{episode}",
                opened_at=moment - timedelta(days=day, minutes=9 + (episode * 53) % 400),
                next_tick_at=None,
                index=episode,
            )
        )
    return seeds


# ---------------------------------------------------------------------------
# Writers
# ---------------------------------------------------------------------------


def _seed_catalog(connection: Connection) -> tuple[int, int]:
    definitions = 0
    for spec in AGENT_DEFINITIONS:
        connection.execute(
            text(
                """
                insert into agent_definitions
                    (id, agent_type, version, trigger_kind, display_name, description)
                values (:id, :agent_type, :version, :trigger_kind, :display_name, :description)
                on conflict (agent_type, version) do update set
                    trigger_kind = excluded.trigger_kind,
                    display_name = excluded.display_name,
                    description = excluded.description
                """
            ),
            {
                "id": stable_id("agent_definition", f"{spec.agent_type}:{spec.version}"),
                "agent_type": spec.agent_type,
                "version": spec.version,
                "trigger_kind": spec.trigger_kind,
                "display_name": spec.display_name,
                "description": spec.description,
            },
        )
        definitions += 1

    configs = 0
    for tenant_id in (ATLAS, MERIDIAN):
        for spec in AGENT_DEFINITIONS:
            enabled = tenant_id == ATLAS and spec.agent_type == "late_pickup"
            config = LATE_PICKUP_CONFIG if spec.agent_type == "late_pickup" else {}
            connection.execute(
                text(
                    """
                    insert into tenant_agent_configs (id, tenant_id, agent_type, enabled, config)
                    values (:id, :tenant_id, :agent_type, :enabled, cast(:config as jsonb))
                    on conflict (tenant_id, agent_type) do update set
                        enabled = excluded.enabled,
                        config = excluded.config,
                        updated_at = now()
                    """
                ),
                {
                    "id": stable_id("agent_config", f"{tenant_id}:{spec.agent_type}"),
                    "tenant_id": tenant_id,
                    "agent_type": spec.agent_type,
                    "enabled": enabled,
                    "config": json.dumps(config),
                },
            )
            configs += 1
    return definitions, configs


def _write_goal(connection: Connection, seed: _GoalSeed) -> tuple[uuid.UUID, int]:
    load_id = stable_id("load", f"{seed.tenant_id}:{seed.spec.reference}")
    stop_id = stable_id("stop", f"{load_id}:1")
    revision = 3 if seed.spec.reference == "LD-1048" else 1
    fingerprint = (
        f"pickup:{stop_id}:appointment:{revision}:late:v1:{seed.fingerprint_suffix}"
    )
    goal_id = stable_id("goal", f"{seed.tenant_id}:late_pickup:stop:{stop_id}:{fingerprint}")

    steps = _story(seed.outcome, seed.state, seed.spec, seed.index)
    closed_at = (
        seed.opened_at + timedelta(seconds=40 * len(steps)) if seed.outcome is not None else None
    )

    connection.execute(
        text(
            """
            insert into goals (
                id, tenant_id, agent_type, agent_version, subject_type, subject_id,
                trigger_fingerprint, load_id, state, state_version, next_tick_at,
                terminal_outcome, opened_at, updated_at, closed_at
            ) values (
                :id, :tenant_id, 'late_pickup', '1.0.0', 'stop', :subject_id,
                :trigger, :load_id, :state, :state_version, :next_tick_at,
                :terminal_outcome, :opened_at, now(), :closed_at
            )
            on conflict (tenant_id, agent_type, subject_type, subject_id, trigger_fingerprint)
            do update set
                state = excluded.state,
                state_version = excluded.state_version,
                next_tick_at = excluded.next_tick_at,
                terminal_outcome = excluded.terminal_outcome,
                opened_at = excluded.opened_at,
                closed_at = excluded.closed_at,
                updated_at = now()
            """
        ),
        {
            "id": goal_id,
            "tenant_id": seed.tenant_id,
            "subject_id": stop_id,
            "trigger": fingerprint,
            "load_id": load_id,
            "state": seed.state,
            "state_version": len(steps) + 1,
            "next_tick_at": seed.next_tick_at,
            "terminal_outcome": seed.outcome,
            "opened_at": seed.opened_at,
            "closed_at": closed_at,
        },
    )

    events: list[tuple[int, str, str | None, str, dict[str, Any], datetime]] = [
        (
            1,
            "opened",
            None,
            "opened",
            {"reference": seed.spec.reference, "source": "seed_history"},
            seed.opened_at,
        )
    ]
    from_state = "opened"
    for step_index, step in enumerate(steps, start=2):
        events.append(
            (
                step_index,
                step.event_type,
                from_state,
                step.to_state,
                step.detail,
                seed.opened_at + timedelta(seconds=40 * (step_index - 1)),
            )
        )
        from_state = step.to_state

    for sequence, event_type, from_st, to_state, detail, occurred_at in events:
        connection.execute(
            text(
                """
                insert into goal_events
                    (tenant_id, goal_id, sequence, event_type, from_state, to_state,
                     detail, occurred_at)
                values (:tenant_id, :goal_id, :sequence, :event_type, :from_state, :to_state,
                        cast(:detail as jsonb), :occurred_at)
                on conflict (goal_id, sequence) do update set
                    event_type = excluded.event_type,
                    from_state = excluded.from_state,
                    to_state = excluded.to_state,
                    detail = excluded.detail,
                    occurred_at = excluded.occurred_at
                """
            ),
            {
                "tenant_id": seed.tenant_id,
                "goal_id": goal_id,
                "sequence": sequence,
                "event_type": event_type,
                "from_state": from_st,
                "to_state": to_state,
                "detail": json.dumps(detail),
                "occurred_at": occurred_at,
            },
        )

    if seed.outcome is not None:
        # The outcomes table has no natural key, so idempotency is explicit:
        # replace only the row this seed wrote for this goal.
        connection.execute(
            text("delete from outcomes where goal_id = :goal_id"), {"goal_id": goal_id}
        )
        connection.execute(
            text(
                """
                insert into outcomes
                    (tenant_id, goal_id, agent_type, agent_version, reason, detail, occurred_at)
                values (:tenant_id, :goal_id, 'late_pickup', '1.0.0', :reason,
                        cast(:detail as jsonb), :occurred_at)
                """
            ),
            {
                "tenant_id": seed.tenant_id,
                "goal_id": goal_id,
                "reason": seed.outcome,
                "detail": json.dumps({"reference": seed.spec.reference}),
                "occurred_at": closed_at,
            },
        )

    return goal_id, len(events)


@dataclass(frozen=True, slots=True)
class HistorySeedSummary:
    agent_definitions: int
    tenant_configs: int
    goals: int
    goal_events: int
    outcomes: int


def seed_history(connection: Connection, now: datetime | None = None) -> HistorySeedSummary:
    """Upsert the demo agent history, anchored to ``now``."""
    moment = (now or datetime.now(UTC)).replace(microsecond=0)

    definitions, configs = _seed_catalog(connection)

    goal_ids: list[uuid.UUID] = []
    for seed in _atlas_seeds(moment) + _meridian_seeds(moment):
        goal_id, _ = _write_goal(connection, seed)
        goal_ids.append(goal_id)

    # Count what is actually present, not what we intended to write.
    goals, events, outcomes = connection.execute(
        text(
            """
            select
                (select count(*) from goals where id = any(:ids)),
                (select count(*) from goal_events where goal_id = any(:ids)),
                (select count(*) from outcomes where goal_id = any(:ids))
            """
        ),
        {"ids": goal_ids},
    ).one()
    return HistorySeedSummary(
        agent_definitions=definitions,
        tenant_configs=configs,
        goals=goals,
        goal_events=events,
        outcomes=outcomes,
    )
