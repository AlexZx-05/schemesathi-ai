"""Link structured eligibility rules to their supporting source.

Revision ID: 0006_eligibility_rule_sources
Revises: 0005_structured_eligibility_rules
"""
from alembic import op
import sqlalchemy as sa

revision = "0006_eligibility_rule_sources"
down_revision = "0005_structured_eligibility_rules"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("scheme_eligibility_rules") as batch_op:
        batch_op.add_column(sa.Column("source_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_scheme_eligibility_rules_source_id_scheme_sources",
            "scheme_sources",
            ["source_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index(
            "ix_scheme_eligibility_rules_source_id",
            ["source_id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("scheme_eligibility_rules") as batch_op:
        batch_op.drop_index("ix_scheme_eligibility_rules_source_id")
        batch_op.drop_constraint(
            "fk_scheme_eligibility_rules_source_id_scheme_sources",
            type_="foreignkey",
        )
        batch_op.drop_column("source_id")
