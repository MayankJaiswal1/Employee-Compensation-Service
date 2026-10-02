"""Department CRUD (extra: the brief only requires Employee CRUD)."""
import azure.functions as func
import pyodbc

import db
from common import handle_errors, json_response, read_json
from errors import ApiError

bp = func.Blueprint()
AUTH = func.AuthLevel.FUNCTION

BASE = ("SELECT d.DepartmentID, d.DepartmentName, d.Location, COUNT(e.EmployeeID) AS EmployeeCount "
        "FROM Department d LEFT JOIN Employee e ON e.DepartmentID = d.DepartmentID ")
GROUP = "GROUP BY d.DepartmentID, d.DepartmentName, d.Location "


def _parse(payload, create):
    if not isinstance(payload, dict):
        raise ApiError(400, "Request body must be a JSON object")
    allowed = {"DepartmentName", "Location"} | ({"DepartmentID"} if create else set())
    errors, clean = [], {}
    if set(payload) - allowed:
        errors.append("Unknown or read-only field(s): " + ", ".join(sorted(set(payload) - allowed)))
    if create and "DepartmentName" not in payload:
        errors.append("Missing required field: DepartmentName")
    if not create and not payload:
        errors.append("Provide at least one field to update")
    for k, v in payload.items():
        if k == "DepartmentName":
            if not isinstance(v, str) or not 1 <= len(v.strip()) <= 100:
                errors.append("DepartmentName must be a non-empty string of at most 100 characters")
            else:
                clean[k] = v.strip()
        elif k == "Location":
            if v is not None and (not isinstance(v, str) or len(v.strip()) > 100):
                errors.append("Location must be a string of at most 100 characters, or null")
            else:
                clean[k] = (v or "").strip() or None
        elif k == "DepartmentID":
            if isinstance(v, bool) or not isinstance(v, int) or v <= 0:
                errors.append("DepartmentID must be a positive integer")
            else:
                clean[k] = v
    if errors:
        raise ApiError(400, "Validation failed", errors)
    return clean


def _get(dept_id):
    return db.fetch_one(BASE + "WHERE d.DepartmentID = ? " + GROUP, [dept_id])


@bp.route(route="departments", methods=["GET"], auth_level=AUTH)
@handle_errors
def list_departments(req: func.HttpRequest) -> func.HttpResponse:
    return json_response(db.fetch_all(BASE + GROUP + "ORDER BY d.DepartmentID"))


@bp.route(route="departments/{id:int}", methods=["GET"], auth_level=AUTH)
@handle_errors
def get_department(req: func.HttpRequest) -> func.HttpResponse:
    dept_id = int(req.route_params["id"])
    row = _get(dept_id)
    if row is None:
        raise ApiError(404, f"Department {dept_id} not found")
    return json_response(row)


@bp.route(route="departments", methods=["POST"], auth_level=AUTH)
@handle_errors
def create_department(req: func.HttpRequest) -> func.HttpResponse:
    """DepartmentID is not an identity column; if omitted, the next number is assigned atomically."""
    data = _parse(read_json(req), create=True)
    name, loc = data["DepartmentName"], data.get("Location")
    if "DepartmentID" in data:
        dept_id = data["DepartmentID"]
        db.execute("INSERT INTO Department (DepartmentID, DepartmentName, Location) VALUES (?, ?, ?)",
                   [dept_id, name, loc])
    else:
        dept_id = db.fetch_one(
            "INSERT INTO Department (DepartmentID, DepartmentName, Location) OUTPUT INSERTED.DepartmentID "
            "SELECT COALESCE(MAX(DepartmentID), 0) + 1, ?, ? FROM Department WITH (UPDLOCK, HOLDLOCK)",
            [name, loc])["DepartmentID"]
    return json_response(_get(dept_id), 201, {"Location": f"/api/departments/{dept_id}"})


@bp.route(route="departments/{id:int}", methods=["PUT", "PATCH"], auth_level=AUTH)
@handle_errors
def update_department(req: func.HttpRequest) -> func.HttpResponse:
    dept_id = int(req.route_params["id"])
    data = _parse(read_json(req), create=False)
    changed = db.fetch_one(
        f"UPDATE Department SET {', '.join(f'{c} = ?' for c in data)} OUTPUT INSERTED.DepartmentID "
        "WHERE DepartmentID = ?", [*data.values(), dept_id])
    if changed is None:
        raise ApiError(404, f"Department {dept_id} not found")
    return json_response(_get(dept_id))


@bp.route(route="departments/{id:int}", methods=["DELETE"], auth_level=AUTH)
@handle_errors
def delete_department(req: func.HttpRequest) -> func.HttpResponse:
    dept_id = int(req.route_params["id"])
    try:
        deleted = db.execute("DELETE FROM Department WHERE DepartmentID = ?", [dept_id])
    except pyodbc.IntegrityError:
        raise ApiError(409, "Department still has employees. Move or delete them first.")
    if deleted == 0:
        raise ApiError(404, f"Department {dept_id} not found")
    return func.HttpResponse(status_code=204)
