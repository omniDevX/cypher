"""Use current graph vocabulary and make FIBO IRIs optional.

Revision ID: 20261123_0004
Revises: 20261123_0003
Create Date: 2026-11-23
"""
from alembic import op
import sqlalchemy as sa

revision = "20261123_0004"
down_revision = "20261123_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_legacy_fibo_target_kind", "legacy_fibo_mappings", type_="check")
    op.create_check_constraint(
        "ck_legacy_fibo_target_kind",
        "legacy_fibo_mappings",
        "fibo_target_kind IN ('class', 'property', 'relationship')",
    )
    op.alter_column(
        "legacy_fibo_mappings",
        "fibo_iri",
        existing_type=sa.Text(),
        nullable=True,
    )


def downgrade() -> None:
    op.execute(
        "UPDATE legacy_fibo_mappings SET fibo_target_kind='property' "
        "WHERE fibo_target_kind='relationship'"
    )
    op.execute("UPDATE legacy_fibo_mappings SET fibo_iri='' WHERE fibo_iri IS NULL")
    op.drop_constraint("ck_legacy_fibo_target_kind", "legacy_fibo_mappings", type_="check")
    op.create_check_constraint(
        "ck_legacy_fibo_target_kind",
        "legacy_fibo_mappings",
        "fibo_target_kind IN ('class', 'property')",
    )
    op.alter_column(
        "legacy_fibo_mappings",
        "fibo_iri",
        existing_type=sa.Text(),
        nullable=False,
    )
