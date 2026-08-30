# RelayOps Increment 2: Late Pickup Vertical Slice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a production-shaped Late Pickup Alert from indexed load scanning through deterministic facts, durable goal state transitions, database idempotency, Celery execution, sandbox email, live operations UI, and a complete audit trace.

**Architecture:** Handwritten PostgreSQL migrations add freight, agent, fact, action, communication, and outcome records. A small agent runtime claims and advances goals through explicit transitions; the Late Pickup extension supplies eligibility, facts, policy, and email rendering. Celery Beat scans indexed candidates, workers use replay-safe tasks, and the React console consumes tenant-scoped APIs and SSE events.

**Tech Stack:** Increment 1 stack plus PostgreSQL `SKIP LOCKED`, Celery task retries, Jinja email templates, Mailpit SMTP, MapLibre GL, TanStack Query, Recharts

**Spec:** `docs/superpowers/specs/2026-08-30-freight-agent-operations-platform-prd.md`

## Global Constraints

- Goal and action idempotency are enforced by PostgreSQL unique constraints, not process memory.
- Celery tasks acknowledge after committed transitions and remain safe under redelivery.
- ETA, lateness, and tracking freshness are deterministic facts; no LLM participates.
- Unknown or stale tracking suppresses an unsafe ETA alert with a distinct outcome.
- Every terminal goal has a countable outcome and immutable fact snapshot.
- Map failure never blocks load, goal, or communication content.
- All tenant queries require explicit scope and receive cross-tenant tests.
- Every behavior follows an observed red-green-refactor cycle.

---

### Task 1: Freight and agent persistence schema

**Files:**
- Create: `backend/migrations/002_freight_and_agents.sql`
- Create: `backend/src/relayops/domain/freight.py`
- Create: `backend/src/relayops/domain/goals.py`
- Create: `backend/src/relayops/domain/communications.py`
- Create: `backend/src/relayops/repositories/loads.py`
- Create: `backend/src/relayops/repositories/goals.py`
- Create: `backend/tests/integration/test_freight_schema.py`
- Create: `backend/tests/integration/test_goal_constraints.py`

**Interfaces:**
- Produces: `Load`, `Stop`, `Leg`, `TrackingPoint`, `Goal`, `GoalEvent`, `FactSnapshot`, `Action`, `ActionAttempt`, `Outcome`
- Produces: `LoadRepository.get_by_reference(tenant_id: UUID, reference: str) -> Load | None`
- Produces: `GoalRepository.open_or_get(request: OpenGoalRequest) -> tuple[Goal, bool]`
- Consumes: Increment 1 database engine and migrations

- [ ] **Step 1: Write the failing tenant-reference uniqueness test**

```python
def test_load_reference_is_unique_only_inside_a_tenant(migrated_connection):
    atlas, meridian = insert_two_tenants(migrated_connection)
    insert_load(migrated_connection, atlas, "LD-1048")
    insert_load(migrated_connection, meridian, "LD-1048")
    with pytest.raises(IntegrityError):
        insert_load(migrated_connection, atlas, "LD-1048")
```

- [ ] **Step 2: Verify schema RED**

Run: `cd backend && uv run pytest tests/integration/test_freight_schema.py -q`  
Expected: FAIL because freight tables are absent.

- [ ] **Step 3: Add freight and tracking tables with indexes**

Create UUID-keyed loads, stops, legs, tracking points, and documents. Include tenant/reference uniqueness; load status, next appointment, latest tracking, stop sequence, and document-status indexes. Preserve source event ids for tracking deduplication.

- [ ] **Step 4: Verify freight schema GREEN**

Run: `cd backend && uv run pytest tests/integration/test_freight_schema.py -q`  
Expected: PASS.

- [ ] **Step 5: Write failing goal and action idempotency tests**

```python
def test_duplicate_goal_and_action_keys_are_rejected(migrated_connection, seeded_load):
    first_goal = insert_goal(migrated_connection, seeded_load, trigger="pickup-1-late-v1")
    with pytest.raises(IntegrityError):
        insert_goal(migrated_connection, seeded_load, trigger="pickup-1-late-v1")
    insert_action(migrated_connection, first_goal, fingerprint="email:am:late-v1")
    with pytest.raises(IntegrityError):
        insert_action(migrated_connection, first_goal, fingerprint="email:am:late-v1")
```

- [ ] **Step 6: Add agent, event, fact, action, outcome, and communication tables**

