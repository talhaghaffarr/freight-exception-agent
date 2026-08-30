# RelayOps Increment 1: Platform Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a one-command local platform with PostgreSQL, Valkey, Flask, Celery, React, seeded tenants, role-aware demo sessions, health reporting, and a polished operator shell.

**Architecture:** A Python 3.13 Flask API owns persistence and demo authentication; Celery worker and Beat processes import the same application package. PostgreSQL is the source of truth, Valkey is the broker, React/Vite is the operator UI, and Docker Compose coordinates the services. The increment establishes contracts consumed by every later agent plan without implementing agent behavior.

**Tech Stack:** Python 3.13, Flask 3, SQLAlchemy 2, psycopg 3, Pydantic 2, Celery 5, PostgreSQL 16, Valkey 8, React 19, TypeScript 5, Vite 7, Vitest, Testing Library, Playwright, Docker Compose

**Spec:** `docs/superpowers/specs/2026-08-30-freight-agent-operations-platform-prd.md`

## Global Constraints

- Python runtime is 3.13; PostgreSQL integration tests may not substitute SQLite.
- Database changes use numbered handwritten SQL migrations; Alembic is absent.
- Environment mode defaults to `sandbox`; external messages are impossible in this increment.
- Tenant-owned repository methods always require an explicit `tenant_id`.
- UI is desktop-first, keyboard accessible, and uses semantic status text in addition to color.
- Every behavior change follows an observed red-green-refactor cycle.
- No production secret or real customer data is committed.

---

### Task 1: Repository contracts and Python application factory

**Files:**
- Create: `.gitignore`
- Create: `.env.example`
- Create: `backend/pyproject.toml`
- Create: `backend/src/relayops/__init__.py`
- Create: `backend/src/relayops/config.py`
- Create: `backend/src/relayops/app.py`
- Create: `backend/src/relayops/errors.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_config.py`
- Create: `backend/tests/test_app_factory.py`

**Interfaces:**
- Produces: `Settings.from_env(environ: Mapping[str, str]) -> Settings`
- Produces: `create_app(settings: Settings | None = None) -> Flask`
- Produces: JSON error envelope `{data, meta, error}` with a request id
- Consumes: no earlier application code

- [ ] **Step 1: Add dependency and environment manifests**

Define a `relayops` package using `src` layout. Pin Flask, SQLAlchemy, psycopg, Pydantic settings, Celery, Redis client, structlog, pytest, pytest-cov, and Ruff to compatible minor ranges. Document `DATABASE_URL`, `CELERY_BROKER_URL`, `SECRET_KEY`, `ENVIRONMENT_MODE`, and `CORS_ORIGINS` in `.env.example`; use conspicuously non-secret local defaults.

- [ ] **Step 2: Write the failing settings tests**

```python
def test_settings_default_to_sandbox():
    settings = Settings.from_env({})
    assert settings.environment_mode == "sandbox"


def test_settings_reject_live_mode_without_explicit_acknowledgement():
    with pytest.raises(ValueError, match="ALLOW_LIVE_SENDS"):
        Settings.from_env({"ENVIRONMENT_MODE": "live"})
```

- [ ] **Step 3: Run the settings test and verify RED**

Run: `cd backend && uv run pytest tests/test_config.py -q`  
Expected: FAIL because `relayops.config.Settings` does not exist.

- [ ] **Step 4: Implement the minimum validated settings object**

```python
class Settings(BaseModel):
    database_url: str = "postgresql+psycopg://relayops:relayops@postgres:5432/relayops"
    celery_broker_url: str = "redis://valkey:6379/0"
    secret_key: SecretStr = SecretStr("local-demo-only")
    environment_mode: Literal["sandbox", "allowlist", "live"] = "sandbox"
    allow_live_sends: bool = False

    @model_validator(mode="after")
    def protect_live_mode(self) -> "Settings":
        if self.environment_mode == "live" and not self.allow_live_sends:
            raise ValueError("ALLOW_LIVE_SENDS=true is required for live mode")
        return self
```

