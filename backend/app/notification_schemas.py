from datetime import datetime
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class NotificationPreferencesUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    in_app_enabled: bool
    email_enabled: bool
    reminders_enabled: bool
    deadline_reminders_enabled: bool
    timezone: str = Field(min_length=1, max_length=80)

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as error:
            raise ValueError("Use a valid IANA time zone, such as Asia/Kolkata.") from error
        return value


class NotificationPreferencesResponse(NotificationPreferencesUpdate):
    updated_at: datetime | None


class NotificationResponse(BaseModel):
    id: int
    notification_type: str
    title: str
    message: str
    created_at: datetime
    read_at: datetime | None
    is_valid: bool
    deadline_at: datetime | None
    source_url: str | None
    source_verified_at: datetime | None
    email_delivery_status: Literal[
        "not_requested", "pending", "sending", "sent", "failed", "skipped", "invalidated"
    ]


class NotificationPageResponse(BaseModel):
    items: list[NotificationResponse]
    unread_count: int
    page: int
    page_size: int
    total: int


class NotificationReadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    read: bool = True


class DeadlineUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    deadline_type: str = Field(default="application", min_length=1, max_length=40)
    deadline_status: Literal["known", "unknown"]
    closes_at: datetime | None = None
    opens_at: datetime | None = None
    source_id: int | None = None
    notes: str | None = Field(default=None, max_length=2_000)

    @field_validator("closes_at", "opens_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.utcoffset() is None:
            raise ValueError("Deadline timestamps must include a time zone.")
        return value

    @model_validator(mode="after")
    def validate_known_deadline(self) -> "DeadlineUpdateRequest":
        if self.deadline_status == "known" and (
            self.closes_at is None or self.source_id is None
        ):
            raise ValueError("A known deadline requires a closing date and verified source.")
        if self.deadline_status == "unknown" and self.closes_at is not None:
            raise ValueError("Unknown deadlines must not include a closing date.")
        return self