Implement the exact unique keys from the PRD, state/lease indexes, append-only event sequence uniqueness, fact content hash, and provider-id uniqueness. Add foreign keys that prevent cross-tenant linkage.

- [ ] **Step 7: Verify constraints and repositories GREEN**

Run: `cd backend && uv run pytest tests/integration/test_goal_constraints.py tests/integration/test_freight_schema.py -q`  
Expected: all tests pass.

- [ ] **Step 8: Commit Task 1**

```bash
git add backend/migrations/002_freight_and_agents.sql backend/src/relayops/domain backend/src/relayops/repositories backend/tests/integration
git commit -m "feat: persist freight goals and actions"
```

### Task 2: Deterministic tracking, ETA, and lateness facts

**Files:**
- Create: `backend/src/relayops/facts/__init__.py`
- Create: `backend/src/relayops/facts/tracking.py`
- Create: `backend/src/relayops/facts/eta.py`
- Create: `backend/src/relayops/facts/late_pickup.py`
- Create: `backend/tests/facts/test_tracking.py`
- Create: `backend/tests/facts/test_eta.py`
- Create: `backend/tests/facts/test_late_pickup.py`

**Interfaces:**
- Produces: `classify_tracking_freshness(point_time, now, max_age) -> Freshness`
- Produces: `compute_eta(route: RouteEstimate, position: TrackingPoint, now: datetime) -> EtaFact`
- Produces: `late_pickup_facts(load: LoadView, config: LatePickupConfig, now: datetime) -> LatePickupFacts`
- Consumes: freight domain value objects

- [ ] **Step 1: Write the failing freshness boundary tests**

```python
@pytest.mark.parametrize(("age_minutes", "expected"), [(4, "fresh"), (15, "aging"), (31, "stale")])
def test_tracking_freshness_has_explicit_boundaries(age_minutes, expected):
    assert classify_tracking_freshness(NOW - timedelta(minutes=age_minutes), NOW, timedelta(minutes=30)).value == expected
```

- [ ] **Step 2: Verify freshness RED, implement, and verify GREEN**

Run RED: `cd backend && uv run pytest tests/facts/test_tracking.py -q`  
Expected: missing function. Implement timezone-aware classification with a separate configurable aging band.  
Run GREEN: same command; expected PASS.

- [ ] **Step 3: Write failing ETA and late classification tests**

Use hand-derived fixture values: at 09:43, a 55-minute remaining route predicts 10:38; a 10:00 appointment is 38 minutes late. Add a stale-tracking case whose ETA is `None` with reason `tracking_stale`.

- [ ] **Step 4: Verify fact tests RED**

Run: `cd backend && uv run pytest tests/facts/test_eta.py tests/facts/test_late_pickup.py -q`  
Expected: missing fact functions.

- [ ] **Step 5: Implement immutable facts with evidence metadata**

Return typed facts containing value, classification, evidence timestamp, source, and reason when unavailable. Reject naive datetimes. Do not accept prose or model output.

- [ ] **Step 6: Verify fact tests GREEN and mutation cases**

Run: `cd backend && uv run pytest tests/facts -q`  
Expected: all boundary, stale, and missing-appointment cases pass.

- [ ] **Step 7: Commit Task 2**

```bash
git add backend/src/relayops/facts backend/tests/facts
git commit -m "feat: compute honest late-pickup facts"
```

### Task 3: Shared agent contracts and transactional state engine

**Files:**
- Create: `backend/src/relayops/agent_core/__init__.py`
- Create: `backend/src/relayops/agent_core/contracts.py`
- Create: `backend/src/relayops/agent_core/states.py`
- Create: `backend/src/relayops/agent_core/engine.py`
- Create: `backend/src/relayops/agent_core/outcomes.py`
- Create: `backend/tests/agent_core/test_state_engine.py`
- Create: `backend/tests/agent_core/test_outcomes.py`
- Create: `backend/tests/integration/test_goal_transitions.py`

**Interfaces:**
- Produces: `AgentType`, `TriggerContext`, `EligibilityDecision`, `TransitionDecision`, `ActionRequest`
- Produces: `AgentEngine.tick(goal_id: UUID, now: datetime) -> Goal`
- Produces: `GoalRepository.transition(goal_id, expected_version, transition) -> Goal`
- Consumes: Goal repository, fact provider registry, action repository

- [ ] **Step 1: Write failing legal-transition tests**

```python
def test_engine_rejects_transition_not_declared_by_agent(fake_agent, opened_goal):
    fake_agent.decide_result = TransitionDecision(next_state="succeeded")
    with pytest.raises(InvalidTransition, match="opened -> succeeded"):
        engine(fake_agent).tick(opened_goal.id, NOW)
```

