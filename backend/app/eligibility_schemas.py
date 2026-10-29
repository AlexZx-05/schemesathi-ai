from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .schemas import (
    AreaType,
    BeneficiaryCategory,
    EducationLevel,
    EmploymentStatus,
    IncomeRange,
    Occupation,
    US_STATES_AND_TERRITORIES,
)

CriterionResult = Literal[
    "satisfied", "not_satisfied", "unknown", "requires_confirmation"
]
EligibilityOutcome = Literal[
    "potentially_eligible",
    "more_information_required",
    "known_criteria_not_satisfied",
    "unable_to_determine",
]


class EligibilityHypotheticalAnswers(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    age: int | None = Field(default=None, ge=0, le=120)
    state: str | None = None
    district: str | None = Field(default=None, max_length=100)
    area_type: AreaType | None = None
    occupation: Occupation | None = None
    employment_status: EmploymentStatus | None = None
    worker_category: str | None = Field(default=None, max_length=80)
    education_level: EducationLevel | None = None
    current_student: bool | None = None
    annual_income_range: IncomeRange | None = None
    household_size: int | None = Field(default=None, ge=1, le=30)
    beneficiary_categories: list[BeneficiaryCategory] = Field(
        default_factory=list, max_length=10
    )

    @field_validator("state")
    @classmethod
    def validate_state(cls, value: str | None) -> str | None:
        if value is not None and value not in US_STATES_AND_TERRITORIES:
            raise ValueError("Select a state or union territory from the list.")
        return value


class EligibilityCheckRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answers: EligibilityHypotheticalAnswers | None = None


class EligibilitySourceResponse(BaseModel):
    title: str | None
    url: str
    last_verified_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class EligibilityCriterionResponse(BaseModel):
    rule_id: int
    criterion: str
    profile_field: str | None = None
    result: CriterionResult
    explanation: str
    required: bool
    evaluated_value: str | int | float | bool | list[str] | None = None
    rule_source_references: list[EligibilitySourceResponse] = Field(
        default_factory=list
    )
    uncertainty_reason: str | None = None


class EligibilityAssessmentResponse(BaseModel):
    scheme_id: str
    scheme_name: str
    outcome: EligibilityOutcome
    summary: str
    criteria: list[EligibilityCriterionResponse] = Field(default_factory=list)
    sources: list[EligibilitySourceResponse] = Field(default_factory=list)
    assessed_at: datetime
    disclaimer: str
    assessment_mode: Literal["saved_profile", "hypothetical_answers"]
    missing_information: list[str] = Field(default_factory=list)
