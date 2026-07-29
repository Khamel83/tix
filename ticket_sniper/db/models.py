from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Text, Float, ForeignKey, UniqueConstraint, CheckConstraint, ForeignKeyConstraint
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

def utcnow_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

class Venue(Base):
    __tablename__ = "venues"
    id = Column(Integer, primary_key=True, autoincrement=True)
    display_name = Column(Text, nullable=False, unique=True)
    source = Column(Text, nullable=False, default="seatgeek")
    source_venue_id = Column(Text, nullable=True)
    city = Column(Text, nullable=True)
    timezone = Column(Text, nullable=False, default="America/Los_Angeles")
    enabled = Column(Integer, nullable=False, default=1)
    resolved_at = Column(Text, nullable=True)
    created_at = Column(Text, nullable=False, default=utcnow_str)
    __table_args__ = (UniqueConstraint("source", "source_venue_id"),)

class SourceEvent(Base):
    __tablename__ = "source_events"
    source = Column(Text, primary_key=True)
    source_event_id = Column(Text, primary_key=True)
    venue_id = Column(Integer, ForeignKey("venues.id", ondelete="SET NULL"), nullable=True)
    canonical_event_id = Column(Text, nullable=True)
    title = Column(Text, nullable=False)
    venue_name = Column(Text, nullable=False)
    performers_json = Column(Text, nullable=True)
    starts_at_utc = Column(Text, nullable=False)
    event_url = Column(Text, nullable=False)
    status = Column(Text, nullable=False, default="active")
    first_seen_at = Column(Text, nullable=False, default=utcnow_str)
    last_seen_at = Column(Text, nullable=False, default=utcnow_str)
    __table_args__ = (CheckConstraint("starts_at_utc LIKE '%Z'"),)

class Rule(Base):
    __tablename__ = "rules"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text, nullable=False)
    enabled = Column(Integer, nullable=False, default=1)
    scope_type = Column(Text, nullable=False, default="venue")
    scope_venue_id = Column(Integer, ForeignKey("venues.id", ondelete="CASCADE"), nullable=True)
    scope_performer_slug = Column(Text, nullable=True)
    scope_source = Column(Text, nullable=True)
    scope_source_event_id = Column(Text, nullable=True)
    max_unit_price_all_in = Column(Float, nullable=False)
    max_order_total = Column(Float, nullable=True)
    quantity_mode = Column(Text, nullable=False, default="exact")
    quantity_value = Column(Integer, nullable=False, default=2)
    minimum_identity_confidence = Column(Text, nullable=False, default="high")
    minimum_fee_confidence = Column(Text, nullable=False, default="medium")
    estimate_safety_margin_pct = Column(Float, nullable=False, default=0.08)
    realert_mode = Column(Text, nullable=False, default="either")
    realert_drop_dollars = Column(Float, nullable=False, default=25.0)
    realert_drop_percent = Column(Float, nullable=False, default=0.10)
    realert_cooldown_minutes = Column(Integer, nullable=False, default=30)
    realert_memory_hours = Column(Integer, nullable=False, default=24)
    rule_fingerprint = Column(Text, nullable=False)
    created_at = Column(Text, nullable=False, default=utcnow_str)
    updated_at = Column(Text, nullable=False, default=utcnow_str)
    matchers = relationship("RuleSectionMatcher", backref="rule", cascade="all, delete-orphan")

class RuleSectionMatcher(Base):
    __tablename__ = "rule_section_matchers"
    id = Column(Integer, primary_key=True, autoincrement=True)
    rule_id = Column(Integer, ForeignKey("rules.id", ondelete="CASCADE"), nullable=False)
    action = Column(Text, nullable=False, default="include")
    matcher_type = Column(Text, nullable=False, default="exact")
    matcher_value = Column(Text, nullable=False)
    sort_order = Column(Integer, nullable=False, default=0)

