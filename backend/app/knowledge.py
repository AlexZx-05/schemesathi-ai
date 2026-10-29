import hashlib
import html
import ipaddress
import json
import os
import re
import socket
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timezone
from html.parser import HTMLParser
from io import BytesIO
from pathlib import PurePosixPath
from typing import Annotated
from urllib.parse import urlparse

from docx import Document
from docx.opc.exceptions import PackageNotFoundError
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)
from pypdf import PdfReader
from pypdf.errors import PdfReadError
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from .auth import _check_origin, get_current_user
from .database import get_db
from .knowledge_schemas import (
    KnowledgeIngestionResponse,
    KnowledgeRetrievalRequest,
    KnowledgeRetrievalResponse,
    RetrievedPassage,
    SourceCreateRequest,
    SourceVerificationRequest,
)
from .models import (
    AuditLog,
    Scheme,
    SchemeKnowledgeChunk,
    SchemeReviewHistory,
    SchemeSource,
    User,
    utc_now,
)

router = APIRouter(prefix="/api/v1", tags=["official knowledge base"])
MAX_DOCUMENT_BYTES = 10 * 1024 * 1024
MAX_TEXT_CHARS = 2_000_000
CHUNK_SIZE = 1200
CHUNK_OVERLAP = 150
EMBEDDING_DIMENSIONS = 1536
EMBEDDING_BATCH_SIZE = 96


def _require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Administrator access required.")
    return user


def _allowlisted_domain(hostname: str) -> bool:
    configured = os.getenv("OFFICIAL_SOURCE_ALLOWLIST", "")
    domains = {
        item.strip().lower().lstrip(".")
        for item in configured.split(",")
        if item.strip()
    }
    return any(
        hostname.lower() == domain or hostname.lower().endswith(f".{domain}")
        for domain in domains
    )