- [ ] **Step 2: Verify engine RED**

Run: `cd backend && uv run pytest tests/agent_core/test_state_engine.py -q`  
Expected: contracts and engine are missing.

- [ ] **Step 3: Implement explicit state graph and optimistic goal versions**

Allow only PRD transitions. In one transaction, compare `state_version`, update state and next tick, and append a sequenced event. A stale version raises a retryable concurrency error.

- [ ] **Step 4: Verify state engine GREEN**

Run: `cd backend && uv run pytest tests/agent_core/test_state_engine.py tests/integration/test_goal_transitions.py -q`  
Expected: transition, stale-write, event-append, and terminal-state tests pass.

- [ ] **Step 5: Write failing terminal-outcome invariant test**

```python
def test_terminal_transition_requires_a_countable_outcome(opened_goal):
    with pytest.raises(MissingOutcome):
        transition_to(opened_goal, "suppressed", outcome=None)
```

- [ ] **Step 6: Implement outcome registry and verify GREEN**

Run RED before implementation and confirm missing invariant. Implement shared PRD reason enum plus type-specific extension namespace; persist outcome in the same transaction as terminal state. Run `uv run pytest tests/agent_core/test_outcomes.py -q`; expected PASS.

- [ ] **Step 7: Commit Task 3**

```bash
git add backend/src/relayops/agent_core backend/tests/agent_core backend/tests/integration/test_goal_transitions.py
git commit -m "feat: add durable agent state engine"
```

### Task 4: Late Pickup extension and indexed scanner

**Files:**
- Create: `backend/src/relayops/agents/__init__.py`
- Create: `backend/src/relayops/agents/late_pickup/__init__.py`
- Create: `backend/src/relayops/agents/late_pickup/config.py`
- Create: `backend/src/relayops/agents/late_pickup/agent.py`
- Create: `backend/src/relayops/agents/late_pickup/scanner.py`
- Create: `backend/src/relayops/sql/late_pickup_candidates.sql`
- Create: `backend/tests/agents/late_pickup/test_policy.py`
- Create: `backend/tests/integration/test_late_pickup_scanner.py`
- Create: `docs/sql-and-indexes.md`

**Interfaces:**
- Produces: `LatePickupConfig`
- Produces: `LatePickupAgent` implementing `AgentType`
- Produces: `scan_late_pickup_candidates(connection, tenant_id, now, limit) -> list[TriggerContext]`
- Produces trigger fingerprint `pickup:{stop_id}:appointment:{appointment_revision}:late:v1`

- [ ] **Step 1: Write failing table-driven policy tests**

Cover enabled/disabled, completed pickup, missing appointment, stale tracking, below threshold, above threshold, prior successful alert, and schedule override. Assert literal decision and outcome values for each case.

- [ ] **Step 2: Verify policy RED, implement minimum agent, verify GREEN**

Run RED: `cd backend && uv run pytest tests/agents/late_pickup/test_policy.py -q`  
Expected: missing agent. Implement eligibility and transitions using only supplied facts/config.  
Run GREEN: same command; expected all cases pass.

- [ ] **Step 3: Write failing scanner tenant and duplicate tests**

Seed eligible loads for both tenants, scan Atlas, and assert only Atlas ids return. Scan twice and call `open_or_get`; assert the second result has `created is False` and the same goal id.

- [ ] **Step 4: Verify scanner RED**

Run: `cd backend && uv run pytest tests/integration/test_late_pickup_scanner.py -q`  
Expected: candidate SQL is missing.

- [ ] **Step 5: Implement parameterized raw SQL and document its index plan**

Select active unpicked stops whose appointment and latest tracking meet coarse conditions. Keep exact policy in Python. Use tenant as the first predicate, bounded order, and limit. Add the literal `EXPLAIN` command and expected index names to `docs/sql-and-indexes.md`.

- [ ] **Step 6: Verify scanner GREEN and inspect query plan**

Run: `cd backend && uv run pytest tests/integration/test_late_pickup_scanner.py -q`  
Expected: tenant, limit, ordering, and deduplication tests pass.  
Run: `cd backend && uv run python -m relayops.cli explain late-pickup-candidates`  
Expected: index or bitmap index scan; no unbounded sequential scan on seeded 10,000-load fixture.

- [ ] **Step 7: Commit Task 4**

