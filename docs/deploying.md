# Deploying the demo

The image is self-contained: it compiles the console, serves it from the API
process, applies migrations on boot, and seeds the synthetic freight. What it
does not contain is a database, so a deployment is the image plus two managed
services.

The shape below keeps the whole thing inside free tiers. Costs and free
allowances change — check each provider's current pricing before relying on it.

| Piece | Service | Why |
|---|---|---|
| App | Fly.io | Scales to zero when idle |
| PostgreSQL | [Neon](https://neon.tech) free tier | Fly's Managed Postgres is a paid add-on |
| Redis | [Upstash](https://upstash.com) free tier | Only needed for the Celery health probe today |

Redis is optional. Without `CELERY_BROKER_URL` the API runs and every screen
works; the System page reports the worker components as unavailable, which is
accurate — no worker is deployed.

## 1. Provision the database

Create a Neon project and copy its connection string. Convert the scheme to the
driver this project uses:

```
postgresql://user:pass@host/db        →  postgresql+psycopg://user:pass@host/db?sslmode=require
```

## 2. Create the Fly app

```bash
fly auth login
```

```bash
fly launch --no-deploy --copy-config --name relayops-demo --region iad
```

## 3. Set secrets

Never commit these; `fly secrets` stores them encrypted and restarts the app.

```bash
fly secrets set SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')"
```

```bash
fly secrets set DATABASE_URL="postgresql+psycopg://USER:PASSWORD@HOST/DB?sslmode=require"
```

Optionally, for the Celery health probe:

```bash
fly secrets set CELERY_BROKER_URL="rediss://default:TOKEN@HOST:6379/0" CELERY_RESULT_BACKEND="rediss://default:TOKEN@HOST:6379/1"
```

## 4. Deploy

```bash
fly deploy
```

```bash
fly open
```

The first request after an idle period pays a cold start of a few seconds,
because `min_machines_running = 0` keeps an unwatched demo free.

## Verifying a deployment

```bash
curl -s https://relayops-demo.fly.dev/healthz
```

Then sign in as **Brokerage admin**, open **Live Operations**, and confirm
`LD-1048` reads `+38 min`. If it reads higher, the board has drifted from its
seed moment — press **Reset demo**.

## Notes for a public demo

- `ENVIRONMENT_MODE=sandbox` is set in `fly.toml`. It is what makes the console
  render the sandbox banner and what keeps `can_reach_external_recipients` false.
- Demo sign-in accepts the four seeded personas and nothing else. There is no
  registration, and no real customer data exists in the image.
- `SEED_ON_BOOT=true` re-anchors the demo on every deploy. Turn it off if you
  ever point this at data you care about.