def _validate_source_url(url: str, *, resolve: bool) -> str:
    parsed = urlparse(url)
    hostname = parsed.hostname
    if (
        parsed.scheme != "https"
        or not hostname
        or parsed.username
        or parsed.password
        or parsed.port not in (None, 443)
        or not _allowlisted_domain(hostname)
    ):
        raise HTTPException(
            status_code=422,
            detail="Source URL must use HTTPS and an allowlisted government domain.",
        )
    if resolve:
        try:
            addresses = {
                item[4][0]
                for item in socket.getaddrinfo(
                    hostname, 443, type=socket.SOCK_STREAM
                )
            }
        except OSError as error:
            raise HTTPException(
                status_code=502, detail="The approved source host could not be resolved."
            ) from error
        if not addresses or any(
            not ipaddress.ip_address(address).is_global for address in addresses
        ):
            raise HTTPException(
                status_code=422,
                detail="The source host resolves to a non-public network address.",
            )
    return hostname.lower()


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg"}:
            self.ignored_depth += 1
        elif tag.lower() in {"p", "div", "li", "br", "h1", "h2", "h3", "tr"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg"}:
            self.ignored_depth = max(0, self.ignored_depth - 1)
        elif tag.lower() in {"p", "div", "li", "br", "h1", "h2", "h3", "tr"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.ignored_depth:
            self.parts.append(data)


def clean_text(text: str) -> str:
    text = html.unescape(text).replace("\x00", " ")
    text = "".join(
        character
        for character in text
        if character in "\n\t" or ord(character) >= 32
    )
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(line for line in lines if line))


def extract_document(data: bytes, filename: str, content_type: str | None) -> str:
    if len(data) > MAX_DOCUMENT_BYTES:
        raise ValueError("Document exceeds the 10 MB ingestion limit.")
    suffix = PurePosixPath(filename.replace("\\", "/")).suffix.lower()
    if suffix in {".html", ".htm"} or content_type == "text/html":
        parser = _TextExtractor()
        parser.feed(data.decode("utf-8", errors="replace"))
        text = "".join(parser.parts)
    elif suffix == ".pdf" or content_type == "application/pdf":
        if not data.startswith(b"%PDF-"):
            raise ValueError("The uploaded file is not a valid PDF.")
        try:
            reader = PdfReader(BytesIO(data))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except (PdfReadError, OSError) as error:
            raise ValueError("The PDF document could not be extracted.") from error
    elif suffix == ".docx" or content_type in {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }:
        if not zipfile.is_zipfile(BytesIO(data)):
            raise ValueError("The uploaded file is not a valid DOCX.")
        try:
            document = Document(BytesIO(data))
            text = "\n".join(paragraph.text for paragraph in document.paragraphs)
            text += "\n" + "\n".join(
                " ".join(cell.text for cell in row.cells)
                for table in document.tables
                for row in table.rows
            )
        except (
            KeyError,
            OSError,
            ValueError,
            zipfile.BadZipFile,
            PackageNotFoundError,
        ) as error:
            raise ValueError("The DOCX document could not be extracted.") from error
    else:
        raise ValueError("Only HTML, PDF, and DOCX documents are supported.")

    cleaned = clean_text(text)
    if not cleaned:
        raise ValueError("No readable text was extracted from the document.")
    if len(cleaned) > MAX_TEXT_CHARS:
        raise ValueError("Extracted document text exceeds the indexing limit.")
    return cleaned


def split_text(text: str) -> list[str]:
    paragraphs = [part.strip() for part in text.split("\n") if part.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        units = (
            [paragraph[index : index + CHUNK_SIZE] for index in range(0, len(paragraph), CHUNK_SIZE)]
            if len(paragraph) > CHUNK_SIZE
            else [paragraph]
        )
        for unit in units:
            candidate = f"{current}\n{unit}".strip() if current else unit
            if len(candidate) <= CHUNK_SIZE:
                current = candidate
                continue
            if current:
                chunks.append(current)
            overlap = current[-CHUNK_OVERLAP:] if current else ""
            current = f"{overlap} {unit}".strip()
    if current:
        chunks.append(current)
    return chunks


def _embedding_settings() -> tuple[str, str, str, str]:
    provider = os.getenv("EMBEDDING_PROVIDER", "").strip().lower()
    endpoint = os.getenv("EMBEDDING_API_URL", "").strip()
    api_key = os.getenv("EMBEDDING_API_KEY", "").strip()
    model = os.getenv("EMBEDDING_MODEL", "").strip()
    if provider != "openai-compatible" or not endpoint or not model:
        raise HTTPException(
            status_code=503,
            detail="Configure an embedding provider before indexing or retrieval.",
        )
    return provider, endpoint, api_key, model


def _request_embeddings(
    texts: list[str], *, endpoint: str, api_key: str, model: str
) -> list[list[float]]:
    """Call an OpenAI-compatible embeddings endpoint for one bounded batch."""
    payload = json.dumps({"model": model, "input": texts}).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = urllib.request.Request(
        endpoint, data=payload, headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
    except (
        urllib.error.URLError,
        TimeoutError,
        json.JSONDecodeError,
        UnicodeDecodeError,
    ) as error:
        raise HTTPException(
            status_code=502, detail="The configured embedding provider failed."
        ) from error
    try:
        items = result["data"]
        if not isinstance(items, list):
            raise TypeError("Embedding data must be a list.")
        # OpenAI-compatible APIs expose the original input index.  Respect it
        # rather than trusting transport ordering, because chunk order is part
        # of the persisted source provenance.
        indexed_items = sorted(items, key=lambda item: item["index"])
        if [item["index"] for item in indexed_items] != list(range(len(texts))):
            raise ValueError("Embedding response indexes are incomplete.")
        vectors = [item["embedding"] for item in indexed_items]
    except (KeyError, TypeError, ValueError) as error:
        raise HTTPException(
            status_code=502, detail="The embedding provider returned an invalid response."
        ) from error
    if (
        len(vectors) != len(texts)
        or any(
            not isinstance(vector, list)
            or len(vector) != EMBEDDING_DIMENSIONS
            or any(
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                for value in vector
            )
            for vector in vectors
        )
    ):
        raise HTTPException(
            status_code=502,
            detail="The embedding provider returned vectors with an unexpected shape.",
        )
    return vectors


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed text with the configured server-side provider.

    The storage schema uses 1536-dimensional vectors.  Batching keeps large,
    approved documents within typical provider request limits while preserving
    chunk order, which is needed for source traceability.
    """
    if not texts:
        return []
    _, endpoint, api_key, model = _embedding_settings()
    return [
        vector
        for start in range(0, len(texts), EMBEDDING_BATCH_SIZE)
        for vector in _request_embeddings(
            texts[start : start + EMBEDDING_BATCH_SIZE],
            endpoint=endpoint,
            api_key=api_key,
            model=model,
        )
    ]


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


def fetch_approved_source(url: str) -> tuple[bytes, str, str]:
    _validate_source_url(url, resolve=True)
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "SchemeSathiKnowledgeIndexer/1.0"},
        method="GET",
    )
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(request, timeout=15) as response:
            content_type = response.headers.get_content_type()
            data = response.read(MAX_DOCUMENT_BYTES + 1)
            if len(data) > MAX_DOCUMENT_BYTES:
                raise HTTPException(
                    status_code=413, detail="Source document exceeds 10 MB."
                )
            filename = PurePosixPath(urlparse(url).path).name or "source.html"
    except urllib.error.HTTPError as error:
        if 300 <= error.code < 400:
            raise HTTPException(
                status_code=422,
                detail="Redirecting source URLs are not accepted. Verify the final URL first.",
            ) from error
        raise HTTPException(
            status_code=502,
            detail=f"Approved source returned HTTP {error.code}.",
        ) from error
    except (urllib.error.URLError, TimeoutError) as error:
        raise HTTPException(
            status_code=502, detail="The approved source could not be retrieved."
        ) from error
    if content_type == "application/octet-stream" and filename.lower().endswith(".pdf"):
        content_type = "application/pdf"
    return data, filename, content_type


def _chunk_response(
    chunk: SchemeKnowledgeChunk, scheme: Scheme, relevance_score: float
) -> RetrievedPassage:
    return RetrievedPassage(
        scheme_id=scheme.slug,
        source_id=chunk.source_id,
        source_url=chunk.source_url,
        source_title=chunk.source_title,
        document_title=chunk.document_title,
        chunk_index=chunk.chunk_index,
        passage=chunk.content,
        state=chunk.state,
        category=chunk.category,
        publication_date=chunk.publication_date,
        effective_date=chunk.effective_date,
        last_verified_at=chunk.last_verified_at,
        verification_status=chunk.verification_status,
        content_hash=chunk.content_hash,
        relevance_score=relevance_score,
    )


def _record_ingestion_failure(
    db: Session,
    *,
    admin: User,
    source: SchemeSource | None,
    detail: str,
) -> None:
    """Persist a compact, non-content error report without masking the API error."""
    try:
        db.add(
            AuditLog(
                actor_user_id=admin.id,
                action="knowledge.ingestion_failed",
                entity_type="scheme_source",
                entity_id=str(source.id) if source is not None else None,
                details={
                    "scheme_id": source.scheme_id if source is not None else None,
                    "error": detail[:1000],
                },
            )
        )
        db.commit()
    except SQLAlchemyError:
        # An audit failure must never replace the actionable extraction/indexing
        # error returned to the administrator.
        db.rollback()


@router.post(
    "/admin/schemes/{scheme_id}/sources",
    status_code=201,
)
def create_scheme_source(
    scheme_id: str,
    data: SourceCreateRequest,
    request: Request,
    admin: User = Depends(_require_admin),
    db: Session = Depends(get_db),
) -> dict[str, int | str]:
    _check_origin(request)
    url = str(data.url)
    domain = _validate_source_url(url, resolve=False)
    scheme = db.scalar(select(Scheme).where(Scheme.slug == scheme_id))
    if scheme is None:
        raise HTTPException(status_code=404, detail="Scheme not found.")
    source = SchemeSource(
        scheme_id=scheme.id,
        url=url,
        title=data.title,
        source_type=data.source_type,
        official_domain=domain,
        document_reference=data.document_reference,
        status="unverified",
    )
    db.add(source)
    try:
        db.flush()
        db.add(
            AuditLog(
                actor_user_id=admin.id,
                action="knowledge.source_created",
                entity_type="scheme_source",
                entity_id=str(source.id),
                details={"scheme_id": scheme.slug, "domain": domain},
            )
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A source with this URL is already registered for the scheme.",
        )
    except SQLAlchemyError:
        db.rollback()
        raise
    return {"source_id": source.id, "status": source.status}


@router.post("/admin/sources/{source_id}/verify")
def verify_scheme_source(
    source_id: int,
    data: SourceVerificationRequest,
    request: Request,
    admin: User = Depends(_require_admin),
    db: Session = Depends(get_db),
) -> dict[str, int | str | datetime]:
    _check_origin(request)
    source = db.get(SchemeSource, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Scheme source not found.")
    domain = _validate_source_url(source.url, resolve=False)
    source.official_domain = domain
    source.status = "verified"
    source.last_verified_at = utc_now()
    source.reviewed_by_user_id = admin.id
    # Reverification is an explicit human review of the registered source.  If
    # the content did not change, keep the already-indexed chunks usable and
    # make their immutable retrieval metadata reflect that review.  Changed
    # content still requires re-indexing, which replaces those chunks.
    for chunk in db.scalars(
        select(SchemeKnowledgeChunk).where(SchemeKnowledgeChunk.source_id == source.id)
    ):
        chunk.verification_status = "verified"
        chunk.last_verified_at = source.last_verified_at
    db.add(
        SchemeReviewHistory(
            scheme_id=source.scheme_id,
            actor_user_id=admin.id,
            action="source_verified",
            reason=data.verification_note,
            before_snapshot={"status": "unverified"},
            after_snapshot={
                "source_id": source.id,
                "status": source.status,
                "official_domain": domain,
                "last_verified_at": source.last_verified_at.isoformat(),
            },
        )
    )
    db.add(
        AuditLog(
            actor_user_id=admin.id,
            action="knowledge.source_verified",
            entity_type="scheme_source",
            entity_id=str(source.id),
            details={"domain": domain, "verification_note": data.verification_note},
        )
    )
    db.commit()
    return {
        "source_id": source.id,
        "status": source.status,
        "last_verified_at": source.last_verified_at,
    }


@router.post("/admin/sources/{source_id}/mark-stale")
def mark_scheme_source_stale(
    source_id: int,
    request: Request,
    admin: User = Depends(_require_admin),
    db: Session = Depends(get_db),
) -> dict[str, int | str]:
    _check_origin(request)
    source = db.get(SchemeSource, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Scheme source not found.")
    source.status = "stale"
    source.reviewed_by_user_id = admin.id
    for chunk in db.scalars(
        select(SchemeKnowledgeChunk).where(SchemeKnowledgeChunk.source_id == source.id)
    ):
        chunk.verification_status = "stale"
    db.add(
        SchemeReviewHistory(
            scheme_id=source.scheme_id,
            actor_user_id=admin.id,
            action="source_marked_stale",
            reason="Administrator marked the source stale.",
            before_snapshot={"status": "verified"},
            after_snapshot={"source_id": source.id, "status": "stale"},
        )
    )
    db.add(
        AuditLog(
            actor_user_id=admin.id,
            action="knowledge.source_marked_stale",
            entity_type="scheme_source",
            entity_id=str(source.id),
            details={"scheme_id": source.scheme_id},
        )
    )
    db.commit()
    return {"source_id": source.id, "status": source.status}


@router.post(
    "/admin/knowledge/ingest",
    response_model=KnowledgeIngestionResponse,
)
async def ingest_knowledge_source(
    request: Request,
    source_id: Annotated[int, Form(gt=0)],
    document: UploadFile | None = File(default=None),
    state: Annotated[str | None, Form(max_length=100)] = None,
    category: Annotated[str | None, Form(max_length=120)] = None,
    publication_date: datetime | None = Form(default=None),
    effective_date: datetime | None = Form(default=None),
    admin: User = Depends(_require_admin),
    db: Session = Depends(get_db),
) -> KnowledgeIngestionResponse:
    _check_origin(request)
    source = db.scalar(
        select(SchemeSource)
        .where(SchemeSource.id == source_id)
        .options(selectinload(SchemeSource.scheme).selectinload(Scheme.categories))
    )
    if source is None:
        raise HTTPException(status_code=404, detail="Scheme source not found.")
    if source.status != "verified" or source.scheme.is_demo:
        raise HTTPException(
            status_code=409,
            detail="Only verified sources for publishable schemes can be indexed.",
        )
    if (
        source.scheme.verification_status != "verified"
        or source.scheme.requires_human_review
    ):
        raise HTTPException(
            status_code=409,
            detail="The scheme record must be verified and clear of human review first.",
        )
    try:
        _validate_source_url(source.url, resolve=document is None)

        if document is None:
            raw, filename, content_type = fetch_approved_source(source.url)
        else:
            filename = document.filename or "uploaded-document"
            content_type = document.content_type
            raw = await document.read(MAX_DOCUMENT_BYTES + 1)
            if len(raw) > MAX_DOCUMENT_BYTES:
                raise HTTPException(
                    status_code=413, detail="Document exceeds the 10 MB limit."
                )
    except HTTPException as error:
        _record_ingestion_failure(db, admin=admin, source=source, detail=error.detail)
        raise
    try:
        text = extract_document(raw, filename, content_type)
    except ValueError as error:
        _record_ingestion_failure(db, admin=admin, source=source, detail=str(error))
        raise HTTPException(status_code=422, detail=str(error)) from error
    # Hash normalized extracted content rather than container bytes.  This
    # treats a byte-for-byte-different DOCX/PDF with unchanged readable content
    # as a duplicate, while retaining per-source provenance in the database.
    content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    duplicate = db.scalar(
        select(SchemeKnowledgeChunk.id)
        .where(
            SchemeKnowledgeChunk.source_id == source.id,
            SchemeKnowledgeChunk.content_hash == content_hash,
        )
        .limit(1)
    )
    if duplicate is not None:
        return KnowledgeIngestionResponse(
            scheme_id=source.scheme.slug,
            source_id=source.id,
            document_title=source.title or filename,
            content_hash=content_hash,
            chunk_count=0,
            duplicate=True,
            replaced_chunks=0,
            verification_status=source.status,
            message="This source content is already indexed.",
        )

    chunks = split_text(text)
    try:
        vectors = embed_texts(chunks)
    except HTTPException as error:
        _record_ingestion_failure(db, admin=admin, source=source, detail=error.detail)
        raise
    previous = db.scalars(
        select(SchemeKnowledgeChunk).where(
            SchemeKnowledgeChunk.source_id == source.id
        )
    ).all()
    replaced = len(previous)
    for chunk in previous:
        db.delete(chunk)
    document_title = source.title or filename
    resolved_category = category or (
        source.scheme.categories[0].slug if source.scheme.categories else None
    )
    for index, (chunk_text, vector) in enumerate(zip(chunks, vectors, strict=True)):
        db.add(
            SchemeKnowledgeChunk(
                scheme_id=source.scheme_id,
                source_id=source.id,
                source_url=source.url,
                source_title=source.title,
                document_title=document_title,
                chunk_index=index,
                content=chunk_text,
                state=state,
                category=resolved_category,
                publication_date=publication_date,
                effective_date=effective_date,
                last_verified_at=source.last_verified_at,
                verification_status=source.status,
                content_hash=content_hash,
                embedding=vector,
            )
        )
    source.retrieved_at = utc_now()
    source.document_reference = filename
    db.add(
        AuditLog(
            actor_user_id=admin.id,
            action="knowledge.source_indexed",
            entity_type="scheme_source",
            entity_id=str(source.id),
            details={
                "scheme_id": source.scheme.slug,
                "content_hash": content_hash,
                "chunk_count": len(chunks),
                "replaced_chunks": replaced,
            },
        )
    )
    try:
        db.commit()
    except SQLAlchemyError as error:
        db.rollback()
        _record_ingestion_failure(
            db,
            admin=admin,
            source=source,
            detail="Database indexing failed. " + str(error),
        )
        raise
    return KnowledgeIngestionResponse(
        scheme_id=source.scheme.slug,
        source_id=source.id,
        document_title=document_title,
        content_hash=content_hash,
        chunk_count=len(chunks),
        duplicate=False,
        replaced_chunks=replaced,
        verification_status=source.status,
        message="Document extracted, chunked, embedded, and indexed.",
    )


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = sum(value * value for value in left) ** 0.5
    right_norm = sum(value * value for value in right) ** 0.5
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)


@router.post(
    "/knowledge/retrieve",
    response_model=KnowledgeRetrievalResponse,
)
def retrieve_knowledge(
    data: KnowledgeRetrievalRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KnowledgeRetrievalResponse:
    del user
    query_vector = embed_texts([data.query])[0]
    conditions = [
        SchemeKnowledgeChunk.verification_status == "verified",
        SchemeKnowledgeChunk.last_verified_at.is_not(None),
        SchemeSource.status == "verified",
        SchemeSource.last_verified_at.is_not(None),
        Scheme.is_demo.is_(False),
        Scheme.verification_status == "verified",
        Scheme.requires_human_review.is_(False),
    ]
    if data.scheme_id:
        conditions.append(Scheme.slug == data.scheme_id)
    if data.state:
        conditions.append(
            or_(
                SchemeKnowledgeChunk.state.is_(None),
                func.lower(SchemeKnowledgeChunk.state) == data.state.casefold(),
            )
        )
    if data.category:
        conditions.append(
            func.lower(SchemeKnowledgeChunk.category) == data.category.casefold()
        )

    max_age_days = max(1, int(os.getenv("KNOWLEDGE_MAX_AGE_DAYS", "365")))
    fresh_after = datetime.now(timezone.utc).timestamp() - max_age_days * 86400
    freshness_cutoff = datetime.fromtimestamp(fresh_after, timezone.utc)
    conditions.extend(
        [
            SchemeKnowledgeChunk.last_verified_at >= freshness_cutoff,
            SchemeSource.last_verified_at >= freshness_cutoff,
        ]
    )
    if db.get_bind().dialect.name == "postgresql":
        semantic_distance = SchemeKnowledgeChunk.embedding.cosine_distance(
            query_vector
        )
        rows = db.execute(
            select(
                SchemeKnowledgeChunk,
                Scheme,
                semantic_distance.label("semantic_distance"),
            )
            .join(SchemeSource, SchemeSource.id == SchemeKnowledgeChunk.source_id)
            .join(Scheme, Scheme.id == SchemeKnowledgeChunk.scheme_id)
            .where(*conditions)
            .order_by(semantic_distance)
            .limit(max(data.limit * 10, 40))
        ).all()
        terms = {
            term.casefold()
            for term in re.findall(r"[\w-]+", data.query)
            if len(term) > 2
        }
        scored = [
            (
                0.7 * (1.0 - float(distance))
                + 0.3
                * (
                    sum(term in chunk.content.casefold() for term in terms)
                    / max(len(terms), 1)
                ),
                chunk,
                scheme,
            )
            for chunk, scheme, distance in rows
        ]
        scored.sort(key=lambda item: item[0], reverse=True)
    else:
        rows = db.execute(
            select(SchemeKnowledgeChunk, Scheme)
            .join(SchemeSource, SchemeSource.id == SchemeKnowledgeChunk.source_id)
            .join(Scheme, Scheme.id == SchemeKnowledgeChunk.scheme_id)
            .where(*conditions)
        ).all()
        terms = {
            term.casefold()
            for term in re.findall(r"[\w-]+", data.query)
            if len(term) > 2
        }
        scored = []
        for chunk, scheme in rows:
            keyword_score = sum(
                term in chunk.content.casefold() for term in terms
            ) / max(len(terms), 1)
            semantic_score = _cosine_similarity(chunk.embedding, query_vector)
            scored.append(
                (0.7 * semantic_score + 0.3 * keyword_score, chunk, scheme)
            )
        scored.sort(key=lambda item: item[0], reverse=True)

    passages = [
        _chunk_response(chunk, scheme, round(score, 6))
        for score, chunk, scheme in scored[: data.limit]
    ]
    return KnowledgeRetrievalResponse(
        query=data.query,
        retrieval_method="hybrid_semantic_keyword",
        passages=passages,
    )
