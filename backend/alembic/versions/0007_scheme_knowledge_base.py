"""Add source ingestion metadata and pgvector knowledge chunks.

Revision ID: 0007_scheme_knowledge_base
Revises: 0006_eligibility_rule_sources
"""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision = "0007_scheme_knowledge_base"
down_revision = "0006_eligibility_rule_sources"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column(
                "is_admin",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )

    op.create_table(
        "scheme_knowledge_chunks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "scheme_id",
            sa.Integer(),
            sa.ForeignKey("schemes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_id",
            sa.Integer(),
            sa.ForeignKey("scheme_sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_url", sa.String(length=2048), nullable=False),
        sa.Column("source_title", sa.String(length=300), nullable=True),
        sa.Column("document_title", sa.String(length=500), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("state", sa.String(length=100), nullable=True),
        sa.Column("category", sa.String(length=120), nullable=True),
        sa.Column("publication_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("effective_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verification_status", sa.String(length=20), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "embedding",
            Vector(1536).with_variant(sa.JSON(), "sqlite"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "source_id",
            "content_hash",
            "chunk_index",
            name="uq_scheme_knowledge_chunk_source_hash_index",
        ),
    )
    op.create_index(
        "ix_scheme_knowledge_chunks_scheme_id",
        "scheme_knowledge_chunks",
        ["scheme_id"],
    )
    op.create_index(
        "ix_scheme_knowledge_chunks_source_id",
        "scheme_knowledge_chunks",
        ["source_id"],
    )
    op.create_index(
        "ix_scheme_knowledge_chunks_state_category",
        "scheme_knowledge_chunks",
        ["state", "category"],
    )
    op.create_index(
        "ix_scheme_knowledge_chunks_source_status",
        "scheme_knowledge_chunks",
        ["source_id", "verification_status"],
    )
    if bind.dialect.name == "postgresql":
        op.create_index(
            "ix_scheme_knowledge_chunks_embedding_hnsw",
            "scheme_knowledge_chunks",
            ["embedding"],
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.drop_index(
            "ix_scheme_knowledge_chunks_embedding_hnsw",
            table_name="scheme_knowledge_chunks",
        )
    op.drop_index(
        "ix_scheme_knowledge_chunks_source_status",
        table_name="scheme_knowledge_chunks",
    )
    op.drop_index(
        "ix_scheme_knowledge_chunks_state_category",
        table_name="scheme_knowledge_chunks",
    )
    op.drop_index(
        "ix_scheme_knowledge_chunks_source_id",
        table_name="scheme_knowledge_chunks",
    )
    op.drop_index(
        "ix_scheme_knowledge_chunks_scheme_id",
        table_name="scheme_knowledge_chunks",
    )
    op.drop_table("scheme_knowledge_chunks")
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("is_admin")
