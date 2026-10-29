from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from .database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(100))
    password_hash: Mapped[str | None] = mapped_column(String(512), nullable=True)
    google_sub: Mapped[str | None] = mapped_column(
        String(255), unique=True, nullable=True
    )
    email_verified: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    profile: Mapped["Profile"] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )
    sessions: Mapped[list["AuthSession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    saved_schemes: Mapped[list["SavedScheme"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    document_progress: Mapped[list["UserSchemeDocumentProgress"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    applications: Mapped[list["ApplicationTracking"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    notification_preferences: Mapped["NotificationPreference | None"] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def profile_complete(self) -> bool:
        return bool(
            self.profile
            and self.profile.state
            and self.profile.occupation
            and self.profile.education_level
        )


class Profile(Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    state: Mapped[str | None] = mapped_column(String(80), nullable=True)
    district: Mapped[str | None] = mapped_column(String(100), nullable=True)
    area_type: Mapped[str | None] = mapped_column(String(10), nullable=True)
    occupation: Mapped[str | None] = mapped_column(String(40), nullable=True)
    occupation_other: Mapped[str | None] = mapped_column(String(80), nullable=True)
    employment_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    worker_category: Mapped[str | None] = mapped_column(String(80), nullable=True)
    education_level: Mapped[str | None] = mapped_column(String(40), nullable=True)
    current_student: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    qualification: Mapped[str | None] = mapped_column(String(120), nullable=True)
    field_of_study: Mapped[str | None] = mapped_column(String(120), nullable=True)
    years_experience: Mapped[int | None] = mapped_column(Integer, nullable=True)
    preferred_job_roles: Mapped[list[str]] = mapped_column(
        JSON, default=list, nullable=False
    )
    preferred_job_states: Mapped[list[str]] = mapped_column(
        JSON, default=list, nullable=False
    )
    annual_income_range: Mapped[str | None] = mapped_column(String(40), nullable=True)
    household_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    beneficiary_categories: Mapped[list[str]] = mapped_column(
        JSON, default=list, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )
    user: Mapped[User] = relationship(back_populates="profile")


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    expires_at: Mapped[int] = mapped_column(Integer, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    user: Mapped[User] = relationship(back_populates="sessions")


class AuthToken(Base):
    __tablename__ = "auth_tokens"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    purpose: Mapped[str] = mapped_column(String(20), index=True)
    expires_at: Mapped[int] = mapped_column(Integer, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class DevelopmentEmail(Base):
    __tablename__ = "development_emails"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(254), index=True)
    purpose: Mapped[str] = mapped_column(String(20))
    token: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class AuthRateLimit(Base):
    __tablename__ = "auth_rate_limits"

    key_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False)
    window_started_at: Mapped[int] = mapped_column(Integer, nullable=False)


scheme_category_links = Table(
    "scheme_category_links",
    Base.metadata,
    Column(
        "scheme_id",
        ForeignKey("schemes.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "category_id",
        ForeignKey("scheme_categories.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class SchemeCategory(Base):
    __tablename__ = "scheme_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    schemes: Mapped[list["Scheme"]] = relationship(
        secondary=scheme_category_links, back_populates="categories"
    )


class Scheme(Base):
    __tablename__ = "schemes"
    __table_args__ = (
        CheckConstraint(
            "government_level IN ('Central', 'State', 'Local', 'Unknown')",
            name="ck_schemes_government_level",
        ),
        CheckConstraint(
            "status IN ('active', 'inactive', 'unknown')",
            name="ck_schemes_status",
        ),
        CheckConstraint(
            "verification_status IN "
            "('demo', 'unverified', 'verified', 'requires_review')",
            name="ck_schemes_verification_status",
        ),
        CheckConstraint(
            "(is_demo = true AND verification_status = 'demo') OR "
            "(is_demo = false AND verification_status != 'demo')",
            name="ck_schemes_demo_verification_consistency",
        ),
        Index("ix_schemes_name", "name"),
        Index("ix_schemes_department", "department"),
        Index("ix_schemes_status_verification", "status", "verification_status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(220), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    benefits: Mapped[str | None] = mapped_column(Text, nullable=True)
    department: Mapped[str | None] = mapped_column(String(200), nullable=True)
    government_level: Mapped[str] = mapped_column(
        String(20), default="Unknown", nullable=False
    )
    target_beneficiaries: Mapped[list[str]] = mapped_column(
        JSON, default=list, nullable=False
    )
    keywords: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    application_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    official_application_url: Mapped[str | None] = mapped_column(
        String(2048), nullable=True
    )
    publication_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    effective_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), default="unknown", nullable=False)
    verification_status: Mapped[str] = mapped_column(
        String(24), default="unverified", nullable=False
    )
    requires_human_review: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reviewed_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    last_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )
    categories: Mapped[list[SchemeCategory]] = relationship(
        secondary=scheme_category_links, back_populates="schemes"
    )
    state_coverage: Mapped[list["SchemeStateCoverage"]] = relationship(
        back_populates="scheme", cascade="all, delete-orphan"
    )
    eligibility_rules: Mapped[list["SchemeEligibilityRule"]] = relationship(
        back_populates="scheme",
        cascade="all, delete-orphan",
        order_by="SchemeEligibilityRule.sort_order",
    )
    documents: Mapped[list["SchemeDocument"]] = relationship(
        back_populates="scheme",
        cascade="all, delete-orphan",
        order_by="SchemeDocument.sort_order",
    )
    sources: Mapped[list["SchemeSource"]] = relationship(
        back_populates="scheme", cascade="all, delete-orphan"
    )
    deadlines: Mapped[list["SchemeDeadline"]] = relationship(
        back_populates="scheme", cascade="all, delete-orphan"
    )


class SchemeStateCoverage(Base):
    __tablename__ = "scheme_state_coverage"
    __table_args__ = (
        UniqueConstraint("scheme_id", "state", name="uq_scheme_state_coverage"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scheme_id: Mapped[int] = mapped_column(
        ForeignKey("schemes.id", ondelete="CASCADE"), index=True
    )
    state: Mapped[str] = mapped_column(String(100), nullable=False)
    scheme: Mapped[Scheme] = relationship(back_populates="state_coverage")


class SchemeEligibilityRule(Base):
    __tablename__ = "scheme_eligibility_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scheme_id: Mapped[int] = mapped_column(
        ForeignKey("schemes.id", ondelete="CASCADE"), index=True
    )
    rule_type: Mapped[str] = mapped_column(String(40), default="general", nullable=False)
    rule_text: Mapped[str] = mapped_column(Text, nullable=False)
    rule_data: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    source_id: Mapped[int | None] = mapped_column(
        ForeignKey("scheme_sources.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    is_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    scheme: Mapped[Scheme] = relationship(back_populates="eligibility_rules")


class SchemeDocument(Base):
    __tablename__ = "scheme_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scheme_id: Mapped[int] = mapped_column(
        ForeignKey("schemes.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    scheme: Mapped[Scheme] = relationship(back_populates="documents")


class GovernmentJob(Base):
    __tablename__ = "government_jobs"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_government_jobs_slug"),
        CheckConstraint(
            "status IN ('upcoming', 'open', 'closed', 'unknown')",
            name="ck_government_jobs_status",
        ),
        CheckConstraint(
            "verification_status IN ('unverified', 'verified', 'requires_review')",
            name="ck_government_jobs_verification_status",
        ),
        CheckConstraint(
            "deadline_status IN ('known', 'unknown')",
            name="ck_government_jobs_deadline_status",
        ),
        CheckConstraint(
            "minimum_age IS NULL OR maximum_age IS NULL OR minimum_age <= maximum_age",
            name="ck_government_jobs_age_range",
        ),
        Index("ix_government_jobs_status_verification", "status", "verification_status"),
        Index("ix_government_jobs_deadline", "application_deadline"),
        Index("ix_government_jobs_title", "title"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(220), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    recruiting_body: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    employment_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    eligible_states: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    minimum_qualification: Mapped[str | None] = mapped_column(String(200), nullable=True)
    minimum_education_level: Mapped[str | None] = mapped_column(String(40), nullable=True)
    field_of_study: Mapped[str | None] = mapped_column(String(120), nullable=True)
    minimum_experience_years: Mapped[int | None] = mapped_column(Integer, nullable=True)
    minimum_age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    maximum_age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    keywords: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    application_opens: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    application_deadline: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deadline_status: Mapped[str] = mapped_column(
        String(20), default="unknown", nullable=False
    )
    official_notice_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    application_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="unknown", nullable=False)
    verification_status: Mapped[str] = mapped_column(
        String(24), default="unverified", nullable=False
    )
    requires_human_review: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    reviewed_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    last_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )
    documents: Mapped[list["GovernmentJobDocument"]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
        order_by="GovernmentJobDocument.sort_order",
    )


class GovernmentJobDocument(Base):
    __tablename__ = "government_job_documents"
    __table_args__ = (
        UniqueConstraint("job_id", "name", name="uq_government_job_documents_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("government_jobs.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    job: Mapped[GovernmentJob] = relationship(back_populates="documents")


class SchemeSource(Base):
    __tablename__ = "scheme_sources"
    __table_args__ = (
        UniqueConstraint("scheme_id", "url", name="uq_scheme_source_url"),
        CheckConstraint(
            "status IN ('unverified', 'verified', 'unavailable', 'stale')",
            name="ck_scheme_sources_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scheme_id: Mapped[int] = mapped_column(
        ForeignKey("schemes.id", ondelete="CASCADE"), index=True
    )
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    title: Mapped[str | None] = mapped_column(String(300), nullable=True)
    source_type: Mapped[str] = mapped_column(String(40), default="other", nullable=False)
    official_domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    relevant_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    document_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    retrieved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(20), default="unverified", nullable=False
    )
    reviewed_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    scheme: Mapped[Scheme] = relationship(back_populates="sources")
    knowledge_chunks: Mapped[list["SchemeKnowledgeChunk"]] = relationship()


class SchemeKnowledgeChunk(Base):
    __tablename__ = "scheme_knowledge_chunks"
    __table_args__ = (
        UniqueConstraint(
            "source_id",
            "content_hash",
            "chunk_index",
            name="uq_scheme_knowledge_chunk_source_hash_index",
        ),
        Index("ix_scheme_knowledge_chunks_scheme_id", "scheme_id"),
        Index("ix_scheme_knowledge_chunks_state_category", "state", "category"),
        Index(
            "ix_scheme_knowledge_chunks_source_status",
            "source_id",
            "verification_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scheme_id: Mapped[int] = mapped_column(
        ForeignKey("schemes.id", ondelete="CASCADE"), nullable=False
    )
    source_id: Mapped[int] = mapped_column(
        ForeignKey("scheme_sources.id", ondelete="CASCADE"), nullable=False
    )
    source_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    source_title: Mapped[str | None] = mapped_column(String(300), nullable=True)
    document_title: Mapped[str] = mapped_column(String(500), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    category: Mapped[str | None] = mapped_column(String(120), nullable=True)
    publication_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    effective_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    verification_status: Mapped[str] = mapped_column(String(20), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    embedding: Mapped[list[float]] = mapped_column(
        Vector(1536).with_variant(JSON, "sqlite"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class SchemeDeadline(Base):
    __tablename__ = "scheme_deadlines"
    __table_args__ = (
        CheckConstraint(
            "deadline_status IN ('known', 'unknown')",
            name="ck_scheme_deadlines_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scheme_id: Mapped[int] = mapped_column(
        ForeignKey("schemes.id", ondelete="CASCADE"), index=True
    )
    deadline_type: Mapped[str] = mapped_column(String(40), default="application", nullable=False)
    opens_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closes_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deadline_status: Mapped[str] = mapped_column(
        String(12), default="unknown", nullable=False
    )
    source_id: Mapped[int | None] = mapped_column(
        ForeignKey("scheme_sources.id", ondelete="SET NULL"), nullable=True, index=True
    )
    last_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )
    scheme: Mapped[Scheme] = relationship(back_populates="deadlines")
    source: Mapped["SchemeSource | None"] = relationship()


class SavedScheme(Base):
    __tablename__ = "saved_schemes"
    __table_args__ = (
        UniqueConstraint("user_id", "scheme_id", name="uq_saved_scheme_user_scheme"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    scheme_id: Mapped[int] = mapped_column(
        ForeignKey("schemes.id", ondelete="CASCADE"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    user: Mapped[User] = relationship(back_populates="saved_schemes")
    scheme: Mapped[Scheme] = relationship()


class UserSchemeDocumentProgress(Base):
    __tablename__ = "user_scheme_document_progress"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "scheme_document_id",
            name="uq_user_scheme_document_progress",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    scheme_document_id: Mapped[int] = mapped_column(
        ForeignKey("scheme_documents.id", ondelete="CASCADE"), index=True, nullable=False
    )
    ready_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )
    user: Mapped[User] = relationship(back_populates="document_progress")
    document: Mapped[SchemeDocument] = relationship()


class ApplicationTracking(Base):
    __tablename__ = "application_tracking"
    __table_args__ = (
        UniqueConstraint("user_id", "scheme_id", name="uq_application_tracking_user_scheme"),
        CheckConstraint(
            "status IN ('planning', 'preparing_documents', 'ready_to_apply', "
            "'submitted_externally', 'in_progress', 'completed', 'not_proceeding')",
            name="ck_application_tracking_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    scheme_id: Mapped[int] = mapped_column(
        ForeignKey("schemes.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(30), default="planning", nullable=False)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status_changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )
    user: Mapped[User] = relationship(back_populates="applications")
    scheme: Mapped[Scheme] = relationship()


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        UniqueConstraint("dedupe_key", name="uq_notifications_dedupe_key"),
        CheckConstraint(
            "email_delivery_status IN "
            "('not_requested', 'pending', 'sending', 'sent', 'failed', 'skipped', 'invalidated')",
            name="ck_notifications_email_delivery_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    notification_type: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    dedupe_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    deadline_id: Mapped[int | None] = mapped_column(
        ForeignKey("scheme_deadlines.id", ondelete="SET NULL"), nullable=True, index=True
    )
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_id: Mapped[int | None] = mapped_column(
        ForeignKey("scheme_sources.id", ondelete="SET NULL"), nullable=True
    )
    source_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    in_app_visible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    email_delivery_status: Mapped[str] = mapped_column(
        String(20), default="not_requested", nullable=False
    )
    email_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    email_next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    email_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    email_failure: Mapped[str | None] = mapped_column(String(500), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    user: Mapped[User] = relationship()
    deadline: Mapped[SchemeDeadline | None] = relationship()
    source: Mapped[SchemeSource | None] = relationship()


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_notification_preferences_user"),
        CheckConstraint(
            "length(timezone) BETWEEN 1 AND 80",
            name="ck_notification_preferences_timezone_length",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    in_app_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    reminders_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    deadline_reminders_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    timezone: Mapped[str] = mapped_column(
        String(80), default="Asia/Kolkata", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )
    user: Mapped[User] = relationship(back_populates="notification_preferences")


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )
    messages: Mapped[list["ConversationMessage"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )
    user: Mapped[User] = relationship(back_populates="conversations")


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"
    __table_args__ = (
        UniqueConstraint(
            "conversation_id", "sequence_number", name="uq_conversation_message_order"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    citations: Mapped[list[dict[str, object]]] = mapped_column(
        JSON, default=list, nullable=False
    )
    feedback: Mapped[str | None] = mapped_column(String(12), nullable=True)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class SchemeReport(Base):
    __tablename__ = "scheme_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    scheme_id: Mapped[int | None] = mapped_column(
        ForeignKey("schemes.id", ondelete="SET NULL"), nullable=True, index=True
    )
    report_type: Mapped[str] = mapped_column(String(40), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False)
    reviewed_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SchemeReviewHistory(Base):
    __tablename__ = "scheme_review_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scheme_id: Mapped[int | None] = mapped_column(
        ForeignKey("schemes.id", ondelete="SET NULL"), nullable=True, index=True
    )
    actor_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    before_snapshot: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    after_snapshot: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False, index=True
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    details: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False, index=True
    )
