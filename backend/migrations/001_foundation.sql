-- 001_foundation
--
-- Tenancy, demo identities, and the append-only audit log.
--
-- Rollback strategy: this migration is additive and creates only new objects.
-- To roll back, drop the objects in reverse dependency order:
--   drop table audit_events, tenant_memberships, users, tenants;
--   drop domain membership_role;
-- No data outside these tables is touched, so a rollback is non-destructive to
-- any later increment that has not yet been applied.

create extension if not exists "pgcrypto";

-- Roles are a constrained text domain rather than a PostgreSQL enum: adding a
-- role later must not require an exclusive lock on every referencing table.
create domain membership_role as text
    check (value in ('platform_operator', 'brokerage_admin', 'account_manager', 'reviewer'));

create table tenants (
    id            uuid        primary key default gen_random_uuid(),
    slug          text        not null,
    name          text        not null,
    timezone      text        not null default 'America/Chicago',
    is_active     boolean     not null default true,
    settings      jsonb       not null default '{}'::jsonb,
    created_at    timestamptz not null default now(),
    updated_at    timestamptz not null default now(),
    constraint tenants_slug_key unique (slug),
    constraint tenants_slug_shape check (slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$')
);

comment on table tenants is 'A freight brokerage boundary. Every tenant-owned row carries tenant_id.';

create table users (
    id            uuid        primary key default gen_random_uuid(),
    email         text        not null,
    display_name  text        not null,
    is_platform_operator boolean not null default false,
    is_active     boolean     not null default true,
    created_at    timestamptz not null default now(),
    updated_at    timestamptz not null default now(),
    constraint users_email_key unique (email),
    constraint users_email_shape check (position('@' in email) > 1)
);

comment on column users.is_platform_operator is
    'Platform operators may read across tenants through operator-only endpoints.';

create table tenant_memberships (
    id         uuid            primary key default gen_random_uuid(),
    tenant_id  uuid            not null references tenants (id) on delete cascade,
    user_id    uuid            not null references users (id) on delete cascade,
    role       membership_role not null,
    created_at timestamptz     not null default now(),
    constraint tenant_memberships_tenant_user_key unique (tenant_id, user_id)
);

create index tenant_memberships_user_idx on tenant_memberships (user_id);

-- Append-only through the application: there is no update or delete path in
-- any repository, and reviewers rely on that for configuration history.
create table audit_events (
    id           bigserial   primary key,
    tenant_id    uuid        references tenants (id) on delete cascade,
    actor_user_id uuid       references users (id) on delete set null,
    actor_label  text        not null,
    action       text        not null,
    subject_type text        not null,
    subject_id   text,
    reason       text,
    old_value    jsonb,
    new_value    jsonb,
    request_id   text,
    occurred_at  timestamptz not null default now()
);

create index audit_events_tenant_time_idx on audit_events (tenant_id, occurred_at desc);
create index audit_events_actor_time_idx on audit_events (actor_user_id, occurred_at desc);
create index audit_events_subject_idx on audit_events (subject_type, subject_id);