- [ ] **Step 5: Verify settings GREEN**

Run: `cd backend && uv run pytest tests/test_config.py -q`  
Expected: PASS with 2 tests.

- [ ] **Step 6: Write the failing application-factory contract test**

```python
def test_application_errors_use_versioned_envelope(app):
    response = app.test_client().get("/api/v1/does-not-exist")
    body = response.get_json()
    assert response.status_code == 404
    assert body["data"] is None
    assert body["error"]["code"] == "NOT_FOUND"
    assert body["meta"]["request_id"].startswith("req_")
```

- [ ] **Step 7: Run the application test and verify RED**

Run: `cd backend && uv run pytest tests/test_app_factory.py -q`  
Expected: FAIL because `create_app` and its error handler do not exist.

- [ ] **Step 8: Implement the application factory and request envelope**

Register request-id creation, JSON errors, `/api/v1` blueprint wiring, strict JSON configuration, and CORS from validated settings. Keep database and Celery initialization behind extension functions so tests can create the app without contacting external services.

- [ ] **Step 9: Verify application GREEN and lint**

Run: `cd backend && uv run pytest tests/test_config.py tests/test_app_factory.py -q && uv run ruff check src tests`  
Expected: 3 tests pass and Ruff exits 0.

- [ ] **Step 10: Commit Task 1**

```bash
git add .gitignore .env.example backend
git commit -m "feat: establish RelayOps application contracts"
```

### Task 2: Handwritten migration runner and foundational schema

**Files:**
- Create: `backend/migrations/001_foundation.sql`
- Create: `backend/src/relayops/db.py`
- Create: `backend/src/relayops/migrations.py`
- Create: `backend/src/relayops/cli.py`
- Create: `backend/tests/integration/test_migrations.py`
- Create: `backend/tests/integration/test_tenant_schema.py`

**Interfaces:**
- Consumes: `Settings.database_url`
- Produces: `run_migrations(engine: Engine, directory: Path) -> list[str]`
- Produces: `check_migrations(engine: Engine, directory: Path) -> MigrationStatus`
- Produces tables: `tenants`, `users`, `tenant_memberships`, `audit_events`, `schema_migrations`

- [ ] **Step 1: Write a failing migration idempotency test**

```python
def test_migrations_apply_once(postgres_engine, migration_directory):
    first = run_migrations(postgres_engine, migration_directory)
    second = run_migrations(postgres_engine, migration_directory)
    assert first == ["001_foundation"]
    assert second == []
```

- [ ] **Step 2: Verify migration RED**

Run: `cd backend && uv run pytest tests/integration/test_migrations.py -q`  
Expected: FAIL because the migration runner is missing.

- [ ] **Step 3: Implement checksum-aware transactional migrations**

Create `schema_migrations(version text primary key, checksum text not null, applied_at timestamptz not null default now())`. Parse files matching `NNN_name.sql`, hash their bytes, take a PostgreSQL advisory lock, apply each unapplied file transactionally, and reject a checksum change for an applied version.

- [ ] **Step 4: Add the foundational tenant and audit SQL**

The migration creates UUID-keyed tenants and users, membership roles constrained to `platform_operator`, `brokerage_admin`, `account_manager`, or `reviewer`, and append-only audit-event columns. Add unique tenant slug, unique user email, unique membership, and tenant/time audit indexes.

- [ ] **Step 5: Write the failing tenant uniqueness and membership test**

```python
def test_membership_is_unique_per_user_and_tenant(migrated_connection):
    tenant_id, user_id = insert_tenant_and_user(migrated_connection)
    insert_membership(migrated_connection, tenant_id, user_id, "reviewer")
    with pytest.raises(IntegrityError):
        insert_membership(migrated_connection, tenant_id, user_id, "account_manager")
```

- [ ] **Step 6: Verify RED against the incomplete schema, then GREEN after SQL**

