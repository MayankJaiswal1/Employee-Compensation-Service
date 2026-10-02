# 💼 Employee Compensation Service

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![Azure Functions](https://img.shields.io/badge/Azure%20Functions-v4-0062AD?logo=azurefunctions&logoColor=white)
![SQL Server](https://img.shields.io/badge/SQL%20Server-T--SQL-CC2927?logo=microsoftsqlserver&logoColor=white)
![Azure SQL](https://img.shields.io/badge/Azure%20SQL-compatible-0078D4?logo=microsoftazure&logoColor=white)
![pyodbc](https://img.shields.io/badge/pyodbc-5.x-4B8BBE?logo=python&logoColor=white)
![pytest](https://img.shields.io/badge/pytest-tested-0A9EDC?logo=pytest&logoColor=white)

A small HTTP backend for managing **employee** and **department** records and answering **bonus / compensation** questions.
Built as **Azure Functions** (Python, v2 programming model) over a **SQL Server / Azure SQL** database.
🔒 All reads and writes go through the Functions layer; clients never touch the database.

## 🧰 Stack
| Layer | Choice |
|---|---|
| 🐍 Language | Python 3.11 |
| ⚡ Compute | Azure Functions v4, HTTP triggers |
| 🗄️ Database | SQL Server / Azure SQL via `pyodbc` + ODBC Driver 18 |
| 🧪 Tests | `pytest` (validation unit tests) |

## 📁 Structure
```
function_app.py        # registers the two blueprints
employees.py           # Part A: CRUD endpoints
reports.py             # Part B: compensation reports
validation.py          # request validation (pure Python, unit-tested)
db.py                  # connection + query helpers (parameterized SQL only)
common.py / errors.py  # JSON responses and error → HTTP status mapping
sql/01_schema.sql      # CREATE TABLE scripts (idempotent)
sql/02_seed.sql        # sample data (idempotent)
tests/                 # pytest
```

## 🚀 Run locally

**Prerequisites:** Python 3.11, [Azure Functions Core Tools v4](https://learn.microsoft.com/azure/azure-functions/functions-run-local), [ODBC Driver 18 for SQL Server](https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server), and a SQL Server instance.

1. **Start a database** (or use any SQL Server / Azure SQL):
   ```bash
   docker run -e ACCEPT_EULA=Y -e MSSQL_SA_PASSWORD='<StrongPassword!1>' -p 1433:1433 -d mcr.microsoft.com/mssql/server:2022-latest
   ```
2. **Create the database and tables** (run in SSMS, Azure Data Studio, or `sqlcmd`):
   ```sql
   CREATE DATABASE HrCompensation;
   ```
   then run `sql/01_schema.sql` followed by `sql/02_seed.sql` against `HrCompensation`.
3. **Install dependencies:**
   ```bash
   python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
4. **Configure settings:** copy `local.settings.sample.json` to `local.settings.json` and set `SQL_CONNECTION_STRING`. This file is git-ignored.
5. **Run:**
   ```bash
   func start
   ```
   The API is at `http://localhost:7071/api/...`. No function key is needed locally.
6. **Test:** `pip install pytest && pytest`

## 🌐 Endpoints

### Part A: Employees
| Method | Route | Purpose |
|---|---|---|
| POST | `/api/employees` | Create (Bonus optional) → `201` + `Location` header |
| GET | `/api/employees/{id}` | Get one → `200` / `404` |
| GET | `/api/employees?departmentId=1` | List, optional department filter |
| PUT / PATCH | `/api/employees/{id}` | Partial update; `"Bonus": null` clears a bonus |
| DELETE | `/api/employees/{id}` | Delete → `204` / `404` |

### Part B: Reports
| Route | Answers |
|---|---|
| `GET /api/reports/total-bonus` | Company-wide bonus total (NULL → 0) |
| `GET /api/reports/no-bonus` | Employees who never received a bonus |
| `GET /api/reports/bonus-percentage` | Bonus as % of salary, 2 dp (employees with a bonus only) |
| `GET /api/reports/departments-bonus-exceeds-avg-salary` | Departments where total bonus > average salary |
| `GET /api/reports/bonus-ranking` | Ranked by bonus; no-bonus employees ranked last, not excluded |
| `GET /api/reports/top-earner` | Highest-salary employee, plus whether they also have the highest total compensation |
| `GET /api/reports/effective-bonus` | *(Optional)* bonus with a 5% default applied at read time |

### Examples
```bash
curl -X POST localhost:7071/api/employees -H "Content-Type: application/json" \
  -d '{"FirstName":"Asha","LastName":"Rao","DepartmentID":1,"Salary":90000,"HireDate":"2024-01-15"}'

curl -X PATCH localhost:7071/api/employees/1 -H "Content-Type: application/json" -d '{"Bonus": 7500}'
curl -X PATCH localhost:7071/api/employees/1 -H "Content-Type: application/json" -d '{"Bonus": null}'
curl localhost:7071/api/reports/top-earner
```
With the seed data, `top-earner` returns Aarav Sharma (salary 125,000) with `HasHighestTotalCompensation: false`, because Neha Joshi's total of 143,000 is higher.

## 🛡️ Production readiness
- **No secrets in source.** The connection string is read from the `SQL_CONNECTION_STRING` app setting. Locally that is `local.settings.json` (git-ignored). In Azure, set it as an app setting backed by a **Key Vault reference** (`@Microsoft.KeyVault(SecretUri=...)`). For stronger security, use a managed identity with Entra ID authentication to Azure SQL and drop the password entirely.
- **Parameterized SQL everywhere** (no string-built values), and update column names come from a whitelist. This prevents SQL injection.
- **Validation before the DB:** types, lengths, non-negative amounts, max 2 decimal places, ISO dates, and unknown or read-only fields rejected.
- **Status codes:** `400` validation or bad JSON · `404` not found · `409` constraint violation (e.g. unknown DepartmentID) · `503` database unavailable · `500` unexpected. Internal details are logged, never returned to the client.
- **Auth:** endpoints use `AuthLevel.FUNCTION` (function key required once deployed).
- **DB-level integrity:** foreign key, `CHECK (Salary >= 0)`, `CHECK (Bonus IS NULL OR Bonus >= 0)`, and an index on `Employee.DepartmentID`.

## 🧠 Design decisions and assumptions
- **NULL bonus = no bonus.** A bonus of `0` is a real value and does *not* count as "never received a bonus".
- **Ties:** `top-earner` returns a list so the answer stays correct if two people share the top salary or total compensation. Bonus ranking uses `RANK()`, so equal bonuses share a rank.
- **Bonus %** excludes employees with no bonus (the brief asks for employees "who have a bonus"). A salary of 0 yields `null` instead of a divide-by-zero.
- **Department comparison** uses `SUM(COALESCE(Bonus,0))` against `AVG(Salary)` per department.
- **DepartmentID is required** on create (the schema doesn't forbid NULL, but an employee belongs to a department). Department CRUD wasn't requested, so departments are seeded via SQL only.
- **JSON uses column names** (`FirstName`, `Salary`, ...) so the API mirrors the data model one-to-one.
- **List endpoint isn't paginated.** For large tables, I'd add `OFFSET/FETCH` with `page` / `pageSize`.

### 🎁 Default 5% bonus: calculated at read time, not written
I chose to **calculate it when reading** (`/api/reports/effective-bonus`, rate configurable via `DEFAULT_BONUS_RATE`) rather than writing it into the table:
1. **It keeps `NULL` meaningful.** Writing 5% into the table would make "no bonus" and "default bonus" indistinguishable, which corrupts reports like *never received a bonus* and *total bonus paid*.
2. **It stays correct.** If salary or the policy rate changes, there's no stale data to backfill.
3. **It's reversible and auditable.** Nothing is lost; the response flags rows with `IsDefaultBonus`.

Writing it would only make sense if the default were an actual payout decision that needs to be recorded as a fact (ideally with an audit trail).
