# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Stack overview

Three services orchestrated by `docker-compose.yml`:

- **evolution-api** (`:8080`) — third-party Evolution API container; the WhatsApp gateway. Posts events to the backend via global webhook (`WEBHOOK_GLOBAL_URL=http://backend:8000/webhook/incoming`).
- **backend** (`:8000`) — FastAPI + SQLAlchemy + Alembic + APScheduler, single SQLite DB at `backend/data/app.db` (bind-mounted from host, so it survives restarts).
- **frontend** (`:5173`) — React 18 + Vite + TypeScript + Tailwind. Built static assets are served by nginx, which proxies `/api/*` → `http://backend:8000/`.

There is also a **legacy CLI** (`whatsapp_sender.py`, `marketing_auto.sh`, `campanhas/`, `evolution_client.py`) that predates the v2 system. It still works and shares the same Evolution container, but is not part of the docker-compose stack. Don't change it unless asked — see `SISTEMA_NOVO.md`.

## Common commands

```bash
# bring everything up (rebuild on code change)
docker compose up -d --build

# logs
docker compose logs -f backend
docker compose logs -f evolution-api
docker compose logs -f frontend

# restart only the backend (e.g. after editing app/ code without rebuilding)
docker compose restart backend

# run a new alembic migration
docker exec wa_backend alembic revision --autogenerate -m "msg"
docker exec wa_backend alembic upgrade head

# inspect the SQLite DB (sqlite3 CLI is not installed; use python)
python3 -c "import sqlite3; c=sqlite3.connect('backend/data/app.db').cursor(); c.execute('SELECT id,name,status FROM campaigns'); print(c.fetchall())"

# frontend dev (outside docker — hits backend at :8000 via vite proxy)
cd frontend && npm install && npm run dev
cd frontend && npm run build   # tsc -b && vite build
```

There is no test suite or linter configured.

## Architecture

### Send pipeline (worker tick loop)

`backend/app/services/worker.py` is the heart of the outbound flow. APScheduler fires `tick()` every `worker_tick_seconds` (default 60s, configurable in `app_settings`). Each tick:

1. Bails out if outside the **send window** (`AppSettings.send_window_start`–`send_window_end`, hour-of-day).
2. Iterates campaigns with `status == "active"` **only** (`draft|paused|done` are ignored — this is the most common reason "messages aren't being sent").
3. For each active campaign: auto-enqueues remaining contacts, then picks one item from `send_queue` respecting `daily_limit` and `delay_seconds` between sends.
4. For each item: lazily probes WhatsApp existence (`has_whatsapp` `unknown→yes|no`), formats the template (`{nome}`, `{telefone}`, `{endereco}`, `{avaliacao}`, `{website}`), calls Evolution to send, writes a `Send` row, deletes the queue item.

Campaign lifecycle: `draft → active → paused → done`. UI must flip a campaign to `active` before anything sends.

### Inbound / bot pipeline

Evolution posts to `POST /webhook/incoming` (`routes/webhook.py`). The route persists the message into a `Conversation` (creating one if needed) and calls `bot_engine.handle_incoming`. The bot only replies when:

- conversation `state == "bot"` (flipping to `human` in the Inbox UI silences the bot)
- a `BotConfig` exists for the contact's recipient type, is `enabled`, and current hour is inside its window
- no handoff keyword matched (otherwise alert is sent to `ALERT_PHONE` via `notifier.send_handoff_alert`)
- the configured LLM `provider` returns a reply

LLM providers live in `backend/app/services/llm/` behind a `get_provider(name)` factory. **Only `stub` is implemented** — it logs but never replies. To make the bot actually talk, add a provider (e.g. `anthropic.py`) and wire it into `llm/__init__.py`.

### Data model relationships

`RecipientType` (e.g. "advocacia") is the central pivot:
- has many `Template`s
- has many `Campaign`s (each pinned to one `Template`)
- has at most one `BotConfig`

`Campaign` has many `Contact`s; each contact may have many `Send`s (history) and at most one `Conversation` (which has many `Message`s).

`SendQueue` is a transient outbox — rows are deleted after the worker processes them. `Send` is the permanent log.

### Settings / config

- `backend/app/config.py` (`Settings` from pydantic-settings) — startup env: `DB_PATH`, `EVOLUTION_URL`, `EVOLUTION_API_KEY`, `INSTANCE_NAME`, `ALERT_PHONE`, `FRONTEND_URL`, `BOT_WINDOW_START/END`. Set in `docker-compose.yml`.
- `AppSettings` table (singleton row) — runtime-tunable: `send_window_start/end`, `worker_tick_seconds`, `typing_delay_seconds`. Edited via `/settings` UI.
- `BotConfig` table (one per recipient type) — `system_prompt`, `model`, `provider`, `handoff_keywords`, `active_hours_*`, `enabled`.

The container's wall-clock controls send/bot windows. `TZ=America/Sao_Paulo` is set in compose; `models.utcnow()` is misnamed and actually returns local time.

## Gotchas

- **nginx caches DNS at startup.** If the backend container restarts and gets a new IP, the frontend keeps proxying to the stale IP and returns 502 for `/api/*`. Fix: `docker restart wa_frontend`. Permanent fix would be a `resolver 127.0.0.11` block in `frontend/nginx.conf` with a variable in `proxy_pass`.
- **Worker only sees `active` campaigns.** A new campaign starts as `draft`. If the queue isn't draining, check `campaigns.status` first.
- **Alembic head must be applied.** `backend/Dockerfile` runs `alembic upgrade head` on container start, but if the DB was created against an older image and the container didn't restart, `alembic_version` may lag (e.g. `578f008d9203` while `af400061e73e` exists on disk). Re-run `docker exec wa_backend alembic upgrade head`.
- **Bind-mounted DB is owned by root.** The bind mount `./backend/data:/app/data` means the SQLite file ends up `root:root` on the host. Editing it from the host needs `sudo` or running through the container.
- **Webhook URL is intra-Docker.** Evolution reaches the backend at `http://backend:8000` (compose network DNS), not `localhost:8000`. Don't "fix" this to `localhost`.
