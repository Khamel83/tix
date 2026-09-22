# Tix

Self-hosted, local-first personal ticket deal monitor built for unattended homelab operation.

Ticket Sniper is the older package and UI name for this same project. Tix and Ticket Sniper are not separate systems.

## Current Status

Tix is a local prototype of the full ticket-deal monitoring loop.

Built today:

- SeatGeek venue resolution and scheduled event discovery.
- SQLite persistence with Alembic migrations.
- Configurable profile preferences for sports and venues.
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

## Optional Scrapling browser collection

Argus remains the default listing fetcher. Scrapling is disabled by default, so
the normal configuration does not launch a browser and preserves the existing
Argus request and fallback behavior.

### Installing browser dependencies

For local development on a supported Python 3.11+ environment, install the
optional fetcher and its Chromium dependencies:

```bash
python3.11 -m pip install -e ".[dev,scrapling]"
python3.11 -m playwright install --with-deps chromium
```

For the container image, install the optional fetcher and browser at build time
by setting the build argument:

```bash
TIX_INSTALL_SCRAPLING=1 SCRAPLING_ENABLED=1 SCRAPLING_SOURCE=scrapling \
  docker compose up -d --build
```

The default build leaves Scrapling and its browser out of the image. The build
argument only installs the runtime; `SCRAPLING_ENABLED=1` and
`SCRAPLING_SOURCE=scrapling` are still required before a browser can be used.

### Scrapling settings

All settings are environment variables. Values outside the stated range, or a
source other than `argus` or `scrapling`, fail configuration construction with
an actionable Pydantic validation error that stops application startup. Boolean
settings accept `0` or `1`, matching the rest of `.env.example`.

| Name | Default | Valid values |
| --- | --- | --- |
| `SCRAPLING_ENABLED` | `0` (`false`) | `0` or `1` |
| `SCRAPLING_SOURCE` | `argus` | `argus`, `scrapling` |
| `SCRAPLING_HEADLESS` | `1` (`true`) | `0` or `1` |
| `SCRAPLING_TIMEOUT_SECONDS` | `30` | Integer `1`–`300` |
| `SCRAPLING_RATE_LIMIT_PER_MINUTE` | `30` | Integer `1`–`600` |
| `SCRAPLING_REQUEST_DELAY_SECONDS` | `1.0` | Number `0`–`3600` |
| `SCRAPLING_SESSION_LIFETIME_SECONDS` | `900` | Integer `1`–`86400` |

`SCRAPLING_RATE_LIMIT_PER_MINUTE` caps requests and
`SCRAPLING_REQUEST_DELAY_SECONDS` spaces them out; configure both
conservatively for the target site. `SCRAPLING_SESSION_LIFETIME_SECONDS`
limits reuse of a browser session during collection.

Scrapling's stealth features do not guarantee that anti-bot defenses will be
bypassed. Follow each target site's terms of service, robots and access
requirements, and published rate limits. Argus remains the unchanged default;
Scrapling does not remove the established Argus fallback/error behavior, and
production collection never silently uses static test fixtures.

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

Open `http://localhost:8000`, inspect the active profile preferences, select the Dodgers or Hollywood Bowl demo event, and use `Poll` to run fixture event stats, listing collection, rule evaluation, alert decision writing, and outbox enqueueing.

## Profile Preferences

Tix keeps sports and venue interests in the default profile rather than only in code-level constants. The default profile tracks Dodgers, Lakers, Clippers, and Kings style interests plus Los Angeles venues including Dodger Stadium, Crypto.com Arena, Intuit Dome, BMO Stadium, and Hollywood Bowl.

SeatGeek discovery reads enabled profile venues when no explicit venue list is passed. `TARGET_SPORTS_VENUES` remains a fallback for empty or missing profile data.
