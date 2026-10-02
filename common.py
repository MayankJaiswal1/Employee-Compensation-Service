"""HTTP helpers: JSON responses and a single error-to-status-code mapping."""
import functools
import json
import logging
from datetime import date, datetime
from decimal import Decimal

import azure.functions as func
import pyodbc

from errors import ApiError


def _default(o):
    if isinstance(o, Decimal):
        return float(o)
    if isinstance(o, (date, datetime)):
        return o.isoformat()
    raise TypeError(f"Not serializable: {type(o)}")


def json_response(body, status=200, headers=None):
    return func.HttpResponse(
        json.dumps(body, default=_default, indent=2),
        status_code=status,
        mimetype="application/json",
        headers=headers,
    )


def handle_errors(fn):
    """Map exceptions to HTTP status codes without leaking internals."""

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except ApiError as e:
            body = {"error": e.message}
            if e.details:
                body["details"] = e.details
            return json_response(body, e.status)
        except pyodbc.IntegrityError:
            logging.exception("Integrity violation")
            return json_response(
                {"error": "Request violates a data rule (e.g. DepartmentID does not exist)"}, 409
            )
        except pyodbc.Error:
            logging.exception("Database error")
            return json_response({"error": "Database is unavailable, please retry"}, 503)
        except Exception:
            logging.exception("Unhandled error")
            return json_response({"error": "Internal server error"}, 500)

    return wrapper


def read_json(req: func.HttpRequest):
    try:
        return req.get_json()
    except ValueError:
        raise ApiError(400, "Request body must be valid JSON")
