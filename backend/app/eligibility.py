from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .auth import _check_origin, get_current_user
from .database import get_db
from .eligibility_schemas import (
    EligibilityAssessmentResponse,
    EligibilityCheckRequest,
    EligibilityCriterionResponse,
    EligibilitySourceResponse,
)
from .models import Scheme, User
from .schemas import US_STATES_AND_TERRITORIES

router = APIRouter(prefix="/api/v1/schemes", tags=["eligibility"])

RULE_OPERATORS = {
    "age": {"eq", "in", "min", "max"},
    "state": {"eq", "in"},
    "district": {"eq", "in"},
    "area_type": {"eq", "in"},
    "occupation": {"eq", "in"},
    "employment_status": {"eq", "in"},
    "worker_category": {"eq", "in"},
    "education_level": {"eq", "in"},
    "current_student": {"eq", "in"},
    "annual_income_range": {"eq", "in", "income_max", "income_min"},
    "household_size": {"eq", "in", "min", "max"},
    "beneficiary_categories": {"in", "contains"},
}

INCOME_RANGES: dict[str, tuple[int, int]] = {
    "Below ₹1 lakh": (0, 100_000),
    "₹1–3 lakh": (100_000, 300_000),
    "₹3–6 lakh": (300_000, 600_000),
    "₹6–10 lakh": (600_000, 1_000_000),
    "Above ₹10 lakh": (1_000_000, 10**15),
}
PROFILE_FIELDS = tuple(RULE_OPERATORS)
RULE_ALLOWED_VALUES = {
    "state": set(US_STATES_AND_TERRITORIES),
    "area_type": {"Rural", "Urban"},
    "occupation": {
        "Student",
        "Farmer",
        "Salaried employee",
        "Self-employed",
        "Job seeker",
        "Homemaker",
        "Other",
    },
    "employment_status": {
        "Employed",
        "Self-employed",
        "Unemployed",
        "Student",
        "Homemaker",
        "Other",
    },
    "education_level": {
        "No formal schooling",
        "Primary",
        "Secondary",
        "Higher secondary",
        "Diploma or vocational",
        "Undergraduate",
        "Postgraduate",
        "Other",
    },
    "annual_income_range": {
        "Prefer not to say",
        *INCOME_RANGES,
    },
    "beneficiary_categories": {
        "Students",
        "Farmers",
        "Job seekers",
        "Women",
        "Children",
        "Families",
        "Low-income households",
        "Persons with disabilities",
        "Senior citizens",
        "Other",
    },
}

DISCLAIMER = (
    "This is preliminary guidance based only on structured, reviewed criteria "
    "and the profile information provided. It is not an eligibility guarantee; "
    "the responsible government authority makes the final decision."
)


