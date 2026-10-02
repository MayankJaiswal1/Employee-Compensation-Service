import azure.functions as func

from employees import bp as employees_bp
from reports import bp as reports_bp
from departments import bp as departments_bp
from dashboard import bp as dashboard_bp

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)
app.register_functions(employees_bp)
app.register_functions(reports_bp)
app.register_functions(departments_bp)
app.register_functions(dashboard_bp)
