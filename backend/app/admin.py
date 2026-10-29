"""Role-protected scheme quality dashboard and review workflows."""

import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from .admin_schemas import (
    AdminCategoryRequest,
    AdminDocumentRequest,
    AdminEligibilityRuleRequest,
    AdminSchemeCreate,
    AdminSchemeUpdate,
    AdminSourceVerificationRequest,
    CorrectionReviewRequest,
    CorrectionSubmissionRequest,
    SchemeReviewRequest,
)
from .auth import _check_origin, get_current_user
from .database import get_db
from .eligibility import PROFILE_FIELDS, RULE_OPERATORS
from .models import (
    AuditLog,
    Conversation,
    ConversationMessage,
    Scheme,
    SchemeCategory,
    SchemeDocument,
    SchemeEligibilityRule,
    SchemeKnowledgeChunk,
    SchemeReport,
    SchemeReviewHistory,
    SchemeSource,
    User,
    utc_now,
)

router = APIRouter(prefix="/api/v1", tags=["administrator dashboard"])

def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Administrator access required.")
    return user


def _record_review(
    db: Session,
    *,
    admin: User,
    scheme_id: int | None,
    action: str,
    reason: str,
    before: dict[str, object] | None = None,
    after: dict[str, object] | None = None,
) -> None:
    db.add(
        SchemeReviewHistory(
            scheme_id=scheme_id,
            actor_user_id=admin.id,
            action=action,
            reason=reason,
            before_snapshot=before,
            after_snapshot=after,
        )
    )


def _scheme_snapshot(scheme: Scheme) -> dict[str, object]:
    return {
        "name": scheme.name,
        "slug": scheme.slug,
        "description": scheme.description,
        "benefits": scheme.benefits,
        "department": scheme.department,
        "government_level": scheme.government_level,
        "beneficiaries": scheme.target_beneficiaries,
        "keywords": scheme.keywords,
        "application_instructions": scheme.application_instructions,
        "official_application_url": scheme.official_application_url,
        "status": scheme.status,
        "verification_status": scheme.verification_status,
        "requires_human_review": scheme.requires_human_review,
    }


def _mark_scheme_for_review(scheme: Scheme) -> None:
    if not scheme.is_demo and scheme.verification_status == "verified":
        scheme.verification_status = "requires_review"
    scheme.requires_human_review = True


def _freshness_days() -> int:
    configured = os.getenv("KNOWLEDGE_MAX_AGE_DAYS", "365")
    try:
        days = int(configured)
    except ValueError as error:
        raise RuntimeError("KNOWLEDGE_MAX_AGE_DAYS must be a positive integer.") from error
    if days < 1:
        raise RuntimeError("KNOWLEDGE_MAX_AGE_DAYS must be a positive integer.")
    return days


def _source_is_current(source: SchemeSource, now: datetime) -> bool:
    if source.status != "verified" or source.last_verified_at is None:
        return False
    verified_at = source.last_verified_at
    if verified_at.tzinfo is None:
        verified_at = verified_at.replace(tzinfo=timezone.utc)
    return verified_at >= now - timedelta(days=_freshness_days())


def _source_data(source: SchemeSource, now: datetime) -> dict[str, object]:
    return {
        "id": source.id,
        "scheme_id": source.scheme.slug,
        "scheme_name": source.scheme.name,
        "url": source.url,
        "title": source.title,
        "domain": source.official_domain,
        "status": source.status,
        "last_verified_at": source.last_verified_at,
        "reviewed_by_user_id": source.reviewed_by_user_id,
        "current": _source_is_current(source, now),
        "indexed_chunks": len(source.knowledge_chunks),
    }


def _eligibility_rule_is_supported(rule_data: object) -> bool:
    if (
        not isinstance(rule_data, dict)
        or set(rule_data) != {"field", "operator", "value"}
    ):
        return False
    field = rule_data["field"]
    operator = rule_data["operator"]
    return (
        isinstance(field, str)
        and field in PROFILE_FIELDS
        and isinstance(operator, str)
        and operator in RULE_OPERATORS[field]
    )