Run before finishing SQL: `cd backend && uv run pytest tests/integration/test_tenant_schema.py -q`  
Expected RED: duplicate membership is accepted or required table is absent.  
Run after SQL: same command.  
Expected GREEN: duplicate membership raises `IntegrityError`.

- [ ] **Step 7: Verify all migration tests**

Run: `cd backend && uv run pytest tests/integration/test_migrations.py tests/integration/test_tenant_schema.py -q`  
Expected: all tests pass against PostgreSQL.

- [ ] **Step 8: Commit Task 2**

```bash
git add backend/migrations backend/src/relayops/db.py backend/src/relayops/migrations.py backend/src/relayops/cli.py backend/tests/integration
git commit -m "feat: add handwritten foundation migrations"
```

### Task 3: Deterministic seed data and demo sessions

**Files:**
- Create: `backend/src/relayops/domain/__init__.py`
- Create: `backend/src/relayops/domain/identity.py`
- Create: `backend/src/relayops/repositories/identity.py`
- Create: `backend/src/relayops/seed.py`
- Create: `backend/src/relayops/api/auth.py`
- Create: `backend/src/relayops/api/tenants.py`
- Create: `backend/tests/test_demo_auth.py`
- Create: `backend/tests/integration/test_seed.py`
- Create: `backend/tests/api/test_tenant_scope.py`

**Interfaces:**
- Produces: `seed_demo_data(connection, seed: int = 1048) -> SeedSummary`
- Produces: `POST /api/v1/auth/demo-session` and `GET /api/v1/auth/me`
- Produces: `require_role(*roles)` and `TenantContext`
- Produces seeded slugs `atlas-brokerage` and `meridian-freight`

- [ ] **Step 1: Write the failing deterministic-seed test**

```python
def test_seed_is_repeatable_and_idempotent(migrated_connection):
    first = seed_demo_data(migrated_connection, seed=1048)
    second = seed_demo_data(migrated_connection, seed=1048)
    assert first.tenants == 2
    assert second == first
```

- [ ] **Step 2: Verify seed RED**

Run: `cd backend && uv run pytest tests/integration/test_seed.py -q`  
Expected: FAIL because `seed_demo_data` is absent.

- [ ] **Step 3: Implement identity repositories and idempotent seed**

Insert two tenants and four demo users with stable UUIDv5 identifiers. Upsert only the known demo rows; never truncate application tables. Return literal counts from rows present after seeding.

- [ ] **Step 4: Verify seed GREEN**

Run: `cd backend && uv run pytest tests/integration/test_seed.py -q`  
Expected: PASS.

- [ ] **Step 5: Write failing session and tenant-isolation API tests**

```python
def test_account_manager_cannot_switch_to_another_tenant(client, atlas_manager):
    login_as(client, atlas_manager)
    response = client.get("/api/v1/tenants/meridian-freight")
    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "NOT_FOUND"
```

- [ ] **Step 6: Verify auth RED**

Run: `cd backend && uv run pytest tests/test_demo_auth.py tests/api/test_tenant_scope.py -q`  
Expected: FAIL because session routes and role enforcement are missing.

- [ ] **Step 7: Implement signed demo sessions and fail-closed tenant context**

Issue a signed HTTP-only same-site session cookie only for seeded users. Resolve every tenant route through membership; return the same 404 for absent and unauthorized tenant ids. Platform operators may request `all` explicitly.

- [ ] **Step 8: Verify auth GREEN**

Run: `cd backend && uv run pytest tests/test_demo_auth.py tests/api/test_tenant_scope.py -q`  
Expected: all tests pass.

- [ ] **Step 9: Commit Task 3**

```bash
git add backend/src/relayops/domain backend/src/relayops/repositories backend/src/relayops/seed.py backend/src/relayops/api backend/tests
git commit -m "feat: seed role-scoped demo identities"
```

### Task 4: Celery application and component health

