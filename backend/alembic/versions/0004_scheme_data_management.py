"""Create normalized scheme and related user data tables.

Revision ID: 0004_scheme_data_management
Revises: 0003_onboarding_auth_workflows
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_scheme_data_management"
down_revision = "0003_onboarding_auth_workflows"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.rename_table("profiles", "user_profiles")

    op.create_table(
        "scheme_categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False, unique=True),
        sa.Column("slug", sa.String(length=120), nullable=False, unique=True),
        sa.Column("description", sa.String(length=500)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "schemes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=220), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("benefits", sa.Text()),
        sa.Column("department", sa.String(length=200)),
        sa.Column("government_level", sa.String(length=20), nullable=False),
        sa.Column("target_beneficiaries", sa.JSON(), nullable=False),
        sa.Column("keywords", sa.JSON(), nullable=False),
        sa.Column("application_instructions", sa.Text()),
        sa.Column("official_application_url", sa.String(length=2048)),
        sa.Column("publication_date", sa.DateTime(timezone=True)),
        sa.Column("effective_date", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("verification_status", sa.String(length=24), nullable=False),
        sa.Column("requires_human_review", sa.Boolean(), nullable=False),
        sa.Column("is_demo", sa.Boolean(), nullable=False),
        sa.Column("last_verified_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "government_level IN ('Central', 'State', 'Local', 'Unknown')",
            name="ck_schemes_government_level",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'inactive', 'unknown')",
            name="ck_schemes_status",
        ),
        sa.CheckConstraint(
            "verification_status IN "
            "('demo', 'unverified', 'verified', 'requires_review')",
            name="ck_schemes_verification_status",
        ),
        sa.CheckConstraint(
            "(is_demo = true AND verification_status = 'demo') OR "
            "(is_demo = false AND verification_status != 'demo')",
            name="ck_schemes_demo_verification_consistency",
        ),
    )
    op.create_index("ix_schemes_name", "schemes", ["name"])
    op.create_index("ix_schemes_department", "schemes", ["department"])
    op.create_index(
        "ix_schemes_status_verification",
        "schemes",
        ["status", "verification_status"],
    )
    op.create_table(
        "scheme_category_links",
        sa.Column(
            "scheme_id",
            sa.Integer(),
            sa.ForeignKey("schemes.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "category_id",
            sa.Integer(),
            sa.ForeignKey("scheme_categories.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )
    op.create_table(
        "scheme_state_coverage",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "scheme_id",
            sa.Integer(),
            sa.ForeignKey("schemes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("state", sa.String(length=100), nullable=False),
        sa.UniqueConstraint("scheme_id", "state", name="uq_scheme_state_coverage"),
    )
    op.create_index(
        "ix_scheme_state_coverage_scheme_id",
        "scheme_state_coverage",
        ["scheme_id"],
    )
    op.create_table(
        "scheme_eligibility_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "scheme_id",
            sa.Integer(),
            sa.ForeignKey("schemes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("rule_type", sa.String(length=40), nullable=False),
        sa.Column("rule_text", sa.Text(), nullable=False),
        sa.Column("is_required", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_scheme_eligibility_rules_scheme_id",
        "scheme_eligibility_rules",
        ["scheme_id"],
    )
    op.create_table(
        "scheme_documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "scheme_id",
            sa.Integer(),
            sa.ForeignKey("schemes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("is_required", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_scheme_documents_scheme_id", "scheme_documents", ["scheme_id"])
    op.create_table(
        "scheme_sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "scheme_id",
            sa.Integer(),
            sa.ForeignKey("schemes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("title", sa.String(length=300)),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("official_domain", sa.String(length=255)),
        sa.Column("relevant_text", sa.Text()),
        sa.Column("document_reference", sa.String(length=500)),
        sa.Column("retrieved_at", sa.DateTime(timezone=True)),
        sa.Column("last_verified_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("scheme_id", "url", name="uq_scheme_source_url"),
        sa.CheckConstraint(
            "status IN ('unverified', 'verified', 'unavailable', 'stale')",
            name="ck_scheme_sources_status",
        ),
    )
    op.create_index("ix_scheme_sources_scheme_id", "scheme_sources", ["scheme_id"])
    op.create_table(
        "scheme_deadlines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "scheme_id",
            sa.Integer(),
            sa.ForeignKey("schemes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("deadline_type", sa.String(length=40), nullable=False),
        sa.Column("opens_at", sa.DateTime(timezone=True)),
        sa.Column("closes_at", sa.DateTime(timezone=True)),
        sa.Column("deadline_status", sa.String(length=12), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "deadline_status IN ('known', 'unknown')",
            name="ck_scheme_deadlines_status",
        ),
    )
    op.create_index(
        "ix_scheme_deadlines_scheme_id", "scheme_deadlines", ["scheme_id"]
    )
    op.create_table(
        "saved_schemes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "scheme_id",
            sa.Integer(),
            sa.ForeignKey("schemes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "scheme_id", name="uq_saved_scheme_user_scheme"),
    )
    op.create_index("ix_saved_schemes_user_id", "saved_schemes", ["user_id"])
    op.create_index("ix_saved_schemes_scheme_id", "saved_schemes", ["scheme_id"])
    op.create_table(
        "application_tracking",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "scheme_id",
            sa.Integer(),
            sa.ForeignKey("schemes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True)),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_application_tracking_user_id", "application_tracking", ["user_id"])
    op.create_index("ix_application_tracking_scheme_id", "application_tracking", ["scheme_id"])
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("notification_type", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_table(
        "notification_preferences",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("email_enabled", sa.Boolean(), nullable=False),
        sa.Column("in_app_enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", name="uq_notification_preferences_user"),
    )
    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=200)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_conversations_user_id", "conversations", ["user_id"])
    op.create_table(
        "conversation_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "conversation_id",
            sa.Integer(),
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "conversation_id", "sequence_number", name="uq_conversation_message_order"
        ),
    )
    op.create_index(
        "ix_conversation_messages_conversation_id",
        "conversation_messages",
        ["conversation_id"],
    )
    op.create_table(
        "scheme_reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "scheme_id",
            sa.Integer(),
            sa.ForeignKey("schemes.id", ondelete="SET NULL"),
        ),
        sa.Column("report_type", sa.String(length=40), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_scheme_reports_user_id", "scheme_reports", ["user_id"])
    op.create_index("ix_scheme_reports_scheme_id", "scheme_reports", ["scheme_id"])
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "actor_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
        ),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("entity_id", sa.String(length=100)),
        sa.Column("details", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_logs_actor_user_id", "audit_logs", ["actor_user_id"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_actor_user_id", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_index("ix_scheme_reports_scheme_id", table_name="scheme_reports")
    op.drop_index("ix_scheme_reports_user_id", table_name="scheme_reports")
    op.drop_table("scheme_reports")
    op.drop_index(
        "ix_conversation_messages_conversation_id", table_name="conversation_messages"
    )
    op.drop_table("conversation_messages")
    op.drop_index("ix_conversations_user_id", table_name="conversations")
    op.drop_table("conversations")
    op.drop_table("notification_preferences")
    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_table("notifications")
    op.drop_index("ix_application_tracking_scheme_id", table_name="application_tracking")
    op.drop_index("ix_application_tracking_user_id", table_name="application_tracking")
    op.drop_table("application_tracking")
    op.drop_index("ix_saved_schemes_scheme_id", table_name="saved_schemes")
    op.drop_index("ix_saved_schemes_user_id", table_name="saved_schemes")
    op.drop_table("saved_schemes")
    op.drop_index("ix_scheme_deadlines_scheme_id", table_name="scheme_deadlines")
    op.drop_table("scheme_deadlines")
    op.drop_index("ix_scheme_sources_scheme_id", table_name="scheme_sources")
    op.drop_table("scheme_sources")
    op.drop_index("ix_scheme_documents_scheme_id", table_name="scheme_documents")
    op.drop_table("scheme_documents")
    op.drop_index(
        "ix_scheme_eligibility_rules_scheme_id", table_name="scheme_eligibility_rules"
    )
    op.drop_table("scheme_eligibility_rules")
    op.drop_index(
        "ix_scheme_state_coverage_scheme_id", table_name="scheme_state_coverage"
    )
    op.drop_table("scheme_state_coverage")
    op.drop_table("scheme_category_links")
    op.drop_index("ix_schemes_status_verification", table_name="schemes")
    op.drop_index("ix_schemes_department", table_name="schemes")
    op.drop_index("ix_schemes_name", table_name="schemes")
    op.drop_table("schemes")
    op.drop_table("scheme_categories")
    op.rename_table("user_profiles", "profiles")
