from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class AdminSchemeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=200)
    slug: str = Field(min_length=2, max_length=220, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    description: str = Field(min_length=10, max_length=12_000)
    category_id: int | None = Field(default=None, gt=0)
    benefits: str | None = Field(default=None, max_length=12_000)
    department: str | None = Field(default=None, max_length=200)
    government_level: Literal["Central", "State", "Local", "Unknown"] = "Unknown"
    beneficiaries: list[str] = Field(default_factory=list, max_length=20)
    keywords: list[str] = Field(default_factory=list, max_length=50)
    application_instructions: str | None = Field(default=None, max_length=12_000)
    official_application_url: HttpUrl | None = None
    status: Literal["active", "inactive", "unknown"] = "unknown"


class AdminSchemeUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = Field(default=None, min_length=10, max_length=12_000)
    category_id: int | None = Field(default=None, gt=0)
    benefits: str | None = Field(default=None, max_length=12_000)
    department: str | None = Field(default=None, max_length=200)
    government_level: Literal["Central", "State", "Local", "Unknown"] | None = None
    beneficiaries: list[str] | None = Field(default=None, max_length=20)
    keywords: list[str] | None = Field(default=None, max_length=50)
    application_instructions: str | None = Field(default=None, max_length=12_000)
    official_application_url: HttpUrl | None = None
    status: Literal["active", "inactive", "unknown"] | None = None
    reason: str = Field(min_length=10, max_length=2_000)


class AdminCategoryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=100)
    slug: str = Field(min_length=2, max_length=120, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    description: str | None = Field(default=None, max_length=500)


class AdminEligibilityRuleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule_type: str = Field(min_length=1, max_length=40)
    rule_text: str = Field(min_length=3, max_length=2_000)
    rule_data: dict[str, object] | None = None
    source_id: int | None = Field(default=None, gt=0)
    is_required: bool = True
    sort_order: int = Field(default=0, ge=0, le=1000)
    reason: str = Field(min_length=10, max_length=2_000)


class AdminDocumentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=2_000)
    is_required: bool = True
    sort_order: int = Field(default=0, ge=0, le=1000)
    reason: str = Field(min_length=10, max_length=2_000)


class SchemeReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_note: str = Field(min_length=10, max_length=2_000)


class CorrectionSubmissionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scheme_id: str = Field(min_length=1, max_length=220)
    report_type: Literal[
        "incorrect_information", "outdated_source", "missing_information", "other"
    ]
    description: str = Field(min_length=10, max_length=2_000)


class CorrectionReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["in_review", "resolved", "declined"]
    review_notes: str = Field(min_length=5, max_length=2_000)


class AdminSourceVerificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    verification_note: str = Field(min_length=10, max_length=2_000)


class AdminSchemeListItem(BaseModel):
    id: int
    slug: str
    name: str
    verification_status: str
    status: str
    requires_human_review: bool
    last_verified_at: datetime | None
    official_application_url: str | None
    issue_flags: list[str]
