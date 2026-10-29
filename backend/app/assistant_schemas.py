from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


AssistantIntent = Literal[
    "greeting",
    "capabilities",
    "scheme_discovery",
    "scheme_information",
    "eligibility_question",
    "document_checklist",
    "application_guidance",
    "general_clarification",
]


class AssistantCitation(BaseModel):
    source_id: int
    title: str | None
    url: str
    document_title: str | None = None
    chunk_index: int | None = None
    last_verified_at: datetime | None = None
    verification_status: str


class AssistantMessageResponse(BaseModel):
    id: int
    role: Literal["user", "assistant"]
    content: str
    citations: list[AssistantCitation] = Field(default_factory=list)
    feedback: Literal["helpful", "not_helpful"] | None = None
    created_at: datetime


class AssistantConversationSummary(BaseModel):
    id: int
    title: str | None
    updated_at: datetime


class AssistantConversationResponse(AssistantConversationSummary):
    messages: list[AssistantMessageResponse]


class AssistantChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=4_000)


class AssistantChatResponse(BaseModel):
    conversation_id: int
    intent: AssistantIntent
    user_message: AssistantMessageResponse
    assistant_message: AssistantMessageResponse
    suggested_questions: list[str] = Field(default_factory=list)
    validation_flags: list[str] = Field(default_factory=list)
    retrieval_warning: str | None = None


class AssistantFeedbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    feedback: Literal["helpful", "not_helpful"]
