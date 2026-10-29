from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from .admin import require_admin
from .auth import _check_origin
from .database import get_db
from .job_schemas import (
    AdminJobCreate,
    AdminJobUpdate,
    GovernmentJobResponse,
    JobReviewRequest,
)
from .models import AuditLog, GovernmentJob, GovernmentJobDocument, User

router = APIRouter(prefix="/api/v1", tags=["administrator government jobs"])


def _job_query():
    return select(GovernmentJob).options(
        selectinload(GovernmentJob.documents)
    )


def _job_snapshot(job: GovernmentJob) -> dict[str, object]:
    return {
        "slug": job.slug,
        "title": job.title,
        "recruiting_body": job.recruiting_body,
        "description": job.description,
        "minimum_qualification": job.minimum_qualification,
        "minimum_education_level": job.minimum_education_level,
        "field_of_study": job.field_of_study,
        "minimum_experience_years": job.minimum_experience_years,
        "minimum_age": job.minimum_age,
        "maximum_age": job.maximum_age,
        "eligible_states": job.eligible_states,
        "application_deadline": (
            job.application_deadline.isoformat()
            if job.application_deadline
            else None
        ),
        "official_notice_url": job.official_notice_url,
        "application_url": job.application_url,
        "status": job.status,
        "verification_status": job.verification_status,
        "documents": [document.name for document in job.documents],
    }


def _job_values(payload: AdminJobCreate | AdminJobUpdate) -> dict[str, object]:
    values = payload.model_dump(exclude={"documents", "reason"})
    values["official_notice_url"] = str(payload.official_notice_url)
    values["application_url"] = (
        str(payload.application_url) if payload.application_url else None
    )
    return values


@router.get("/admin/jobs", response_model=list[GovernmentJobResponse])
def list_admin_jobs(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[GovernmentJobResponse]:
    jobs = db.scalars(_job_query().order_by(GovernmentJob.title)).all()
    return [GovernmentJobResponse.model_validate(job) for job in jobs]


@router.post("/admin/jobs", status_code=201, response_model=GovernmentJobResponse)
def create_job(
    payload: AdminJobCreate,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> GovernmentJobResponse:
    _check_origin(request)
    values = _job_values(payload)
    values.pop("slug", None)
    job = GovernmentJob(
        **values,
        slug=payload.slug,
        verification_status="unverified",
        requires_human_review=True,
        documents=[
            GovernmentJobDocument(
                name=document.name,
                description=document.description,
                is_required=document.is_required,
                sort_order=index,
            )
            for index, document in enumerate(payload.documents)
        ],
    )
    db.add(job)
    try:
        db.flush()
        db.add(
            AuditLog(
                actor_user_id=admin.id,
                action="admin.government_job_created",
                entity_type="government_job",
                entity_id=str(job.id),
                details={
                    "slug": job.slug,
                    "reason": payload.reason,
                    "verification_status": "unverified",
                },
            )
        )
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="A government job with this slug already exists."
        ) from error
    db.refresh(job)
    return GovernmentJobResponse.model_validate(job)


@router.put(
    "/admin/jobs/{job_slug}",
    response_model=GovernmentJobResponse,
)
def update_job(
    job_slug: str,
    payload: AdminJobUpdate,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> GovernmentJobResponse:
    _check_origin(request)
    job = db.scalar(_job_query().where(GovernmentJob.slug == job_slug))
    if job is None:
        raise HTTPException(status_code=404, detail="Government job not found.")
    if payload.slug != job_slug:
        raise HTTPException(status_code=422, detail="A job slug cannot be changed.")

    before = _job_snapshot(job)
    values = _job_values(payload)
    values.pop("slug", None)
    for field, value in values.items():
        setattr(job, field, value)
    job.documents.clear()
    db.flush()
    job.documents = [
        GovernmentJobDocument(
            name=document.name,
            description=document.description,
            is_required=document.is_required,
            sort_order=index,
        )
        for index, document in enumerate(payload.documents)
    ]
    job.requires_human_review = True
    if job.verification_status == "verified":
        job.verification_status = "requires_review"
    db.add(
        AuditLog(
            actor_user_id=admin.id,
            action="admin.government_job_updated",
            entity_type="government_job",
            entity_id=str(job.id),
            details={
                "before": before,
                "after": _job_snapshot(job),
                "reason": payload.reason,
                "requires_human_review": True,
            },
        )
    )
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="The government job update conflicts with existing data."
        ) from error
    db.refresh(job)
    return GovernmentJobResponse.model_validate(job)


@router.post(
    "/admin/jobs/{job_slug}/verify",
    response_model=GovernmentJobResponse,
)
def verify_job(
    job_slug: str,
    payload: JobReviewRequest,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> GovernmentJobResponse:
    _check_origin(request)
    job = db.scalar(_job_query().where(GovernmentJob.slug == job_slug))
    if job is None:
        raise HTTPException(status_code=404, detail="Government job not found.")
    now = datetime.now(timezone.utc)
    if job.status not in {"upcoming", "open"}:
        raise HTTPException(
            status_code=409,
            detail="Only upcoming or open recruitment notices can be verified.",
        )
    if job.application_deadline is not None:
        deadline = job.application_deadline
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)
        if deadline <= now:
            raise HTTPException(
                status_code=409,
                detail="Expired recruitment notices cannot be verified as current.",
            )

    before = _job_snapshot(job)
    job.verification_status = "verified"
    job.requires_human_review = False
    job.reviewed_by_user_id = admin.id
    job.last_verified_at = now
    db.add(
        AuditLog(
            actor_user_id=admin.id,
            action="admin.government_job_verified",
            entity_type="government_job",
            entity_id=str(job.id),
            details={
                "before": before,
                "after": _job_snapshot(job),
                "review_note": payload.review_note,
            },
        )
    )
    db.commit()
    db.refresh(job)
    return GovernmentJobResponse.model_validate(job)
