from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

SchemeStatus = Literal["active", "inactive", "unknown"]
SourceStatus = Literal["unverified", "verified", "unavailable", "stale"]
DeadlineStatus = Literal["known", "unknown"]


class SchemeCategoryResponse(BaseModel):
    id: int
    name: str
    slug: str
    description: str | None

    model_config = ConfigDict(from_attributes=True)


class SchemeSourceResponse(BaseModel):
    id: int
    url: HttpUrl
    title: str | None
    source_type: str
    official_domain: str | None
    relevant_text: str | None
    document_reference: str | None
    retrieved_at: datetime | None
    last_verified_at: datetime | None
    status: SourceStatus

    model_config = ConfigDict(from_attributes=True)


class SchemeDeadlineResponse(BaseModel):
    id: int
    deadline_type: str
    opens_at: datetime | None
    closes_at: datetime | None
    deadline_status: DeadlineStatus
    notes: str | None

    model_config = ConfigDict(from_attributes=True)


class SchemeSummaryResponse(BaseModel):
    id: str
    name: str
    short_description: str
    category: str | None
    beneficiaries: list[str]
    government_level: str
    keywords: list[str] = Field(default_factory=list)
    benefits: list[str]
    eligibility_criteria: list[str]
    required_documents: list[str]
    application_procedure: list[str]
    official_source: str | None
    last_verified_date: str | None
    data_status: Literal["verified"]


class SchemeDetailResponse(SchemeSummaryResponse):
    department: str | None
    state_coverage: list[str]
    application_url: HttpUrl | None
    sources: list[SchemeSourceResponse]
    publication_date: datetime | None
    effective_date: datetime | None
    status: SchemeStatus
    verification_status: Literal["verified"]
    requires_human_review: bool
    deadline_information_status: Literal["known", "unknown"]
    deadlines: list[SchemeDeadlineResponse]
    created_at: datetime
    updated_at: datetime


class SchemePageResponse(BaseModel):
    items: list[SchemeSummaryResponse]
    page: int
    page_size: int
    total: int
    pages: int


class DevelopmentCategoryList(BaseModel):
    items: list[SchemeCategoryResponse]
