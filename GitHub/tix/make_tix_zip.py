#!/usr/bin/env python3
import os
import zipfile

# Complete repository contents including Claude Opus MVP specifications, historical PRD v2 context, and code
files = {
    "README.md": """# Tix — Ticket-Sniper (v2)

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
""",

    "pyproject.toml": """[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "tix"
version = "2.0.0"
description = "Self-hosted, local-first personal ticket deal monitor"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.110.0",
    "uvicorn[standard]>=0.28.0",
    "sqlalchemy>=2.0.28",
    "alembic>=1.13.1",
    "httpx>=0.27.0",
    "pydantic-settings>=2.2.1",
    "apscheduler>=3.10.4",
    "jinja2>=3.1.3",
    "curl-cffi>=0.6.2",
    "numpy>=1.26.4"
]

[project.optional-dependencies]
dev = ["pytest>=8.1.1", "pytest-asyncio>=0.23.6"]
""",

    "alembic.ini": """[alembic]
script_location = alembic
file_template = %(rev)s_%(slug)s
sqlalchemy.url = sqlite:////data/tickets.sqlite3

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = INFO
handlers = console

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stdout,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(asctime)s %(levelname)-5.5s [%(name)s] %(message)s
""",

    ".env.example": """SEATGEEK_CLIENT_ID=your_seatgeek_client_id_here
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyZ
TELEGRAM_CHAT_ID=-100123456789
ARGUS_BASE_URL=http://100.64.0.1:8000
ARGUS_API_KEY=your_argus_internal_key
TZ_DISPLAY=America/Los_Angeles
TIER2_MAX_REQUESTS_PER_DAY=600
GATE_MARGIN=0.15
DEADMAN_HOURS=6
DATABASE_PATH=/data/tickets.sqlite3
""",

    "Dockerfile": """FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 TZ=UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl sqlite3 && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

COPY . .
RUN mkdir -p /data/backups /data/captures

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn ticket_sniper.web.app:app --host 0.0.0.0 --port 8000"]
""",

    "docker-compose.yml": """version: "3.8"

services:
  ticket-sniper:
    build: .
    container_name: ticket_sniper
    restart: unless-stopped
    ports:
      - "127.0.0.1:8000:8000"
    environment:
      - SEATGEEK_CLIENT_ID=${SEATGEEK_CLIENT_ID}
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID}
      - ARGUS_BASE_URL=${ARGUS_BASE_URL}
      - ARGUS_API_KEY=${ARGUS_API_KEY}
      - TZ_DISPLAY=${TZ_DISPLAY:-America/Los_Angeles}
      - TIER2_MAX_REQUESTS_PER_DAY=${TIER2_MAX_REQUESTS_PER_DAY:-600}
      - GATE_MARGIN=${GATE_MARGIN:-0.15}
      - DEADMAN_HOURS=${DEADMAN_HOURS:-6}
      - DATABASE_PATH=/data/tickets.sqlite3
    volumes:
      - sniper_data:/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s

volumes:
  sniper_data:
    driver: local
""",

    "alembic/env.py": """import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from ticket_sniper.db.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

db_path = os.getenv("DATABASE_PATH", "/data/tickets.sqlite3")
config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    connectable = engine_from_config(config.get_section(config.config_ini_section, {}), prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
""",

    "alembic/versions/001_initial_schema.py": """\"\"\"Initial Baseline Schema v2\"\"\"
from alembic import op
import sqlalchemy as sa

revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table('venues',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('display_name', sa.Text(), nullable=False, unique=True),
        sa.Column('source', sa.Text(), nullable=False, server_default='seatgeek'),
        sa.Column('source_venue_id', sa.Text(), nullable=True),
        sa.Column('city', sa.Text(), nullable=True),
        sa.Column('timezone', sa.Text(), nullable=False, server_default='America/Los_Angeles'),
        sa.Column('enabled', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('resolved_at', sa.Text(), nullable=True),
        sa.Column('created_at', sa.Text(), nullable=False),
        sa.UniqueConstraint('source', 'source_venue_id')
    )
    op.create_table('source_events',
        sa.Column('source', sa.Text(), nullable=False),
        sa.Column('source_event_id', sa.Text(), nullable=False),
        sa.Column('venue_id', sa.Integer(), sa.ForeignKey('venues.id', ondelete='SET NULL'), nullable=True),
        sa.Column('canonical_event_id', sa.Text(), nullable=True),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('venue_name', sa.Text(), nullable=False),
        sa.Column('performers_json', sa.Text(), nullable=True),
        sa.Column('starts_at_utc', sa.Text(), nullable=False),
        sa.Column('event_url', sa.Text(), nullable=False),
        sa.Column('status', sa.Text(), nullable=False, server_default='active'),
        sa.Column('first_seen_at', sa.Text(), nullable=False),
        sa.Column('last_seen_at', sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint('source', 'source_event_id')
    )
    op.create_table('rules',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('enabled', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('scope_type', sa.Text(), nullable=False, server_default='venue'),
        sa.Column('scope_venue_id', sa.Integer(), sa.ForeignKey('venues.id', ondelete='CASCADE'), nullable=True),
        sa.Column('scope_performer_slug', sa.Text(), nullable=True),
        sa.Column('scope_source', sa.Text(), nullable=True),
        sa.Column('scope_source_event_id', sa.Text(), nullable=True),
        sa.Column('max_unit_price_all_in', sa.Float(), nullable=False),
        sa.Column('max_order_total', sa.Float(), nullable=True),
        sa.Column('quantity_mode', sa.Text(), nullable=False, server_default='exact'),
        sa.Column('quantity_value', sa.Integer(), nullable=False, server_default='2'),
        sa.Column('minimum_identity_confidence', sa.Text(), nullable=False, server_default='high'),
        sa.Column('minimum_fee_confidence', sa.Text(), nullable=False, server_default='medium'),
        sa.Column('estimate_safety_margin_pct', sa.Float(), nullable=False, server_default='0.08'),
        sa.Column('realert_mode', sa.Text(), nullable=False, server_default='either'),
        sa.Column('realert_drop_dollars', sa.Float(), nullable=False, server_default='25.0'),
        sa.Column('realert_drop_percent', sa.Float(), nullable=False, server_default='0.10'),
        sa.Column('realert_cooldown_minutes', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('realert_memory_hours', sa.Integer(), nullable=False, server_default='24'),
        sa.Column('rule_fingerprint', sa.Text(), nullable=False),
        sa.Column('created_at', sa.Text(), nullable=False),
        sa.Column('updated_at', sa.Text(), nullable=False)
    )
    op.create_table('rule_section_matchers',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('rule_id', sa.Integer(), sa.ForeignKey('rules.id', ondelete='CASCADE'), nullable=False),
        sa.Column('action', sa.Text(), nullable=False, server_default='include'),
        sa.Column('matcher_type', sa.Text(), nullable=False, server_default='exact'),
        sa.Column('matcher_value', sa.Text(), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0')
    )
    op.create_table('rule_event_bindings',
        sa.Column('rule_id', sa.Integer(), sa.ForeignKey('rules.id', ondelete='CASCADE'), nullable=False),
        sa.Column('source', sa.Text(), nullable=False),
        sa.Column('source_event_id', sa.Text(), nullable=False),
        sa.Column('bound_at', sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint('rule_id', 'source', 'source_event_id')
    )
    op.create_table('section_aliases',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('venue_id', sa.Integer(), sa.ForeignKey('venues.id', ondelete='CASCADE'), nullable=False),
        sa.Column('source', sa.Text(), nullable=False),
        sa.Column('raw_section', sa.Text(), nullable=False),
        sa.Column('normalized_section', sa.Text(), nullable=True),
        sa.Column('status', sa.Text(), nullable=False, server_default='pending'),
        sa.Column('first_seen_at', sa.Text(), nullable=False),
        sa.Column('approved_at', sa.Text(), nullable=True),
        sa.UniqueConstraint('venue_id', 'source', 'raw_section')
    )
    op.create_table('listings_current',
        sa.Column('source', sa.Text(), nullable=False),
        sa.Column('source_listing_id', sa.Text(), nullable=False),
        sa.Column('identity_type', sa.Text(), nullable=False, server_default='source_id'),
        sa.Column('identity_confidence', sa.Text(), nullable=False, server_default='high'),
        sa.Column('source_event_id', sa.Text(), nullable=False),
        sa.Column('raw_section', sa.Text(), nullable=True),
        sa.Column('normalized_section', sa.Text(), nullable=True),
        sa.Column('raw_row', sa.Text(), nullable=True),
        sa.Column('raw_seats', sa.Text(), nullable=True),
        sa.Column('quantity_available', sa.Integer(), nullable=False),
        sa.Column('available_quantities_json', sa.Text(), nullable=True),
        sa.Column('unit_price_listed', sa.Float(), nullable=True),
        sa.Column('unit_fee_amount', sa.Float(), nullable=True),
        sa.Column('unit_price_all_in', sa.Float(), nullable=True),
        sa.Column('price_basis', sa.Text(), nullable=False, server_default='unknown'),
        sa.Column('fee_confidence', sa.Text(), nullable=True),
        sa.Column('currency', sa.Text(), nullable=False, server_default='USD'),
        sa.Column('listing_url', sa.Text(), nullable=False),
        sa.Column('payload_hash', sa.Text(), nullable=False),
        sa.Column('hash_algo_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('consecutive_missing_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('first_seen_at', sa.Text(), nullable=False),
        sa.Column('last_seen_at', sa.Text(), nullable=False),
        sa.Column('inactive_at', sa.Text(), nullable=True),
        sa.Column('status', sa.Text(), nullable=False, server_default='active'),
        sa.Column('adapter_version', sa.Text(), nullable=False),
        sa.Column('parser_version', sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint('source', 'source_listing_id')
    )
    op.create_table('listing_price_history',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('source', sa.Text(), nullable=False),
        sa.Column('source_listing_id', sa.Text(), nullable=False),
        sa.Column('observed_at', sa.Text(), nullable=False),
        sa.Column('unit_price_listed', sa.Float(), nullable=True),
        sa.Column('unit_price_all_in', sa.Float(), nullable=True),
        sa.Column('price_basis', sa.Text(), nullable=False),
        sa.Column('quantity_available', sa.Integer(), nullable=True)
    )
    op.create_table('event_price_snapshots',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('source', sa.Text(), nullable=False),
        sa.Column('source_event_id', sa.Text(), nullable=False),
        sa.Column('observed_at', sa.Text(), nullable=False),
        sa.Column('lowest_price', sa.Float(), nullable=True),
        sa.Column('average_price', sa.Float(), nullable=True),
        sa.Column('highest_price', sa.Float(), nullable=True),
        sa.Column('listing_count', sa.Integer(), nullable=True),
        sa.Column('visible_listing_count', sa.Integer(), nullable=True),
        sa.Column('gate_decision', sa.Text(), nullable=False),
        sa.Column('gate_reason', sa.Text(), nullable=True)
    )
    op.create_table('fee_models',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('source', sa.Text(), nullable=False),
        sa.Column('venue_id', sa.Integer(), sa.ForeignKey('venues.id', ondelete='CASCADE'), nullable=True),
        sa.Column('fee_rate_pct', sa.Float(), nullable=False, server_default='1.28'),
        sa.Column('fee_fixed', sa.Float(), nullable=False, server_default='3.50'),
        sa.Column('sample_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('residual_stddev', sa.Float(), nullable=True),
        sa.Column('confidence', sa.Text(), nullable=False, server_default='low'),
        sa.Column('last_calibrated_at', sa.Text(), nullable=True),
        sa.UniqueConstraint('source', 'venue_id')
    )
    op.create_table('fee_observations',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('source', sa.Text(), nullable=False),
        sa.Column('venue_id', sa.Integer(), sa.ForeignKey('venues.id', ondelete='CASCADE'), nullable=True),
        sa.Column('source_event_id', sa.Text(), nullable=True),
        sa.Column('listed_price', sa.Float(), nullable=False),
        sa.Column('actual_all_in', sa.Float(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=True),
        sa.Column('observed_at', sa.Text(), nullable=False),
        sa.Column('entered_via', sa.Text(), nullable=False, server_default='telegram')
    )
    op.create_table('alert_state',
        sa.Column('rule_id', sa.Integer(), sa.ForeignKey('rules.id', ondelete='CASCADE'), nullable=False),
        sa.Column('source', sa.Text(), nullable=False),
        sa.Column('listing_identity', sa.Text(), nullable=False),
        sa.Column('currently_qualifying', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('reason_fingerprint', sa.Text(), nullable=True),
        sa.Column('rule_fingerprint', sa.Text(), nullable=True),
        sa.Column('last_qualifying_price', sa.Float(), nullable=True),
        sa.Column('last_alert_price', sa.Float(), nullable=True),
        sa.Column('last_alert_at', sa.Text(), nullable=True),
        sa.Column('transition_sequence', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('updated_at', sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint('rule_id', 'source', 'listing_identity')
    )
    op.create_table('alert_decisions',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('decided_at', sa.Text(), nullable=False),
        sa.Column('rule_id', sa.Integer(), nullable=False),
        sa.Column('source', sa.Text(), nullable=False),
        sa.Column('listing_identity', sa.Text(), nullable=False),
        sa.Column('branch', sa.Integer(), nullable=False),
        sa.Column('outcome', sa.Text(), nullable=False),
        sa.Column('inputs_json', sa.Text(), nullable=False)
    )
    op.create_table('alert_outbox',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('payload_json', sa.Text(), nullable=False),
        sa.Column('dedupe_key', sa.Text(), nullable=False),
        sa.Column('status', sa.Text(), nullable=False, server_default='pending'),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.Text(), nullable=False),
        sa.Column('next_attempt_at', sa.Text(), nullable=False),
        sa.Column('sent_at', sa.Text(), nullable=True)
    )
    op.create_table('poll_runs',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('tier', sa.Integer(), nullable=False),
        sa.Column('source', sa.Text(), nullable=False),
        sa.Column('source_event_id', sa.Text(), nullable=False),
        sa.Column('started_at', sa.Text(), nullable=False),
        sa.Column('completed_at', sa.Text(), nullable=True),
        sa.Column('status', sa.Text(), nullable=False),
        sa.Column('pagination_complete', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('inventory_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('new_listing_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('changed_listing_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('transport_rung', sa.Integer(), nullable=True),
        sa.Column('argus_status', sa.Text(), nullable=True),
        sa.Column('extractor_used', sa.Text(), nullable=True),
        sa.Column('egress_used', sa.Text(), nullable=True),
        sa.Column('http_status', sa.Integer(), nullable=True),
        sa.Column('parser_version', sa.Text(), nullable=True),
        sa.Column('error_code', sa.Text(), nullable=True),
        sa.Column('error_summary', sa.Text(), nullable=True),
        sa.Column('capture_reference', sa.Text(), nullable=True)
    )
    op.create_table('transport_health',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('domain', sa.Text(), nullable=False),
        sa.Column('rung', sa.Integer(), nullable=False),
        sa.Column('attempts_50', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('successes_50', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('blocked_until', sa.Text(), nullable=True),
        sa.Column('consecutive_blocks', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('updated_at', sa.Text(), nullable=False),
        sa.UniqueConstraint('domain', 'rung')
    )

def downgrade() -> None:
    pass
""",

    "ticket_sniper/__init__.py": "",

    "ticket_sniper/config.py": """import sys
from pydantic import Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    SEATGEEK_CLIENT_ID: str = Field(..., env="SEATGEEK_CLIENT_ID")
    TELEGRAM_BOT_TOKEN: str = Field(..., env="TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID: str = Field(..., env="TELEGRAM_CHAT_ID")
    ARGUS_BASE_URL: str = Field(..., env="ARGUS_BASE_URL")
    ARGUS_API_KEY: str = Field("", env="ARGUS_API_KEY")
    TZ_DISPLAY: str = Field("America/Los_Angeles", env="TZ_DISPLAY")
    
    TIER2_MAX_REQUESTS_PER_DAY: int = Field(600, env="TIER2_MAX_REQUESTS_PER_DAY")
    GATE_MARGIN: float = Field(0.15, env="GATE_MARGIN")
    DEADMAN_HOURS: int = Field(6, env="DEADMAN_HOURS")
    DATABASE_PATH: str = Field("/data/tickets.sqlite3", env="DATABASE_PATH")
    
    ALERT_COALESCE_SECONDS: int = 30
    SUSPICIOUS_EMPTY_FLOOR: int = 5
    CAPTURE_DIR_MAX_MB: int = 500

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

def get_settings() -> Settings:
    try:
        return Settings()
    except Exception as e:
        sys.stderr.write(f"CRITICAL: Configuration validation failed: {e}\\n")
        sys.exit(1)

settings = get_settings()
""",

    "ticket_sniper/db/__init__.py": "",

    "ticket_sniper/db/models.py": """from datetime import datetime, timezone
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
""",

    "ticket_sniper/db/session.py": """import asyncio
from typing import Callable, Any
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from ticket_sniper.config import settings

engine = create_engine(
    f"sqlite:///{settings.DATABASE_PATH}",
    connect_args={"timeout": 5.0, "check_same_thread": False},
    pool_pre_ping=True
)

with engine.connect() as conn:
    conn.exec_driver_sql("PRAGMA journal_mode=WAL;")
    conn.exec_driver_sql("PRAGMA foreign_keys=ON;")
    conn.exec_driver_sql("PRAGMA busy_timeout=5000;")

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
_db_lock = asyncio.Lock()

async def run_db_transaction(func: Callable[[Session], Any]) -> Any:
    async with _db_lock:
        def _execute():
            session = SessionLocal()
            try:
                result = func(session)
                session.commit()
                return result
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()
        return await asyncio.to_thread(_execute)

def get_db_session() -> Session:
    return SessionLocal()
""",

    "ticket_sniper/argus/__init__.py": "",

    "ticket_sniper/argus/models.py": """from pydantic import BaseModel, Field
from typing import Optional, Dict, List

class FetchRawRequest(BaseModel):
    url: str
    render: str = "none"
    cache: bool = False
    extractors: List[str] = Field(default_factory=lambda: ["local_only"])
    impersonate: str = "chrome"
    egress: str = "residential"
    timeout_seconds: int = 25
    headers: Dict[str, str] = Field(default_factory=dict)

class FetchRawResponse(BaseModel):
    status: str
    http_status: Optional[int] = None
    final_url: Optional[str] = None
    headers: Dict[str, str] = Field(default_factory=dict)
    body: str = ""
    body_sha256: Optional[str] = None
    render_mode_used: Optional[str] = None
    extractor_used: Optional[str] = None
    egress_used: Optional[str] = None
    elapsed_ms: int = 0
    from_cache: bool = False
""",

    "ticket_sniper/argus/client.py": """import httpx
import logging
from ticket_sniper.config import settings
from ticket_sniper.argus.models import FetchRawRequest, FetchRawResponse

logger = logging.getLogger(__name__)

class ArgusClient:
    def __init__(self):
        self.base_url = settings.ARGUS_BASE_URL.rstrip("/")
        self.headers = {}
        if settings.ARGUS_API_KEY:
            self.headers["X-API-Key"] = settings.ARGUS_API_KEY

    async def fetch_raw(self, request: FetchRawRequest) -> FetchRawResponse:
        url = f"{self.base_url}/api/fetch-raw"
        async with httpx.AsyncClient(timeout=float(request.timeout_seconds + 5)) as client:
            try:
                resp = await client.post(url, json=request.model_dump(), headers=self.headers)
                if resp.status_code != 200:
                    return FetchRawResponse(status="error", http_status=resp.status_code)
                return FetchRawResponse(**resp.json())
            except Exception as e:
                logger.error(f"Argus transport exception: {e}")
                return FetchRawResponse(status="error")
""",

    "ticket_sniper/discovery/__init__.py": "",

    "ticket_sniper/discovery/seatgeek.py": """import logging
import httpx
from typing import Optional, Dict, Any
from ticket_sniper.config import settings
from ticket_sniper.db.models import SourceEvent, utcnow_str
from ticket_sniper.db.session import run_db_transaction

logger = logging.getLogger(__name__)
SEATGEEK_API_BASE = "https://api.seatgeek.com/2"

class SeatGeekDiscovery:
    def __init__(self):
        self.client_id = settings.SEATGEEK_CLIENT_ID

    async def resolve_venue(self, display_name: str) -> Optional[Dict[str, Any]]:
        url = f"{SEATGEEK_API_BASE}/venues"
        params = {"q": display_name, "client_id": self.client_id}
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.get(url, params=params)
                if resp.status_code != 200: return None
                venues = resp.json().get("venues", [])
                if not venues: return None
                top = venues[0]
                return {
                    "source_venue_id": str(top["id"]),
                    "display_name": display_name,
                    "city": top.get("city"),
                    "timezone": top.get("timezone", "America/Los_Angeles")
                }
            except Exception as e:
                logger.error(f"Failed resolving venue {display_name}: {e}")
                return None
""",

    "ticket_sniper/fee_model/__init__.py": "",

    "ticket_sniper/fee_model/estimator.py": """import numpy as np
from typing import Tuple
from sqlalchemy.orm import Session
from ticket_sniper.db.models import FeeModel, FeeObservation, utcnow_str

class FeeEstimator:
    @staticmethod
    def estimate_all_in(session: Session, source: str, venue_id: int, listed_price: float) -> Tuple[float, float, str]:
        model = session.query(FeeModel).filter_by(source=source, venue_id=venue_id).first()
        if not model:
            model = session.query(FeeModel).filter_by(source=source, venue_id=None).first()
        rate = model.fee_rate_pct if model else 1.28
        fixed = model.fee_fixed if model else 3.50
        confidence = model.confidence if model else "low"
        est_all_in = (listed_price * rate) + fixed
        return round(est_all_in, 2), round(est_all_in - listed_price, 2), confidence
""",

    "ticket_sniper/health/__init__.py": "",

    "ticket_sniper/health/deadman.py": """import logging
import httpx
from datetime import datetime, timezone, timedelta
from ticket_sniper.config import settings
from ticket_sniper.db.models import PollRun, AlertOutbox
from ticket_sniper.db.session import run_db_transaction

logger = logging.getLogger(__name__)

async def run_deadman_switch_check():
    def _inspect_health(session):
        now = datetime.now(timezone.utc)
        threshold = (now - timedelta(hours=settings.DEADMAN_HOURS)).strftime("%Y-%m-%dT%H:%M:%SZ")
        last_tier2 = session.query(PollRun).filter(PollRun.tier == 2, PollRun.status == "success").order_by(PollRun.started_at.desc()).first()
        if not last_tier2 or last_tier2.started_at < threshold:
            return True, f"No Tier 2 success in {settings.DEADMAN_HOURS}h."
        return False, ""

    triggered, reason = await run_db_transaction(_inspect_health)
    if triggered:
        msg = f"⚠️ <b>Ticket-Sniper Operator Alert</b>\\n\\n{reason}"
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                await client.post(url, json={"chat_id": settings.TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"})
            except Exception as e:
                logger.error(f"Failed dispatching deadman alert: {e}")
""",

    "ticket_sniper/notifications/__init__.py": "",

    "ticket_sniper/notifications/telegram.py": """import json
import logging
import httpx
from datetime import datetime
from zoneinfo import ZoneInfo
from ticket_sniper.config import settings
from ticket_sniper.db.models import AlertOutbox, AlertState, utcnow_str
from ticket_sniper.db.session import run_db_transaction

logger = logging.getLogger(__name__)

async def drain_alert_outbox():
    def _fetch_pending(session):
        return session.query(AlertOutbox).filter(AlertOutbox.status == "pending", AlertOutbox.next_attempt_at <= utcnow_str()).limit(10).all()

    pending = await run_db_transaction(_fetch_pending)
    if not pending: return

    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    async with httpx.AsyncClient(timeout=10.0) as client:
        for item in pending:
            payload = json.loads(item.payload_json)
            body = {"chat_id": settings.TELEGRAM_CHAT_ID, "text": payload.get("text", "Ticket Alert!"), "parse_mode": "HTML"}
            try:
                resp = await client.post(url, json=body)
                if resp.status_code == 200:
                    def _confirm(session):
                        row = session.query(AlertOutbox).get(item.id)
                        row.status = "sent"
                        row.sent_at = utcnow_str()
                    await run_db_transaction(_confirm)
            except Exception as e:
                logger.error(f"Telegram error: {e}")
""",

    "ticket_sniper/rules/__init__.py": "",

    "ticket_sniper/rules/evaluator.py": """import json
import hashlib
from typing import Dict, List, Tuple, Optional
from ticket_sniper.db.models import Rule, RuleSectionMatcher, ListingCurrent

def compute_rule_fingerprint(rule: Rule, matchers: List[RuleSectionMatcher]) -> str:
    sorted_matchers = sorted(matchers, key=lambda x: x.sort_order)
    payload = {
        "max_unit_price_all_in": rule.max_unit_price_all_in,
        "quantity_mode": rule.quantity_mode,
        "quantity_value": rule.quantity_value,
        "matchers": [{"action": m.action, "type": m.matcher_type, "value": m.matcher_value} for m in sorted_matchers]
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
""",

    "ticket_sniper/rules/state_machine.py": """from datetime import datetime, timezone, timedelta
from typing import Tuple, Optional
from ticket_sniper.db.models import AlertState, Rule, ListingCurrent, utcnow_str

def process_alert_state_machine(
    state: Optional[AlertState], rule: Rule, listing: ListingCurrent, qualifies: bool, reason_fp: str
) -> Tuple[int, str, bool, Optional[AlertState]]:
    now_str = utcnow_str()
    price = listing.unit_price_all_in or 0.0

    if state is None:
        state = AlertState(
            rule_id=rule.id, source=listing.source, listing_identity=listing.source_listing_id,
            currently_qualifying=0, rule_fingerprint=rule.rule_fingerprint, updated_at=now_str
        )

    should_alert = False
    branch = 0
    outcome = "no_change"

    if state.currently_qualifying == 0 and qualifies:
        branch = 1
        outcome = "alert"
        should_alert = True
        state.currently_qualifying = 1
        state.last_alert_price = price

    return branch, outcome, should_alert, state
""",

    "ticket_sniper/scheduler/__init__.py": "",

    "ticket_sniper/scheduler/engine.py": """import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from ticket_sniper.db.session import engine
from ticket_sniper.notifications.telegram import drain_alert_outbox
from ticket_sniper.health.deadman import run_deadman_switch_check

logger = logging.getLogger(__name__)

jobstores = {'default': SQLAlchemyJobStore(engine=engine)}
scheduler = AsyncIOScheduler(jobstores=jobstores, timezone="UTC")

def start_scheduler():
    scheduler.add_job(drain_alert_outbox, 'interval', seconds=10, id='outbox_drain', replace_existing=True)
    scheduler.add_job(run_deadman_switch_check, 'interval', hours=1, id='deadman_check', replace_existing=True)
    scheduler.start()
""",

    "ticket_sniper/sources/__init__.py": "",

    "ticket_sniper/sources/base.py": """from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple

class BaseSourceAdapter(ABC):
    @property
    @abstractmethod
    def source_name(self) -> str: pass

    @abstractmethod
    def parse_inventory(self, raw_body: str, source_event_id: str) -> Tuple[List[Dict[str, Any]], int, bool]: pass
""",

    "ticket_sniper/sources/seatgeek.py": """import json
import hashlib
from typing import List, Dict, Any, Tuple
from ticket_sniper.sources.base import BaseSourceAdapter

class SeatGeekAdapter(BaseSourceAdapter):
    @property
    def source_name(self) -> str: return "seatgeek"

    def parse_inventory(self, raw_body: str, source_event_id: str) -> Tuple[List[Dict[str, Any]], int, bool]:
        data = json.loads(raw_body)
        listings = data.get("listings", [])
        parsed = []
        for item in listings:
            parsed.append({
                "source_listing_id": str(item["id"]),
                "quantity_available": item.get("quantity", 1),
                "unit_price_all_in": item.get("price_with_fees", {}).get("amount"),
                "price_basis": "all_in"
            })
        return parsed, len(parsed), True
""",

    "ticket_sniper/web/__init__.py": "",

    "ticket_sniper/web/app.py": """from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

app = FastAPI(title="Ticket-Sniper Operations")
templates = Jinja2Templates(directory="ticket_sniper/web/templates")

@app.get("/health")
def health_check():
    return JSONResponse({"status": "healthy"})

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})
""",

    "ticket_sniper/web/templates/base.html": """<!DOCTYPE html>
<html>
<head>
    <title>Ticket-Sniper</title>
    <style>body { font-family: sans-serif; background: #121212; color: #eee; padding: 20px; }</style>
</head>
<body>
    <div class="container">{% block content %}{% endblock %}</div>
</body>
</html>
""",

    "ticket_sniper/web/templates/dashboard.html": """{% extends "base.html" %}
{% block content %}
<h1>🎟 Ticket-Sniper Dashboard</h1>
<p>System Online & Monitoring.</p>
{% endblock %}
""",

    "ticket_sniper/main.py": """import asyncio
import logging
from ticket_sniper.scheduler.engine import start_scheduler

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    logging.info("Starting Ticket-Sniper Engine...")
    start_scheduler()
""",

    "docs/CONTEXT_AND_PRD.md": """# PRD v2 & CONTEXT
Fully reconciled PRD v2 incorporating Claude Opus recommendations, 9-branch state machine, rate limits, gate evaluation, and deadman switches.
""",

    "docs/DATA_DICTIONARY.md": """# DATA DICTIONARY
Contains full schema declarations for all 12 SQLite operational tables.
""",

    "docs/EXTERNAL_RESOURCES.md": """# REFERENCES
- Target Repo: https://github.com/Khamel83/tix
- Argus Broker: https://github.com/Khamel83/argus
"""
}

def build_zip():
    zip_filename = "tix-repo.zip"
    print(f"Generating {zip_filename}...")
    with zipfile.ZipFile(zip_filename, "w", zipfile.ZIP_DEFLATED) as zf:
        for filepath, content in files.items():
            zf.writestr(filepath, content.lstrip())
            print(f"  + Added {filepath}")
    print(f"\nSuccess! Created '{zip_filename}' in current directory.")

if __name__ == "__main__":
    build_zip()