```bash
git add backend/src/relayops/agents backend/src/relayops/sql backend/tests/agents backend/tests/integration/test_late_pickup_scanner.py docs/sql-and-indexes.md
git commit -m "feat: scan and evaluate late pickups"
```

### Task 5: Celery scan, dispatch, leases, and concurrency proof

**Files:**
- Create: `backend/src/relayops/tasks/scanners.py`
- Create: `backend/src/relayops/tasks/dispatch.py`
- Create: `backend/src/relayops/agent_core/leases.py`
- Modify: `backend/src/relayops/celery_app.py`
- Create: `backend/tests/integration/test_racing_scanners.py`
- Create: `backend/tests/integration/test_dispatch_redelivery.py`
- Create: `backend/tests/integration/test_goal_leases.py`

**Interfaces:**
- Produces Celery tasks: `relayops.scan.late_pickup`, `relayops.dispatch.goal`, `relayops.recover.expired_leases`
- Produces: `claim_due_goals(connection, worker_id, now, limit) -> list[GoalLease]`
- Consumes: scanner, goal engine, Celery application

- [ ] **Step 1: Write the failing racing-scanner test**

Use two real database connections synchronized by a barrier to open the same trigger. Assert one goal row and one `opened` event remain, and both callers receive the same goal id.

- [ ] **Step 2: Verify concurrency RED**

Run: `cd backend && uv run pytest tests/integration/test_racing_scanners.py -q`  
Expected: the current repository raises an unhandled unique violation or creates duplicate observable events.

- [ ] **Step 3: Implement conflict-safe goal opening**

Use `INSERT ... ON CONFLICT DO NOTHING RETURNING id`; when conflict occurs, select the existing goal by the same complete unique key. Append the opened event only in the insertion path.

- [ ] **Step 4: Verify racing scanner GREEN**

Run: `cd backend && uv run pytest tests/integration/test_racing_scanners.py -q`  
Expected: repeated runs pass with exactly one goal.

- [ ] **Step 5: Write failing lease and redelivery tests**

Test `FOR UPDATE SKIP LOCKED` returns disjoint goal sets to two workers, expired leases are reclaimable, and dispatching an already advanced goal is a no-op with `already_completed` task result.

- [ ] **Step 6: Verify lease tests RED, implement tasks, then verify GREEN**

Run RED: `cd backend && uv run pytest tests/integration/test_goal_leases.py tests/integration/test_dispatch_redelivery.py -q`.  
Implement late acknowledgement, bounded retry, stable task args, leases, and version-aware ticks.  
Run GREEN: same command; expected PASS.

- [ ] **Step 7: Commit Task 5**

```bash
git add backend/src/relayops/tasks backend/src/relayops/agent_core/leases.py backend/src/relayops/celery_app.py backend/tests/integration
git commit -m "feat: dispatch replay-safe agent goals"
```

### Task 6: Idempotent sandbox email action

**Files:**
- Create: `backend/src/relayops/channels/__init__.py`
- Create: `backend/src/relayops/channels/contracts.py`
- Create: `backend/src/relayops/channels/email_smtp.py`
- Create: `backend/src/relayops/templates/email/late_pickup.html.j2`
- Create: `backend/src/relayops/templates/email/late_pickup.txt.j2`
- Create: `backend/src/relayops/agent_core/actions.py`
- Create: `backend/tests/channels/test_late_pickup_email.py`
- Create: `backend/tests/integration/test_action_idempotency.py`

**Interfaces:**
- Produces: `EmailMessage`, `DeliveryResult`, `EmailProvider`
- Produces: `ActionService.create_or_get(request: ActionRequest) -> tuple[Action, bool]`
- Produces: `ActionService.execute(action_id: UUID) -> Action`
- Consumes: LatePickupAgent action request and SMTP settings

- [ ] **Step 1: Write failing honest-template tests**

Assert an available ETA renders reference, appointment, predicted ETA, minutes late, and evidence time in both MIME alternatives. Assert unavailable ETA raises `UnsafeTemplateFacts` instead of rendering a blank or invented value.

- [ ] **Step 2: Verify template RED, implement rendering, verify GREEN**

Run RED: `cd backend && uv run pytest tests/channels/test_late_pickup_email.py -q`.  
Implement strict templates and sanitized subject lines.  
Run GREEN: same command; expected PASS.

- [ ] **Step 3: Write failing action race and uncertain-delivery tests**

Run two action creators against the same fingerprint and assert one action. Simulate provider timeout after acceptance; assert state `delivery_unknown` and no automatic second send without reconciliation evidence.

