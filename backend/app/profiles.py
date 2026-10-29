from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from .auth import _check_origin, get_current_user
from .database import get_db
from .models import Profile, User
from .schemas import ProfileResponse, ProfileUpdate

router = APIRouter(prefix="/profile", tags=["profile"])


def _profile_response(user: User) -> ProfileResponse:
    profile = user.profile
    return ProfileResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        age=profile.age if profile else None,
        state=profile.state if profile else None,
        district=profile.district if profile else None,
        area_type=profile.area_type if profile else None,
        occupation=profile.occupation if profile else None,
        occupation_other=profile.occupation_other if profile else None,
        employment_status=profile.employment_status if profile else None,
        worker_category=profile.worker_category if profile else None,
        education_level=profile.education_level if profile else None,
        current_student=profile.current_student if profile else None,
        qualification=profile.qualification if profile else None,
        field_of_study=profile.field_of_study if profile else None,
        years_experience=profile.years_experience if profile else None,
        preferred_job_roles=profile.preferred_job_roles if profile else [],
        preferred_job_states=profile.preferred_job_states if profile else [],
        annual_income_range=(
            profile.annual_income_range if profile else None
        ),
        household_size=profile.household_size if profile else None,
        beneficiary_categories=(
            profile.beneficiary_categories if profile else []
        ),
        profile_complete=user.profile_complete,
    )


@router.get("", response_model=ProfileResponse)
def read_profile(user: User = Depends(get_current_user)) -> ProfileResponse:
    return _profile_response(user)


@router.put("", response_model=ProfileResponse)
@router.patch("", response_model=ProfileResponse)
def update_profile(
    data: ProfileUpdate,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProfileResponse:
    _check_origin(request)
    if user.profile is None:
        user.profile = Profile(beneficiary_categories=[])
    if "full_name" in data.model_fields_set and data.full_name is not None:
        user.full_name = data.full_name
    for field in (
        "age",
        "state",
        "district",
        "area_type",
        "occupation",
        "occupation_other",
        "employment_status",
        "worker_category",
        "education_level",
        "current_student",
        "qualification",
        "field_of_study",
        "years_experience",
        "preferred_job_roles",
        "preferred_job_states",
        "annual_income_range",
        "household_size",
        "beneficiary_categories",
    ):
        if field in data.model_fields_set:
            setattr(user.profile, field, getattr(data, field))
    db.add(user)
    db.commit()
    db.refresh(user)
    return _profile_response(user)