@router.get("/admin/dashboard")
def get_admin_dashboard(
    admin: User = Depends(require_admin), db: Session = Depends(get_db)
) -> dict[str, object]:
    now = utc_now()
    schemes = db.scalars(
        select(Scheme).where(Scheme.is_demo.is_(False)).options(
            selectinload(Scheme.categories),
            selectinload(Scheme.sources).selectinload(SchemeSource.knowledge_chunks),
            selectinload(Scheme.eligibility_rules),
            selectinload(Scheme.documents),
            selectinload(Scheme.deadlines),
        ).order_by(Scheme.name)
    ).all()
    scheme_items = []
    source_items = []
    for scheme in schemes:
        flags: list[str] = []
        if scheme.description.startswith(
            "Candidate record awaiting administrator review"
        ):
            flags.append("Replace candidate placeholder with a source-backed overview")
        if not scheme.official_application_url:
            flags.append("Missing official application URL")
        if any(
            not _eligibility_rule_is_supported(rule.rule_data)
            for rule in scheme.eligibility_rules
        ):
            flags.append("Unsupported or unstructured eligibility rule")
        if any(deadline.deadline_status == "known" and (
            deadline.source_id is None
            or deadline.last_verified_at is None
            or deadline.last_verified_at.replace(tzinfo=timezone.utc)
            < now - timedelta(days=_freshness_days())
        ) for deadline in scheme.deadlines):
            flags.append("Deadline requires re-verification")
        if any(source.status == "verified" and not _source_is_current(source, now) for source in scheme.sources):
            flags.append("Source is stale")
        if scheme.requires_human_review:
            flags.append("Human review required")
        scheme_items.append(
            {
                "id": scheme.id,
                "slug": scheme.slug,
                "name": scheme.name,
                "description": scheme.description,
                "benefits": scheme.benefits,
                "department": scheme.department,
                "government_level": scheme.government_level,
                "beneficiaries": scheme.target_beneficiaries,
                "keywords": scheme.keywords,
                "application_instructions": scheme.application_instructions,
                "status": scheme.status,
                "verification_status": scheme.verification_status,
                "requires_human_review": scheme.requires_human_review,
                "reviewed_by_user_id": scheme.reviewed_by_user_id,
                "last_verified_at": scheme.last_verified_at,
                "official_application_url": scheme.official_application_url,
                "category_names": [category.name for category in scheme.categories],
                "issue_flags": flags,
                "source_count": len(scheme.sources),
                "rule_count": len(scheme.eligibility_rules),
                "document_count": len(scheme.documents),
                "eligibility_rules": [
                    {
                        "id": rule.id,
                        "rule_type": rule.rule_type,
                        "rule_text": rule.rule_text,
                        "rule_data": rule.rule_data,
                        "source_id": rule.source_id,
                        "required": rule.is_required,
                    }
                    for rule in scheme.eligibility_rules
                ],
                "documents": [
                    {
                        "id": document.id,
                        "name": document.name,
                        "description": document.description,
                        "required": document.is_required,
                    }
                    for document in scheme.documents
                ],
                "deadlines": [
                    {
                        "id": deadline.id,
                        "status": deadline.deadline_status,
                        "closes_at": deadline.closes_at,
                        "source_id": deadline.source_id,
                        "last_verified_at": deadline.last_verified_at,
                    }
                    for deadline in scheme.deadlines
                ],
            }
        )
        source_items.extend(_source_data(source, now) for source in scheme.sources)

    failures = db.scalars(
        select(AuditLog)
        .where(AuditLog.action == "knowledge.ingestion_failed")
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .limit(50)
    ).all()
    failed_source_ids = {
        int(item.entity_id)
        for item in failures
        if item.entity_id and item.entity_id.isdecimal()
    }
    ingestion = []
    for source in [source for scheme in schemes for source in scheme.sources]:
        ingestion.append(
            {
                **_source_data(source, now),
                "indexed_chunks": len(source.knowledge_chunks),
                "indexed": bool(source.knowledge_chunks),
                "latest_failure": next(
                    (
                        item.details.get("error")
                        for item in failures
                        if item.entity_id == str(source.id)
                    ),
                    None,
                ),
                "has_failure": source.id in failed_source_ids,
            }
        )
    corrections = db.scalars(
        select(SchemeReport)
        .where(SchemeReport.status.in_(["open", "in_review"]))
        .order_by(SchemeReport.created_at.desc())
        .limit(50)
    ).all()
    categories = db.scalars(
        select(SchemeCategory).options(selectinload(SchemeCategory.schemes))
        .order_by(SchemeCategory.name)
    ).all()
    feedback = db.execute(
        select(
            ConversationMessage.id,
            ConversationMessage.content,
            ConversationMessage.feedback,
            ConversationMessage.created_at,
            Conversation.id.label("conversation_id"),
        )
        .join(Conversation, Conversation.id == ConversationMessage.conversation_id)
        .where(
            ConversationMessage.role == "assistant",
            ConversationMessage.feedback.is_not(None),
        )
        .order_by(ConversationMessage.created_at.desc())
        .limit(50)
    ).all()
    audit = db.scalars(
        select(AuditLog).order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).limit(50)
    ).all()
    reviews = db.scalars(
        select(SchemeReviewHistory)
        .order_by(SchemeReviewHistory.created_at.desc(), SchemeReviewHistory.id.desc())
        .limit(50)
    ).all()
    return {
        "administrator": {"id": admin.id, "name": admin.full_name},
        "counts": {
            "schemes": len(schemes),
            "verified_schemes": sum(
                scheme.verification_status == "verified" for scheme in schemes
            ),
            "categories": db.scalar(select(func.count(SchemeCategory.id))) or 0,
            "sources": len(source_items),
            "stale_sources": sum(not item["current"] for item in source_items),
            "indexed_documents": sum(bool(item["indexed"]) for item in ingestion),
            "failed_extractions": sum(
                item.action == "knowledge.ingestion_failed" for item in failures
            ),
            "open_corrections": len(corrections),
            "feedback_items": len(feedback),
        },
        "schemes": scheme_items,
        "categories": [
            {
                "id": category.id,
                "name": category.name,
                "slug": category.slug,
                "description": category.description,
                "scheme_count": len(category.schemes),
            }
            for category in categories
        ],
        "sources": source_items,
        "ingestion": ingestion,
        "failed_extractions": [
            {
                "id": item.id,
                "source_id": item.entity_id,
                "created_at": item.created_at,
                "error": (item.details or {}).get("error"),
                "scheme_id": (item.details or {}).get("scheme_id"),
            }
            for item in failures
        ],
        "corrections": [
            {
                "id": item.id,
                "scheme_id": item.scheme_id,
                "report_type": item.report_type,
                "description": item.description,
                "status": item.status,
                "created_at": item.created_at,
                "review_notes": item.review_notes,
            }
            for item in corrections
        ],
        "assistant_feedback": [
            {
                "message_id": item.id,
                "conversation_id": item.conversation_id,
                "content": item.content,
                "feedback": item.feedback,
                "created_at": item.created_at,
            }
            for item in feedback
        ],
        "audit_logs": [
            {
                "id": item.id,
                "actor_user_id": item.actor_user_id,
                "action": item.action,
                "entity_type": item.entity_type,
                "entity_id": item.entity_id,
                "details": item.details,
                "created_at": item.created_at,
            }
            for item in audit
        ],
        "review_history": [
            {
                "id": item.id,
                "scheme_id": item.scheme_id,
                "actor_user_id": item.actor_user_id,
                "action": item.action,
                "reason": item.reason,
                "before_snapshot": item.before_snapshot,
                "after_snapshot": item.after_snapshot,
                "created_at": item.created_at,
            }
            for item in reviews
        ],
    }


