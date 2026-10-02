"""Input validation for employee payloads. Returns clean, typed values keyed by column name."""
from datetime import date
from decimal import Decimal, InvalidOperation

from errors import ApiError

ALLOWED_FIELDS = {"FirstName", "LastName", "DepartmentID", "Salary", "Bonus", "HireDate"}
REQUIRED_ON_CREATE = {"FirstName", "LastName", "DepartmentID", "Salary"}
MAX_MONEY = Decimal("10000000000")  # DECIMAL(12,2) holds < 10^10


def _name(field, value, errors):
    if not isinstance(value, str) or not (1 <= len(value.strip()) <= 50):
        errors.append(f"{field} must be a non-empty string of at most 50 characters")
        return None
    return value.strip()


def _int(field, value, errors):
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        errors.append(f"{field} must be a positive integer")
        return None
    return value


def _money(field, value, errors, nullable=False):
    if value is None:
        if not nullable:
            errors.append(f"{field} is required and cannot be null")
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        errors.append(f"{field} must be a number")
        return None
    try:
        d = Decimal(str(value))
    except InvalidOperation:
        errors.append(f"{field} must be a number")
        return None
    if not d.is_finite() or d < 0 or d >= MAX_MONEY:
        errors.append(f"{field} must be between 0 and 9999999999.99")
        return None
    if d.as_tuple().exponent < -2:
        errors.append(f"{field} must have at most 2 decimal places")
        return None
    return d


def _date(field, value, errors):
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        errors.append(f"{field} must be an ISO date (YYYY-MM-DD)")
        return None


def parse_employee(payload, partial=False) -> dict:
    """Validate a create (partial=False) or update (partial=True) body."""
    if not isinstance(payload, dict):
        raise ApiError(400, "Request body must be a JSON object")

    errors = []
    unknown = set(payload) - ALLOWED_FIELDS
    if unknown:
        errors.append(f"Unknown or read-only field(s): {', '.join(sorted(unknown))}")
    if not partial:
        missing = REQUIRED_ON_CREATE - set(payload)
        if missing:
            errors.append(f"Missing required field(s): {', '.join(sorted(missing))}")

    clean = {}
    for field, value in payload.items():
        if field not in ALLOWED_FIELDS:
            continue
        if field in ("FirstName", "LastName"):
            clean[field] = _name(field, value, errors)
        elif field == "DepartmentID":
            clean[field] = _int(field, value, errors)
        elif field == "Salary":
            clean[field] = _money(field, value, errors)
        elif field == "Bonus":
            clean[field] = _money(field, value, errors, nullable=True)  # null clears the bonus
        elif field == "HireDate":
            clean[field] = _date(field, value, errors)

    if partial and not payload:
        errors.append("Provide at least one field to update")
    if errors:
        raise ApiError(400, "Validation failed", errors)
    return clean