**Files:**
- Create: `backend/src/relayops/celery_app.py`
- Create: `backend/src/relayops/tasks/health.py`
- Create: `backend/src/relayops/health.py`
- Create: `backend/src/relayops/api/health.py`
- Create: `backend/tests/test_health.py`
- Create: `backend/tests/integration/test_celery_health.py`

**Interfaces:**
- Produces: `celery_app`
- Produces: `collect_health(probes: Sequence[HealthProbe]) -> HealthReport`
- Produces: `GET /api/v1/system/health`
- Produces: `relayops.health.ping` task

- [ ] **Step 1: Write the failing health-semantics test**

```python
def test_optional_provider_failure_degrades_but_does_not_fail_readiness():
    report = collect_health([
        StaticProbe("database", "healthy", required=True),
        StaticProbe("voice", "unhealthy", required=False),
    ])
    assert report.status == "degraded"
    assert report.ready is True
```

- [ ] **Step 2: Verify health RED**

Run: `cd backend && uv run pytest tests/test_health.py -q`  
Expected: FAIL because health contracts do not exist.

- [ ] **Step 3: Implement health aggregation and API**

Support `healthy`, `degraded`, `unhealthy`, and `unknown`. Required database or migration failures set readiness false; optional provider failures set degraded. Include last checked timestamp and latency for each probe.

- [ ] **Step 4: Verify health GREEN**

Run: `cd backend && uv run pytest tests/test_health.py -q`  
Expected: PASS.

- [ ] **Step 5: Write failing real-worker ping test**

Create an integration test that sends `relayops.health.ping` through the configured test broker and asserts the task returns its task id and worker timestamp. Do not assert a mock invocation.

- [ ] **Step 6: Verify worker RED, implement task, then verify GREEN**

Run RED: `cd backend && uv run pytest tests/integration/test_celery_health.py -q`  
Expected: task is unregistered.  
Implement the Celery factory, routing, JSON serialization, late acknowledgement defaults, and ping task.  
Run GREEN: same command.  
Expected: PASS with the integration worker fixture.

- [ ] **Step 7: Commit Task 4**

```bash
git add backend/src/relayops/celery_app.py backend/src/relayops/tasks backend/src/relayops/health.py backend/src/relayops/api/health.py backend/tests
git commit -m "feat: expose worker and component health"
```

### Task 5: Docker Compose development environment

**Files:**
- Create: `compose.yaml`
- Create: `backend/Dockerfile`
- Create: `backend/docker-entrypoint.sh`
- Create: `frontend/Dockerfile`
- Create: `infra/postgres/healthcheck.sql`
- Create: `scripts/wait-for-stack.sh`
- Create: `tests/smoke/test_compose.py`

**Interfaces:**
- Produces services: `postgres`, `valkey`, `web`, `worker`, `beat`, `frontend`, `mailpit`
- Produces health endpoints on ports 8000, 5173, and 8025
- Consumes: migration CLI, seed CLI, Flask and Celery factories

- [ ] **Step 1: Write a failing black-box stack smoke test**

```python
def test_stack_reports_required_components_healthy(http_client):
    response = http_client.get("http://localhost:8000/api/v1/system/health")
    assert response.status_code == 200
    components = response.json()["data"]["components"]
    assert {"api", "database", "valkey", "worker", "beat"} <= set(components)
```

- [ ] **Step 2: Verify smoke RED**

Run: `uv run pytest tests/smoke/test_compose.py -q`  
Expected: FAIL with connection refused because the stack is not defined.

- [ ] **Step 3: Add non-root images, health checks, and startup ordering**

The web entrypoint waits for PostgreSQL, applies migrations, seeds demo data, then starts Gunicorn. Worker and Beat wait for the migration readiness record. Compose health checks use real HTTP, PostgreSQL, and Valkey commands. Mailpit exposes SMTP 1025 and UI 8025.

- [ ] **Step 4: Start the stack and verify smoke GREEN**

Run: `docker compose up --build -d && uv run pytest tests/smoke/test_compose.py -q`  
Expected: PASS; `docker compose ps` shows every required service healthy.

