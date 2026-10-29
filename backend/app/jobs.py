from datetime import datetime, timedelta, timezone
from math import ceil
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from .auth import get_current_user
from .database import get_db
from .job_schemas import (
    GovernmentJobPageResponse,
    GovernmentJobRecommendationPageResponse,
    GovernmentJobRecommendationResponse,
    GovernmentJobResponse,
)
from .models import GovernmentJob, User
from .schemas import US_STATES_AND_TERRITORIES

router = APIRouter(prefix="/api/v1", tags=["government jobs"])
MAX_VERIFICATION_AGE = timedelta(days=30)
EDUCATION_RANK = {
    "No formal schooling": 0,
    "Primary": 1,
    "Secondary": 2,
    "Higher secondary": 3,
    "Diploma or vocational": 4,
    "Undergraduate": 5,
    "Postgraduate": 6,
}


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def _is_public(job: GovernmentJob, now: datetime) -> bool:
    if (
        job.status not in {"open", "upcoming"}
        or job.verification_status != "verified"
        or job.requires_human_review
        or job.last_verified_at is None
        or _utc(job.last_verified_at) < now - MAX_VERIFICATION_AGE
    ):
        return False
    if job.deadline_status == "known" and job.application_deadline is None:
        return False
    if job.application_deadline and _utc(job.application_deadline) < now:
        return False
    if (
        job.status == "open"
        and job.application_opens
        and _utc(job.application_opens) > now
    ):
        return False
    if (
        job.status == "upcoming"
        and job.application_opens
        and _utc(job.application_opens) <= now
    ):
        return False
    return True


def _job_query():
    return select(GovernmentJob).options(
        selectinload(GovernmentJob.documents)
    )


def _matches_location(job: GovernmentJob, state: str | None) -> bool:
    return not job.eligible_states or state is None or any(
        item.casefold() == state.casefold() for item in job.eligible_states
    )


@router.get("/jobs", response_model=GovernmentJobPageResponse)
def list_jobs(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 20,
    q: Annotated[str | None, Query(max_length=200)] = None,
    state: Annotated[str | None, Query(max_length=80)] = None,
    db: Session = Depends(get_db),
) -> GovernmentJobPageResponse:
    if state is not None and state not in US_STATES_AND_TERRITORIES:
        raise HTTPException(
            status_code=422,
            detail="Select a state or union territory from the supported list.",
        )
    statement = _job_query()
    if q and q.strip():
        pattern = f"%{q.strip()}%"
        statement = statement.where(
            or_(
                GovernmentJob.title.ilike(pattern),
                GovernmentJob.recruiting_body.ilike(pattern),
                GovernmentJob.description.ilike(pattern),
            )
        )
    jobs = db.scalars(statement).all()
    now = datetime.now(timezone.utc)
    matching = [
        job
        for job in jobs
        if _is_public(job, now) and _matches_location(job, state)
    ]
    matching.sort(
        key=lambda job: (
            _utc(job.application_deadline)
            if job.application_deadline
            else datetime.max.replace(tzinfo=timezone.utc),
            job.title.casefold(),
            job.id,
        )
    )
    total = len(matching)
    offset = (page - 1) * page_size
    return GovernmentJobPageResponse(
        items=[
            GovernmentJobResponse.model_validate(job)
            for job in matching[offset : offset + page_size]
        ],
        page=page,
        page_size=page_size,
        total=total,
        pages=ceil(total / page_size) if total else 0,
    )


@router.get("/jobs/{job_slug}", response_model=GovernmentJobResponse)
def get_job(
    job_slug: str,
    db: Session = Depends(get_db),
) -> GovernmentJobResponse:
    job = db.scalar(_job_query().where(GovernmentJob.slug == job_slug))
    if job is None or not _is_public(job, datetime.now(timezone.utc)):
        raise HTTPException(status_code=404, detail="Government job not found.")
    return GovernmentJobResponse.model_validate(job)


