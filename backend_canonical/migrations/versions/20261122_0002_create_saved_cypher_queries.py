"""Create table for saved Cypher queries.

Revision ID: 20261122_0002
Revises: 20261122_0001
Create Date: 2026-11-22
"""
from alembic import op
import sqlalchemy as sa

revision = "20261122_0002"
down_revision = "20261122_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "saved_cypher_queries",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("cypher", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("saved_cypher_queries")
