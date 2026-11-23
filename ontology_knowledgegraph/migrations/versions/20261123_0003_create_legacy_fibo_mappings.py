"""Create editable legacy-to-FIBO mappings.

Revision ID: 20261123_0003
Revises: 20261122_0002
Create Date: 2026-11-23
"""
from alembic import op
import sqlalchemy as sa

revision = "20261123_0003"
down_revision = "20261122_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "legacy_fibo_mappings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("source_ref", sa.Text(), nullable=False, unique=True),
        sa.Column("source_kind", sa.Text(), nullable=False),
        sa.Column("source_table", sa.Text(), nullable=False),
        sa.Column("source_field", sa.Text()),
        sa.Column("graph_element", sa.Text(), nullable=False),
        sa.Column("fibo_target_kind", sa.Text(), nullable=False),
        sa.Column("fibo_iri", sa.Text(), nullable=False),
        sa.Column("fibo_label", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False, server_default=""),
        sa.Column("is_cde", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("cde_definition", sa.Text()),
        sa.Column("review_status", sa.Text(), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("source_kind IN ('entity', 'field', 'relationship')", name="ck_legacy_fibo_source_kind"),
        sa.CheckConstraint("fibo_target_kind IN ('class', 'property')", name="ck_legacy_fibo_target_kind"),
        sa.CheckConstraint("review_status IN ('draft', 'reviewed')", name="ck_legacy_fibo_review_status"),
        sa.CheckConstraint("NOT is_cde OR source_kind = 'field'", name="ck_legacy_fibo_cde_field_only"),
    )


def downgrade() -> None:
    op.drop_table("legacy_fibo_mappings")