class RuleEventBinding(Base):
    __tablename__ = "rule_event_bindings"
    rule_id = Column(Integer, ForeignKey("rules.id", ondelete="CASCADE"), primary_key=True)
    source = Column(Text, primary_key=True)
    source_event_id = Column(Text, primary_key=True)
    bound_at = Column(Text, nullable=False, default=utcnow_str)

class SectionAlias(Base):
    __tablename__ = "section_aliases"
    id = Column(Integer, primary_key=True, autoincrement=True)
    venue_id = Column(Integer, ForeignKey("venues.id", ondelete="CASCADE"), nullable=False)
    source = Column(Text, nullable=False)
    raw_section = Column(Text, nullable=False)
    normalized_section = Column(Text, nullable=True)
    status = Column(Text, nullable=False, default="pending")
    first_seen_at = Column(Text, nullable=False, default=utcnow_str)
    approved_at = Column(Text, nullable=True)
    __table_args__ = (UniqueConstraint("venue_id", "source", "raw_section"),)

class ListingCurrent(Base):
    __tablename__ = "listings_current"
    source = Column(Text, primary_key=True)
    source_listing_id = Column(Text, primary_key=True)
    identity_type = Column(Text, nullable=False, default="source_id")
    identity_confidence = Column(Text, nullable=False, default="high")
    source_event_id = Column(Text, nullable=False)
    raw_section = Column(Text, nullable=True)
    normalized_section = Column(Text, nullable=True)
    raw_row = Column(Text, nullable=True)
    raw_seats = Column(Text, nullable=True)
    quantity_available = Column(Integer, nullable=False)
    available_quantities_json = Column(Text, nullable=True)
    unit_price_listed = Column(Float, nullable=True)
    unit_fee_amount = Column(Float, nullable=True)
    unit_price_all_in = Column(Float, nullable=True)
    price_basis = Column(Text, nullable=False, default="unknown")
    fee_confidence = Column(Text, nullable=True)
    currency = Column(Text, nullable=False, default="USD")
    listing_url = Column(Text, nullable=False)
    payload_hash = Column(Text, nullable=False)
    hash_algo_version = Column(Integer, nullable=False, default=1)
    consecutive_missing_count = Column(Integer, nullable=False, default=0)
    first_seen_at = Column(Text, nullable=False, default=utcnow_str)
    last_seen_at = Column(Text, nullable=False, default=utcnow_str)
    inactive_at = Column(Text, nullable=True)
    status = Column(Text, nullable=False, default="active")
    adapter_version = Column(Text, nullable=False)
    parser_version = Column(Text, nullable=False)

class ListingPriceHistory(Base):
    __tablename__ = "listing_price_history"
    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(Text, nullable=False)
    source_listing_id = Column(Text, nullable=False)
    observed_at = Column(Text, nullable=False, default=utcnow_str)
    unit_price_listed = Column(Float, nullable=True)
    unit_price_all_in = Column(Float, nullable=True)
    price_basis = Column(Text, nullable=False)
    quantity_available = Column(Integer, nullable=True)

class EventPriceSnapshot(Base):
    __tablename__ = "event_price_snapshots"
    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(Text, nullable=False)
    source_event_id = Column(Text, nullable=False)
    observed_at = Column(Text, nullable=False, default=utcnow_str)
    lowest_price = Column(Float, nullable=True)
    average_price = Column(Float, nullable=True)
    highest_price = Column(Float, nullable=True)
    listing_count = Column(Integer, nullable=True)
    visible_listing_count = Column(Integer, nullable=True)
    gate_decision = Column(Text, nullable=False)
    gate_reason = Column(Text, nullable=True)

class FeeModel(Base):
    __tablename__ = "fee_models"
    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(Text, nullable=False)
    venue_id = Column(Integer, ForeignKey("venues.id", ondelete="CASCADE"), nullable=True)
    fee_rate_pct = Column(Float, nullable=False, default=1.28)
    fee_fixed = Column(Float, nullable=False, default=3.50)
    sample_count = Column(Integer, nullable=False, default=0)
    residual_stddev = Column(Float, nullable=True)
    confidence = Column(Text, nullable=False, default="low")
    last_calibrated_at = Column(Text, nullable=True)
    __table_args__ = (UniqueConstraint("source", "venue_id"),)