- [ ] **Step 4: Verify action tests RED, implement, then GREEN**

Run RED: `cd backend && uv run pytest tests/integration/test_action_idempotency.py -q`.  
Implement transactional action creation, stable provider idempotency header, attempts, and normalized outcomes.  
Run GREEN: same command; expected PASS.

- [ ] **Step 5: Verify Mailpit delivery in the Compose stack**

Run: `docker compose up -d postgres valkey mailpit web worker beat && cd backend && uv run python -m relayops.cli scenario late-pickup-success`  
Expected: one Mailpit message with matching HTML/text content and one succeeded action.

- [ ] **Step 6: Commit Task 6**

```bash
git add backend/src/relayops/channels backend/src/relayops/templates backend/src/relayops/agent_core/actions.py backend/tests/channels backend/tests/integration/test_action_idempotency.py
git commit -m "feat: send idempotent sandbox alerts"
```

### Task 7: Load, goal, trace, and live-event APIs

**Files:**
- Create: `backend/src/relayops/api/loads.py`
- Create: `backend/src/relayops/api/goals.py`
- Create: `backend/src/relayops/api/events.py`
- Create: `backend/src/relayops/serializers/loads.py`
- Create: `backend/src/relayops/serializers/goals.py`
- Create: `backend/tests/api/test_loads.py`
- Create: `backend/tests/api/test_goals.py`
- Create: `backend/tests/api/test_goal_trace.py`
- Create: `backend/tests/api/test_events.py`

**Interfaces:**
- Produces: PRD load, goals, goal trace, retry, resolve, route, and SSE endpoints
- Consumes: load/goal repositories, role/tenant context, event records

- [ ] **Step 1: Write failing tenant-scoped list and trace tests**

Seed same reference in two tenants. Assert Atlas list and trace contain only Atlas facts, recipient masking, actions, events, and outcomes. Assert reviewer retry returns 403; terminal retry returns `GOAL_NOT_RETRYABLE`.

- [ ] **Step 2: Verify API RED**

Run: `cd backend && uv run pytest tests/api/test_loads.py tests/api/test_goals.py tests/api/test_goal_trace.py -q`  
Expected: missing routes.

- [ ] **Step 3: Implement paginated resources and complete trace serializer**

Use cursor pagination, validated filters, versioned timestamps, and stable error codes. Trace order is event sequence; fact snapshots are immutable and payload secrets are redacted.

- [ ] **Step 4: Verify resource GREEN**

Run: same API test command.  
Expected: all authorization, pagination, and trace assertions pass.

- [ ] **Step 5: Write failing SSE replay test**

Create two goal events, connect with the first event id as `Last-Event-ID`, and assert only the second version notification arrives with tenant scope.

- [ ] **Step 6: Verify SSE RED, implement heartbeat/replay, then GREEN**

Run RED: `cd backend && uv run pytest tests/api/test_events.py -q`.  
Implement bounded event replay and heartbeat comments; stream identifiers and versions only.  
Run GREEN: same command; expected PASS.

- [ ] **Step 7: Commit Task 7**

```bash
git add backend/src/relayops/api backend/src/relayops/serializers backend/tests/api
git commit -m "feat: expose load and goal operations APIs"
```

### Task 8: Live Operations, Goals Queue, and Goal Trace UI

**Files:**
- Create: `frontend/src/features/live/LiveOperationsPage.tsx`
- Create: `frontend/src/features/live/LoadList.tsx`
- Create: `frontend/src/features/live/LoadMap.tsx`
- Create: `frontend/src/features/live/LoadContext.tsx`
- Create: `frontend/src/features/goals/GoalsPage.tsx`
- Create: `frontend/src/features/goals/GoalTracePage.tsx`
- Create: `frontend/src/features/goals/IdempotencyPanel.tsx`
- Create: `frontend/src/features/goals/TransitionTimeline.tsx`
- Create: `frontend/src/features/goals/GoalTracePage.test.tsx`
- Create: `frontend/src/features/live/LiveOperationsPage.test.tsx`
- Create: `frontend/src/features/goals/GoalsPage.test.tsx`
- Modify: `frontend/src/app/router.tsx`

**Interfaces:**
- Consumes: load, route, goals, trace, retry, resolve, and SSE endpoints
- Produces: routes `/operations`, `/goals`, `/goals/:goalId`

- [ ] **Step 1: Write failing load-to-goal continuity test**

