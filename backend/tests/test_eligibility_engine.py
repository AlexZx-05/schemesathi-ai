from types import SimpleNamespace

import pytest

from backend.app.eligibility import _evaluate_rule


@pytest.mark.parametrize(
    ("field", "operator", "expected", "profile_value", "result"),
    [
        ("age", "min", 18, 23, "satisfied"),
        ("age", "max", 30, 23, "satisfied"),
        ("age", "in", [20, 23], 23, "satisfied"),
        ("state", "eq", "Bihar", "Bihar", "satisfied"),
        ("state", "in", ["Bihar", "Odisha"], "Bihar", "satisfied"),
        ("district", "eq", "Patna", "Patna", "satisfied"),
        ("area_type", "eq", "Rural", "Rural", "satisfied"),
        ("education_level", "eq", "Undergraduate", "Undergraduate", "satisfied"),
        ("occupation", "in", ["Student", "Farmer"], "Student", "satisfied"),
        ("employment_status", "eq", "Student", "Student", "satisfied"),
        ("worker_category", "eq", "Agricultural worker", "Agricultural worker", "satisfied"),
        ("current_student", "eq", True, True, "satisfied"),
        ("current_student", "in", [False, True], True, "satisfied"),
        ("household_size", "min", 3, 4, "satisfied"),
        ("household_size", "max", 5, 4, "satisfied"),
        (
            "beneficiary_categories",
            "contains",
            "Students",
            ["Students", "Families"],
            "satisfied",
        ),
        (
            "beneficiary_categories",
            "in",
            ["Students", "Farmers"],
            ["Students", "Families"],
            "satisfied",
        ),
        (
            "annual_income_range",
            "income_max",
            300_000,
            "₹1–3 lakh",
            "satisfied",
        ),
        (
            "annual_income_range",
            "income_min",
            100_000,
            "₹1–3 lakh",
            "satisfied",
        ),
    ],
)
def test_supported_structured_rule_types(
    field: str,
    operator: str,
    expected: object,
    profile_value: object,
    result: str,
) -> None:
    actual_result, _, returned_field, evaluated_value, uncertainty = _evaluate_rule(
        {"field": field, "operator": operator, "value": expected},
        SimpleNamespace(**{field: profile_value}),
    )

    assert actual_result == result
    assert returned_field == field
    assert evaluated_value == profile_value
    assert uncertainty is None


def test_income_range_overlap_is_unknown_not_positive() -> None:
    result, _, field, value, uncertainty = _evaluate_rule(
        {
            "field": "annual_income_range",
            "operator": "income_max",
            "value": 250_000,
        },
        SimpleNamespace(annual_income_range="₹1–3 lakh"),
    )

    assert result == "unknown"
    assert field == "annual_income_range"
    assert value == "₹1–3 lakh"
    assert uncertainty and "crosses the threshold" in uncertainty


def test_missing_and_conflicting_profile_values_remain_unknown() -> None:
    missing = _evaluate_rule(
        {"field": "age", "operator": "min", "value": 18},
        SimpleNamespace(age=None),
    )
    conflicting = _evaluate_rule(
        {"field": "age", "operator": "min", "value": 18},
        SimpleNamespace(age="eighteen"),
    )

    assert missing[0] == "unknown"
    assert missing[3] is None
    assert missing[4] is not None
    assert conflicting[0] == "unknown"
    assert conflicting[3] is None
    assert conflicting[4] is not None


def test_unsupported_operators_and_malformed_rules_need_confirmation() -> None:
    unsupported = _evaluate_rule(
        {"field": "age", "operator": "execute", "value": 18},
        SimpleNamespace(age=23),
    )
    malformed = _evaluate_rule(
        {"field": "age", "operator": "min", "value": True},
        SimpleNamespace(age=23),
    )
    invalid_collection_operator = _evaluate_rule(
        {
            "field": "beneficiary_categories",
            "operator": "eq",
            "value": "Students",
        },
        SimpleNamespace(beneficiary_categories=["Students"]),
    )

    assert unsupported[0] == "requires_confirmation"
    assert "not supported" in (unsupported[4] or "")
    assert malformed[0] == "requires_confirmation"
    assert invalid_collection_operator[0] == "requires_confirmation"
