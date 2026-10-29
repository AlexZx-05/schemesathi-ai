from math import ceil
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import String, and_, cast, func, or_, select
from sqlalchemy.orm import Session, selectinload

from .catalog_schemas import (
    SchemeCategoryResponse,
    SchemeDetailResponse,
    SchemePageResponse,
    SchemeSourceResponse,
    SchemeSummaryResponse,
)
from .database import get_db
from .models import Scheme, SchemeCategory, SchemeSource, SchemeStateCoverage

router = APIRouter(prefix="/api/v1", tags=["scheme catalogue"])


def _split_content(value: str | None) -> list[str]:
    return [part.strip() for part in (value or "").splitlines() if part.strip()]


def _summary(scheme: Scheme) -> SchemeSummaryResponse:
    verified_source = next(
        (source.url for source in scheme.sources if source.status == "verified"),
        None,
    )
    return SchemeSummaryResponse(
        id=scheme.slug,
        name=scheme.name,
        short_description=scheme.description,
        category=scheme.categories[0].name if scheme.categories else None,
        beneficiaries=scheme.target_beneficiaries,
        government_level=scheme.government_level,
        keywords=scheme.keywords,
        benefits=_split_content(scheme.benefits),
        eligibility_criteria=[rule.rule_text for rule in scheme.eligibility_rules],
        required_documents=[document.name for document in scheme.documents],
        application_procedure=_split_content(scheme.application_instructions),
        official_source=verified_source,
        last_verified_date=(
            scheme.last_verified_at.date().isoformat()
            if scheme.last_verified_at
            else None
        ),
        data_status="verified",
    )


def _detail(scheme: Scheme) -> SchemeDetailResponse:
    summary = _summary(scheme)
    return SchemeDetailResponse(
        **summary.model_dump(),
        department=scheme.department,
        state_coverage=[entry.state for entry in scheme.state_coverage],
        application_url=scheme.official_application_url,
        sources=[
            SchemeSourceResponse.model_validate(source)
            for source in scheme.sources
            if source.status == "verified"
        ],
        publication_date=scheme.publication_date,
        effective_date=scheme.effective_date,
        status=scheme.status,
        verification_status=scheme.verification_status,
        requires_human_review=scheme.requires_human_review,
        deadline_information_status=(
            "known"
            if any(item.deadline_status == "known" for item in scheme.deadlines)
            else "unknown"
        ),
        deadlines=scheme.deadlines,
        created_at=scheme.created_at,
        updated_at=scheme.updated_at,
    )


def _with_details():
    return (
        selectinload(Scheme.categories),
        selectinload(Scheme.state_coverage),
        selectinload(Scheme.eligibility_rules),
        selectinload(Scheme.documents),
        selectinload(Scheme.sources),
        selectinload(Scheme.deadlines),
    )


def _public_scheme_conditions():
    return (
        Scheme.is_demo.is_(False),
        Scheme.verification_status == "verified",
        Scheme.requires_human_review.is_(False),
        Scheme.sources.any(SchemeSource.status == "verified"),
    )


@router.get("/schemes", response_model=SchemePageResponse)
def list_schemes(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    q: Annotated[str | None, Query(max_length=200)] = None,
    category: Annotated[str | None, Query(max_length=120)] = None,
    state: Annotated[str | None, Query(max_length=100)] = None,
    government_level: Annotated[str | None, Query(max_length=20)] = None,
    status: Annotated[str | None, Query(pattern="^(active|inactive|unknown)$")] = None,
    db: Session = Depends(get_db),
) -> SchemePageResponse:
    conditions = list(_public_scheme_conditions())
    if q and q.strip():
        pattern = f"%{q.strip()}%"
        conditions.append(
            or_(
                Scheme.name.ilike(pattern),
                Scheme.description.ilike(pattern),
                Scheme.department.ilike(pattern),
                cast(Scheme.target_beneficiaries, String).ilike(pattern),
                cast(Scheme.keywords, String).ilike(pattern),
                Scheme.categories.any(
                    or_(
                        SchemeCategory.name.ilike(pattern),
                        SchemeCategory.slug.ilike(pattern),
                    )
                ),
            )
        )
    if category:
        conditions.append(
            Scheme.categories.any(
                or_(
                    SchemeCategory.slug == category,
                    SchemeCategory.name.ilike(category),
                )
            )
        )
    if state:
        conditions.append(Scheme.state_coverage.any(SchemeStateCoverage.state == state))
    if government_level:
        conditions.append(Scheme.government_level == government_level)
    if status:
        conditions.append(Scheme.status == status)

    total = db.scalar(select(func.count(Scheme.id)).where(*conditions)) or 0
    records = db.scalars(
        select(Scheme)
        .where(*conditions)
        .options(*_with_details())
        .order_by(Scheme.name, Scheme.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return SchemePageResponse(
        items=[_summary(scheme) for scheme in records],
        page=page,
        page_size=page_size,
        total=total,
        pages=ceil(total / page_size) if total else 0,
    )


@router.get("/schemes/{scheme_id}", response_model=SchemeDetailResponse)
def get_scheme(scheme_id: str, db: Session = Depends(get_db)) -> SchemeDetailResponse:
    statement = (
        select(Scheme)
        .where(Scheme.slug == scheme_id, *_public_scheme_conditions())
        .options(*_with_details())
    )
    if scheme_id.isdecimal():
        statement = (
            select(Scheme)
            .where(
                or_(Scheme.slug == scheme_id, Scheme.id == int(scheme_id)),
                *_public_scheme_conditions(),
            )
            .options(*_with_details())
        )
    scheme = db.scalar(statement)
    if scheme is None:
        raise HTTPException(status_code=404, detail="Scheme not found.")
    return _detail(scheme)


@router.get(
    "/schemes/{scheme_id}/sources",
    response_model=list[SchemeSourceResponse],
)
def list_scheme_sources(
    scheme_id: str,
    db: Session = Depends(get_db),
) -> list[SchemeSourceResponse]:
    scheme = db.scalar(
        select(Scheme)
        .where(Scheme.slug == scheme_id, *_public_scheme_conditions())
        .options(selectinload(Scheme.sources))
    )
    if scheme is None:
        raise HTTPException(status_code=404, detail="Scheme not found.")
    sources = [source for source in scheme.sources if source.status == "verified"]
    return [SchemeSourceResponse.model_validate(source) for source in sources]


@router.get("/categories", response_model=list[SchemeCategoryResponse])
def list_categories(db: Session = Depends(get_db)) -> list[SchemeCategoryResponse]:
    public_scheme = and_(*_public_scheme_conditions())
    categories = db.scalars(
        select(SchemeCategory)
        .where(SchemeCategory.schemes.any(public_scheme))
        .order_by(SchemeCategory.name)
    ).all()
    return [SchemeCategoryResponse.model_validate(category) for category in categories]
