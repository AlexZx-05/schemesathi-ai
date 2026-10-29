"""Add administrator review attribution and change history.

Revision ID: 0011_admin_review_history
Revises: 0010_notifications_and_deadline_reminders
"""

from alembic import op
import sqlalchemy as sa

revision = "0011_admin_review_history"
down_revision = "0010_notifications_and_deadline_reminders"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("schemes") as batch_op:
        batch_op.add_column(sa.Column("reviewed_by_user_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_schemes_reviewed_by_user_id_users",
            "users",
            ["reviewed_by_user_id"],
            ["id"],
            ondelete="SET NULL",
        )

    with op.batch_alter_table("scheme_sources") as batch_op:
        batch_op.add_column(sa.Column("reviewed_by_user_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_scheme_sources_reviewed_by_user_id_users",
            "users",
            ["reviewed_by_user_id"],
            ["id"],
            ondelete="SET NULL",
        )

    with op.batch_alter_table("scheme_reports") as batch_op:
        batch_op.add_column(sa.Column("reviewed_by_user_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("review_notes", sa.Text(), nullable=True))
        batch_op.create_foreign_key(
            "fk_scheme_reports_reviewed_by_user_id_users",
            "users",
            ["reviewed_by_user_id"],
            ["id"],
            ondelete="SET NULL",
        )

    op.create_table(
        "scheme_review_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("scheme_id", sa.Integer(), nullable=True),
        sa.Column("actor_user_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("before_snapshot", sa.JSON(), nullable=True),
        sa.Column("after_snapshot", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["scheme_id"], ["schemes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_scheme_review_history_scheme_id", "scheme_review_history", ["scheme_id"])
    op.create_index("ix_scheme_review_history_actor_user_id", "scheme_review_history", ["actor_user_id"])
    op.create_index("ix_scheme_review_history_created_at", "scheme_review_history", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_scheme_review_history_created_at", table_name="scheme_review_history")
    op.drop_index("ix_scheme_review_history_actor_user_id", table_name="scheme_review_history")
    op.drop_index("ix_scheme_review_history_scheme_id", table_name="scheme_review_history")
    op.drop_table("scheme_review_history")

    with op.batch_alter_table("scheme_reports") as batch_op:
        batch_op.drop_constraint("fk_scheme_reports_reviewed_by_user_id_users", type_="foreignkey")
        batch_op.drop_column("review_notes")
        batch_op.drop_column("reviewed_by_user_id")

    with op.batch_alter_table("scheme_sources") as batch_op:
        batch_op.drop_constraint("fk_scheme_sources_reviewed_by_user_id_users", type_="foreignkey")
        batch_op.drop_column("reviewed_by_user_id")

    with op.batch_alter_table("schemes") as batch_op:
        batch_op.drop_constraint("fk_schemes_reviewed_by_user_id_users", type_="foreignkey")
        batch_op.drop_column("reviewed_by_user_id")
