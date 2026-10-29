"""Add curated government job listings and optional job profile fields.

Revision ID: 0012_government_jobs
Revises: 0011_admin_review_history
"""

from alembic import op
import sqlalchemy as sa

revision = "0012_government_jobs"
down_revision = "0011_admin_review_history"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("user_profiles") as batch_op:
        batch_op.add_column(sa.Column("qualification", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("field_of_study", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("years_experience", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "preferred_job_roles",
                sa.JSON(),
                server_default=sa.text("'[]'"),
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "preferred_job_states",
                sa.JSON(),
                server_default=sa.text("'[]'"),
                nullable=False,
            )
        )

    op.create_table(
        "government_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(length=220), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("recruiting_body", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("employment_type", sa.String(length=80), nullable=True),
        sa.Column(
            "eligible_states",
            sa.JSON(),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
        sa.Column("minimum_qualification", sa.String(length=200), nullable=True),
        sa.Column("minimum_education_level", sa.String(length=40), nullable=True),
        sa.Column("field_of_study", sa.String(length=120), nullable=True),
        sa.Column("minimum_experience_years", sa.Integer(), nullable=True),
        sa.Column("minimum_age", sa.Integer(), nullable=True),
        sa.Column("maximum_age", sa.Integer(), nullable=True),
        sa.Column(
            "keywords",
            sa.JSON(),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
        sa.Column("application_opens", sa.DateTime(timezone=True), nullable=True),
        sa.Column("application_deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "deadline_status",
            sa.String(length=20),
            server_default="unknown",
            nullable=False,
        ),
        sa.Column("official_notice_url", sa.String(length=2048), nullable=False),
        sa.Column("application_url", sa.String(length=2048), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="unknown",
            nullable=False,
        ),
        sa.Column(
            "verification_status",
            sa.String(length=24),
            server_default="unverified",
            nullable=False,
        ),
        sa.Column(
            "requires_human_review",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
        sa.Column("reviewed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('upcoming', 'open', 'closed', 'unknown')",
            name="ck_government_jobs_status",
        ),
        sa.CheckConstraint(
            "verification_status IN ('unverified', 'verified', 'requires_review')",
            name="ck_government_jobs_verification_status",
        ),
        sa.CheckConstraint(
            "deadline_status IN ('known', 'unknown')",
            name="ck_government_jobs_deadline_status",
        ),
        sa.CheckConstraint(
            "minimum_age IS NULL OR maximum_age IS NULL OR minimum_age <= maximum_age",
            name="ck_government_jobs_age_range",
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.UniqueConstraint("slug", name="uq_government_jobs_slug"),
    )
    op.create_index(
        "ix_government_jobs_status_verification",
        "government_jobs",
        ["status", "verification_status"],
    )
    op.create_index(
        "ix_government_jobs_deadline",
        "government_jobs",
        ["application_deadline"],
    )
    op.create_index("ix_government_jobs_title", "government_jobs", ["title"])
    op.create_table(
        "government_job_documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "is_required",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["job_id"], ["government_jobs.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("job_id", "name", name="uq_government_job_documents_name"),
    )
    op.create_index(
        "ix_government_job_documents_job_id",
        "government_job_documents",
        ["job_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_government_job_documents_job_id",
        table_name="government_job_documents",
    )
    op.drop_table("government_job_documents")
    op.drop_index("ix_government_jobs_title", table_name="government_jobs")
    op.drop_index("ix_government_jobs_deadline", table_name="government_jobs")
    op.drop_index(
        "ix_government_jobs_status_verification",
        table_name="government_jobs",
    )
    op.drop_table("government_jobs")
    with op.batch_alter_table("user_profiles") as batch_op:
        batch_op.drop_column("preferred_job_states")
        batch_op.drop_column("preferred_job_roles")
        batch_op.drop_column("years_experience")
        batch_op.drop_column("field_of_study")
        batch_op.drop_column("qualification")