def _recommendation(
    job: GovernmentJob, user: User
) -> tuple[int, GovernmentJobRecommendationResponse] | None:
    profile = user.profile
    profile_states = (
        profile.preferred_job_states
        or ([profile.state] if profile and profile.state else [])
        if profile
        else []
    )
    if job.eligible_states and profile_states and not any(
        eligible.casefold() == selected.casefold()
        for eligible in job.eligible_states
        for selected in profile_states
    ):
        return None

    match_reasons: list[str] = []
    missing: list[str] = []
    score = 0

    if job.minimum_age is not None or job.maximum_age is not None:
        if profile is None or profile.age is None:
            missing.append("Age requirement needs confirmation")
        elif (
            (job.minimum_age is not None and profile.age < job.minimum_age)
            or (job.maximum_age is not None and profile.age > job.maximum_age)
        ):
            return None
        else:
            match_reasons.append("Your recorded age is within the listed age range.")
            score += 2

    if job.minimum_education_level:
        if profile is None or profile.education_level is None:
            missing.append("Education level")
        elif (
            profile.education_level in EDUCATION_RANK
            and job.minimum_education_level in EDUCATION_RANK
        ):
            if (
                EDUCATION_RANK[profile.education_level]
                < EDUCATION_RANK[job.minimum_education_level]
            ):
                return None
            match_reasons.append(
                "Your recorded education level meets the listed minimum level."
            )
            score += 3
        else:
            missing.append("Confirm education requirements in the official notice")

    if job.minimum_qualification:
        if profile is None or not profile.qualification:
            missing.append("Specific qualification")
        elif profile.qualification.casefold() in job.minimum_qualification.casefold():
            match_reasons.append("Your recorded qualification matches the notice.")
            score += 3
        else:
            missing.append("Confirm the specific qualification in the official notice")

    if job.field_of_study:
        if profile is None or not profile.field_of_study:
            missing.append("Field of study")
        elif profile.field_of_study.casefold() in job.field_of_study.casefold():
            match_reasons.append("Your recorded field of study matches the notice.")
            score += 2
        else:
            missing.append("Confirm the required subject or discipline in the notice")

    if job.minimum_experience_years is not None:
        if profile is None or profile.years_experience is None:
            missing.append("Years of experience")
        elif profile.years_experience < job.minimum_experience_years:
            return None
        else:
            match_reasons.append(
                "Your recorded experience meets the listed minimum."
            )
            score += 2

    preferred_roles = profile.preferred_job_roles if profile else []
    searchable_job = " ".join((job.title, *job.keywords)).casefold()
    role_matches = [
        role for role in preferred_roles if role.casefold() in searchable_job
    ]
    if role_matches:
        match_reasons.append(
            f"Matches your job interest: {', '.join(role_matches)}."
        )
        score += len(role_matches) * 2

    if job.eligible_states and profile_states:
        match_reasons.append(
            "The notice lists your preferred location among eligible locations."
        )
        score += 2
    if not match_reasons:
        match_reasons.append(
            "Potential listing only; compare your details with the official notice."
        )

    data = GovernmentJobResponse.model_validate(job).model_dump()
    return score, GovernmentJobRecommendationResponse(
        **data,
        match_reasons=match_reasons,
        missing_information=list(dict.fromkeys(missing)),
    )


@router.get(
    "/job-recommendations",
    response_model=GovernmentJobRecommendationPageResponse,
)
def get_job_recommendations(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GovernmentJobRecommendationPageResponse:
    jobs = db.scalars(_job_query()).all()
    now = datetime.now(timezone.utc)
    ranked = [
        recommendation
        for job in jobs
        if _is_public(job, now)
        and (recommendation := _recommendation(job, user)) is not None
    ]
    ranked.sort(
        key=lambda item: (
            -item[0],
            _utc(item[1].application_deadline)
            if item[1].application_deadline
            else datetime.max.replace(tzinfo=timezone.utc),
            item[1].title.casefold(),
        )
    )
    return GovernmentJobRecommendationPageResponse(
        items=[item for _, item in ranked[:20]],
        profile_complete=user.profile_complete,
    )