- [ ] **Step 5: Verify clean shutdown and commit Task 5**

Run: `docker compose down`  
Expected: exit 0 without orphaned project containers.

```bash
git add compose.yaml backend/Dockerfile backend/docker-entrypoint.sh frontend/Dockerfile infra scripts tests/smoke
git commit -m "build: add one-command local platform"
```

### Task 6: React design system and role-aware application shell

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/vitest.config.ts`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/app/App.tsx`
- Create: `frontend/src/app/router.tsx`
- Create: `frontend/src/app/api.ts`
- Create: `frontend/src/app/session.tsx`
- Create: `frontend/src/components/AppShell.tsx`
- Create: `frontend/src/components/StatusBadge.tsx`
- Create: `frontend/src/styles/tokens.css`
- Create: `frontend/src/styles/global.css`
- Create: `frontend/src/test/setup.ts`
- Create: `frontend/src/components/AppShell.test.tsx`
- Create: `frontend/src/components/StatusBadge.test.tsx`

**Interfaces:**
- Consumes: `GET /api/v1/auth/me`, `POST /api/v1/auth/demo-session`
- Produces: `AppShell`, `StatusBadge`, `useSession`, and application route slots
- Produces navigation ids: overview, live-operations, goals, inbox, agents, communications, analytics, system, simulator

- [ ] **Step 1: Install the frontend test/build toolchain**

Use React, React Router, TanStack Query, Lucide React, MapLibre GL, Recharts, Zod, Vitest, Testing Library, user-event, axe-core, and Playwright. Commit the generated lockfile with the task.

- [ ] **Step 2: Write the failing shell accessibility test**

```tsx
it("exposes role-aware primary navigation and environment status", async () => {
  renderApp({ role: "reviewer", environmentMode: "sandbox" });
  expect(screen.getByRole("navigation", { name: /primary/i })).toBeVisible();
  expect(screen.getByText("Sandbox")).toBeVisible();
  expect(screen.queryByRole("button", { name: /pause all agents/i })).not.toBeInTheDocument();
  expect(await axe(document.body)).toHaveNoViolations();
});
```

- [ ] **Step 3: Verify shell RED**

Run: `cd frontend && npm test -- AppShell.test.tsx --run`  
Expected: FAIL because the shell does not exist.

- [ ] **Step 4: Implement tokens, shell, responsive navigation, and session boundary**

Use graphite navigation, off-white workspace, semantic teal/amber/red/blue/purple tokens, tabular numerals, a 64 px rail, compact header, tenant switcher, search, environment badge, component health, and route outlet. Hide unauthorized controls; do not merely disable them.

- [ ] **Step 5: Verify shell GREEN**

Run: `cd frontend && npm test -- AppShell.test.tsx StatusBadge.test.tsx --run`  
Expected: component tests and axe checks pass.

- [ ] **Step 6: Verify production build**

Run: `cd frontend && npm run build`  
Expected: TypeScript and Vite exit 0 with assets in `frontend/dist`.

- [ ] **Step 7: Commit Task 6**

```bash
git add frontend
git commit -m "feat: create RelayOps operator shell"
```

### Task 7: Fleet overview and system-health foundation screens

**Files:**
- Create: `backend/src/relayops/api/dashboard.py`
- Create: `backend/src/relayops/repositories/dashboard.py`
- Create: `backend/tests/api/test_dashboard.py`
- Create: `frontend/src/features/overview/OverviewPage.tsx`
- Create: `frontend/src/features/overview/OverviewPage.test.tsx`
- Create: `frontend/src/features/system/SystemHealthPage.tsx`
- Create: `frontend/src/features/system/SystemHealthPage.test.tsx`
- Modify: `frontend/src/app/router.tsx`

**Interfaces:**
- Produces: `GET /api/v1/dashboard` with `agents`, `goals`, `communications`, `value`, and `recent_activity` empty-but-typed collections
- Consumes: `/api/v1/system/health`
- Produces: overview and system routes ready for later increments to fill