def _evaluate_rule(
    rule_data: object,
    profile: object,
) -> tuple[str, str, str | None, object | None, str | None]:
    if not isinstance(rule_data, dict) or set(rule_data) != {
        "field",
        "operator",
        "value",
    }:
        return (
            "requires_confirmation",
            "This criterion has no supported structured rule and needs human confirmation.",
            None,
            None,
            "The record does not contain a supported structured rule.",
        )

    field = rule_data["field"]
    operator = rule_data["operator"]
    if (
        not isinstance(field, str)
        or field not in RULE_OPERATORS
        or not isinstance(operator, str)
        or operator not in RULE_OPERATORS[field]
    ):
        return (
            "requires_confirmation",
            "This criterion uses an unsupported rule definition and needs human confirmation.",
            None,
            None,
            "The rule field or operator is not supported by the deterministic evaluator.",
        )

    expected = rule_data["value"]
    expected_values = expected if operator == "in" else [expected]
    if not isinstance(expected_values, list) or not expected_values:
        return (
            "requires_confirmation",
            "This criterion has an invalid rule value and needs human confirmation.",
            field,
            None,
            "The recorded rule value has an invalid shape.",
        )
    numeric_rule = operator in {"min", "max", "income_min", "income_max"}
    if numeric_rule and any(
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < 0
        or value
        > (
            10**15
            if field == "annual_income_range"
            else 120
            if field == "age"
            else 30
        )
        or field == "household_size" and value < 1
        for value in expected_values
    ):
        return (
            "requires_confirmation",
            "This criterion has an invalid numeric threshold and needs human confirmation.",
            field,
            None,
            "The threshold must be a non-negative whole number.",
        )

    if not numeric_rule:
        expected_type = (
            str
            if field in {
                "state",
                "district",
                "area_type",
                "occupation",
                "employment_status",
                "worker_category",
                "education_level",
                "annual_income_range",
                "beneficiary_categories",
            }
            else bool
            if field == "current_student"
            else int
        )
        if any(
            not isinstance(value, expected_type)
            or isinstance(value, bool) and expected_type is not bool
            or isinstance(value, str) and not value.strip()
            for value in expected_values
        ):
            return (
                "requires_confirmation",
                "This criterion has an invalid rule value and needs human confirmation.",
                field,
                None,
                "The recorded value does not match the expected data type.",
            )
        allowed_values = RULE_ALLOWED_VALUES.get(field)
        if allowed_values is not None and any(
            value not in allowed_values for value in expected_values
        ):
            return (
                "requires_confirmation",
                "This criterion contains a value outside the supported profile choices.",
                field,
                None,
                "The recorded rule value is not in the supported value set.",
            )
        if field in {"age", "household_size"} and any(
            value < (0 if field == "age" else 1)
            or value > (120 if field == "age" else 30)
            for value in expected_values
        ):
            return (
                "requires_confirmation",
                "This numeric criterion is outside the supported profile range.",
                field,
                None,
                "The recorded rule value is outside the validated profile range.",
            )

    actual = getattr(profile, field, None) if profile is not None else None
    if (
        actual is None
        or actual == []
        or actual == ""
        or isinstance(actual, str) and not actual.strip()
    ):
        return (
            "unknown",
            f"Add {field.replace('_', ' ')} to your profile or provide a temporary answer.",
            field,
            None,
            f"No value was provided for {field.replace('_', ' ')}.",
        )
    if field in {"age", "household_size"}:
        valid_actual = isinstance(actual, int) and not isinstance(actual, bool)
    elif field == "current_student":
        valid_actual = isinstance(actual, bool)
    elif field == "beneficiary_categories":
        valid_actual = isinstance(actual, list) and all(
            isinstance(item, str) for item in actual
        )
    else:
        valid_actual = isinstance(actual, str)
    if not valid_actual:
        return (
            "unknown",
            "The profile value cannot be compared reliably to this criterion.",
            field,
            None,
            "The stored profile value has a conflicting or invalid format.",
        )

    if operator in {"income_min", "income_max"}:
        income_interval = INCOME_RANGES.get(actual)
        if income_interval is None:
            return (
                "unknown",
                "The selected income range does not provide enough detail to assess this threshold.",
                field,
                actual if isinstance(actual, str) else None,
                "The profile contains an income response that cannot be compared to this threshold.",
            )
        lower, upper = income_interval
        threshold = expected
        if operator == "income_max":
            result = (
                "satisfied"
                if upper <= threshold
                else "not_satisfied"
                if lower > threshold
                else "unknown"
            )
        else:
            result = (
                "satisfied"
                if lower >= threshold
                else "not_satisfied"
                if upper < threshold
                else "unknown"
            )
        if result == "unknown":
            return (
                result,
                "The selected family-income range overlaps the recorded threshold.",
                field,
                actual,
                "The profile stores an income band, not an exact amount, and the band crosses the threshold.",
            )
    elif operator in {"eq", "contains"} and isinstance(expected, str):
        if operator == "contains":
            actual_items = actual if isinstance(actual, list) else []
            if not all(isinstance(item, str) for item in actual_items):
                return (
                    "unknown",
                    "The profile value cannot be compared reliably to this category requirement.",
                    field,
                    None,
                    "The stored beneficiary categories have an invalid format.",
                )
            matches = expected.casefold() in {
                item.casefold() for item in actual_items
            }
        else:
            matches = (
                isinstance(actual, str)
                and actual.strip().casefold() == expected.strip().casefold()
            )
        result = "satisfied" if matches else "not_satisfied"
    elif operator == "in":
        if isinstance(actual, list):
            if not all(isinstance(item, str) for item in actual):
                return (
                    "unknown",
                    "The profile value cannot be compared reliably to this criterion.",
                    field,
                    None,
                    "The stored list value has an invalid format.",
                )
            matches = bool(
                {item.casefold() for item in actual}
                & {item.casefold() for item in expected_values}
            )
        elif isinstance(actual, str):
            matches = actual.strip().casefold() in {
                item.strip().casefold() for item in expected_values
            }
        else:
            matches = actual in expected_values
        result = "satisfied" if matches else "not_satisfied"
    elif operator == "min":
        result = "satisfied" if actual >= expected else "not_satisfied"
    elif operator == "max":
        result = "satisfied" if actual <= expected else "not_satisfied"
    else:
        result = "satisfied" if actual == expected else "not_satisfied"

    explanation = (
        "The profile information provided matches this recorded criterion."
        if result == "satisfied"
        else "The profile information provided does not match this recorded criterion."
    ) if operator not in {"min", "max", "income_min", "income_max"} else (
        "The profile value meets this recorded threshold."
        if result == "satisfied"
        else "The profile value does not meet this recorded threshold."
    )
    return result, explanation, field, actual, None


def scheme_is_trusted(scheme: Scheme) -> bool:
    return (
        not scheme.is_demo
        and scheme.verification_status == "verified"
        and not scheme.requires_human_review
        and any(source.status == "verified" for source in scheme.sources)
    )