class FeeObservation(Base):
    __tablename__ = "fee_observations"
    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(Text, nullable=False)
    venue_id = Column(Integer, ForeignKey("venues.id", ondelete="CASCADE"), nullable=True)
    source_event_id = Column(Text, nullable=True)
    listed_price = Column(Float, nullable=False)
    actual_all_in = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=True)
    observed_at = Column(Text, nullable=False, default=utcnow_str)
    entered_via = Column(Text, nullable=False, default="telegram")

class AlertState(Base):
    __tablename__ = "alert_state"
    rule_id = Column(Integer, ForeignKey("rules.id", ondelete="CASCADE"), primary_key=True)
    source = Column(Text, primary_key=True)
    listing_identity = Column(Text, primary_key=True)
    currently_qualifying = Column(Integer, nullable=False, default=0)
    reason_fingerprint = Column(Text, nullable=True)
    rule_fingerprint = Column(Text, nullable=True)
    last_qualifying_price = Column(Float, nullable=True)
    last_alert_price = Column(Float, nullable=True)
    last_alert_at = Column(Text, nullable=True)
    transition_sequence = Column(Integer, nullable=False, default=0)
    updated_at = Column(Text, nullable=False, default=utcnow_str)

class AlertDecision(Base):
    __tablename__ = "alert_decisions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    decided_at = Column(Text, nullable=False, default=utcnow_str)
    rule_id = Column(Integer, nullable=False)
    source = Column(Text, nullable=False)
    listing_identity = Column(Text, nullable=False)
    branch = Column(Integer, nullable=False)
    outcome = Column(Text, nullable=False)
    inputs_json = Column(Text, nullable=False)

class AlertOutbox(Base):
    __tablename__ = "alert_outbox"
    id = Column(Integer, primary_key=True, autoincrement=True)
    payload_json = Column(Text, nullable=False)
    dedupe_key = Column(Text, nullable=False)
    status = Column(Text, nullable=False, default="pending")
    attempts = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)
    created_at = Column(Text, nullable=False, default=utcnow_str)
    next_attempt_at = Column(Text, nullable=False, default=utcnow_str)
    sent_at = Column(Text, nullable=True)

class PollRun(Base):
    __tablename__ = "poll_runs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    tier = Column(Integer, nullable=False)
    source = Column(Text, nullable=False)
    source_event_id = Column(Text, nullable=False)
    started_at = Column(Text, nullable=False, default=utcnow_str)
    completed_at = Column(Text, nullable=True)
    status = Column(Text, nullable=False)
    pagination_complete = Column(Integer, nullable=False, default=0)
    inventory_count = Column(Integer, nullable=False, default=0)
    new_listing_count = Column(Integer, nullable=False, default=0)
    changed_listing_count = Column(Integer, nullable=False, default=0)
    transport_rung = Column(Integer, nullable=True)
    argus_status = Column(Text, nullable=True)
    extractor_used = Column(Text, nullable=True)
    egress_used = Column(Text, nullable=True)
    http_status = Column(Integer, nullable=True)
    parser_version = Column(Text, nullable=True)
    error_code = Column(Text, nullable=True)
    error_summary = Column(Text, nullable=True)
    capture_reference = Column(Text, nullable=True)

class TransportHealth(Base):
    __tablename__ = "transport_health"
    id = Column(Integer, primary_key=True, autoincrement=True)
    domain = Column(Text, nullable=False)
    rung = Column(Integer, nullable=False)
    attempts_50 = Column(Integer, nullable=False, default=0)
    successes_50 = Column(Integer, nullable=False, default=0)
    blocked_until = Column(Text, nullable=True)
    consecutive_blocks = Column(Integer, nullable=False, default=0)
    updated_at = Column(Text, nullable=False, default=utcnow_str)
    __table_args__ = (UniqueConstraint("domain", "rung"),)
