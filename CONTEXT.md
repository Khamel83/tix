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
<!-- janitor:begin:recent -->
- Source commit: `6da9e0d5b47f825141b1e8973f8e78ba325b8ecf` (merge of `codex/argus-live-integration`, PR #15).
- Commit subjects indicate listing collection was integrated with Argus raw fetch, and the Argus raw fetch contract was subsequently fixed (`808c4fd7f1c3533002c0a116692955e0c23075f8`, `71aa988bc4d2a26310c55798875a1de53a4fce5e`).
- Configurable profile preferences were added and merged via PR #14 (`9b127823c5199145b1cdf75fc5679841c93a2661`, `83fcf868c45f06dd907022e09e189bd76634f195`).
- The local product loop prototype was completed (`afcf409d197960b4dfd146bb042e3557eb4816b4`), after product loop implementation plan docs (`3c61dae8a7b5e34c36ee507ca8faa391f5153a4d`) and plan review synthesis (`7372a36a577f3f92ff827cf27073c64150d3a4c5`).
- Dynamic SeatGeek event polling was added (`c8077aa188876afe78f27161c319806e65801b6e`).
- Earlier commits established the MVP architecture baseline (PRD v2, engine, schemas, docs) and normalized the repository root (`74177127fa90869f1a0dce3742eb7ee6fe8e998a`, `929a83e1c3fe1f0c2183fc79bc6554ce0c073c63`, `f3a939a982cf2240a05177489b5ecf61db4bd840`).
<!-- janitor:end:recent -->
