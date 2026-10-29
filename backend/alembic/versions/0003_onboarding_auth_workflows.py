"""Add verification, password recovery, and onboarding fields.

Revision ID: 0003_onboarding_auth_workflows
Revises: 0002_google_accounts
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_onboarding_auth_workflows"
down_revision = "0002_google_accounts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "email_verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    op.add_column("profiles", sa.Column("district", sa.String(length=100)))
    op.add_column("profiles", sa.Column("area_type", sa.String(length=10)))
    op.add_column("profiles", sa.Column("employment_status", sa.String(length=40)))
    op.add_column("profiles", sa.Column("worker_category", sa.String(length=80)))
    op.add_column("profiles", sa.Column("current_student", sa.Boolean()))
    op.add_column("profiles", sa.Column("household_size", sa.Integer()))
    op.create_table(
        "auth_tokens",
        sa.Column("token_hash", sa.String(length=64), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("purpose", sa.String(length=20), nullable=False),
        sa.Column("expires_at", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_auth_tokens_user_id", "auth_tokens", ["user_id"])
    op.create_index("ix_auth_tokens_purpose", "auth_tokens", ["purpose"])
    op.create_index("ix_auth_tokens_expires_at", "auth_tokens", ["expires_at"])
    op.create_table(
        "development_emails",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("purpose", sa.String(length=20), nullable=False),
        sa.Column("token", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_development_emails_email", "development_emails", ["email"]
    )
    op.create_table(
        "auth_rate_limits",
        sa.Column("key_hash", sa.String(length=64), primary_key=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("window_started_at", sa.Integer(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("auth_rate_limits")
    op.drop_index("ix_development_emails_email", table_name="development_emails")
    op.drop_table("development_emails")
    op.drop_index("ix_auth_tokens_expires_at", table_name="auth_tokens")
    op.drop_index("ix_auth_tokens_purpose", table_name="auth_tokens")
    op.drop_index("ix_auth_tokens_user_id", table_name="auth_tokens")
    op.drop_table("auth_tokens")
    op.drop_column("profiles", "household_size")
    op.drop_column("profiles", "current_student")
    op.drop_column("profiles", "worker_category")
    op.drop_column("profiles", "employment_status")
    op.drop_column("profiles", "area_type")
    op.drop_column("profiles", "district")
    op.drop_column("users", "email_verified")