Render a priority load with an active late-pickup goal, select it, and assert the milestones, tracking freshness, map fallback, next action, and trace link all reference `LD-1048`.

- [ ] **Step 2: Verify operations UI RED**

Run: `cd frontend && npm test -- LiveOperationsPage.test.tsx --run`  
Expected: missing page/components.

- [ ] **Step 3: Implement the operations split workspace**

Use priority list, one-third map, selected-load context, status segments, and active goals. Initialize MapLibre/OpenFreeMap lazily; render the same route geometry on an accessible SVG fallback if tiles or WebGL fail.

- [ ] **Step 4: Verify operations UI GREEN**

Run: same command.  
Expected: load context and fallback tests pass.

- [ ] **Step 5: Write failing goals and signature trace tests**

Assert URL-persisted filters, semantic states, transition order, fact evidence, policy configuration, idempotency conflict result, one action attempt, email preview, and reviewer-safe controls.

- [ ] **Step 6: Verify goals UI RED, implement pages, then GREEN**

Run RED: `cd frontend && npm test -- GoalsPage.test.tsx GoalTracePage.test.tsx --run`.  
Implement compact table and full-page trace; do not hide evidence in decorative drawers.  
Run GREEN: same command; expected PASS and axe checks clean.

- [ ] **Step 7: Verify frontend build and commit Task 8**

Run: `cd frontend && npm run build`  
Expected: exit 0.

```bash
git add frontend/src
git commit -m "feat: visualize live goals and decision traces"
```

### Task 9: Race scenario, seed expansion, and Increment 2 checkpoint

**Files:**
- Modify: `backend/src/relayops/seed.py`
- Create: `backend/src/relayops/simulator/__init__.py`
- Create: `backend/src/relayops/simulator/late_pickup.py`
- Create: `backend/tests/e2e/test_late_pickup_scenario.py`
- Create: `frontend/e2e/late-pickup.spec.ts`
- Create: `docs/agent-runtime.md`
- Create: `docs/interview-walkthrough.md`

**Interfaces:**
- Produces scenarios `late-pickup-success` and `racing-scanners`
- Consumes complete Increment 2 runtime and UI

- [ ] **Step 1: Write failing scenario invariant test**

Launch `racing-scanners` through the simulator service and assert two trigger attempts, one goal, one action, one Mailpit message, and one `acted_successfully` outcome.

- [ ] **Step 2: Verify scenario RED, implement deterministic scenario, then GREEN**

Run RED: `cd backend && uv run pytest tests/e2e/test_late_pickup_scenario.py -q`.  
Implement isolated scenario records and fixed virtual timestamps.  
Run GREEN: same command; expected PASS.

- [ ] **Step 3: Write and run the failing browser journey**

Playwright starts the scenario, opens the goal trace, verifies `38 min late`, database conflict evidence, and one email preview. Run `cd frontend && npx playwright test e2e/late-pickup.spec.ts`; expected RED until simulator UI/API wiring is complete, then GREEN.

- [ ] **Step 4: Document runtime and demo evidence**

Document state graph, acknowledgement timing, unique constraints, scanner SQL, lease recovery, honest facts, and a literal five-minute walkthrough for this vertical slice.

- [ ] **Step 5: Run the complete Increment 2 verification**

Run: `make lint && make test && make build && docker compose up --build -d && ./scripts/wait-for-stack.sh && cd frontend && npx playwright test e2e/late-pickup.spec.ts`  
Expected: lint, backend/frontend suites, builds, health checks, and browser journey all pass.

- [ ] **Step 6: Inspect logs, stop stack, and commit Task 9**

Run: `docker compose logs --no-color --tail=200 web worker beat | tee /tmp/relayops-increment2.log`  
Expected: no traceback, duplicate provider send, or migration error. Then run `docker compose down`.

```bash
git add backend/src/relayops/seed.py backend/src/relayops/simulator backend/tests/e2e frontend/e2e docs/agent-runtime.md docs/interview-walkthrough.md
git commit -m "feat: prove late-pickup correctness end to end"
```

## Increment 2 exit criteria

- A Beat scan opens and dispatches a Late Pickup goal end to end.
- Stale or unknown facts suppress unsafe communication with explicit outcomes.
- Racing scanners and action creators produce one goal, one action, and one email.
- Celery redelivery and expired leases are replay-safe.
- Live Operations and Goal Trace expose facts, policy, transitions, idempotency, attempts, and outcome.
- Backend, frontend, integration, concurrency, smoke, build, and browser checks pass before Increment 3 starts.
