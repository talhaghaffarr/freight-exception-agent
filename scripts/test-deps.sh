#!/usr/bin/env bash
# Start (or stop) the PostgreSQL and Valkey containers that back the
# integration test suite. Integration tests refuse to run against SQLite, so
# these are required for `make test-integration`.
set -euo pipefail

PG_CONTAINER=relayops-test-postgres
VALKEY_CONTAINER=relayops-test-valkey
PG_PORT=${PG_PORT:-55432}
VALKEY_PORT=${VALKEY_PORT:-56379}

case "${1:-up}" in
  up)
    if ! docker ps --format '{{.Names}}' | grep -qx "$PG_CONTAINER"; then
      docker rm -f "$PG_CONTAINER" >/dev/null 2>&1 || true
      docker run -d --name "$PG_CONTAINER" \
        -e POSTGRES_USER=relayops \
        -e POSTGRES_PASSWORD=relayops \
        -e POSTGRES_DB=relayops_test \
        -p "${PG_PORT}:5432" \
        --health-cmd='pg_isready -U relayops -d relayops_test' \
        --health-interval=2s --health-timeout=3s --health-retries=30 \
        postgres:16-alpine >/dev/null
      echo "started $PG_CONTAINER on :$PG_PORT"
    fi
    if ! docker ps --format '{{.Names}}' | grep -qx "$VALKEY_CONTAINER"; then
      docker rm -f "$VALKEY_CONTAINER" >/dev/null 2>&1 || true
      docker run -d --name "$VALKEY_CONTAINER" \
        -p "${VALKEY_PORT}:6379" \
        --health-cmd='valkey-cli ping' \
        --health-interval=2s --health-timeout=3s --health-retries=30 \
        valkey/valkey:8-alpine >/dev/null
      echo "started $VALKEY_CONTAINER on :$VALKEY_PORT"
    fi
    for _ in $(seq 1 60); do
      pg_state=$(docker inspect -f '{{.State.Health.Status}}' "$PG_CONTAINER" 2>/dev/null || echo starting)
      vk_state=$(docker inspect -f '{{.State.Health.Status}}' "$VALKEY_CONTAINER" 2>/dev/null || echo starting)
      [ "$pg_state" = healthy ] && [ "$vk_state" = healthy ] && { echo "test dependencies healthy"; exit 0; }
      sleep 1
    done
    echo "test dependencies did not become healthy" >&2
    exit 1
    ;;
  down)
    docker rm -f "$PG_CONTAINER" "$VALKEY_CONTAINER" >/dev/null 2>&1 || true
    echo "test dependencies removed"
    ;;
  *)
    echo "usage: $0 [up|down]" >&2
    exit 2
    ;;
esac
