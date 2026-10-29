"""Seed source-linked central scheme candidates that still require review."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import SessionLocal
from .models import Scheme, SchemeCategory, SchemeSource

CANDIDATE_NOTICE = (
    "Candidate record awaiting administrator review of the linked government "
    "source. Eligibility, benefits, documents, application steps, and current "
    "availability have not been independently reviewed."
)

CENTRAL_SCHEME_CANDIDATES = (
    {
        "slug": "pm-kisan",
        "name": "PM-KISAN (Pradhan Mantri Kisan Samman Nidhi)",
        "category": "Agriculture",
        "keywords": ["agriculture", "farmer", "PM-KISAN"],
        "url": "https://pmkisan.gov.in/",
        "source_title": "PM-KISAN official portal",
    },
    {
        "slug": "pm-usp-csss",
        "name": (
            "PM-USP Central Sector Scheme of Scholarship for College and "
            "University Students"
        ),
        "category": "Education",
        "keywords": ["education", "scholarship", "college", "university"],
        "url": "https://scholarships.gov.in/",
        "source_title": "National Scholarship Portal",
    },
    {
        "slug": "ab-pm-jay",
        "name": "Ayushman Bharat - Pradhan Mantri Jan Arogya Yojana (AB PM-JAY)",
        "category": "Healthcare",
        "keywords": ["healthcare", "health", "PM-JAY", "Ayushman Bharat"],
        "url": "https://nha.gov.in/PM-JAY.php",
        "source_title": "National Health Authority - PM-JAY",
    },
    {
        "slug": "naps",
        "name": "National Apprenticeship Promotion Scheme (NAPS)",
        "category": "Employment",
        "keywords": ["employment", "apprenticeship", "skills", "NAPS"],
        "url": "https://www.apprenticeshipindia.gov.in/",
        "source_title": "Apprenticeship Training Portal",
    },
    {
        "slug": "pmjdy",
        "name": "Pradhan Mantri Jan Dhan Yojana (PMJDY)",
        "category": "Financial assistance",
        "keywords": ["financial assistance", "banking", "PMJDY"],
        "url": "https://pmjdy.gov.in/",
        "source_title": "PMJDY official portal",
    },
    {
        "slug": "pmay-urban",
        "name": "Pradhan Mantri Awas Yojana - Urban (PMAY-U)",
        "category": "Housing",
        "keywords": ["housing", "urban", "PMAY-U"],
        "url": "https://pmay-urban.gov.in/",
        "source_title": "PMAY-Urban official portal",
    },
    {
        "slug": "pmmvy",
        "name": "Pradhan Mantri Matru Vandana Yojana (PMMVY)",
        "category": "Women and child welfare",
        "keywords": ["women", "maternity", "child welfare", "PMMVY"],
        "url": "https://pmmvy.wcd.gov.in/",
        "source_title": "PMMVY official portal",
    },
)


def _category_slug(value: str) -> str:
    return "-".join(value.casefold().split())


def seed_central_scheme_candidates(db: Session) -> int:
    categories = {
        category.name: category
        for category in db.scalars(select(SchemeCategory)).all()
    }
    for candidate in CENTRAL_SCHEME_CANDIDATES:
        category_name = candidate["category"]
        if category_name not in categories:
            category = SchemeCategory(
                name=category_name,
                slug=_category_slug(category_name),
            )
            db.add(category)
            categories[category_name] = category
    db.flush()

    inserted = 0
    for candidate in CENTRAL_SCHEME_CANDIDATES:
        scheme = db.scalar(
            select(Scheme).where(Scheme.slug == candidate["slug"])
        )
        if scheme is None:
            scheme = Scheme(
                name=candidate["name"],
                slug=candidate["slug"],
                description=CANDIDATE_NOTICE,
                government_level="Central",
                target_beneficiaries=[],
                keywords=candidate["keywords"],
                status="unknown",
                verification_status="unverified",
                requires_human_review=True,
                is_demo=False,
                categories=[categories[candidate["category"]]],
            )
            db.add(scheme)
            db.flush()
            inserted += 1

        source_exists = db.scalar(
            select(SchemeSource.id).where(
                SchemeSource.scheme_id == scheme.id,
                SchemeSource.url == candidate["url"],
            )
        )
        if source_exists is None:
            db.add(
                SchemeSource(
                    scheme_id=scheme.id,
                    url=candidate["url"],
                    title=candidate["source_title"],
                    source_type="official_portal",
                    official_domain=candidate["url"].split("/")[2],
                    status="unverified",
                )
            )

    db.commit()
    return inserted


def main() -> None:
    with SessionLocal() as db:
        inserted = seed_central_scheme_candidates(db)
    print(
        f"Inserted {inserted} central scheme candidates. "
        "All records and source links still require administrator review."
    )


if __name__ == "__main__":
    main()
