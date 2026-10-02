"""Optional viewer: a single HTML page that calls the API and shows the results as tables."""
import azure.functions as func

bp = func.Blueprint()

PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Employee Compensation Dashboard</title>
<style>
  :root { --bg:#f5f7fb; --card:#fff; --ink:#1b2430; --muted:#6b7686; --line:#e3e8ef; --accent:#2563eb; }
  * { box-sizing: border-box; }
  body { margin:0; font-family: system-ui, Segoe UI, Roboto, sans-serif; background:var(--bg); color:var(--ink); }
  header { padding:20px 28px; background:var(--card); border-bottom:1px solid var(--line); }
  header h1 { margin:0; font-size:20px; }
  header p { margin:4px 0 0; color:var(--muted); font-size:13px; }
  main { max-width:1400px; margin:0 auto; padding:20px 28px 48px; }
  .tabs { display:flex; flex-wrap:wrap; gap:8px; margin-bottom:16px; }
  .tabs button { border:1px solid var(--line); background:var(--card); color:var(--ink); padding:8px 12px;
                 border-radius:8px; cursor:pointer; font-size:13px; }
  .tabs button:hover { border-color:var(--accent); }
  .tabs button.active { background:var(--accent); border-color:var(--accent); color:#fff; }
  .panel { background:var(--card); border:1px solid var(--line); border-radius:12px; padding:18px; margin-bottom:16px; }
  .panel h2 { margin:0 0 4px; font-size:16px; }
  .panel .desc { margin:0 0 12px; color:var(--muted); font-size:13px; }
  .table-wrap { overflow-x:auto; }
  table { border-collapse:collapse; width:100%; font-size:14px; }
  th { text-align:left; background:#f0f3f9; font-weight:600; padding:9px 12px; border-bottom:1px solid var(--line); white-space:nowrap; }
  td { padding:9px 12px; border-bottom:1px solid var(--line); white-space:nowrap; }
  td.num, th.num { text-align:right; font-variant-numeric: tabular-nums; }
  tr:last-child td { border-bottom:none; }
  .pill { display:inline-block; padding:2px 8px; border-radius:999px; font-size:12px; background:#eef1f6; color:var(--muted); }
  .yes { background:#dcfce7; color:#166534; } .no { background:#fee2e2; color:#991b1b; }
  .big { font-size:34px; font-weight:700; margin:6px 0; }
  .empty, .error { padding:12px; color:var(--muted); }
  .error { color:#991b1b; background:#fee2e2; border-radius:8px; }
  .form { display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:10px; margin-bottom:12px; }
  .form label { display:flex; flex-direction:column; gap:4px; font-size:12px; color:var(--muted); }
  .form input { padding:8px; border:1px solid var(--line); border-radius:6px; font-size:14px; color:var(--ink); }
  .btn { border:1px solid var(--accent); background:var(--accent); color:#fff; padding:6px 12px; border-radius:6px; cursor:pointer; font-size:13px; margin-right:6px; }
  .btn.alt { background:#fff; color:var(--accent); }
  .btn.danger { background:#fff; border-color:#b91c1c; color:#b91c1c; }
  #msg:empty { display:none; }
  #msg { margin-bottom:12px; padding:10px 12px; border-radius:8px; }
  #msg.ok { background:#dcfce7; color:#166534; } #msg.error { background:#fee2e2; color:#991b1b; }
</style>
</head>
<body>
<header>
  <h1>Employee Compensation Dashboard</h1>
  <p>A friendly view of the API responses. The raw JSON is still available at each /api/... URL.</p>
</header>
<main>
  <div class="tabs" id="tabs"></div>
  <div id="msg"></div>
  <div id="out"></div>
</main>
<script>
const VIEWS = [
  { label: "Employees",            url: "/api/employees",                                        desc: "All employees. Use the form to add one, and Edit / Delete on each row.", crud: true },
  { label: "Departments", url: "/api/departments", desc: "Departments and how many employees each has. Add, edit or delete them here.", crud: "dept" },
  { label: "Total bonus",          url: "/api/reports/total-bonus",                              desc: "Total bonus paid across the company (no bonus counts as 0)." },
  { label: "No bonus",             url: "/api/reports/no-bonus",                                 desc: "Employees who have never received a bonus." },
  { label: "Bonus % of salary",    url: "/api/reports/bonus-percentage",                         desc: "Bonus as a percentage of salary, rounded to 2 decimals." },
    { label: "Average salary", url: "/api/reports/average-salary", desc: "Average salary per department." },
  { label: "Dept bonus > avg salary", url: "/api/reports/departments-bonus-exceeds-avg-salary",  desc: "Departments where the total bonus exceeds the average salary." },
  { label: "Bonus ranking",        url: "/api/reports/bonus-ranking",                            desc: "Ranked by bonus; employees without a bonus are ranked last." },
  { label: "Top earner",           url: "/api/reports/top-earner",                               desc: "Highest base salary, and whether that person also has the highest total compensation." },
  { label: "Effective bonus (5% default)", url: "/api/reports/effective-bonus",                  desc: "Bonus with a 5% default applied at read time. Nothing is written to the table." }
];
const MONEY = new Set(["Salary","Bonus","TotalBonus","AverageSalary","TotalCompensation","EffectiveBonus"]);
const code = new URLSearchParams(location.search).get("code");   // function key, when deployed

function pretty(s) { return s.replace(/([a-z])([A-Z])/g, "$1 $2").replace(/\bID\b/, "ID"); }
function fmtNumber(n) { return Number(n).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }

function cell(td, key, value) {
  if (value === null || value === undefined) {
    const s = document.createElement("span"); s.className = "pill"; s.textContent = key === "Bonus" ? "No bonus" : "-";
    td.appendChild(s);
  } else if (typeof value === "boolean") {
    const s = document.createElement("span"); s.className = "pill " + (value ? "yes" : "no"); s.textContent = value ? "Yes" : "No";
    td.appendChild(s);
  } else if (MONEY.has(key) || key === "BonusPercentOfSalary") {
    td.className = "num";
    td.textContent = key === "BonusPercentOfSalary" ? fmtNumber(value) + " %" : fmtNumber(value);
  } else {
    td.textContent = value;
  }
}

function table(rows, actions) {
  if (!rows.length) { const d = document.createElement("div"); d.className = "empty"; d.textContent = "No rows."; return d; }
  const wrap = document.createElement("div"); wrap.className = "table-wrap";
  const t = document.createElement("table");
  const keys = Object.keys(rows[0]);
  const hr = t.createTHead().insertRow();
  keys.forEach(k => { const th = document.createElement("th"); th.textContent = pretty(k);
    if (MONEY.has(k) || k === "BonusPercentOfSalary") th.className = "num"; hr.appendChild(th); });
  if (actions) { const th = document.createElement("th"); th.textContent = "Actions"; hr.appendChild(th); }
  const body = t.createTBody();
  rows.forEach(r => { const tr = body.insertRow(); keys.forEach(k => cell(tr.insertCell(), k, r[k]));
    if (actions) { const td = tr.insertCell();
      td.appendChild(button("Edit", "btn alt", () => actions.edit(r)));
      td.appendChild(button("Delete", "btn danger", () => actions.del(r))); } });
  wrap.appendChild(t); return wrap;
}

function panel(title, desc) {
  const p = document.createElement("section"); p.className = "panel";
  const h = document.createElement("h2"); h.textContent = title; p.appendChild(h);
  if (desc) { const d = document.createElement("p"); d.className = "desc"; d.textContent = desc; p.appendChild(d); }
  return p;
}

function render(view, data) {
  const out = document.getElementById("out"); out.replaceChildren();
  if (Array.isArray(data)) {
    const dept = view.crud === "dept", F = dept ? deptForm : formPanel;
    let holder = null;
    if (view.crud) { holder = document.createElement("div"); holder.appendChild(F(null, holder)); out.appendChild(holder); }
    const p = panel(view.label, view.desc);
    p.appendChild(table(data, view.crud ? {
      edit: r => { holder.replaceChildren(F(r, holder)); window.scrollTo({ top: 0, behavior: "smooth" }); },
      del: dept ? delDepartment : delEmployee } : null));
    out.appendChild(p);
  } else {
    // object: scalars become big numbers, arrays become tables
    Object.entries(data).forEach(([k, v]) => {
      const p = panel(Array.isArray(v) ? pretty(k) : view.label, Array.isArray(v) ? "" : view.desc);
      if (Array.isArray(v)) p.appendChild(table(v));
      else { const b = document.createElement("div"); b.className = "big"; b.textContent = MONEY.has(k) ? fmtNumber(v) : v; p.appendChild(b); }
      out.appendChild(p);
    });
  }
}

let current = null;

function button(text, cls, onclick) {
  const b = document.createElement("button"); b.className = cls; b.textContent = text; b.onclick = onclick; return b;
}

function notify(msg, ok) {
  const n = document.getElementById("msg"); n.className = ok ? "ok" : "error"; n.textContent = msg;
}

async function api(method, path, body) {
  const url = path + (code ? "?code=" + encodeURIComponent(code) : "");
  const res = await fetch(url, { method, headers: body ? { "Content-Type": "application/json" } : {}, body: body ? JSON.stringify(body) : undefined });
  const data = res.status === 204 ? null : await res.json().catch(() => null);
  if (!res.ok) throw new Error(data && data.error ? data.error + (data.details ? ": " + data.details.join("; ") : "") : res.statusText);
  return data;
}

function formPanel(emp, holder) {
  const p = panel(emp ? "Edit employee #" + emp.EmployeeID : "Add employee", "Bonus is optional: leave it blank for no bonus.");
  const fields = [["FirstName", "text"], ["LastName", "text"], ["DepartmentID", "number"], ["Salary", "number"], ["Bonus", "number"], ["HireDate", "date"]];
  const inputs = {};
  const f = document.createElement("div"); f.className = "form";
  fields.forEach(([k, type]) => {
    const l = document.createElement("label"); l.textContent = pretty(k);
    const i = document.createElement("input"); i.type = type; if (type === "number") i.step = "0.01";
    i.value = emp && emp[k] != null ? emp[k] : "";
    inputs[k] = i; l.appendChild(i); f.appendChild(l);
  });
  p.appendChild(f);
  p.appendChild(button(emp ? "Save changes" : "Add employee", "btn", async () => {
    const body = {};
    fields.forEach(([k, type]) => {
      const v = inputs[k].value.trim();
      if (v === "") { if (emp && (k === "Bonus" || k === "HireDate")) body[k] = null; return; }
      body[k] = k === "DepartmentID" ? parseInt(v, 10) : type === "number" ? Number(v) : v;
    });
    try {
      if (emp) await api("PATCH", "/api/employees/" + emp.EmployeeID, body);
      else await api("POST", "/api/employees", body);
      notify(emp ? "Employee updated." : "Employee created.", true);
      load(current.view, current.btn);
    } catch (e) { notify(e.message, false); }
  }));
  if (emp) p.appendChild(button("Cancel", "btn alt", () => holder.replaceChildren(formPanel(null, holder))));
  return p;
}

function deptForm(rec, holder) {
  const p = panel(rec ? "Edit department #" + rec.DepartmentID : "Add department",
                  rec ? "" : "Leave Department ID blank to assign the next number automatically.");
  const fields = [["DepartmentID", "number"], ["DepartmentName", "text"], ["Location", "text"]];
  const inputs = {};
  const f = document.createElement("div"); f.className = "form";
  fields.forEach(([k, type]) => {
    const l = document.createElement("label"); l.textContent = pretty(k);
    const i = document.createElement("input"); i.type = type;
    i.value = rec && rec[k] != null ? rec[k] : ""; if (rec && k === "DepartmentID") i.disabled = true;
    inputs[k] = i; l.appendChild(i); f.appendChild(l);
  });
  p.appendChild(f);
  p.appendChild(button(rec ? "Save changes" : "Add department", "btn", async () => {
    const body = {};
    fields.forEach(([k, type]) => {
      if (rec && k === "DepartmentID") return;
      const v = inputs[k].value.trim();
      if (v === "") { if (rec && k === "Location") body[k] = null; return; }
      body[k] = type === "number" ? parseInt(v, 10) : v;
    });
    try {
      if (rec) await api("PATCH", "/api/departments/" + rec.DepartmentID, body);
      else await api("POST", "/api/departments", body);
      notify(rec ? "Department updated." : "Department created.", true);
      load(current.view, current.btn);
    } catch (e) { notify(e.message, false); }
  }));
  if (rec) p.appendChild(button("Cancel", "btn alt", () => holder.replaceChildren(deptForm(null, holder))));
  return p;
}

async function delDepartment(r) {
  if (!confirm("Delete department " + r.DepartmentName + "?")) return;
  try { await api("DELETE", "/api/departments/" + r.DepartmentID); notify("Department deleted.", true); load(current.view, current.btn); }
  catch (e) { notify(e.message, false); }
}

async function delEmployee(r) {
  if (!confirm("Delete " + r.FirstName + " " + r.LastName + "?")) return;
  try { await api("DELETE", "/api/employees/" + r.EmployeeID); notify("Employee deleted.", true); load(current.view, current.btn); }
  catch (e) { notify(e.message, false); }
}

async function load(view, btn) {
  current = { view, btn };
  document.querySelectorAll(".tabs button").forEach(b => b.classList.toggle("active", b === btn));
  const out = document.getElementById("out");
  try {
    const url = view.url + (code ? "?code=" + encodeURIComponent(code) : "");
    const res = await fetch(url);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || res.statusText);
    render(view, data);
  } catch (e) {
    out.replaceChildren(); const d = document.createElement("div"); d.className = "error"; d.textContent = "Could not load data: " + e.message; out.appendChild(d);
  }
}

const tabs = document.getElementById("tabs");
VIEWS.forEach((v, i) => {
  const b = document.createElement("button"); b.textContent = v.label; b.onclick = () => { notify("", true); load(v, b); };
  tabs.appendChild(b); if (i === 0) load(v, b);
});
</script>
</body>
</html>
"""


@bp.route(route="dashboard", methods=["GET"], auth_level=func.AuthLevel.FUNCTION)
def dashboard(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse(PAGE, mimetype="text/html")
