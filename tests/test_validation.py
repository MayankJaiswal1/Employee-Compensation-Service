import os
import sys
from decimal import Decimal

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from errors import ApiError  # noqa: E402
from validation import parse_employee  # noqa: E402

VALID = {"FirstName": "Asha", "LastName": "Rao", "DepartmentID": 1, "Salary": 50000}


def test_create_without_bonus_is_valid():
    assert "Bonus" not in parse_employee(VALID)


def test_bonus_null_allowed_and_decimal_parsed():
    out = parse_employee({**VALID, "Bonus": None, "Salary": "50000.50"})
    assert out["Bonus"] is None and out["Salary"] == Decimal("50000.50")


@pytest.mark.parametrize("bad", [
    {**VALID, "Salary": -1},
    {**VALID, "Salary": 10.123},
    {**VALID, "Salary": True},
    {**VALID, "DepartmentID": "1"},
    {**VALID, "FirstName": ""},
    {**VALID, "HireDate": "12/03/2020"},
    {**VALID, "EmployeeID": 5},
    {"FirstName": "Asha"},
])
def test_create_rejects_bad_input(bad):
    with pytest.raises(ApiError) as e:
        parse_employee(bad)
    assert e.value.status == 400


def test_partial_update_and_empty_update():
    assert parse_employee({"Bonus": 1200}, partial=True) == {"Bonus": Decimal("1200")}
    with pytest.raises(ApiError):
        parse_employee({}, partial=True)
