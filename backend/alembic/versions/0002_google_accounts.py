"""Allow verified Google accounts to authenticate without passwords.

Revision ID: 0002_google_accounts
Revises: 0001_auth_profiles
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_google_accounts"
down_revision = "0001_auth_profiles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("google_sub", sa.String(length=255)))
    op.create_index("ix_users_google_sub", "users", ["google_sub"], unique=True)
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "password_hash",
            existing_type=sa.String(length=512),
            nullable=True,
        )


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "password_hash",
            existing_type=sa.String(length=512),
            nullable=False,
        )
    op.drop_index("ix_users_google_sub", table_name="users")
    op.drop_column("users", "google_sub")
