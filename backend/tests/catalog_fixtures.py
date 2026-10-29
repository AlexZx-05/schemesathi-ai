import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models import Scheme, SchemeCategory, SchemeDocument, SchemeEligibilityRule

TEST_RECORD_NOTICE = (
    "Illustrative example only. This is not an actual government scheme or entitlement."
)

TEST_SCHEMES = (
    {
        "slug": "demo-education",
        "name": "Education Support (Sample Record)",
        "description": (
            "An example listing showing how education-related support information "
            "could be organized for students and families."
        ),
        "category": "Education",
        "beneficiaries": ["Students", "Families"],
        "government_level": "Central",
        "keywords": ["school", "college", "learning", "student", "education"],
    },
    {
        "slug": "demo-agriculture",
        "name": "Farm Support (Sample Record)",
        "description": (
            "An example listing showing how agriculture-related information for "
            "farmers could be presented."
        ),
        "category": "Agriculture",
        "beneficiaries": ["Farmers"],
        "government_level": "State",
        "keywords": ["farming", "crop", "rural", "agriculture", "farmer"],
    },
    {
        "slug": "demo-employment",
        "name": "Skills and Employment (Sample Record)",
        "description": (
            "An example listing showing how employment and skills information for "
            "job seekers could be organized."
        ),
        "category": "Employment",
        "beneficiaries": ["Job seekers", "Students"],
        "government_level": "Local",
        "keywords": ["jobs", "career", "skills", "training", "employment"],
    },
    {
        "slug": "demo-healthcare",
        "name": "Community Health Support (Sample Record)",
        "description": (
            "An example listing showing how healthcare-related information for "
            "families could be structured."
        ),
        "category": "Healthcare",
        "beneficiaries": ["Families", "Low-income households"],
        "government_level": "Central",
        "keywords": ["health", "medical", "care", "wellbeing", "healthcare"],
    },
    {
        "slug": "demo-women-child",
        "name": "Women and Child Wellbeing (Sample Record)",
        "description": (
            "An example listing showing how women- and child-focused information "
            "could be made easier to navigate."
        ),
        "category": "Women and child welfare",
        "beneficiaries": ["Women", "Children", "Families"],
        "government_level": "State",
        "keywords": ["women", "children", "family", "wellbeing", "child welfare"],
    },
    {
        "slug": "demo-housing",
        "name": "Housing Information (Sample Record)",
        "description": (
            "An example listing showing how housing-related information for "
            "households could be summarized."
        ),
        "category": "Housing",
        "beneficiaries": ["Families", "Low-income households"],
        "government_level": "Local",
        "keywords": ["home", "shelter", "housing", "household", "residence"],
    },
    {
        "slug": "demo-financial",
        "name": "Household Financial Guidance (Sample Record)",
        "description": (
            "An example listing showing how financial-assistance information for "
            "households could be presented."
        ),
        "category": "Financial assistance",
        "beneficiaries": ["Low-income households", "Women"],
        "government_level": "Central",
        "keywords": ["financial", "assistance", "household", "income", "support"],
    },
)


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")


def seed_catalog_test_fixtures(db: Session) -> int:
    categories = {
        category.name: category
        for category in db.scalars(select(SchemeCategory)).all()
    }
    for name in (
        "Education",
        "Agriculture",
        "Employment",
        "Healthcare",
        "Women and child welfare",
        "Housing",
        "Financial assistance",
    ):
        if name not in categories:
            category = SchemeCategory(name=name, slug=_slug(name))
            db.add(category)
            categories[name] = category
    db.flush()

    inserted = 0
    for record in TEST_SCHEMES:
        if db.scalar(select(Scheme.id).where(Scheme.slug == record["slug"])) is not None:
            continue
        scheme = Scheme(
            name=record["name"],
            slug=record["slug"],
            description=record["description"],
            benefits="\n".join(
                (
                    "Illustrative benefit summary field; no actual benefit is described.",
                    TEST_RECORD_NOTICE,
                )
            ),
            government_level=record["government_level"],
            target_beneficiaries=record["beneficiaries"],
            keywords=record["keywords"],
            application_instructions="\n".join(
                (
                    "Example application guidance field; no live application steps are provided.",
                    TEST_RECORD_NOTICE,
                )
            ),
            status="unknown",
            verification_status="demo",
            requires_human_review=True,
            is_demo=True,
            categories=[categories[record["category"]]],
            eligibility_rules=[
                SchemeEligibilityRule(
                    rule_type="demo",
                    rule_text="Illustrative eligibility field; no real eligibility rules are provided.",
                    sort_order=1,
                ),
                SchemeEligibilityRule(
                    rule_type="demo",
                    rule_text=TEST_RECORD_NOTICE,
                    sort_order=2,
                ),
            ],
            documents=[
                SchemeDocument(
                    name="Example document checklist field; no official documents are specified.",
                    is_required=False,
                    sort_order=1,
                ),
                SchemeDocument(
                    name=TEST_RECORD_NOTICE,
                    is_required=False,
                    sort_order=2,
                ),
            ],
        )
        db.add(
            scheme
        )
        inserted += 1
    db.commit()
    return inserted
