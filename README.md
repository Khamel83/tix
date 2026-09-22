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


## Apple silicon macOS development with Apple `container`

This is a local development workflow for hosts that meet Apple's requirements: an
Apple-silicon Mac and macOS 26 or later. Install Apple's signed [`container`
CLI](https://github.com/apple/container/releases) before starting. This workflow
does not support Intel Macs or older macOS releases.

Docker Compose remains the canonical unattended homelab deployment path. Apple
`container` is an optional local workflow for the supported Apple host; it does
not replace Compose and does not modify Compose resources. Use [Build and
launch](#build-and-launch) for the launcher command and [Smoke test](#smoke-test)
for the verification and cleanup command.

### Prerequisites and service setup

From a fresh checkout:

1. Copy `.env.example` to `.env` and fill in the credentials and service
   settings. The launcher passes this file to the container with
   `--env-file .env`.
2. Start Apple's container service and confirm it is available:

   ```bash
   container system start
   container system status
   ```

The `.env` contract is the same one used by the Compose service:

| Variable | Purpose/default |
| --- | --- |
| `SEATGEEK_CLIENT_ID` | SeatGeek client credential |
| `TELEGRAM_BOT_TOKEN` | Telegram bot credential |
| `TELEGRAM_CHAT_ID` | Telegram destination |
| `ARGUS_BASE_URL` | Argus service URL |
| `ARGUS_API_KEY` | Argus credential |
| `TZ_DISPLAY` | Display timezone; defaults to `America/Los_Angeles` |
| `TIER2_MAX_REQUESTS_PER_DAY` | Tier-2 request budget; defaults to `600` |
| `GATE_MARGIN` | Gate margin; defaults to `0.15` |
| `DEADMAN_HOURS` | Deadman threshold; defaults to `6` |
| `TIX_PROTOTYPE_MODE` | Deterministic prototype mode; defaults to `0` |
| `DATABASE_PATH` | Must remain `/data/tickets.sqlite3` inside the container |

### Build and launch

Build the image from the repository root, create the persistent host data
directory, and launch the service. The bind mount keeps the SQLite database and
other `/data` contents at `~/.local/share/tix` across container recreation.

```bash
container build --tag tix:local .
mkdir -p "$HOME/.local/share/tix"
container run \
  --detach \
  --name tix-apple \
  --publish 127.0.0.1:8000:8000 \
  --env-file .env \
  --volume "$HOME/.local/share/tix:/data" \
  tix:local
```

The service is bound to `127.0.0.1:8000` on the Mac. Its health endpoint is
[`http://127.0.0.1:8000/health`](http://127.0.0.1:8000/health), and the
operator dashboard is [`http://127.0.0.1:8000/`](http://127.0.0.1:8000/).

### Smoke test

Run this while `tix-apple` is running. The first command verifies both the
HTTP 200 response and the expected `{"status":"healthy"}` body from `/health`;
the second verifies that the dashboard responds with HTTP 200. The final two
commands stop and remove only the Apple `container` instance:

```bash
test "$(curl --fail --show-error --silent http://127.0.0.1:8000/health)" \
  = '{"status":"healthy"}'
curl --fail --show-error --silent http://127.0.0.1:8000/ >/dev/null
container stop tix-apple
container rm tix-apple
```

To stop the service without removing it, run `container stop tix-apple`. To
remove an already-stopped instance, run `container rm tix-apple`. These commands
do not stop or remove the `ticket_sniper` Compose service or its `sniper_data`
volume.

If `container system status` or any `container` command reports that the
container service is unavailable, run `container system start` again and check
`container system logs --last 5m`. On first use, `container system start` may
prompt to install Apple's recommended Linux kernel; accept that install, then
rerun the launch command. This workflow requires Apple silicon and macOS 26 or
later; use Docker Compose on other hosts.

See the [Apple `container` tutorial](https://github.com/apple/container/blob/main/docs/tutorials/start-here.md)
for host-tool installation and runtime details.

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
