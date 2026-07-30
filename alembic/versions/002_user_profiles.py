"""Add user profile preferences"""
from alembic import op
import sqlalchemy as sa

revision = "002_user_profiles"
down_revision = "001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_profiles",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("slug", sa.Text(), nullable=False, unique=True),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("home_city", sa.Text(), nullable=True),
        sa.Column("timezone", sa.Text(), nullable=False, server_default="America/Los_Angeles"),
        sa.Column("default_source", sa.Text(), nullable=False, server_default="seatgeek"),
        sa.Column("preferred_quantity", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("max_unit_price_all_in", sa.Float(), nullable=True),
        sa.Column("max_order_total", sa.Float(), nullable=True),
        sa.Column("enabled", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
    )
    op.create_table(
        "profile_sports",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("profile_id", sa.Integer(), sa.ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sport_name", sa.Text(), nullable=False),
        sa.Column("performer_slug", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.UniqueConstraint("profile_id", "sport_name"),
    )
    op.create_table(
        "profile_venues",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("profile_id", sa.Integer(), sa.ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False, server_default="seatgeek"),
        sa.Column("source_venue_id", sa.Text(), nullable=True),
        sa.Column("city", sa.Text(), nullable=True),
        sa.Column("timezone", sa.Text(), nullable=False, server_default="America/Los_Angeles"),
        sa.Column("enabled", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.UniqueConstraint("profile_id", "source", "display_name"),
    )


def downgrade() -> None:
    op.drop_table("profile_venues")
    op.drop_table("profile_sports")
    op.drop_table("user_profiles")
