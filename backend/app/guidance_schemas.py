from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


ApplicationStatus = Literal[
    "planning",
    "preparing_documents",
    "ready_to_apply",
    "submitted_externally",
    "in_progress",
    "completed",
    "not_proceeding",
]


class SavedSchemeResponse(BaseModel):
    id: int
    scheme_id: str
    scheme_name: str
    scheme_status: str
    verification_status: str
    last_verified_at: datetime | None
    guidance_available: bool
    availability_notice: str | None = None
    saved_at: datetime


class DocumentChecklistItemResponse(BaseModel):
    document_id: int
    name: str
    description: str | None
    is_required: bool
    ready: bool
    ready_at: datetime | None
    uncertainty_notice: str | None = None


class DocumentChecklistResponse(BaseModel):
    scheme_id: str
    scheme_name: str
    verification_status: str
    last_verified_at: datetime | None
    source_urls: list[HttpUrl]
    items: list[DocumentChecklistItemResponse]
    notice: str = (
        "Marking an item ready only records your own preparation. It does not "
        "validate a document or confirm that the government portal will accept it."
    )


class DocumentReadyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ready: bool


class ApplicationGuidanceResponse(BaseModel):
    scheme_id: str
    scheme_name: str
    application_steps: list[str]
    official_application_url: HttpUrl | None
    source_urls: list[HttpUrl]
    checklist_complete: bool
    checklist_required_remaining: int
    portal_notice: str
    submission_notice: str = (
        "SchemeSathi does not submit applications. Apply only through the "
        "official government portal and never share that portal's password here."
    )


class ApplicationCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scheme_id: str = Field(min_length=1, max_length=220)
    notes: str | None = Field(default=None, max_length=2_000)


class ApplicationUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ApplicationStatus
    notes: str | None = Field(default=None, max_length=2_000)
    confirm_external_submission: bool = False


class ApplicationTrackingResponse(BaseModel):
    id: int
    scheme_id: str
    scheme_name: str
    status: ApplicationStatus
    notes: str | None
    created_at: datetime
    updated_at: datetime
    status_changed_at: datetime
    submitted_at: datetime | None
    submitted_by_user_confirmation: bool
    progress_percent: int

