from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from .auth import get_current_user
from .database import get_db
from .eligibility import evaluate_scheme_criteria, scheme_is_trusted
from .models import (
    ApplicationTracking,
    Scheme,
    SchemeDeadline,
    SchemeStateCoverage,
    User,
)
from .recommendation_schemas import (
    DashboardSummaryResponse,
    RecommendationPageResponse,
    RecommendationSourceResponse,
    SchemeRecommendationResponse,
    VerifiedDeadlineResponse,
    page_count,
)

router = APIRouter(prefix="/api/v1", tags=["personalized discovery"])
REQUIRED_PROFILE_FIELDS = (
    ("state", "State or territory"),
    ("education_level", "Education level"),
    ("occupation", "Occupation"),
)


def _profile_completion(user: User) -> tuple[list[str], int]:
    profile = user.profile
    missing = [
        label
        for field, label in REQUIRED_PROFILE_FIELDS
        if not profile or not getattr(profile, field)
    ]
    completed = len(REQUIRED_PROFILE_FIELDS) - len(missing)
    return missing, round(completed / len(REQUIRED_PROFILE_FIELDS) * 100)


def _scheme_load_options():
    return (
        selectinload(Scheme.categories),
        selectinload(Scheme.state_coverage),
        selectinload(Scheme.eligibility_rules),
        selectinload(Scheme.sources),
    )


def _build_recommendation(
    scheme: Scheme,
    user: User,
) -> tuple[int, SchemeRecommendationResponse] | None:
    trusted = scheme_is_trusted(scheme)
    profile_groups = {
        category.casefold()
        for category in (user.profile.beneficiary_categories if user.profile else [])
        if isinstance(category, str)
    }
    matched_groups = [
        label
        for label in scheme.target_beneficiaries
        if isinstance(label, str) and label.casefold() in profile_groups
    ]
    criteria, outcome, summary = evaluate_scheme_criteria(scheme, user.profile)
    satisfied_criteria = [item for item in criteria if item.result == "satisfied"]

    state = user.profile.state if user.profile else None
    covered_states = [coverage.state for coverage in scheme.state_coverage]
    if trusted and covered_states and state and not any(
        covered.casefold() == state.casefold() for covered in covered_states
    ):
        return None

    if not trusted:
        return None

    if not matched_groups and not satisfied_criteria:
        return None

    reasons = [
        f"Your selected beneficiary group “{label}” matches the recorded target audience."
        for label in matched_groups
    ]
    if trusted and state and covered_states:
        reasons.append(f"The verified state coverage includes {state}.")
    reasons.extend(
        f"Your profile matches this recorded criterion: {item.criterion}"
        for item in satisfied_criteria
        if item.required
    )
    missing_information = list(
        dict.fromkeys(
            item.profile_field.replace("_", " ").capitalize()
            for item in criteria
            if item.result == "unknown" and item.profile_field
        )
    )
    if trusted and covered_states and not state:
        missing_information.append("State or territory")

    sources = [
        RecommendationSourceResponse(
            title=source.title,
            url=source.url,
            last_verified_at=source.last_verified_at,
        )
        for source in scheme.sources
        if trusted and source.status == "verified"
    ]
    rank = len(matched_groups) * 10 + len(satisfied_criteria) * 3
    if trusted:
        rank += 1
    return rank, SchemeRecommendationResponse(
        scheme_id=scheme.slug,
        scheme_name=scheme.name,
        short_description=scheme.description,
        category=scheme.categories[0].name if scheme.categories else None,
        data_status="verified",
        eligibility_status=outcome,
        summary=summary,
        reasons=reasons,
        criteria=criteria,
        missing_information=missing_information,
        sources=sources,
    )


@router.get("/recommendations", response_model=RecommendationPageResponse)
def get_recommendations(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 12,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RecommendationPageResponse:
    missing_profile_fields, completion = _profile_completion(user)
    statement = select(Scheme).where(
        Scheme.status != "inactive",
        Scheme.is_demo.is_(False),
        Scheme.verification_status == "verified",
        Scheme.requires_human_review.is_(False),
        Scheme.sources.any(status="verified"),
    )
    if user.profile and user.profile.state:
        statement = statement.where(
            or_(
                ~Scheme.state_coverage.any(),
                Scheme.state_coverage.any(
                    SchemeStateCoverage.state.ilike(user.profile.state)
                ),
            )
        )

    schemes = db.scalars(
        statement.options(*_scheme_load_options()).order_by(Scheme.name, Scheme.id)
    ).all()
    ranked = [
        recommendation
        for scheme in schemes
        if (recommendation := _build_recommendation(scheme, user)) is not None
    ]
    ranked.sort(
        key=lambda item: (
            -item[0],
            item[1].scheme_name.casefold(),
            item[1].scheme_id,
        )
    )
    total = len(ranked)
    start = (page - 1) * page_size
    items = [entry for _, entry in ranked[start : start + page_size]]
    return RecommendationPageResponse(
        profile_complete=user.profile_complete,
        completion_percentage=completion,
        missing_profile_fields=missing_profile_fields,
        items=items,
        page=page,
        page_size=page_size,
        total=total,
        pages=page_count(total, page_size),
    )


@router.get("/dashboard/summary", response_model=DashboardSummaryResponse)
def get_dashboard_summary(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DashboardSummaryResponse:
    status_rows = db.execute(
        select(ApplicationTracking.status, func.count(ApplicationTracking.id))
        .where(ApplicationTracking.user_id == user.id)
        .group_by(ApplicationTracking.status)
    ).all()
    status_counts = {status: count for status, count in status_rows}
    deadlines = db.scalars(
        select(SchemeDeadline)
        .join(Scheme, Scheme.id == SchemeDeadline.scheme_id)
        .where(
            SchemeDeadline.deadline_status == "known",
            SchemeDeadline.closes_at >= datetime.now(timezone.utc),
            Scheme.is_demo.is_(False),
            Scheme.verification_status == "verified",
            Scheme.requires_human_review.is_(False),
            Scheme.sources.any(status="verified"),
        )
        .options(
            selectinload(SchemeDeadline.scheme).selectinload(Scheme.sources)
        )
        .order_by(SchemeDeadline.closes_at)
        .limit(5)
    ).all()
    verified_deadlines = []
    for deadline in deadlines:
        scheme = deadline.scheme
        source = next(
            (item for item in scheme.sources if item.status == "verified"),
            None,
        )
        if source is None or deadline.closes_at is None:
            continue
        verified_deadlines.append(
            VerifiedDeadlineResponse(
                scheme_id=scheme.slug,
                scheme_name=scheme.name,
                closes_at=deadline.closes_at,
                source_title=source.title,
                source_url=source.url,
            )
        )
    return DashboardSummaryResponse(
        application_total=sum(status_counts.values()),
        application_status_counts=status_counts,
        verified_upcoming_deadlines=verified_deadlines,
    )
