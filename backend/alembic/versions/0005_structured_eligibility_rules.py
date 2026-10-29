"""Add structured eligibility rule definitions.

Revision ID: 0005_structured_eligibility_rules
Revises: 0004_scheme_data_management
"""
from alembic import op
import sqlalchemy as sa

revision = "0005_structured_eligibility_rules"
down_revision = "0004_scheme_data_management"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "scheme_eligibility_rules",
        sa.Column("rule_data", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("scheme_eligibility_rules", "rule_data")
