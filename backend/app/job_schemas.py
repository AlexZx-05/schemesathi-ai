from datetime import datetime, timezone
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

from .schemas import EducationLevel, US_STATES_AND_TERRITORIES

JobStatus = Literal["upcoming", "open", "closed", "unknown"]
JobVerificationStatus = Literal["unverified", "verified", "requires_review"]
DeadlineStatus = Literal["known", "unknown"]


class GovernmentJobDocumentResponse(BaseModel):
    id: int
    name: str
    description: str | None
    is_required: bool

    model_config = ConfigDict(from_attributes=True)


class GovernmentJobResponse(BaseModel):
    id: int
    slug: str
    title: str
    recruiting_body: str
    description: str
    employment_type: str | None
    eligible_states: list[str]
    minimum_qualification: str | None
    minimum_education_level: EducationLevel | None
    field_of_study: str | None
    minimum_experience_years: int | None
    minimum_age: int | None
    maximum_age: int | None
    keywords: list[str]
    application_opens: datetime | None
    application_deadline: datetime | None
    deadline_status: DeadlineStatus
    official_notice_url: HttpUrl
    application_url: HttpUrl | None
    status: JobStatus
    verification_status: JobVerificationStatus
    last_verified_at: datetime | None
    documents: list[GovernmentJobDocumentResponse]

    model_config = ConfigDict(from_attributes=True)


class GovernmentJobPageResponse(BaseModel):
    items: list[GovernmentJobResponse]
    page: int
    page_size: int
    total: int
    pages: int


class GovernmentJobRecommendationResponse(GovernmentJobResponse):
    match_reasons: list[str]
    missing_information: list[str]


class GovernmentJobRecommendationPageResponse(BaseModel):
    items: list[GovernmentJobRecommendationResponse]
    profile_complete: bool


class JobDocumentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=2_000)
    is_required: bool = True


class JobReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_note: str = Field(min_length=10, max_length=2_000)


class AdminJobCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slug: str = Field(min_length=2, max_length=220, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    title: str = Field(min_length=2, max_length=200)
    recruiting_body: str = Field(min_length=2, max_length=200)
    description: str = Field(min_length=10, max_length=12_000)
    employment_type: str | None = Field(default=None, max_length=80)
    eligible_states: list[str] = Field(default_factory=list, max_length=35)
    minimum_qualification: str | None = Field(default=None, max_length=200)
    minimum_education_level: EducationLevel | None = None
    field_of_study: str | None = Field(default=None, max_length=120)
    minimum_experience_years: int | None = Field(default=None, ge=0, le=60)
    minimum_age: int | None = Field(default=None, ge=18, le=100)
    maximum_age: int | None = Field(default=None, ge=18, le=100)
    keywords: list[str] = Field(default_factory=list, max_length=50)
    application_opens: datetime | None = None
    application_deadline: datetime | None = None
    deadline_status: DeadlineStatus = "unknown"
    official_notice_url: HttpUrl
    application_url: HttpUrl | None = None
    status: JobStatus = "unknown"
    documents: list[JobDocumentInput] = Field(default_factory=list, max_length=50)
    reason: str = Field(min_length=10, max_length=2_000)

    @field_validator("official_notice_url", "application_url")
    @classmethod
    def require_https(cls, value: HttpUrl | None) -> HttpUrl | None:
        if value is not None and value.scheme != "https":
            raise ValueError("Government recruitment links must use HTTPS.")
        return value

    @field_validator("eligible_states")
    @classmethod
    def validate_eligible_states(cls, values: list[str]) -> list[str]:
        if any(value not in US_STATES_AND_TERRITORIES for value in values):
            raise ValueError("Choose eligible locations from the official state list.")
        return list(dict.fromkeys(values))

    @field_validator("application_opens", "application_deadline")
    @classmethod
    def normalize_application_datetime(
        cls, value: datetime | None
    ) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=ZoneInfo("Asia/Kolkata"))
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def validate_job_dates_and_age(self) -> "AdminJobCreate":
        if (
            self.minimum_age is not None
            and self.maximum_age is not None
            and self.minimum_age > self.maximum_age
        ):
            raise ValueError("Minimum age cannot exceed maximum age.")
        if self.deadline_status == "known" and self.application_deadline is None:
            raise ValueError("A known application deadline must include its date and time.")
        if self.deadline_status == "unknown" and self.application_deadline is not None:
            raise ValueError("An unknown deadline cannot include a deadline date.")
        if (
            self.application_opens is not None
            and self.application_deadline is not None
            and self.application_opens >= self.application_deadline
        ):
            raise ValueError("The application deadline must follow the opening date.")
        return self


class AdminJobUpdate(AdminJobCreate):
    reason: str = Field(min_length=10, max_length=2_000)
