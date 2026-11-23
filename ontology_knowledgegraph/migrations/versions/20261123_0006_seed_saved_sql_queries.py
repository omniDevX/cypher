"""Seed saved SQL queries from the existing lineage source.

Revision ID: 20261123_0006
Revises: 20261123_0005
Create Date: 2026-11-23
"""
import sys
from pathlib import Path

from alembic import op
import sqlalchemy as sa

PROJECT_ROOT = Path(__file__).resolve().parents[2]

revision = "20261123_0006"
down_revision = "20261123_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    sys.path.insert(0, str(PROJECT_ROOT))
    from app.sql_lineage_parser import load_sql_lineage

    op.add_column(
        "saved_sql_queries",
        sa.Column("is_seeded", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    connection = op.get_bind()
    _, _, queries = load_sql_lineage()
    insert_query = sa.text(
        "INSERT INTO saved_sql_queries (name, sql_text, is_seeded) "
        "SELECT :name, :sql_text, TRUE "
        "WHERE NOT EXISTS ("
        "SELECT 1 FROM saved_sql_queries WHERE name = :name AND sql_text = :sql_text"
        ")"
    )
    for query in queries:
        connection.execute(
            insert_query,
            {"name": query["name"], "sql_text": query["statement"]},
        )


def downgrade() -> None:
    op.execute("DELETE FROM saved_sql_queries WHERE is_seeded = TRUE")
    op.drop_column("saved_sql_queries", "is_seeded")
