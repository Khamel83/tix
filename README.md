# Tix

Self-hosted, local-first personal ticket deal monitor built for unattended homelab operation.

Ticket Sniper is the older package and UI name for this same project. Tix and Ticket Sniper are not separate systems.

## Current Status

Tix is a local prototype of the full ticket-deal monitoring loop.

Built today:

- SeatGeek venue resolution and scheduled event discovery.
- SQLite persistence with Alembic migrations.
- Fixture-backed prototype events for Dodger Stadium and Hollywood Bowl.
- Listing parsing, current listing persistence, and price history.
- Gate evaluation from aggregate event stats into deeper listing collection.
- Rule evaluation for section matchers, exact quantity splits, all-in unit price, order total, and fee confidence.
- Alert decisions, duplicate suppression, re-alert handling, durable outbox rows, and Telegram outbox processing.
- Scheduler jobs for discovery, outbox draining, deadman checks, and dynamic event polling.
- Operator dashboard with active events, listings, gate snapshots, poll runs, decisions, outbox counts, and manual event polling.
- Docker Compose service for local homelab operation.

See [CONTEXT.md](CONTEXT.md) for domain language and [docs/AUDIT.md](docs/AUDIT.md) for the current build audit.

## Quick Start
1. Copy `.env.example` to `.env` and fill in credentials (`SEATGEEK_CLIENT_ID`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `ARGUS_BASE_URL`).
2. Run `docker-compose up -d --build`.
3. Check health at `http://localhost:8000/health` or access the UI at `http://localhost:8000`.

## Local Prototype

The prototype loop can run without live Argus or Telegram credentials:

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
cp .env.example .env
.venv/bin/python -m pytest
TIX_PROTOTYPE_MODE=1 DATABASE_PATH=./tickets.sqlite3 .venv/bin/python -m ticket_sniper.demo.seed
TIX_PROTOTYPE_MODE=1 DATABASE_PATH=./tickets.sqlite3 .venv/bin/uvicorn ticket_sniper.web.app:app --reload
```

Open `http://localhost:8000`, select the Dodgers or Hollywood Bowl demo event, and use `Poll` to run fixture event stats, listing collection, rule evaluation, alert decision writing, and outbox enqueueing.

## Target Sports Venues
By default the SeatGeek discovery job seeds and refreshes events for Dodger Stadium, Crypto.com Arena, and Intuit Dome. Override `TARGET_SPORTS_VENUES` with a JSON array of SeatGeek venue names to track a different venue set. Demo seed data also includes Hollywood Bowl.
