-- 002_freight_and_agents
--
-- Freight (loads, stops, legs, tracking, documents) plus the agent runtime
-- (goals, events, fact snapshots, actions, attempts, outcomes) and the agent
-- catalog and tenant configuration.
--
-- Idempotency lives here, in constraints, not in worker code: a duplicate
-- scanner result, a Celery redelivery, or two racing workers all collapse onto
-- one row because the database refuses the second insert.
--
-- Composite foreign keys ((tenant_id, id) -> (tenant_id, id)) are used
-- deliberately so a child row can never point at a parent in another tenant.
--
-- Rollback strategy: additive. Drop in reverse dependency order:
--   drop table outcomes, action_attempts, actions, fact_snapshots, goal_events,
--     goals, documents, tracking_points, legs, stops, loads,
--     tenant_agent_configs, agent_definitions;
--   drop domain load_status, stop_type, goal_state, action_state.

-- ---------------------------------------------------------------------------
-- Constrained text domains (not enums: adding a value must not lock tables).
-- ---------------------------------------------------------------------------
create domain load_status as text
    check (value in ('active', 'delivered', 'cancelled', 'draft'));

create domain stop_type as text
    check (value in ('pickup', 'delivery'));

create domain goal_state as text
    check (value in (
        'opened', 'collecting_facts', 'evaluating', 'action_pending',
        'executing', 'waiting', 'needs_review', 'succeeded', 'suppressed',
        'failed', 'expired'
    ));

create domain action_state as text
    check (value in (
        'pending', 'executing', 'succeeded', 'delivery_unknown',
        'retry_scheduled', 'failed'
    ));

-- ---------------------------------------------------------------------------
-- Freight
-- ---------------------------------------------------------------------------
create table loads (
    id                    uuid        primary key default gen_random_uuid(),
    tenant_id             uuid        not null references tenants (id) on delete cascade,
    reference             text        not null,
    status                load_status not null default 'active',
    customer_name         text        not null,
    account_manager_email text        not null,
    account_manager_name  text,
    carrier_name          text,
    driver_name           text,
    driver_phone          text,
    -- Denormalised latest position, maintained from tracking_points, so the
    -- scanner can filter on freshness without a correlated subquery per row.
    latest_tracking_at    timestamptz,
    latest_latitude       double precision,
    latest_longitude      double precision,
    created_at            timestamptz not null default now(),
    updated_at            timestamptz not null default now(),
    constraint loads_tenant_reference_key unique (tenant_id, reference),
    -- Target of the composite foreign keys below.
    constraint loads_tenant_id_id_key unique (tenant_id, id)
);

create index loads_tenant_status_idx on loads (tenant_id, status);
create index loads_latest_tracking_idx on loads (tenant_id, latest_tracking_at);

create table stops (
    id                uuid        primary key default gen_random_uuid(),
    tenant_id         uuid        not null,
    load_id           uuid        not null,
    sequence          integer     not null,
    stop_type         stop_type   not null,
    facility_name     text,
    city              text,
    state             text,
    latitude          double precision,
    longitude         double precision,
    timezone          text        not null default 'America/Chicago',
    -- An appointment revision lets a rescheduled window open a fresh goal
    -- episode without colliding with the prior one's idempotency key.
    appointment_revision integer  not null default 1,
    appointment_start timestamptz,
    appointment_end   timestamptz,
    arrived_at        timestamptz,
    departed_at       timestamptz,
    completed_at      timestamptz,
    created_at        timestamptz not null default now(),
    updated_at        timestamptz not null default now(),
    constraint stops_load_sequence_key unique (load_id, sequence),
    constraint stops_tenant_id_id_key unique (tenant_id, id),
    constraint stops_load_fk foreign key (tenant_id, load_id)
        references loads (tenant_id, id) on delete cascade
);

create index stops_tenant_type_appt_idx
    on stops (tenant_id, stop_type, appointment_start)
    where completed_at is null;

create table legs (
    id           uuid    primary key default gen_random_uuid(),
    tenant_id    uuid    not null,
    load_id      uuid    not null,
    sequence     integer not null,
    origin_stop_id      uuid,
    destination_stop_id uuid,
    distance_meters     double precision,
    expected_duration_seconds integer,
    created_at   timestamptz not null default now(),
    constraint legs_load_sequence_key unique (load_id, sequence),
    constraint legs_load_fk foreign key (tenant_id, load_id)
        references loads (tenant_id, id) on delete cascade
);

create table tracking_points (
    id              uuid        primary key default gen_random_uuid(),
    tenant_id       uuid        not null,
    load_id         uuid        not null,
    recorded_at     timestamptz not null,
    latitude        double precision not null,
    longitude       double precision not null,
    source          text        not null default 'eld',
    source_event_id text,
    created_at      timestamptz not null default now(),
    constraint tracking_source_event_key unique (source, source_event_id),
    constraint tracking_load_fk foreign key (tenant_id, load_id)
        references loads (tenant_id, id) on delete cascade
);

create index tracking_latest_idx on tracking_points (tenant_id, load_id, recorded_at desc);

create table documents (
    id          uuid        primary key default gen_random_uuid(),
    tenant_id   uuid        not null,
    load_id     uuid        not null,
    stop_id     uuid,
    doc_type    text        not null default 'pod',
    status      text        not null default 'missing',
    reference   text,
    created_at  timestamptz not null default now(),
    updated_at  timestamptz not null default now(),
    constraint documents_load_fk foreign key (tenant_id, load_id)
        references loads (tenant_id, id) on delete cascade
);

create index documents_status_idx on documents (tenant_id, load_id, doc_type, status);

