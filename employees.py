"""Part A: Employee CRUD."""
import azure.functions as func

import db
from common import handle_errors, json_response, read_json
from errors import ApiError
from validation import parse_employee

bp = func.Blueprint()
AUTH = func.AuthLevel.FUNCTION

COLS = "EmployeeID, FirstName, LastName, DepartmentID, Salary, Bonus, HireDate"
OUT_COLS = ", ".join(f"INSERTED.{c.strip()}" for c in COLS.split(","))


@bp.route(route="employees", methods=["POST"], auth_level=AUTH)
@handle_errors
def create_employee(req: func.HttpRequest) -> func.HttpResponse:
    data = parse_employee(read_json(req))
    data.setdefault("Bonus", None)      # optional: NULL = no bonus
    data.setdefault("HireDate", None)
    cols = list(data)
    row = db.fetch_one(
        f"INSERT INTO Employee ({', '.join(cols)}) OUTPUT {OUT_COLS} "
        f"VALUES ({', '.join('?' for _ in cols)})",
        [data[c] for c in cols],
    )
    return json_response(row, 201, {"Location": f"/api/employees/{row['EmployeeID']}"})


@bp.route(route="employees/{id:int}", methods=["GET"], auth_level=AUTH)
@handle_errors
def get_employee(req: func.HttpRequest) -> func.HttpResponse:
    emp_id = int(req.route_params["id"])
    row = db.fetch_one(f"SELECT {COLS} FROM Employee WHERE EmployeeID = ?", [emp_id])
    if row is None:
        raise ApiError(404, f"Employee {emp_id} not found")
    return json_response(row)


@bp.route(route="employees", methods=["GET"], auth_level=AUTH)
@handle_errors
def list_employees(req: func.HttpRequest) -> func.HttpResponse:
    dept = req.params.get("departmentId")
    if dept is None:
        rows = db.fetch_all(f"SELECT {COLS} FROM Employee ORDER BY EmployeeID")
    else:
        if not dept.isdigit():
            raise ApiError(400, "departmentId must be a positive integer")
        rows = db.fetch_all(
            f"SELECT {COLS} FROM Employee WHERE DepartmentID = ? ORDER BY EmployeeID", [int(dept)]
        )
    return json_response(rows)


@bp.route(route="employees/{id:int}", methods=["PUT", "PATCH"], auth_level=AUTH)
@handle_errors
def update_employee(req: func.HttpRequest) -> func.HttpResponse:
    """Partial update: only supplied fields change. Send "Bonus": null to clear a bonus."""
    emp_id = int(req.route_params["id"])
    data = parse_employee(read_json(req), partial=True)
    set_clause = ", ".join(f"{c} = ?" for c in data)  # column names come from a whitelist
    row = db.fetch_one(
        f"UPDATE Employee SET {set_clause} OUTPUT {OUT_COLS} WHERE EmployeeID = ?",
        [*data.values(), emp_id],
    )
    if row is None:
        raise ApiError(404, f"Employee {emp_id} not found")
    return json_response(row)


@bp.route(route="employees/{id:int}", methods=["DELETE"], auth_level=AUTH)
@handle_errors
def delete_employee(req: func.HttpRequest) -> func.HttpResponse:
    emp_id = int(req.route_params["id"])
    if db.execute("DELETE FROM Employee WHERE EmployeeID = ?", [emp_id]) == 0:
        raise ApiError(404, f"Employee {emp_id} not found")
    return func.HttpResponse(status_code=204)
