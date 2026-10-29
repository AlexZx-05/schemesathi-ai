from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

US_STATES_AND_TERRITORIES = (
    "Andaman and Nicobar Islands",
    "Andhra Pradesh",
    "Arunachal Pradesh",
    "Assam",
    "Bihar",
    "Chandigarh",
    "Chhattisgarh",
    "Dadra and Nagar Haveli and Daman and Diu",
    "Delhi",
    "Goa",
    "Gujarat",
    "Haryana",
    "Himachal Pradesh",
    "Jammu and Kashmir",
    "Jharkhand",
    "Karnataka",
    "Kerala",
    "Ladakh",
    "Lakshadweep",
    "Madhya Pradesh",
    "Maharashtra",
    "Manipur",
    "Meghalaya",
    "Mizoram",
    "Nagaland",
    "Odisha",
    "Puducherry",
    "Punjab",
    "Rajasthan",
    "Sikkim",
    "Tamil Nadu",
    "Telangana",
    "Tripura",
    "Uttar Pradesh",
    "Uttarakhand",
    "West Bengal",
)
Occupation = Literal[
    "Student",
    "Farmer",
    "Salaried employee",
    "Self-employed",
    "Job seeker",
    "Homemaker",
    "Other",
]
EducationLevel = Literal[
    "No formal schooling",
    "Primary",
    "Secondary",
    "Higher secondary",
    "Diploma or vocational",
    "Undergraduate",
    "Postgraduate",
    "Other",
]
IncomeRange = Literal[
    "Prefer not to say",
    "Below ₹1 lakh",
    "₹1–3 lakh",
    "₹3–6 lakh",
    "₹6–10 lakh",
    "Above ₹10 lakh",
]
BeneficiaryCategory = Literal[
    "Students",
    "Farmers",
    "Job seekers",
    "Women",
    "Children",
    "Families",
    "Low-income households",
    "Persons with disabilities",
    "Senior citizens",
    "Other",
]
AreaType = Literal["Rural", "Urban"]
EmploymentStatus = Literal[
    "Employed",
    "Self-employed",
    "Unemployed",
    "Student",
    "Homemaker",
    "Other",
]


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr = Field(max_length=254)
    full_name: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=12, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().casefold()

    @field_validator("full_name")
    @classmethod
    def normalize_full_name(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if len(normalized) < 2:
            raise ValueError("Enter your name.")
        return normalized


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr = Field(max_length=254)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().casefold()


class GoogleTokenRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    credential: str = Field(min_length=1, max_length=8192)


class GoogleIdentityClaims(BaseModel):
    model_config = ConfigDict(extra="ignore")

    sub: str = Field(min_length=1, max_length=255)
    email: EmailStr = Field(max_length=254)
    email_verified: bool
    name: str = Field(min_length=2, max_length=100)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    profile_complete: bool
    is_admin: bool = False


class EmailRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr = Field(max_length=254)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().casefold()


class TokenRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str = Field(min_length=20, max_length=128)


class EmailDeliveryStatusResponse(BaseModel):
    development_inbox_available: bool


class PasswordResetRequest(TokenRequest):
    new_password: str = Field(min_length=12, max_length=128)


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str | None = Field(default=None, min_length=2, max_length=100)
    age: int | None = Field(default=None, ge=18, le=120)
    state: str | None = None
    district: str | None = Field(default=None, max_length=100)
    area_type: AreaType | None = None
    occupation: Occupation | None = None
    occupation_other: str | None = Field(default=None, max_length=80)
    employment_status: EmploymentStatus | None = None
    worker_category: str | None = Field(default=None, max_length=80)
    education_level: EducationLevel | None = None
    current_student: bool | None = None
    qualification: str | None = Field(default=None, max_length=120)
    field_of_study: str | None = Field(default=None, max_length=120)
    years_experience: int | None = Field(default=None, ge=0, le=60)
    preferred_job_roles: list[str] = Field(default_factory=list, max_length=10)
    preferred_job_states: list[str] = Field(default_factory=list, max_length=35)
    annual_income_range: IncomeRange | None = None
    household_size: int | None = Field(default=None, ge=1, le=30)
    beneficiary_categories: list[BeneficiaryCategory] = Field(
        default_factory=list, max_length=10
    )

    @field_validator("full_name")
    @classmethod
    def normalize_full_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.split())
        if len(normalized) < 2:
            raise ValueError("Enter your name.")
        return normalized

    @field_validator("state")
    @classmethod
    def validate_state(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if value not in US_STATES_AND_TERRITORIES:
            raise ValueError("Select a state or union territory from the list.")
        return value

    @field_validator("preferred_job_states")
    @classmethod
    def validate_preferred_job_states(cls, values: list[str]) -> list[str]:
        if any(value not in US_STATES_AND_TERRITORIES for value in values):
            raise ValueError(
                "Choose preferred job locations from the state and territory list."
            )
        return list(dict.fromkeys(values))

    @field_validator("preferred_job_roles")
    @classmethod
    def normalize_preferred_job_roles(cls, values: list[str]) -> list[str]:
        normalized = list(dict.fromkeys(" ".join(value.split()) for value in values))
        if any(not value or len(value) > 80 for value in normalized):
            raise ValueError("Job interests must be 1 to 80 characters.")
        return normalized

    @field_validator("qualification", "field_of_study")
    @classmethod
    def normalize_job_profile_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.split())
        return normalized or None

    @field_validator("occupation_other")
    @classmethod
    def normalize_other_occupation(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.split())
        return normalized or None

    @model_validator(mode="after")
    def validate_conditional_occupation(self) -> "ProfileUpdate":
        if self.occupation == "Other" and not self.occupation_other:
            raise ValueError("Describe your occupation.")
        if self.occupation is not None and self.occupation != "Other":
            self.occupation_other = None
        return self


class ProfileResponse(BaseModel):
    id: int
    email: str
    full_name: str
    age: int | None
    state: str | None
    district: str | None
    area_type: str | None
    occupation: str | None
    occupation_other: str | None
    employment_status: str | None
    worker_category: str | None
    education_level: str | None
    current_student: bool | None
    qualification: str | None
    field_of_study: str | None
    years_experience: int | None
    preferred_job_roles: list[str]
    preferred_job_states: list[str]
    annual_income_range: str | None
    household_size: int | None
    beneficiary_categories: list[str]
    profile_complete: bool
