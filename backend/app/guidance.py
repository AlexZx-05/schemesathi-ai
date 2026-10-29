"""Authenticated Phase 10 saved schemes, checklists, and self-reported tracking."""

import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from .auth import _check_origin, get_current_user
from .database import get_db
from .guidance_schemas import (
    ApplicationCreateRequest,
    ApplicationGuidanceResponse,
    ApplicationStatus,
    ApplicationTrackingResponse,
    ApplicationUpdateRequest,
    DocumentChecklistItemResponse,
    DocumentChecklistResponse,
    DocumentReadyRequest,
    SavedSchemeResponse,
)
from .models import (
    ApplicationTracking,
    AuditLog,
    SavedScheme,
    Scheme,
    SchemeDocument,
    SchemeSource,
    User,
    UserSchemeDocumentProgress,
    utc_now,
)

router = APIRouter(prefix="/api/v1", tags=["scheme guidance"])

STATUS_PROGRESS: dict[str, int] = {
    "planning": 10,
    "preparing_documents": 30,
    "ready_to_apply": 50,
    "submitted_externally": 65,
    "in_progress": 80,
    "completed": 100,
    "not_proceeding": 0,
}
ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "planning": {"preparing_documents", "ready_to_apply", "not_proceeding"},
    "preparing_documents": {"planning", "ready_to_apply", "not_proceeding"},
    "ready_to_apply": {"preparing_documents", "submitted_externally", "not_proceeding"},
    "submitted_externally": {"in_progress", "completed", "not_proceeding"},
    "in_progress": {"completed", "not_proceeding"},
    "completed": set(),
    "not_proceeding": {"planning", "preparing_documents"},
}
DOCUMENT_UNCERTAINTY_NOTICE = (
    "This requirement is not individually linked to a source in the catalogue. "
    "Confirm it with the official scheme source before applying."
)


def _source_max_age_days() -> int:
    configured = os.getenv("KNOWLEDGE_MAX_AGE_DAYS", "365")
    try:
        days = int(configured)
    except ValueError as error:
        raise RuntimeError("KNOWLEDGE_MAX_AGE_DAYS must be a positive integer.") from error
    if days < 1:
        raise RuntimeError("KNOWLEDGE_MAX_AGE_DAYS must be a positive integer.")
    return days


def _scheme_statement(scheme_id: str):
    return (
        select(Scheme)
        .where(Scheme.slug == scheme_id)
        .options(
            selectinload(Scheme.sources),
            selectinload(Scheme.documents),
        )
    )


def _scheme_or_404(db: Session, scheme_id: str) -> Scheme:
    scheme = db.scalar(_scheme_statement(scheme_id))
    if scheme is None:
        raise HTTPException(status_code=404, detail="Scheme not found.")
    return scheme


def _verified_sources(scheme: Scheme) -> list[SchemeSource]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=_source_max_age_days())
    return [
        source
        for source in scheme.sources
        if source.status == "verified"
        and source.last_verified_at is not None
        and (
            source.last_verified_at.replace(tzinfo=timezone.utc)
            if source.last_verified_at.tzinfo is None
            else source.last_verified_at
        )
        >= cutoff
    ]


def _guidance_notice(scheme: Scheme) -> str | None:
    if scheme.status != "active":
        return "This scheme is not currently recorded as active. Verify its current status first."
    if scheme.verification_status != "verified" or scheme.requires_human_review:
        return "This scheme record has not completed verification and cannot provide guidance."
    current_sources = _verified_sources(scheme)
    if not current_sources:
        if any(source.status == "stale" for source in scheme.sources):
            return "The scheme source has been marked stale and needs review."
        if any(source.status == "verified" for source in scheme.sources):
            return (
                "The verified source has no current verification date or is older "
                f"than {_source_max_age_days()} days. Review it before using this guidance."
            )
        return "No current verified source is available for this scheme."
    return None


def _require_guidance_scheme(db: Session, scheme_id: str) -> Scheme:
    scheme = _scheme_or_404(db, scheme_id)
    if notice := _guidance_notice(scheme):
        raise HTTPException(status_code=409, detail=notice)
    return scheme


def _saved_response(saved: SavedScheme) -> SavedSchemeResponse:
    scheme = saved.scheme
    notice = _guidance_notice(scheme)
    verified_dates = [
        source.last_verified_at
        for source in scheme.sources
        if source.status == "verified" and source.last_verified_at is not None
    ]
    last_verified_at = max(
        [date for date in [scheme.last_verified_at, *verified_dates] if date is not None],
        key=lambda date: (
            date.replace(tzinfo=timezone.utc)
            if date.tzinfo is None
            else date
        ),
        default=None,
    )
    return SavedSchemeResponse(
        id=saved.id,
        scheme_id=scheme.slug,
        scheme_name=scheme.name,
        scheme_status=scheme.status,
        verification_status=scheme.verification_status,
        last_verified_at=last_verified_at,
        guidance_available=notice is None,
        availability_notice=notice,
        saved_at=saved.created_at,
    )