@router.get("/admin/categories")
def list_admin_categories(
    _: User = Depends(require_admin), db: Session = Depends(get_db)
) -> list[dict[str, object]]:
    categories = db.scalars(select(SchemeCategory).order_by(SchemeCategory.name)).all()
    return [
        {
            "id": item.id,
            "name": item.name,
            "slug": item.slug,
            "description": item.description,
            "scheme_count": len(item.schemes),
        }
        for item in categories
    ]


@router.post("/admin/categories", status_code=201)
def create_category(
    payload: AdminCategoryRequest,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    _check_origin(request)
    category = SchemeCategory(**payload.model_dump())
    db.add(category)
    try:
        db.flush()
        db.add(
            AuditLog(
                actor_user_id=admin.id,
                action="admin.category_created",
                entity_type="scheme_category",
                entity_id=str(category.id),
                details={"slug": category.slug},
            )
        )
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="Category name or slug already exists.") from error
    return {"id": category.id, "name": category.name, "slug": category.slug}


@router.put("/admin/categories/{category_id}")
def update_category(
    category_id: int,
    payload: AdminCategoryRequest,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    _check_origin(request)
    category = db.get(SchemeCategory, category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found.")
    before = {"name": category.name, "slug": category.slug, "description": category.description}
    for field, value in payload.model_dump().items():
        setattr(category, field, value)
    for scheme in category.schemes:
        _mark_scheme_for_review(scheme)
        _record_review(
            db,
            admin=admin,
            scheme_id=scheme.id,
            action="category_updated",
            reason="Category metadata changed; scheme record requires review.",
            before={"category": before},
            after={"category": payload.model_dump()},
        )
    db.add(
        AuditLog(
            actor_user_id=admin.id,
            action="admin.category_updated",
            entity_type="scheme_category",
            entity_id=str(category.id),
            details={"before": before, "after": payload.model_dump()},
        )
    )
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="Category name or slug already exists.") from error
    return {"id": category.id, **payload.model_dump()}


@router.delete("/admin/categories/{category_id}", status_code=204)
def delete_category(
    category_id: int,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> None:
    _check_origin(request)
    category = db.scalar(
        select(SchemeCategory)
        .where(SchemeCategory.id == category_id)
        .options(selectinload(SchemeCategory.schemes))
    )
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found.")
    if category.schemes:
        raise HTTPException(
            status_code=409,
            detail="Move schemes to another category before deleting this category.",
        )
    before = {"name": category.name, "slug": category.slug}
    db.add(
        AuditLog(
            actor_user_id=admin.id,
            action="admin.category_deleted",
            entity_type="scheme_category",
            entity_id=str(category.id),
            details=before,
        )
    )
    db.delete(category)
    db.commit()


@router.post("/admin/schemes", status_code=201)
def create_scheme(
    payload: AdminSchemeCreate,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    _check_origin(request)
    values = payload.model_dump()
    category_id = values.pop("category_id")
    values["target_beneficiaries"] = values.pop("beneficiaries")
    if category_id is not None:
        category = db.get(SchemeCategory, category_id)
        if category is None:
            raise HTTPException(status_code=422, detail="Category not found.")
        categories = [category]
    else:
        categories = []
    values["official_application_url"] = (
        str(values["official_application_url"])
        if values["official_application_url"]
        else None
    )
    scheme = Scheme(
        **values,
        categories=categories,
        verification_status="unverified",
        requires_human_review=True,
        is_demo=False,
    )
    db.add(scheme)
    try:
        db.flush()
        _record_review(
            db,
            admin=admin,
            scheme_id=scheme.id,
            action="scheme_created",
            reason="New scheme records require independent review before verification.",
            after=_scheme_snapshot(scheme),
        )
        db.add(
            AuditLog(
                actor_user_id=admin.id,
                action="admin.scheme_created",
                entity_type="scheme",
                entity_id=str(scheme.id),
                details={"slug": scheme.slug},
            )
        )
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="Scheme slug already exists.") from error
    return {"id": scheme.id, "slug": scheme.slug, "verification_status": scheme.verification_status}


@router.patch("/admin/schemes/{scheme_id}")
def update_scheme(
    scheme_id: str,
    payload: AdminSchemeUpdate,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    _check_origin(request)
    scheme = db.scalar(
        select(Scheme).where(Scheme.slug == scheme_id).options(selectinload(Scheme.categories))
    )
    if scheme is None:
        raise HTTPException(status_code=404, detail="Scheme not found.")
    before = _scheme_snapshot(scheme)
    changes = payload.model_dump(exclude_unset=True, exclude={"reason"})
    category_id = changes.pop("category_id", None)
    if "category_id" in payload.model_fields_set:
        category = db.get(SchemeCategory, category_id) if category_id else None
        if category_id is not None and category is None:
            raise HTTPException(status_code=422, detail="Category not found.")
        scheme.categories = [category] if category else []
    if "official_application_url" in changes:
        changes["official_application_url"] = (
            str(changes["official_application_url"])
            if changes["official_application_url"]
            else None
        )
    for field, value in changes.items():
        setattr(scheme, field, value)
    _mark_scheme_for_review(scheme)
    after = _scheme_snapshot(scheme)
    _record_review(
        db,
        admin=admin,
        scheme_id=scheme.id,
        action="scheme_updated_pending_review",
        reason=payload.reason,
        before=before,
        after=after,
    )
    db.add(
        AuditLog(
            actor_user_id=admin.id,
            action="admin.scheme_updated",
            entity_type="scheme",
            entity_id=str(scheme.id),
            details={"changed_fields": sorted(changes), "requires_review": True},
        )
    )
    db.commit()
    return {
        "id": scheme.id,
        "slug": scheme.slug,
        "verification_status": scheme.verification_status,
        "requires_human_review": scheme.requires_human_review,
    }


@router.post("/admin/schemes/{scheme_id}/verify")
def verify_scheme_record(
    scheme_id: str,
    payload: SchemeReviewRequest,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    _check_origin(request)
    scheme = db.scalar(
        select(Scheme)
        .where(Scheme.slug == scheme_id)
        .options(selectinload(Scheme.sources))
    )
    if scheme is None:
        raise HTTPException(status_code=404, detail="Scheme not found.")
    if scheme.is_demo:
        raise HTTPException(
            status_code=409,
            detail="This record is marked as non-publishable and cannot be verified.",
        )
    if scheme.description.startswith(
        "Candidate record awaiting administrator review"
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "Replace the candidate placeholder with a source-backed overview "
                "before verifying this scheme."
            ),
        )
    now = utc_now()
    current_sources = [source for source in scheme.sources if _source_is_current(source, now)]
    if not current_sources:
        raise HTTPException(
            status_code=409,
            detail="Verify at least one current official source before verifying this scheme.",
        )
    before = _scheme_snapshot(scheme)
    scheme.verification_status = "verified"
    scheme.requires_human_review = False
    scheme.reviewed_by_user_id = admin.id
    scheme.last_verified_at = now
    after = _scheme_snapshot(scheme)
    _record_review(
        db,
        admin=admin,
        scheme_id=scheme.id,
        action="scheme_verified",
        reason=payload.review_note,
        before=before,
        after=after,
    )
    db.add(
        AuditLog(
            actor_user_id=admin.id,
            action="admin.scheme_verified",
            entity_type="scheme",
            entity_id=str(scheme.id),
            details={"source_ids": [source.id for source in current_sources]},
        )
    )
    db.commit()
    return {
        "slug": scheme.slug,
        "verification_status": scheme.verification_status,
        "last_verified_at": scheme.last_verified_at,
        "reviewed_by_user_id": scheme.reviewed_by_user_id,
    }


def _scheme_for_edit(db: Session, slug: str) -> Scheme:
    scheme = db.scalar(select(Scheme).where(Scheme.slug == slug))
    if scheme is None:
        raise HTTPException(status_code=404, detail="Scheme not found.")
    return scheme


def _require_scheme_source(
    db: Session, scheme: Scheme, source_id: int | None
) -> SchemeSource | None:
    if source_id is None:
        return None
    source = db.get(SchemeSource, source_id)
    if source is None or source.scheme_id != scheme.id:
        raise HTTPException(status_code=422, detail="Rule source must belong to this scheme.")
    return source


@router.post("/admin/schemes/{scheme_id}/eligibility-rules", status_code=201)
def create_eligibility_rule(
    scheme_id: str,
    payload: AdminEligibilityRuleRequest,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    _check_origin(request)
    scheme = _scheme_for_edit(db, scheme_id)
    _require_scheme_source(db, scheme, payload.source_id)
    rule = SchemeEligibilityRule(
        scheme_id=scheme.id,
        rule_type=payload.rule_type,
        rule_text=payload.rule_text,
        rule_data=payload.rule_data,
        source_id=payload.source_id,
        is_required=payload.is_required,
        sort_order=payload.sort_order,
    )
    db.add(rule)
    db.flush()
    before = None
    after = {
        "rule_type": rule.rule_type,
        "rule_text": rule.rule_text,
        "rule_data": rule.rule_data,
        "source_id": rule.source_id,
        "is_required": rule.is_required,
    }
    _mark_scheme_for_review(scheme)
    _record_review(
        db,
        admin=admin,
        scheme_id=scheme.id,
        action="eligibility_rule_created",
        reason=payload.reason,
        before=before,
        after=after,
    )
    db.add(
        AuditLog(
            actor_user_id=admin.id,
            action="admin.eligibility_rule_created",
            entity_type="eligibility_rule",
            entity_id=str(rule.id),
            details={"scheme_id": scheme.slug, "source_id": rule.source_id},
        )
    )
    db.commit()
    return {"id": rule.id, **after}


@router.put("/admin/eligibility-rules/{rule_id}")
def update_eligibility_rule(
    rule_id: int,
    payload: AdminEligibilityRuleRequest,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    _check_origin(request)
    rule = db.get(SchemeEligibilityRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Eligibility rule not found.")
    scheme = _scheme_for_edit(db, rule.scheme.slug)
    _require_scheme_source(db, scheme, payload.source_id)
    before = {
        "rule_type": rule.rule_type,
        "rule_text": rule.rule_text,
        "rule_data": rule.rule_data,
        "source_id": rule.source_id,
        "is_required": rule.is_required,
    }
    for field in (
        "rule_type",
        "rule_text",
        "rule_data",
        "source_id",
        "is_required",
        "sort_order",
    ):
        setattr(rule, field, getattr(payload, field))
    after = {
        **before,
        "rule_type": rule.rule_type,
        "rule_text": rule.rule_text,
        "rule_data": rule.rule_data,
        "source_id": rule.source_id,
        "is_required": rule.is_required,
    }
    _mark_scheme_for_review(scheme)
    _record_review(
        db,
        admin=admin,
        scheme_id=scheme.id,
        action="eligibility_rule_updated",
        reason=payload.reason,
        before=before,
        after=after,
    )
    db.add(
        AuditLog(
            actor_user_id=admin.id,
            action="admin.eligibility_rule_updated",
            entity_type="eligibility_rule",
            entity_id=str(rule.id),
            details={"scheme_id": scheme.slug},
        )
    )
    db.commit()
    return {"id": rule.id, **after}


@router.delete("/admin/eligibility-rules/{rule_id}", status_code=204)
def delete_eligibility_rule(
    rule_id: int,
    request: Request,
    reason: str = Query(min_length=10, max_length=2_000),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> None:
    _check_origin(request)
    rule = db.get(SchemeEligibilityRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Eligibility rule not found.")
    scheme = _scheme_for_edit(db, rule.scheme.slug)
    before = {
        "rule_type": rule.rule_type,
        "rule_text": rule.rule_text,
        "rule_data": rule.rule_data,
        "source_id": rule.source_id,
        "is_required": rule.is_required,
    }
    _record_review(
        db,
        admin=admin,
        scheme_id=scheme.id,
        action="eligibility_rule_deleted",
        reason=reason,
        before=before,
    )
    _mark_scheme_for_review(scheme)
    db.add(
        AuditLog(
            actor_user_id=admin.id,
            action="admin.eligibility_rule_deleted",
            entity_type="eligibility_rule",
            entity_id=str(rule.id),
            details={"scheme_id": scheme.slug},
        )
    )
    db.delete(rule)
    db.commit()


@router.post("/admin/schemes/{scheme_id}/documents", status_code=201)
def create_document_requirement(
    scheme_id: str,
    payload: AdminDocumentRequest,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    _check_origin(request)
    scheme = _scheme_for_edit(db, scheme_id)
    document = SchemeDocument(
        scheme_id=scheme.id,
        name=payload.name,
        description=payload.description,
        is_required=payload.is_required,
        sort_order=payload.sort_order,
    )
    db.add(document)
    db.flush()
    after = {
        "name": document.name,
        "description": document.description,
        "is_required": document.is_required,
        "sort_order": document.sort_order,
    }
    _mark_scheme_for_review(scheme)
    _record_review(
        db,
        admin=admin,
        scheme_id=scheme.id,
        action="document_requirement_created",
        reason=payload.reason,
        after=after,
    )
    db.add(
        AuditLog(
            actor_user_id=admin.id,
            action="admin.document_requirement_created",
            entity_type="scheme_document",
            entity_id=str(document.id),
            details={"scheme_id": scheme.slug},
        )
    )
    db.commit()
    return {"id": document.id, **after}


@router.put("/admin/documents/{document_id}")
def update_document_requirement(
    document_id: int,
    payload: AdminDocumentRequest,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    _check_origin(request)
    document = db.get(SchemeDocument, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document requirement not found.")
    scheme = _scheme_for_edit(db, document.scheme.slug)
    before = {
        "name": document.name,
        "description": document.description,
        "is_required": document.is_required,
        "sort_order": document.sort_order,
    }
    for field in ("name", "description", "is_required", "sort_order"):
        setattr(document, field, getattr(payload, field))
    after = {
        "name": document.name,
        "description": document.description,
        "is_required": document.is_required,
        "sort_order": document.sort_order,
    }
    _mark_scheme_for_review(scheme)
    _record_review(
        db,
        admin=admin,
        scheme_id=scheme.id,
        action="document_requirement_updated",
        reason=payload.reason,
        before=before,
        after=after,
    )
    db.add(
        AuditLog(
            actor_user_id=admin.id,
            action="admin.document_requirement_updated",
            entity_type="scheme_document",
            entity_id=str(document.id),
            details={"scheme_id": scheme.slug},
        )
    )
    db.commit()
    return {"id": document.id, **after}


@router.delete("/admin/documents/{document_id}", status_code=204)
def delete_document_requirement(
    document_id: int,
    request: Request,
    reason: str = Query(min_length=10, max_length=2_000),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> None:
    _check_origin(request)
    document = db.get(SchemeDocument, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document requirement not found.")
    scheme = _scheme_for_edit(db, document.scheme.slug)
    before = {
        "name": document.name,
        "description": document.description,
        "is_required": document.is_required,
        "sort_order": document.sort_order,
    }
    _mark_scheme_for_review(scheme)
    _record_review(
        db,
        admin=admin,
        scheme_id=scheme.id,
        action="document_requirement_deleted",
        reason=reason,
        before=before,
    )
    db.add(
        AuditLog(
            actor_user_id=admin.id,
            action="admin.document_requirement_deleted",
            entity_type="scheme_document",
            entity_id=str(document.id),
            details={"scheme_id": scheme.slug},
        )
    )
    db.delete(document)
    db.commit()


@router.post("/admin/sources/{source_id}/review")
def review_source(
    source_id: int,
    payload: AdminSourceVerificationRequest,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    _check_origin(request)
    source = db.scalar(
        select(SchemeSource)
        .where(SchemeSource.id == source_id)
        .options(selectinload(SchemeSource.scheme))
    )
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found.")
    before = {
        "status": source.status,
        "last_verified_at": source.last_verified_at.isoformat() if source.last_verified_at else None,
        "reviewed_by_user_id": source.reviewed_by_user_id,
    }
    source.reviewed_by_user_id = admin.id
    _record_review(
        db,
        admin=admin,
        scheme_id=source.scheme_id,
        action="source_reviewed",
        reason=payload.verification_note,
        before=before,
        after={"status": source.status, "source_id": source.id},
    )
    db.add(
        AuditLog(
            actor_user_id=admin.id,
            action="admin.source_review_recorded",
            entity_type="scheme_source",
            entity_id=str(source.id),
            details={"scheme_id": source.scheme.slug, "status": source.status},
        )
    )
    db.commit()
    return {"source_id": source.id, "reviewed_by_user_id": source.reviewed_by_user_id}


@router.get("/admin/scheme-corrections")
def list_scheme_corrections(
    status: str | None = Query(default=None, pattern="^(open|in_review|resolved|declined)$"),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    statement = select(SchemeReport).order_by(SchemeReport.created_at.desc())
    if status:
        statement = statement.where(SchemeReport.status == status)
    reports = db.scalars(statement.limit(100)).all()
    return [
        {
            "id": item.id,
            "scheme_id": item.scheme_id,
            "report_type": item.report_type,
            "description": item.description,
            "status": item.status,
            "created_at": item.created_at,
            "reviewed_by_user_id": item.reviewed_by_user_id,
            "review_notes": item.review_notes,
            "resolved_at": item.resolved_at,
        }
        for item in reports
    ]


@router.post("/scheme-corrections", status_code=201)
def submit_scheme_correction(
    payload: CorrectionSubmissionRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    _check_origin(request)
    scheme = db.scalar(select(Scheme).where(Scheme.slug == payload.scheme_id))
    if scheme is None:
        raise HTTPException(status_code=404, detail="Scheme not found.")
    report = SchemeReport(
        user_id=user.id,
        scheme_id=scheme.id,
        report_type=payload.report_type,
        description=payload.description,
    )
    db.add(report)
    db.flush()
    db.add(
        AuditLog(
            actor_user_id=user.id,
            action="scheme_correction.submitted",
            entity_type="scheme_report",
            entity_id=str(report.id),
            details={"scheme_id": scheme.slug, "report_type": report.report_type},
        )
    )
    db.commit()
    return {"id": report.id, "status": report.status}


@router.patch("/admin/scheme-corrections/{report_id}")
def review_scheme_correction(
    report_id: int,
    payload: CorrectionReviewRequest,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    _check_origin(request)
    report = db.get(SchemeReport, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Correction report not found.")
    before = {"status": report.status, "review_notes": report.review_notes}
    report.status = payload.status
    report.review_notes = payload.review_notes
    report.reviewed_by_user_id = admin.id
    report.resolved_at = utc_now() if payload.status in {"resolved", "declined"} else None
    if report.scheme_id:
        _record_review(
            db,
            admin=admin,
            scheme_id=report.scheme_id,
            action="user_correction_reviewed",
            reason=payload.review_notes,
            before={"report_status": before["status"]},
            after={"report_status": report.status},
        )
    db.add(
        AuditLog(
            actor_user_id=admin.id,
            action="admin.scheme_correction_reviewed",
            entity_type="scheme_report",
            entity_id=str(report.id),
            details={"before": before, "status": report.status},
        )
    )
    db.commit()
    return {
        "id": report.id,
        "status": report.status,
        "reviewed_by_user_id": report.reviewed_by_user_id,
        "resolved_at": report.resolved_at,
    }


@router.get("/admin/assistant-feedback")
def list_assistant_feedback(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    statement = (
        select(
            ConversationMessage.id,
            ConversationMessage.content,
            ConversationMessage.citations,
            ConversationMessage.feedback,
            ConversationMessage.created_at,
            Conversation.id.label("conversation_id"),
        )
        .join(Conversation, Conversation.id == ConversationMessage.conversation_id)
        .where(
            ConversationMessage.role == "assistant",
            ConversationMessage.feedback.is_not(None),
        )
        .order_by(ConversationMessage.created_at.desc())
    )
    total = db.scalar(
        select(func.count(ConversationMessage.id)).where(
            ConversationMessage.role == "assistant",
            ConversationMessage.feedback.is_not(None),
        )
    ) or 0
    rows = db.execute(statement.offset((page - 1) * page_size).limit(page_size)).all()
    return {
        "items": [
            {
                "message_id": item.id,
                "conversation_id": item.conversation_id,
                "response": item.content,
                "citations": item.citations,
                "feedback": item.feedback,
                "created_at": item.created_at,
            }
            for item in rows
        ],
        "page": page,
        "page_size": page_size,
        "total": total,
    }


@router.get("/admin/audit-logs")
def list_admin_audit_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    statement = select(AuditLog).order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
    total = db.scalar(select(func.count(AuditLog.id))) or 0
    rows = db.scalars(statement.offset((page - 1) * page_size).limit(page_size)).all()
    return {
        "items": [
            {
                "id": item.id,
                "actor_user_id": item.actor_user_id,
                "action": item.action,
                "entity_type": item.entity_type,
                "entity_id": item.entity_id,
                "details": item.details,
                "created_at": item.created_at,
            }
            for item in rows
        ],
        "page": page,
        "page_size": page_size,
        "total": total,
    }


@router.get("/admin/review-history")
def list_review_history(
    scheme_id: int | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    statement = select(SchemeReviewHistory).order_by(
        SchemeReviewHistory.created_at.desc(), SchemeReviewHistory.id.desc()
    )
    if scheme_id:
        statement = statement.where(SchemeReviewHistory.scheme_id == scheme_id)
    total = db.scalar(
        select(func.count(SchemeReviewHistory.id)).where(
            *([SchemeReviewHistory.scheme_id == scheme_id] if scheme_id else [])
        )
    ) or 0
    rows = db.scalars(statement.offset((page - 1) * page_size).limit(page_size)).all()
    return {
        "items": [
            {
                "id": item.id,
                "scheme_id": item.scheme_id,
                "actor_user_id": item.actor_user_id,
                "action": item.action,
                "reason": item.reason,
                "before_snapshot": item.before_snapshot,
                "after_snapshot": item.after_snapshot,
                "created_at": item.created_at,
            }
            for item in rows
        ],
        "page": page,
        "page_size": page_size,
        "total": total,
    }