- [ ] **Step 1: Write the failing typed-empty-dashboard API test**

```python
def test_dashboard_has_stable_sections_before_agents_exist(authenticated_client):
    body = authenticated_client.get("/api/v1/dashboard").get_json()["data"]
    assert body == {
        "agents": [],
        "goals": {"opened": 0, "waiting": 0, "needs_review": 0, "failed": 0},
        "communications": {"email": 0, "sms": 0, "voice": 0},
        "value": {"operator_minutes_saved": 0},
        "recent_activity": [],
    }
```

- [ ] **Step 2: Verify API RED, implement query, then verify GREEN**

Run RED: `cd backend && uv run pytest tests/api/test_dashboard.py -q`  
Expected: 404 for missing dashboard route.  
Implement tenant-scoped stable response and platform-operator aggregation.  
Run GREEN: same command.  
Expected: PASS.

- [ ] **Step 3: Write failing overview and health screen tests**

Test that zero-state cards explain how to start a simulation, health rows show text status and last-check time, and a reviewer sees no mutation buttons. Run tests and confirm failure because pages do not exist.

- [ ] **Step 4: Implement both pages with operational empty states**

Build dense cards and tables without fake metrics. Link the empty overview to Simulator; link degraded health rows to a component detail drawer placeholder route owned by Increment 5.

- [ ] **Step 5: Verify frontend GREEN and build**

Run: `cd frontend && npm test -- OverviewPage.test.tsx SystemHealthPage.test.tsx --run && npm run build`  
Expected: tests and build pass.

- [ ] **Step 6: Commit Task 7**

```bash
git add backend/src/relayops/api/dashboard.py backend/src/relayops/repositories/dashboard.py backend/tests/api/test_dashboard.py frontend/src
git commit -m "feat: add operational overview foundation"
```

### Task 8: Foundation CI, documentation, and checkpoint verification

**Files:**
- Create: `.github/workflows/ci.yml`
- Create: `README.md`
- Create: `docs/architecture.md`
- Create: `docs/testing.md`
- Create: `Makefile`

**Interfaces:**
- Produces commands: `make setup`, `make test`, `make lint`, `make build`, `make up`, `make down`
- Consumes all Increment 1 tests and builds

- [ ] **Step 1: Add documented commands and CI jobs**

CI runs backend unit tests, PostgreSQL integration tests, Ruff, frontend tests, TypeScript build, Docker image build, and migration checksum validation. README explains demo users, ports, sandbox mode, and the boundary between completed foundation and later increments.

- [ ] **Step 2: Run the complete foundation verification**

Run: `make lint && make test && make build`  
Expected: every backend and frontend test passes; lint and both builds exit 0.

- [ ] **Step 3: Verify the one-command clean start**

Run: `docker compose down -v && docker compose up --build -d && ./scripts/wait-for-stack.sh && uv run pytest tests/smoke/test_compose.py -q`  
Expected: clean volumes migrate and seed, all services become healthy, and smoke tests pass.

- [ ] **Step 4: Capture the checkpoint and stop the stack**

Run: `docker compose ps && docker compose logs --no-color --tail=100 web worker beat && docker compose down`  
Expected: no traceback or migration error; services stop cleanly.

- [ ] **Step 5: Commit Task 8**

```bash
git add .github README.md docs/architecture.md docs/testing.md Makefile
git commit -m "docs: document and verify RelayOps foundation"
```

## Increment 1 exit criteria

- A clean checkout starts with `docker compose up --build`.
- PostgreSQL migrations and seed data are deterministic and idempotent.
- Demo roles cannot cross tenant boundaries.
- API, worker, Beat, PostgreSQL, and Valkey health are visible.
- Operator shell, Overview, and System Health are keyboard-accessible and production-built.
- Full Increment 1 test, lint, build, and smoke commands pass before Increment 2 starts.
