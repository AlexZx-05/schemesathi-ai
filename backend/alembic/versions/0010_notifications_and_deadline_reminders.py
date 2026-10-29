"""Add notification preferences and verified deadline reminder metadata.

Revision ID: 0010_notifications_and_deadline_reminders
Revises: 0009_scheme_guidance_workflows
"""

from alembic import op
import sqlalchemy as sa

revision = "0010_notifications_and_deadline_reminders"
down_revision = "0009_scheme_guidance_workflows"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("scheme_deadlines") as batch_op:
        batch_op.add_column(sa.Column("source_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.create_foreign_key(
            "fk_scheme_deadlines_source_id_scheme_sources",
            "scheme_sources",
            ["source_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("ix_scheme_deadlines_source_id", ["source_id"])

    with op.batch_alter_table("notifications") as batch_op:
        batch_op.add_column(sa.Column("dedupe_key", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("deadline_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("source_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("source_verified_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(
            sa.Column("is_valid", sa.Boolean(), nullable=False, server_default=sa.true())
        )
        batch_op.add_column(
            sa.Column("in_app_visible", sa.Boolean(), nullable=False, server_default=sa.true())
        )
        batch_op.add_column(
            sa.Column(
                "email_delivery_status",
                sa.String(length=20),
                nullable=False,
                server_default="not_requested",
            )
        )
        batch_op.add_column(
            sa.Column("email_attempts", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.add_column(sa.Column("email_next_attempt_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("email_sent_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("email_failure", sa.String(length=500), nullable=True))
        batch_op.create_foreign_key(
            "fk_notifications_deadline_id_scheme_deadlines",
            "scheme_deadlines",
            ["deadline_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_notifications_source_id_scheme_sources",
            "scheme_sources",
            ["source_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("ix_notifications_deadline_id", ["deadline_id"])
        batch_op.create_unique_constraint("uq_notifications_dedupe_key", ["dedupe_key"])
        batch_op.create_check_constraint(
            "ck_notifications_email_delivery_status",
            "email_delivery_status IN "
            "('not_requested', 'pending', 'sending', 'sent', 'failed', 'skipped', 'invalidated')",
        )

    with op.batch_alter_table("notification_preferences") as batch_op:
        batch_op.add_column(
            sa.Column("reminders_enabled", sa.Boolean(), nullable=False, server_default=sa.true())
        )
        batch_op.add_column(
            sa.Column(
                "deadline_reminders_enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            )
        )
        batch_op.add_column(
            sa.Column(
                "timezone",
                sa.String(length=80),
                nullable=False,
                server_default="Asia/Kolkata",
            )
        )
        batch_op.create_check_constraint(
            "ck_notification_preferences_timezone_length",
            "length(timezone) BETWEEN 1 AND 80",
        )


def downgrade() -> None:
    with op.batch_alter_table("notification_preferences") as batch_op:
        batch_op.drop_constraint("ck_notification_preferences_timezone_length", type_="check")
        batch_op.drop_column("timezone")
        batch_op.drop_column("deadline_reminders_enabled")
        batch_op.drop_column("reminders_enabled")

    with op.batch_alter_table("notifications") as batch_op:
        batch_op.drop_constraint("ck_notifications_email_delivery_status", type_="check")
        batch_op.drop_constraint("uq_notifications_dedupe_key", type_="unique")
        batch_op.drop_index("ix_notifications_deadline_id")
        batch_op.drop_constraint("fk_notifications_source_id_scheme_sources", type_="foreignkey")
        batch_op.drop_constraint("fk_notifications_deadline_id_scheme_deadlines", type_="foreignkey")
        for column in (
            "email_failure",
            "email_sent_at",
            "email_next_attempt_at",
            "email_attempts",
            "email_delivery_status",
            "is_valid",
            "in_app_visible",
            "source_verified_at",
            "source_id",
            "deadline_at",
            "deadline_id",
            "dedupe_key",
        ):
            batch_op.drop_column(column)

    with op.batch_alter_table("scheme_deadlines") as batch_op:
        batch_op.drop_index("ix_scheme_deadlines_source_id")
        batch_op.drop_constraint("fk_scheme_deadlines_source_id_scheme_sources", type_="foreignkey")
        batch_op.drop_column("last_verified_at")
        batch_op.drop_column("source_id")
