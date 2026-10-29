from datetime import datetime
from math import ceil
from typing import Literal

from pydantic import BaseModel, Field

from .eligibility_schemas import (
    EligibilityCriterionResponse,
    EligibilityOutcome,
)


class RecommendationSourceResponse(BaseModel):
    title: str | None
    url: str
    last_verified_at: datetime | None


class SchemeRecommendationResponse(BaseModel):
    scheme_id: str
    scheme_name: str
    short_description: str
    category: str | None
    data_status: Literal["verified"]
    eligibility_status: EligibilityOutcome
    summary: str
    reasons: list[str] = Field(default_factory=list)
    criteria: list[EligibilityCriterionResponse] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    sources: list[RecommendationSourceResponse] = Field(default_factory=list)


class RecommendationPageResponse(BaseModel):
    profile_complete: bool
    completion_percentage: int
    missing_profile_fields: list[str] = Field(default_factory=list)
    items: list[SchemeRecommendationResponse] = Field(default_factory=list)
    page: int
    page_size: int
    total: int
    pages: int


class VerifiedDeadlineResponse(BaseModel):
    scheme_id: str
    scheme_name: str
    closes_at: datetime
    source_title: str | None
    source_url: str


class DashboardSummaryResponse(BaseModel):
    application_total: int
    application_status_counts: dict[str, int]
    verified_upcoming_deadlines: list[VerifiedDeadlineResponse]


def page_count(total: int, page_size: int) -> int:
    return ceil(total / page_size) if total else 0
