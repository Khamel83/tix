# Tix — Ticket-Sniper (v2)

Self-hosted, local-first personal ticket deal monitor built for unattended homelab operation.

Target Repository: [Khamel83/tix](https://github.com/Khamel83/tix)

## Architecture & Features
- **Option B Pricing**: Tracks specific high-value venue sections and exact purchasable quantities.
- **Venue-Seeded Discovery**: Automatically discovers upcoming events for seeded LA venues via official SeatGeek Platform APIs.
- **Monotonic Gate**: Stats API acts as a cheap filter before triggering listing-level scrapes.
- **Transactional Outbox**: Guarantees zero lost alerts during Telegram network drops.
- **State Machine Anti-Flap**: Tracks 9 branches with composite reason vectors to suppress duplicate alerts.

## Quick Start
1. Copy `.env.example` to `.env` and fill in credentials (`SEATGEEK_CLIENT_ID`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `ARGUS_BASE_URL`).
2. Run `docker-compose up -d --build`.
3. Check health at `http://localhost:8000/health` or access the UI at `http://localhost:8000`.

## Target Sports Venues
By default the SeatGeek discovery job seeds and refreshes events for Dodger Stadium, Crypto.com Arena, and Intuit Dome. Override `TARGET_SPORTS_VENUES` with a JSON array of SeatGeek venue names to track a different venue set.
