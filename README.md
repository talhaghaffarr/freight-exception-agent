# RelayOps

A freight agent operations platform: deterministic freight facts, database-enforced
idempotency, and observable non-action outcomes.

> **Sandbox.** Synthetic freight data. No external messages are ever sent.

## Walkthrough

[![RelayOps walkthrough — 90 seconds](docs/walkthrough-poster.png)](https://talhaghaffarr.github.io/freight-exception-agent/)

**▶ [Watch the 90-second walkthrough](https://talhaghaffarr.github.io/freight-exception-agent/)** — the late-pickup slice end to end: computed ETAs, the agent's decision ledger, honest handling of an unknown ETA, and two racing scanners resolving to one database goal. ([Live demo](https://relayops-demo.onrender.com/).)

Brokers lose money on pickups that quietly run late and on shipment questions that
sit in an inbox. The usual answer is to point a language model at the problem.
This is the other answer: the model is confined to interpreting unstructured
input, and every fact that reaches a customer is computed from recorded evidence
by code that can be read, tested, and blamed.

---

## What actually works today

This is a portfolio build in progress, so the distinction matters.

**Working, with tests:**

| Capability | Where |
|---|---|
| Freight schema with tenant-scoped composite foreign keys | [`migrations/002_freight_and_agents.sql`](backend/migrations/002_freight_and_agents.sql) |
| Deterministic fact engine — tracking freshness, ETA, lateness | [`relayops/facts/`](backend/src/relayops/facts) |
| Goal idempotency enforced by a unique constraint | `goals_idempotency_key` |
| Racing scanners converging on one goal | [`services/race_demo.py`](backend/src/relayops/services/race_demo.py) |
| Live operations board with computed facts | [`services/board.py`](backend/src/relayops/services/board.py) |
| Tenant-scoped HTTP API, fail-closed authorization | [`relayops/api/`](backend/src/relayops/api) |
| Role-scoped demo identities, health and readiness probes | [`relayops/health.py`](backend/src/relayops/health.py) |
| React console: board, map, evidence ledger | [`frontend/src/features/live/`](frontend/src/features/live) |

**Not built yet.** Named here rather than implied by a screenshot:

- Notification rendering, provider delivery, and action outcomes. The agent's
  decision currently stops at goal creation.
- The Celery scan/dispatch path. Celery and Beat are configured and run health
  heartbeats; the late-pickup workflow is not yet dispatched through them.
- The reactive inbound email agent, its safety gate ladder, and the narrow LLM
  extraction step. Specified in the PRD, not implemented.
- POD, ETA confirmation, and detention agents.

## The three demonstrations

### 1. A late pickup, computed rather than asserted

`LD-1048` runs Chicago → Dallas. At the seeded moment its truck is outside
Springfield, MO with a fresh position and 55 minutes of route remaining against a
pickup appointment 17 minutes out. The board reports **+38 minutes**, and the
console shows the evidence each step rests on.

No part of that number comes from a model.

### 2. Unknown is a valid answer

`LD-1051` has not reported a position in 42 minutes, past the tenant's maximum
tracking age. Its ETA is not estimated, not interpolated, and not left blank:

```json
{ "predicted_arrival": null, "reason": "tracking_stale" }
```

The console prints `ETA unknown · Tracking stale`, and the agent suppresses the
alert with a countable outcome rather than falling silent.

### 3. Two scanners, one goal

The demonstration this design exists for. **Race two scanners** opens two real
database connections, meets them at a barrier, and issues the same INSERT from
both:

```
scanner-A  →  INSERT             goal bd97601d  ·  2.98ms
scanner-B  →  UNIQUE CONFLICT    goal bd97601d  ·  5.96ms

Goals created         1
Opened events         1
Duplicates prevented  1
Enforced by           goals_idempotency_key
```

Both callers receive the same goal id. Correctness comes from the database, not
from a worker remembering what it did — so a Celery redelivery, a retry, or a
second scanner cannot double-send. See
[`tests/integration/test_racing_scanners.py`](backend/tests/integration/test_racing_scanners.py).

## Design commitments

- **Facts are computed; prose is generated.** Location, ETA, lateness, tenant
  identity, authorization, and state transitions are deterministic.
- **Unknown is a valid answer.** The system never invents a location or an ETA.
- **Every non-action is observable.** Stale tracking, below threshold, already
  notified, and tenant disabled are distinct, countable outcomes.
- **Idempotency lives in the schema.** Not in worker memory.
- **Tenant scope is a parameter, never a filter applied afterwards.** An
  unauthorized tenant and a non-existent tenant return the same 404, so tenant
  existence cannot be probed.
- **Naive datetimes are rejected at the boundary**, because a silent UTC
  assumption becomes a wrong time quoted to a customer.

## Running it

Requires Docker, Python 3.13 with [uv](https://docs.astral.sh/uv/), and Node 20+.

Start PostgreSQL, Valkey and Mailpit:

```bash
docker compose -f docker-compose.dev.yml up -d
```

Install dependencies, apply migrations, and seed the demo freight:

```bash
cd backend && uv sync && set -a && source .env.dev 2>/dev/null; set +a && uv run python -m relayops.cli migrate && uv run python -m relayops.cli seed
```

```bash
cd backend && DATABASE_URL='postgresql+psycopg://relayops:relayops@localhost:55433/relayops' SECRET_KEY=dev uv run flask --app relayops.app:create_app run --port 5055
```

```bash
cd frontend && npm install && VITE_API_ORIGIN=http://localhost:5055 npm run dev
```

Open the console, sign in as **Brokerage admin**, and go to **Live Operations**.

Appointments are stored as absolute timestamps, so a board left open drifts away
from the figures above. **Reset demo** re-anchors it.

## Tests

```bash
cd backend && uv run pytest -q && uv run ruff check .
```

```bash
cd frontend && npm test -- --run && npm run build
```

Persistence tests run against real PostgreSQL. SQLite is not an accepted
substitute: the behaviours under test are unique constraints, `ON CONFLICT`
semantics, and `FOR UPDATE SKIP LOCKED`, and a mock cannot violate a unique index.

## Documentation

- [Product requirements](docs/superpowers/specs/2026-08-30-freight-agent-operations-platform-prd.md)
- [Increment 1 plan](docs/superpowers/plans/2026-08-30-relayops-01-foundation.md)
- [Increment 2 plan](docs/superpowers/plans/2026-08-30-relayops-02-late-pickup-vertical-slice.md)

## Stack

Python 3.13, Flask, Celery, PostgreSQL, Valkey, SQLAlchemy Core with hand-written
SQL and hand-written migrations, React 19, TypeScript, TanStack Query, MapLibre GL
on OpenFreeMap tiles, Vitest, pytest.
