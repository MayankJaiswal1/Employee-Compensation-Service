"""Part B: compensation reporting. NULL bonus is handled explicitly in every query."""
import os
from decimal import Decimal, InvalidOperation

import azure.functions as func

import db
from common import handle_errors, json_response

bp = func.Blueprint()
AUTH = func.AuthLevel.FUNCTION


@bp.route(route="reports/total-bonus", methods=["GET"], auth_level=AUTH)
@handle_errors
def total_bonus(req: func.HttpRequest) -> func.HttpResponse:
    row = db.fetch_one("SELECT COALESCE(SUM(Bonus), 0) AS TotalBonus FROM Employee")
    return json_response(row)


@bp.route(route="reports/no-bonus", methods=["GET"], auth_level=AUTH)
@handle_errors
def no_bonus(req: func.HttpRequest) -> func.HttpResponse:
    rows = db.fetch_all(
        "SELECT EmployeeID, FirstName, LastName, DepartmentID, Salary, HireDate "
        "FROM Employee WHERE Bonus IS NULL ORDER BY EmployeeID"
    )
    return json_response(rows)


@bp.route(route="reports/bonus-percentage", methods=["GET"], auth_level=AUTH)
@handle_errors
def bonus_percentage(req: func.HttpRequest) -> func.HttpResponse:
    rows = db.fetch_all(
        "SELECT EmployeeID, FirstName, LastName, Salary, Bonus, "
        "       CAST(ROUND(Bonus * 100.0 / NULLIF(Salary, 0), 2) AS DECIMAL(10,2)) AS BonusPercentOfSalary "
        "FROM Employee WHERE Bonus IS NOT NULL ORDER BY EmployeeID"
    )
    return json_response(rows)


@bp.route(route="reports/departments-bonus-exceeds-avg-salary", methods=["GET"], auth_level=AUTH)
@handle_errors
def departments_bonus_exceeds_avg_salary(req: func.HttpRequest) -> func.HttpResponse:
    rows = db.fetch_all(
        "SELECT d.DepartmentID, d.DepartmentName, "
        "       SUM(COALESCE(e.Bonus, 0)) AS TotalBonus, "
        "       CAST(AVG(e.Salary) AS DECIMAL(12,2)) AS AverageSalary "
        "FROM Department d JOIN Employee e ON e.DepartmentID = d.DepartmentID "
        "GROUP BY d.DepartmentID, d.DepartmentName "
        "HAVING SUM(COALESCE(e.Bonus, 0)) > AVG(e.Salary) "
        "ORDER BY d.DepartmentID"
    )
    return json_response(rows)


@bp.route(route="reports/bonus-ranking", methods=["GET"], auth_level=AUTH)
@handle_errors
def bonus_ranking(req: func.HttpRequest) -> func.HttpResponse:
    """Highest bonus first; employees with no bonus are ranked last (not excluded)."""
    rows = db.fetch_all(
        "SELECT RANK() OVER (ORDER BY CASE WHEN Bonus IS NULL THEN 1 ELSE 0 END, Bonus DESC) AS BonusRank, "
        "       EmployeeID, FirstName, LastName, Salary, Bonus "
        "FROM Employee ORDER BY BonusRank, LastName, FirstName"
    )
    return json_response(rows)


_TOP_EARNER_CTE = (
    "WITH Comp AS ( "
    "  SELECT EmployeeID, FirstName, LastName, DepartmentID, Salary, Bonus, "
    "         Salary + COALESCE(Bonus, 0) AS TotalCompensation FROM Employee), "
    "Mx AS (SELECT MAX(Salary) AS MaxSalary, MAX(TotalCompensation) AS MaxComp FROM Comp) "
)


@bp.route(route="reports/top-earner", methods=["GET"], auth_level=AUTH)
@handle_errors
def top_earner(req: func.HttpRequest) -> func.HttpResponse:
    """Highest base salary, and separately whether that person also has the highest total compensation.
    Ties are returned (a list), so the answer stays correct if two people share the top value."""
    flag = "CASE WHEN c.TotalCompensation = m.MaxComp THEN 1 ELSE 0 END AS HasHighestTotalCompensation"
    by_salary = db.fetch_all(
        _TOP_EARNER_CTE + f"SELECT c.*, {flag} FROM Comp c CROSS JOIN Mx m WHERE c.Salary = m.MaxSalary"
    )
    by_comp = db.fetch_all(
        _TOP_EARNER_CTE + "SELECT c.* FROM Comp c CROSS JOIN Mx m WHERE c.TotalCompensation = m.MaxComp"
    )
    for r in by_salary:
        r["HasHighestTotalCompensation"] = bool(r["HasHighestTotalCompensation"])
    return json_response({"highestSalary": by_salary, "highestTotalCompensation": by_comp})


@bp.route(route="reports/effective-bonus", methods=["GET"], auth_level=AUTH)
@handle_errors
def effective_bonus(req: func.HttpRequest) -> func.HttpResponse:
    """Optional: default bonus (5% of salary) calculated at read time; nothing is written to the table."""
    try:
        rate = Decimal(os.environ.get("DEFAULT_BONUS_RATE", "0.05"))
    except InvalidOperation:
        rate = Decimal("0.05")
    rows = db.fetch_all(
        "SELECT EmployeeID, FirstName, LastName, Salary, Bonus, "
        "       COALESCE(Bonus, ROUND(Salary * ?, 2)) AS EffectiveBonus, "
        "       CASE WHEN Bonus IS NULL THEN 1 ELSE 0 END AS IsDefaultBonus "
        "FROM Employee ORDER BY EmployeeID",
        [rate],
    )
    for r in rows:
        r["IsDefaultBonus"] = bool(r["IsDefaultBonus"])
    return json_response(rows)


@bp.route(route="reports/average-salary", methods=["GET"], auth_level=AUTH)
@handle_errors
def average_salary(req: func.HttpRequest) -> func.HttpResponse:
    rows = db.fetch_all(
        "SELECT d.DepartmentID, d.DepartmentName, COUNT(e.EmployeeID) AS EmployeeCount, "
        "       CAST(AVG(e.Salary) AS DECIMAL(12,2)) AS AverageSalary "
        "FROM Department d LEFT JOIN Employee e ON e.DepartmentID = d.DepartmentID "
        "GROUP BY d.DepartmentID, d.DepartmentName ORDER BY d.DepartmentID"
    )
    return json_response(rows)