-- ---------------------------------------------------------------------------
-- Agent catalog and tenant configuration
-- ---------------------------------------------------------------------------
create table agent_definitions (
    id           uuid        primary key default gen_random_uuid(),
    agent_type   text        not null,
    version      text        not null,
    trigger_kind text        not null check (trigger_kind in ('scanner', 'inbound')),
    display_name text        not null,
    description  text,
    created_at   timestamptz not null default now(),
    constraint agent_definitions_type_version_key unique (agent_type, version)
);

create table tenant_agent_configs (
    id            uuid        primary key default gen_random_uuid(),
    tenant_id     uuid        not null references tenants (id) on delete cascade,
    agent_type    text        not null,
    enabled       boolean     not null default false,
    config        jsonb       not null default '{}'::jsonb,
    config_version integer    not null default 1,
    created_at    timestamptz not null default now(),
    updated_at    timestamptz not null default now(),
    constraint tenant_agent_configs_key unique (tenant_id, agent_type)
);

-- ---------------------------------------------------------------------------
-- Agent runtime
-- ---------------------------------------------------------------------------
create table goals (
    id               uuid        primary key default gen_random_uuid(),
    tenant_id        uuid        not null references tenants (id) on delete cascade,
    agent_type       text        not null,
    agent_version    text        not null,
    subject_type     text        not null,
    subject_id       uuid        not null,
    trigger_fingerprint text     not null,
    load_id          uuid,
    state            goal_state  not null default 'opened',
    state_version    integer     not null default 1,
    -- Optimistic lease: which worker holds this goal, and until when.
    lease_worker     text,
    lease_expires_at timestamptz,
    next_tick_at     timestamptz,
    terminal_outcome text,
    opened_at        timestamptz not null default now(),
    updated_at       timestamptz not null default now(),
    closed_at        timestamptz,
    -- THE idempotency constraint. One goal per tenant + agent + subject +
    -- trigger episode. Everything else about at-least-once delivery rests here.
    constraint goals_idempotency_key
        unique (tenant_id, agent_type, subject_type, subject_id, trigger_fingerprint),
    constraint goals_tenant_id_id_key unique (tenant_id, id),
    constraint goals_load_fk foreign key (tenant_id, load_id)
        references loads (tenant_id, id) on delete set null
);

create index goals_state_idx on goals (tenant_id, state);
create index goals_due_idx on goals (state, next_tick_at)
    where state not in ('succeeded', 'failed', 'expired', 'suppressed');
create index goals_lease_idx on goals (lease_expires_at)
    where lease_expires_at is not null;

create table goal_events (
    id          bigserial   primary key,
    tenant_id   uuid        not null,
    goal_id     uuid        not null,
    sequence    integer     not null,
    event_type  text        not null,
    from_state  text,
    to_state    text,
    detail      jsonb       not null default '{}'::jsonb,
    occurred_at timestamptz not null default now(),
    constraint goal_events_sequence_key unique (goal_id, sequence),
    constraint goal_events_goal_fk foreign key (tenant_id, goal_id)
        references goals (tenant_id, id) on delete cascade
);

create index goal_events_goal_idx on goal_events (goal_id, sequence);

create table fact_snapshots (
    id           uuid        primary key default gen_random_uuid(),
    tenant_id    uuid        not null,
    goal_id      uuid        not null,
    version      integer     not null,
    content      jsonb       not null,
    content_hash text        not null,
    computed_at  timestamptz not null default now(),
    constraint fact_snapshots_goal_version_key unique (goal_id, version),
    constraint fact_snapshots_goal_fk foreign key (tenant_id, goal_id)
        references goals (tenant_id, id) on delete cascade
);

create table actions (
    id            uuid        primary key default gen_random_uuid(),
    tenant_id     uuid        not null,
    goal_id       uuid        not null,
    action_kind   text        not null,
    recipient     text        not null,
    recipient_fingerprint text not null,
    action_fingerprint    text not null,
    template_key  text,
    template_version text,
    idempotency_key text     not null,
    state         action_state not null default 'pending',
    subject       text,
    body_preview  text,
    created_at    timestamptz not null default now(),
    updated_at    timestamptz not null default now(),
    -- One action per goal + kind + recipient + action fingerprint. A retry
    -- re-uses this row; it never creates a second provider send.
    constraint actions_idempotency_key
        unique (tenant_id, goal_id, action_kind, recipient_fingerprint, action_fingerprint),
    constraint actions_tenant_id_id_key unique (tenant_id, id),
    constraint actions_goal_fk foreign key (tenant_id, goal_id)
        references goals (tenant_id, id) on delete cascade
);

create index actions_goal_idx on actions (goal_id);

create table action_attempts (
    id             uuid        primary key default gen_random_uuid(),
    tenant_id      uuid        not null,
    action_id      uuid        not null,
    attempt        integer     not null,
    provider       text        not null,
    provider_message_id text,
    result_class   text        not null,
    detail         jsonb       not null default '{}'::jsonb,
    attempted_at   timestamptz not null default now(),
    constraint action_attempts_attempt_key unique (action_id, attempt),
    constraint action_attempts_provider_msg_key unique (provider, provider_message_id),
    constraint action_attempts_action_fk foreign key (tenant_id, action_id)
        references actions (tenant_id, id) on delete cascade
);

create table outcomes (
    id           bigserial   primary key,
    tenant_id    uuid        not null references tenants (id) on delete cascade,
    goal_id      uuid,
    agent_type   text        not null,
    agent_version text       not null,
    reason       text        not null,
    detail       jsonb       not null default '{}'::jsonb,
    occurred_at  timestamptz not null default now()
);

create index outcomes_reason_idx on outcomes (tenant_id, agent_type, reason, occurred_at desc);
create index outcomes_goal_idx on outcomes (goal_id);