def _application_response(application: ApplicationTracking) -> ApplicationTrackingResponse:
    return ApplicationTrackingResponse(
        id=application.id,
        scheme_id=application.scheme.slug,
        scheme_name=application.scheme.name,
        status=application.status,
        notes=application.notes,
        created_at=application.created_at,
        updated_at=application.updated_at,
        status_changed_at=application.status_changed_at,
        submitted_at=application.submitted_at,
        submitted_by_user_confirmation=application.submitted_at is not None,
        progress_percent=STATUS_PROGRESS[application.status],
    )


@router.get("/saved-schemes", response_model=list[SavedSchemeResponse])
def list_saved_schemes(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[SavedSchemeResponse]:
    saved = db.scalars(
        select(SavedScheme)
        .where(SavedScheme.user_id == user.id)
        .options(selectinload(SavedScheme.scheme).selectinload(Scheme.sources))
        .order_by(SavedScheme.created_at.desc())
    ).all()
    return [_saved_response(item) for item in saved]


@router.post("/saved-schemes/{scheme_id}", response_model=SavedSchemeResponse, status_code=201)
def save_scheme(
    scheme_id: str,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SavedSchemeResponse:
    _check_origin(request)
    scheme = _scheme_or_404(db, scheme_id)
    saved = SavedScheme(user_id=user.id, scheme_id=scheme.id)
    db.add(saved)
    try:
        db.flush()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="This scheme is already saved.") from error
    db.add(
        AuditLog(
            actor_user_id=user.id,
            action="saved_scheme.created",
            entity_type="saved_scheme",
            entity_id=str(saved.id),
            details={"scheme_id": scheme.slug},
        )
    )
    db.commit()
    db.refresh(saved)
    saved.scheme = scheme
    return _saved_response(saved)


@router.delete("/saved-schemes/{scheme_id}", status_code=204)
def unsave_scheme(
    scheme_id: str,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    _check_origin(request)
    saved = db.scalar(
        select(SavedScheme)
        .join(Scheme, Scheme.id == SavedScheme.scheme_id)
        .where(SavedScheme.user_id == user.id, Scheme.slug == scheme_id)
    )
    if saved is None:
        raise HTTPException(status_code=404, detail="Saved scheme not found.")
    db.add(
        AuditLog(
            actor_user_id=user.id,
            action="saved_scheme.removed",
            entity_type="saved_scheme",
            entity_id=str(saved.id),
            details={"scheme_id": scheme_id},
        )
    )
    db.delete(saved)
    db.commit()
    return Response(status_code=204)


@router.get("/schemes/{scheme_id}/documents/checklist", response_model=DocumentChecklistResponse)
def get_document_checklist(
    scheme_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentChecklistResponse:
    scheme = _require_guidance_scheme(db, scheme_id)
    progress = {
        item.scheme_document_id: item
        for item in db.scalars(
            select(UserSchemeDocumentProgress).where(
                UserSchemeDocumentProgress.user_id == user.id,
                UserSchemeDocumentProgress.scheme_document_id.in_([document.id for document in scheme.documents]),
            )
        ).all()
    }
    return DocumentChecklistResponse(
        scheme_id=scheme.slug,
        scheme_name=scheme.name,
        verification_status=scheme.verification_status,
        last_verified_at=scheme.last_verified_at,
        source_urls=[source.url for source in _verified_sources(scheme)],
        items=[
            DocumentChecklistItemResponse(
                document_id=document.id,
                name=document.name,
                description=document.description,
                is_required=document.is_required,
                ready=document.id in progress and progress[document.id].ready_at is not None,
                ready_at=progress[document.id].ready_at if document.id in progress else None,
                uncertainty_notice=DOCUMENT_UNCERTAINTY_NOTICE,
            )
            for document in scheme.documents
        ],
    )


@router.put("/schemes/{scheme_id}/documents/{document_id}", response_model=DocumentChecklistItemResponse)
def set_document_ready(
    scheme_id: str,
    document_id: int,
    payload: DocumentReadyRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentChecklistItemResponse:
    _check_origin(request)
    scheme = _require_guidance_scheme(db, scheme_id)
    document = next((item for item in scheme.documents if item.id == document_id), None)
    if document is None:
        raise HTTPException(status_code=404, detail="Scheme document not found.")
    progress = db.scalar(
        select(UserSchemeDocumentProgress).where(
            UserSchemeDocumentProgress.user_id == user.id,
            UserSchemeDocumentProgress.scheme_document_id == document.id,
        )
    )
    if progress is None:
        progress = UserSchemeDocumentProgress(
            user_id=user.id, scheme_document_id=document.id
        )
        db.add(progress)
    progress.ready_at = utc_now() if payload.ready else None
    db.add(
        AuditLog(
            actor_user_id=user.id,
            action="document_checklist.updated",
            entity_type="scheme_document",
            entity_id=str(document.id),
            details={"scheme_id": scheme.slug, "ready": payload.ready},
        )
    )
    db.commit()
    db.refresh(progress)
    return DocumentChecklistItemResponse(
        document_id=document.id,
        name=document.name,
        description=document.description,
        is_required=document.is_required,
        ready=progress.ready_at is not None,
        ready_at=progress.ready_at,
        uncertainty_notice=DOCUMENT_UNCERTAINTY_NOTICE,
    )


@router.get("/schemes/{scheme_id}/application-guidance", response_model=ApplicationGuidanceResponse)
def get_application_guidance(
    scheme_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApplicationGuidanceResponse:
    scheme = _require_guidance_scheme(db, scheme_id)
    ready_document_ids = set(
        db.scalars(
            select(UserSchemeDocumentProgress.scheme_document_id).where(
                UserSchemeDocumentProgress.user_id == user.id,
                UserSchemeDocumentProgress.scheme_document_id.in_([document.id for document in scheme.documents]),
                UserSchemeDocumentProgress.ready_at.is_not(None),
            )
        ).all()
    )
    required_remaining = sum(
        document.is_required and document.id not in ready_document_ids
        for document in scheme.documents
    )
    steps = [
        line.strip(" -•\t")
        for line in (scheme.application_instructions or "").splitlines()
        if line.strip()
    ]
    return ApplicationGuidanceResponse(
        scheme_id=scheme.slug,
        scheme_name=scheme.name,
        application_steps=steps,
        official_application_url=scheme.official_application_url,
        source_urls=[source.url for source in _verified_sources(scheme)],
        checklist_complete=required_remaining == 0,
        checklist_required_remaining=required_remaining,
        portal_notice=(
            "Use the recorded official portal to apply yourself."
            if scheme.official_application_url
            else "No official application portal is recorded. Review the verified sources before proceeding."
        ),
    )


@router.post("/applications", response_model=ApplicationTrackingResponse, status_code=201)
def create_application_tracking(
    payload: ApplicationCreateRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApplicationTrackingResponse:
    _check_origin(request)
    scheme = _require_guidance_scheme(db, payload.scheme_id)
    application = ApplicationTracking(
        user_id=user.id,
        scheme_id=scheme.id,
        status="planning",
        notes=payload.notes,
        status_changed_at=utc_now(),
    )
    db.add(application)
    try:
        db.flush()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="You are already tracking this scheme.") from error
    db.add(
        AuditLog(
            actor_user_id=user.id,
            action="application_tracking.created",
            entity_type="application_tracking",
            entity_id=str(application.id),
            details={"scheme_id": scheme.slug, "status": application.status},
        )
    )
    db.commit()
    db.refresh(application)
    application.scheme = scheme
    return _application_response(application)


@router.get("/applications", response_model=list[ApplicationTrackingResponse])
def list_applications(
    status: ApplicationStatus | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ApplicationTrackingResponse]:
    statement = (
        select(ApplicationTracking)
        .where(ApplicationTracking.user_id == user.id)
        .options(selectinload(ApplicationTracking.scheme))
        .order_by(ApplicationTracking.updated_at.desc())
    )
    if status:
        statement = statement.where(ApplicationTracking.status == status)
    return [_application_response(item) for item in db.scalars(statement).all()]


def _application_or_404(db: Session, application_id: int, user_id: int) -> ApplicationTracking:
    application = db.scalar(
        select(ApplicationTracking)
        .where(ApplicationTracking.id == application_id, ApplicationTracking.user_id == user_id)
        .options(selectinload(ApplicationTracking.scheme))
    )
    if application is None:
        raise HTTPException(status_code=404, detail="Application tracking record not found.")
    return application


@router.get("/applications/{application_id}", response_model=ApplicationTrackingResponse)
def get_application(
    application_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApplicationTrackingResponse:
    return _application_response(_application_or_404(db, application_id, user.id))


@router.patch("/applications/{application_id}", response_model=ApplicationTrackingResponse)
def update_application(
    application_id: int,
    payload: ApplicationUpdateRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApplicationTrackingResponse:
    _check_origin(request)
    application = _application_or_404(db, application_id, user.id)
    target = payload.status
    if target != application.status and target not in ALLOWED_TRANSITIONS[application.status]:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot move application from {application.status} to {target}.",
        )
    if target == "submitted_externally" and application.status != target and not payload.confirm_external_submission:
        raise HTTPException(
            status_code=422,
            detail="Confirm that you submitted this application through the official external portal.",
        )
    previous_status = application.status
    if target != previous_status:
        application.status = target
        application.status_changed_at = utc_now()
        if target == "submitted_externally":
            application.submitted_at = application.status_changed_at
            application.applied_at = application.status_changed_at
    if payload.notes is not None:
        application.notes = payload.notes
    db.add(
        AuditLog(
            actor_user_id=user.id,
            action="application_tracking.updated",
            entity_type="application_tracking",
            entity_id=str(application.id),
            details={
                "scheme_id": application.scheme.slug,
                "previous_status": previous_status,
                "status": application.status,
                "confirmed_external_submission": target == "submitted_externally" and previous_status != target,
            },
        )
    )
    db.commit()
    db.refresh(application)
    return _application_response(application)