def evaluate_scheme_criteria(
    scheme: Scheme,
    profile: object,
) -> tuple[list[EligibilityCriterionResponse], str, str]:
    trusted = scheme_is_trusted(scheme)
    criteria: list[EligibilityCriterionResponse] = []
    if not trusted:
        criteria = [
            EligibilityCriterionResponse(
                rule_id=rule.id,
                criterion=rule.rule_text,
                profile_field=None,
                result="requires_confirmation",
                explanation="This scheme record or its sources have not completed verification.",
                required=rule.is_required,
                rule_source_references=[],
                uncertainty_reason="Scheme data has not completed verification.",
            )
            for rule in scheme.eligibility_rules
        ]
        return (
            criteria,
            "unable_to_determine",
            "This scheme’s information is not verified, so an assessment cannot be provided.",
        )

    for rule in scheme.eligibility_rules:
        rule_source = next(
            (
                source
                for source in scheme.sources
                if source.id == rule.source_id
                and source.scheme_id == scheme.id
                and source.status == "verified"
            ),
            None,
        )
        if rule_source is None:
            structured_field = (
                rule.rule_data.get("field")
                if isinstance(rule.rule_data, dict)
                else None
            )
            criteria.append(
                EligibilityCriterionResponse(
                    rule_id=rule.id,
                    criterion=rule.rule_text,
                    profile_field=(
                        structured_field
                        if isinstance(structured_field, str)
                        and structured_field in RULE_OPERATORS
                        else None
                    ),
                    result="requires_confirmation",
                    explanation=(
                        "This criterion has no verified source linked directly "
                        "to its structured rule."
                    ),
                    required=rule.is_required,
                    uncertainty_reason=(
                        "A verified source reference must be attached to this "
                        "specific rule before it can be evaluated."
                    ),
                )
            )
            continue
        (
            result,
            explanation,
            profile_field,
            evaluated_value,
            uncertainty_reason,
        ) = _evaluate_rule(rule.rule_data, profile)
        criteria.append(
            EligibilityCriterionResponse(
                rule_id=rule.id,
                criterion=rule.rule_text,
                profile_field=profile_field,
                result=result,
                explanation=explanation,
                required=rule.is_required,
                evaluated_value=evaluated_value,
                rule_source_references=[
                    EligibilitySourceResponse(
                        title=rule_source.title,
                        url=rule_source.url,
                        last_verified_at=rule_source.last_verified_at,
                    )
                ],
                uncertainty_reason=uncertainty_reason,
            )
        )

    required_results = [item.result for item in criteria if item.required]
    if not required_results:
        return (
            criteria,
            "unable_to_determine",
            "No reviewed, supported eligibility criteria are available for this record.",
        )
    if "not_satisfied" in required_results:
        return (
            criteria,
            "known_criteria_not_satisfied",
            "At least one recorded required criterion does not match the profile information provided.",
        )
    if any(
        result in {"unknown", "requires_confirmation"}
        for result in required_results
    ):
        return (
            criteria,
            "more_information_required",
            "More information or confirmation is needed to assess all required criteria.",
        )
    return (
        criteria,
        "potentially_eligible",
        "The profile information matches the recorded required criteria; verify the details with the official source.",
    )


@router.post(
    "/{scheme_id}/eligibility-check",
    response_model=EligibilityAssessmentResponse,
)
@router.post(
    "/{scheme_id}/eligibility",
    response_model=EligibilityAssessmentResponse,
)
def assess_eligibility(
    scheme_id: str,
    request: Request,
    payload: EligibilityCheckRequest | None = Body(default=None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EligibilityAssessmentResponse:
    _check_origin(request)
    statement = (
        select(Scheme)
        .where(Scheme.slug == scheme_id)
        .options(
            selectinload(Scheme.eligibility_rules),
            selectinload(Scheme.sources),
        )
    )
    if scheme_id.isdecimal():
        statement = (
            select(Scheme)
            .where((Scheme.slug == scheme_id) | (Scheme.id == int(scheme_id)))
            .options(
                selectinload(Scheme.eligibility_rules),
                selectinload(Scheme.sources),
            )
        )
    scheme = db.scalar(statement)
    if scheme is None:
        raise HTTPException(status_code=404, detail="Scheme not found.")

    assessment_profile: object = user.profile
    hypothetical_answers = payload.answers if payload else None
    if hypothetical_answers is not None:
        profile_values = {
            field: getattr(user.profile, field, None) if user.profile else None
            for field in PROFILE_FIELDS
        }
        profile_values.update(
            hypothetical_answers.model_dump(exclude_unset=True)
        )
        assessment_profile = SimpleNamespace(**profile_values)

    criteria, outcome, summary = evaluate_scheme_criteria(
        scheme, assessment_profile
    )

    sources = [
        EligibilitySourceResponse(
            title=source.title,
            url=source.url,
            last_verified_at=source.last_verified_at,
        )
        for source in scheme.sources
        if scheme_is_trusted(scheme) and source.status == "verified"
    ]
    missing_information = list(
        dict.fromkeys(
            item.profile_field.replace("_", " ").capitalize()
            for item in criteria
            if item.result == "unknown" and item.profile_field
        )
    )
    return EligibilityAssessmentResponse(
        scheme_id=scheme.slug,
        scheme_name=scheme.name,
        outcome=outcome,
        summary=summary,
        criteria=criteria,
        sources=sources,
        assessed_at=datetime.now(timezone.utc),
        disclaimer=DISCLAIMER,
        assessment_mode=(
            "hypothetical_answers"
            if hypothetical_answers is not None
            else "saved_profile"
        ),
        missing_information=missing_information,
    )
