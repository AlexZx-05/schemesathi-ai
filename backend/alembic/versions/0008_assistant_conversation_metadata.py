"""Add persisted citations and feedback to assistant messages.

Revision ID: 0008_assistant_conversation_metadata
Revises: 0007_scheme_knowledge_base
"""

from alembic import op
import sqlalchemy as sa

revision = "0008_assistant_conversation_metadata"
down_revision = "0007_scheme_knowledge_base"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("conversation_messages") as batch_op:
        batch_op.add_column(
            sa.Column(
                "citations",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'[]'"),
            )
        )
        batch_op.add_column(sa.Column("feedback", sa.String(length=12), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("conversation_messages") as batch_op:
        batch_op.drop_column("feedback")
        batch_op.drop_column("citations")
