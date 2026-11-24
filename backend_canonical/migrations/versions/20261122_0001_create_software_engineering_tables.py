"""Create software engineering demo tables.

Revision ID: 20261122_0001
Revises:
Create Date: 2026-11-22
"""
from alembic import op
import sqlalchemy as sa

revision = "20261122_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("status", sa.Text(), nullable=False, server_default="active"),
        sa.Column("start_date", sa.Date()),
        sa.Column("end_date", sa.Date()),
        sa.Column("budget", sa.Float()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "teams",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id")),
        sa.Column("leader_id", sa.Integer()),
        sa.Column("description", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "developers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), unique=True),
        sa.Column("role", sa.Text(), nullable=False, server_default="developer"),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id")),
        sa.Column("experience_years", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skills", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "requirements",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id")),
        sa.Column("priority", sa.Text(), nullable=False, server_default="medium"),
        sa.Column("status", sa.Text(), nullable=False, server_default="open"),
        sa.Column("complexity", sa.Text(), nullable=False, server_default="medium"),
        sa.Column("assigned_to", sa.Integer(), sa.ForeignKey("developers.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("requirement_id", sa.Integer(), sa.ForeignKey("requirements.id")),
        sa.Column("assigned_to", sa.Integer(), sa.ForeignKey("developers.id")),
        sa.Column("status", sa.Text(), nullable=False, server_default="todo"),
        sa.Column("priority", sa.Text(), nullable=False, server_default="medium"),
        sa.Column("estimated_hours", sa.Float()),
        sa.Column("actual_hours", sa.Float()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("tasks")
    op.drop_table("requirements")
    op.drop_table("developers")
    op.drop_table("teams")
    op.drop_table("projects")
