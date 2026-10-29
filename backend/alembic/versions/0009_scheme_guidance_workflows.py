"""Add persistent document readiness and controlled application tracking.

Revision ID: 0009_scheme_guidance_workflows
Revises: 0008_assistant_conversation_metadata
"""

from alembic import op
import sqlalchemy as sa

revision = "0009_scheme_guidance_workflows"
down_revision = "0008_assistant_conversation_metadata"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_scheme_document_progress",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scheme_document_id", sa.Integer(), sa.ForeignKey("scheme_documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ready_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "scheme_document_id", name="uq_user_scheme_document_progress"),
    )
    op.create_index("ix_user_scheme_document_progress_user_id", "user_scheme_document_progress", ["user_id"])
    op.create_index("ix_user_scheme_document_progress_scheme_document_id", "user_scheme_document_progress", ["scheme_document_id"])
    op.execute("UPDATE application_tracking SET status = 'planning' WHERE status = 'interested'")
    with op.batch_alter_table("application_tracking") as batch_op:
        batch_op.add_column(sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(
            sa.Column(
                "status_changed_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            )
        )
        batch_op.create_unique_constraint(
            "uq_application_tracking_user_scheme", ["user_id", "scheme_id"]
        )
        batch_op.create_check_constraint(
            "ck_application_tracking_status",
            "status IN ('planning', 'preparing_documents', 'ready_to_apply', "
            "'submitted_externally', 'in_progress', 'completed', 'not_proceeding')",
        )


def downgrade() -> None:
    with op.batch_alter_table("application_tracking") as batch_op:
        batch_op.drop_constraint("ck_application_tracking_status", type_="check")
        batch_op.drop_constraint("uq_application_tracking_user_scheme", type_="unique")
        batch_op.drop_column("status_changed_at")
        batch_op.drop_column("submitted_at")
    op.drop_index("ix_user_scheme_document_progress_scheme_document_id", table_name="user_scheme_document_progress")
    op.drop_index("ix_user_scheme_document_progress_user_id", table_name="user_scheme_document_progress")
    op.drop_table("user_scheme_document_progress")
