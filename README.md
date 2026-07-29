# Tix

Self-hosted, local-first personal ticket deal monitor built for unattended homelab operation.

Ticket Sniper is the older package and UI name for this same project. Tix and Ticket Sniper are not separate systems.

## Current Status

Tix is early-stage. It has the database shape and pieces of the monitoring loop, but it is not yet a complete ticket-deal sniper.

Built today:

- SeatGeek venue resolution and scheduled event discovery.
- SQLite persistence with Alembic migrations.
- Scheduler jobs for discovery, Telegram outbox draining, and deadman checks.
- Skeletons for Argus fetching, listing parsing, fee estimation, rule evaluation, and alert state.
- Docker Compose service for local homelab operation.

Not yet complete:

- Listing-level collection and persistence.
- Gate evaluation from event stats to deeper listing polling.
- Full rule evaluation and anti-flap alert state machine.
- Alert creation from qualifying listings.
- Operational dashboard beyond a basic health page.

See [CONTEXT.md](CONTEXT.md) for domain language and [docs/AUDIT.md](docs/AUDIT.md) for the current build audit.

## Quick Start
1. Copy `.env.example` to `.env` and fill in credentials (`SEATGEEK_CLIENT_ID`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `ARGUS_BASE_URL`).
2. Run `docker-compose up -d --build`.
3. Check health at `http://localhost:8000/health` or access the UI at `http://localhost:8000`.

## Target Sports Venues
By default the SeatGeek discovery job seeds and refreshes events for Dodger Stadium, Crypto.com Arena, and Intuit Dome. Override `TARGET_SPORTS_VENUES` with a JSON array of SeatGeek venue names to track a different venue set.
