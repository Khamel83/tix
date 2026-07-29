# Tix

Tix is a personal ticket-deal monitor. It discovers events, watches market data, evaluates user rules, and alerts when a listing looks worth acting on.

## Language

**Tix**:
The project and product. Tix and Ticket Sniper refer to the same system.
_Avoid_: Separate app names for Tix and Ticket Sniper

**Ticket Sniper**:
The older package and UI name for Tix. Use it only where existing code, package names, or user-facing labels still require that wording.
_Avoid_: Treating Ticket Sniper as a separate subsystem

**Source**:
An external ticket marketplace or data provider that supplies event or listing data.
_Avoid_: Vendor, scraper target

**Venue**:
A physical place whose upcoming events may be monitored.
_Avoid_: Location, arena, stadium

**Source Event**:
An event as identified by a Source. It may later be connected to a canonical cross-source event, but the current system primarily operates on source-specific events.
_Avoid_: Event when source identity matters

**Listing**:
A purchasable ticket offer from a Source for a Source Event.
_Avoid_: Ticket, offer

**Rule**:
A user's definition of what counts as a worthwhile Listing, including event scope, section matching, quantity, and maximum all-in price.
_Avoid_: Filter, alert config

**Section Matcher**:
A rule condition that includes or excludes venue sections by raw or normalized section text.
_Avoid_: Section filter

**All-In Price**:
The estimated or observed per-ticket price after fees.
_Avoid_: Price when fees matter

**Fee Model**:
A source or venue-specific model for estimating All-In Price from listed price.
_Avoid_: Fee calculator

**Gate**:
A cheap decision point that decides whether aggregate event data is promising enough to justify deeper listing collection.
_Avoid_: Filter when referring to the staged polling decision

**Poll Run**:
A recorded attempt to collect market data for a Source Event.
_Avoid_: Scrape, job run

**Poll Tier**:
The intensity level for polling. Higher tiers are used for more urgent or promising events.
_Avoid_: Priority, schedule class

**Alert Decision**:
The recorded result of evaluating a Listing against a Rule and prior Alert State.
_Avoid_: Notification

**Alert State**:
The remembered qualification state for a Rule and Listing pair, used to avoid duplicate or noisy alerts.
_Avoid_: Alert cache

**Alert Outbox**:
A durable queue of alert messages waiting to be delivered.
_Avoid_: Telegram queue

**Deadman Check**:
A health check that warns when recent successful high-tier polling is missing.
_Avoid_: Health check when referring to stale polling specifically

**Argus**:
The external fetch broker intended to perform raw or rendered data collection for ticket sources.
_Avoid_: Browser, scraper
