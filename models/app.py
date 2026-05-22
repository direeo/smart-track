import os
import sys
from pathlib import Path

# Force unbuffered output
sys.stdout = sys.stderr = open(sys.stdout.fileno(), mode='w', buffering=1)

try:
    from fastapi import FastAPI, Request, Form, HTTPException
    from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
    from fastapi.staticfiles import StaticFiles
    from fastapi.templating import Jinja2Templates
    from starlette.middleware.sessions import SessionMiddleware
    from typing import Optional, List
except ImportError as e:
    print(f"[CRITICAL] Failed to import FastAPI modules: {e}", file=sys.stderr, flush=True)
    sys.exit(1)

print("[*] FastAPI imports successful", flush=True)

# Ensure directories exist
print("[*] Creating directory structure...", flush=True)
try:
    Path("static").mkdir(exist_ok=True, parents=True)
    Path("templates").mkdir(exist_ok=True, parents=True)
    print("[OK] Directories created", flush=True)
except Exception as e:
    print(f"[ERROR] Failed to create directories: {e}", file=sys.stderr, flush=True)
    sys.exit(1)

print("[*] Importing database and ML modules...", flush=True)
try:
    from database import init_db, get_conn, hash_pw, generate_code
    from ml import predict_kpi, predict_behaviour
    print("[OK] Database and ML imports successful", flush=True)
except Exception as e:
    print(f"[CRITICAL] Failed to import database/ml: {e}", file=sys.stderr, flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("[*] Creating FastAPI app...", flush=True)
app = FastAPI()
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", "fallback-secret")
)

# Mount static files with error handling
print("[*] Mounting static files...", flush=True)
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
    print("[OK] Static files mounted", flush=True)
except Exception as e:
    print(f"[WARNING] Failed to mount static files: {e}", file=sys.stderr, flush=True)

# Load templates
print("[*] Loading Jinja2 templates...", flush=True)
try:
    templates = Jinja2Templates(directory="templates")
    print("[OK] Templates loaded", flush=True)
except Exception as e:
    print(f"[CRITICAL] Failed to load templates: {e}", file=sys.stderr, flush=True)
    sys.exit(1)


@app.get("/health")
def health():
    return {"status": "ok"}


# Initialize database on startup
print("[*] Initializing database...", flush=True)
try:
    init_db()
    print("[OK] Database initialized successfully", flush=True)
except Exception as e:
    print(f"[CRITICAL] Database initialization failed: {e}", file=sys.stderr, flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("[OK] Application startup complete", flush=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def current_user(request: Request):
    uid = request.session.get("user_id")
    if not uid:
        return None
    conn = get_conn()
    user = conn.execute(
        "SELECT u.*, d.name as dept_name FROM users u "
        "LEFT JOIN departments d ON u.department_id = d.id WHERE u.id=?", (uid,)
    ).fetchone()
    conn.close()
    return user


def require_role(request: Request, *roles):
    user = current_user(request)
    if not user or user["role"] not in roles:
        raise HTTPException(status_code=403)
    return user


# ── Auth ──────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    user = current_user(request)
    if user:
        return RedirectResponse(f"/{user['role']}/dashboard")
    return templates.TemplateResponse("login.html",
                                      {"request": request, "error": None, "success": None})


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html",
                                      {"request": request, "error": None, "success": None})


@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    conn = get_conn()
    user = conn.execute(
        "SELECT * FROM users WHERE username=? AND password=?",
        (username, hash_pw(password))
    ).fetchone()
    conn.close()
    if not user:
        return templates.TemplateResponse("login.html",
                                          {"request": request,
                                           "error": "Invalid username or password.",
                                           "success": None})
    request.session["user_id"] = user["id"]
    return RedirectResponse(f"/{user['role']}/dashboard", status_code=302)


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/")


@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse("register.html",
                                      {"request": request, "error": None, "success": None})


@app.post("/register")
async def register_company(request: Request,
                            company_name: str = Form(...),
                            full_name: str = Form(...),
                            username: str = Form(...),
                            password: str = Form(...),
                            department_names: str = Form(...)):
    conn = get_conn()
    if conn.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone():
        conn.close()
        return templates.TemplateResponse("register.html",
                                          {"request": request,
                                           "error": "Username already taken.",
                                           "success": None})
    code = generate_code()
    while conn.execute("SELECT id FROM companies WHERE code=?", (code,)).fetchone():
        code = generate_code()
    conn.execute("INSERT INTO companies (name, code) VALUES (?,?)", (company_name, code))
    company_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    dept_list = [d.strip() for d in department_names.split(",") if d.strip()] or ["General"]
    for dept in dept_list:
        conn.execute("INSERT INTO departments (name, company_id) VALUES (?,?)", (dept, company_id))
    conn.execute(
        "INSERT INTO users (username,password,full_name,role,department_id,company_id) VALUES (?,?,?,?,?,?)",
        (username, hash_pw(password), full_name, "admin", None, company_id)
    )
    conn.commit()
    conn.close()
    return templates.TemplateResponse("register.html",
                                      {"request": request, "error": None,
                                       "success": code, "company_name": company_name})


@app.get("/signup", response_class=HTMLResponse)
def signup_page(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request, "error": None})


@app.get("/api/company-departments")
def get_company_departments(code: str):
    conn = get_conn()
    company = conn.execute("SELECT * FROM companies WHERE code=?", (code.upper(),)).fetchone()
    if not company:
        conn.close()
        return JSONResponse({"error": "Invalid company code."}, status_code=404)
    depts = conn.execute("SELECT id, name FROM departments WHERE company_id=?",
                         (company["id"],)).fetchall()
    conn.close()
    return JSONResponse({"company_name": company["name"],
                         "departments": [{"id": d["id"], "name": d["name"]} for d in depts]})


@app.post("/signup")
async def signup_staff(request: Request,
                        full_name: str = Form(...),
                        username: str = Form(...),
                        password: str = Form(...),
                        company_code: str = Form(...),
                        department_id: int = Form(...)):
    conn = get_conn()
    company = conn.execute("SELECT * FROM companies WHERE code=?",
                           (company_code.upper(),)).fetchone()
    if not company:
        conn.close()
        return templates.TemplateResponse("signup.html",
                                          {"request": request, "error": "Invalid company code."})
    dept = conn.execute("SELECT * FROM departments WHERE id=? AND company_id=?",
                        (department_id, company["id"])).fetchone()
    if not dept:
        conn.close()
        return templates.TemplateResponse("signup.html",
                                          {"request": request, "error": "Invalid department."})
    if conn.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone():
        conn.close()
        return templates.TemplateResponse("signup.html",
                                          {"request": request, "error": "Username already taken."})
    conn.execute(
        "INSERT INTO users (username,password,full_name,role,department_id,company_id) VALUES (?,?,?,?,?,?)",
        (username, hash_pw(password), full_name, "employee", department_id, company["id"])
    )
    conn.commit()
    conn.close()
    return templates.TemplateResponse("login.html",
                                      {"request": request, "error": None,
                                       "success": "Account created. You can now sign in."})


# ── Employee ──────────────────────────────────────────────────────────────────

@app.get("/employee/dashboard", response_class=HTMLResponse)
def emp_dashboard(request: Request):
    user = require_role(request, "employee")
    conn = get_conn()
    # Get projects this employee is a member of
    projects = conn.execute(
        "SELECT p.*, "
        "(SELECT COUNT(*) FROM kpis WHERE project_id=p.id AND assigned_to=?) as my_kpi_count "
        "FROM projects p "
        "JOIN project_members pm ON p.id = pm.project_id "
        "WHERE pm.user_id=? AND p.company_id=? "
        "ORDER BY p.end_date",
        (user["id"], user["id"], user["company_id"])
    ).fetchall()
    conn.close()
    return templates.TemplateResponse("employee.html",
                                      {"request": request, "user": user, "projects": projects})


@app.get("/employee/project/{project_id}", response_class=HTMLResponse)
def emp_project(request: Request, project_id: int):
    user = require_role(request, "employee")
    conn = get_conn()
    project = conn.execute(
        "SELECT p.* FROM projects p "
        "JOIN project_members pm ON p.id = pm.project_id "
        "WHERE p.id=? AND pm.user_id=?",
        (project_id, user["id"])
    ).fetchone()
    if not project:
        raise HTTPException(status_code=404)
    kpis = conn.execute(
        "SELECT k.*, "
        "(SELECT value FROM kpi_updates WHERE kpi_id=k.id ORDER BY updated_at DESC LIMIT 1) as current_value, "
        "(SELECT COUNT(*) FROM kpi_updates WHERE kpi_id=k.id) as update_count "
        "FROM kpis k WHERE k.project_id=? AND k.assigned_to=? ORDER BY k.deadline",
        (project_id, user["id"])
    ).fetchall()
    conn.close()
    return templates.TemplateResponse("emp_project.html",
                                      {"request": request, "user": user,
                                       "project": project, "kpis": kpis})


@app.get("/employee/kpi/{kpi_id}", response_class=HTMLResponse)
def emp_kpi_detail(request: Request, kpi_id: int):
    user = require_role(request, "employee")
    conn = get_conn()
    kpi = conn.execute(
        "SELECT k.*, p.name as project_name FROM kpis k "
        "LEFT JOIN projects p ON k.project_id = p.id "
        "WHERE k.id=? AND k.assigned_to=?",
        (kpi_id, user["id"])
    ).fetchone()
    if not kpi:
        raise HTTPException(status_code=404)
    updates = conn.execute(
        "SELECT * FROM kpi_updates WHERE kpi_id=? ORDER BY updated_at", (kpi_id,)
    ).fetchall()
    conn.close()
    return templates.TemplateResponse("kpi_detail.html",
                                      {"request": request, "user": user,
                                       "kpi": kpi, "updates": updates})


@app.post("/employee/kpi/{kpi_id}/update")
async def emp_update_kpi(request: Request, kpi_id: int,
                          value: float = Form(...), note: str = Form("")):
    user = require_role(request, "employee")
    conn = get_conn()
    kpi = conn.execute("SELECT * FROM kpis WHERE id=? AND assigned_to=?",
                        (kpi_id, user["id"])).fetchone()
    if not kpi:
        raise HTTPException(status_code=404)
    conn.execute("INSERT INTO kpi_updates (kpi_id, value, note) VALUES (?,?,?)",
                 (kpi_id, value, note))
    conn.commit()
    conn.close()
    return RedirectResponse(f"/employee/kpi/{kpi_id}", status_code=302)


# ── Manager ───────────────────────────────────────────────────────────────────

@app.get("/manager/dashboard", response_class=HTMLResponse)
def mgr_dashboard(request: Request):
    user = require_role(request, "manager")
    conn = get_conn()
    projects = conn.execute(
        "SELECT p.*, "
        "(SELECT COUNT(*) FROM project_members WHERE project_id=p.id) as member_count, "
        "(SELECT COUNT(*) FROM kpis WHERE project_id=p.id) as kpi_count "
        "FROM projects p WHERE p.department_id=? "
        "ORDER BY p.end_date",
        (user["department_id"],)
    ).fetchall()
    conn.close()
    return templates.TemplateResponse("manager.html",
                                      {"request": request, "user": user, "projects": projects})


@app.get("/manager/project/new", response_class=HTMLResponse)
def mgr_new_project(request: Request):
    user = require_role(request, "manager")
    conn = get_conn()
    employees = conn.execute(
        "SELECT * FROM users WHERE department_id=? AND role IN ('employee','manager') ORDER BY full_name",
        (user["department_id"],)
    ).fetchall()
    conn.close()
    return templates.TemplateResponse("create_project.html",
                                      {"request": request, "user": user,
                                       "employees": employees, "error": None})


@app.post("/manager/project/new")
async def mgr_create_project(request: Request,
                               name: str = Form(...),
                               description: str = Form(""),
                               start_date: str = Form(...),
                               end_date: str = Form(...),
                               member_ids: List[int] = Form(...)):
    user = require_role(request, "manager")
    conn = get_conn()
    conn.execute(
        "INSERT INTO projects (name,description,start_date,end_date,created_by,department_id,company_id) "
        "VALUES (?,?,?,?,?,?,?)",
        (name, description, start_date, end_date,
         user["id"], user["department_id"], user["company_id"])
    )
    project_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    # Always add the manager themselves
    all_members = set(member_ids) | {user["id"]}
    for uid in all_members:
        try:
            conn.execute("INSERT INTO project_members (project_id, user_id) VALUES (?,?)",
                         (project_id, uid))
        except Exception:
            pass
    conn.commit()
    conn.close()
    return RedirectResponse(f"/manager/project/{project_id}", status_code=302)


@app.get("/manager/project/{project_id}", response_class=HTMLResponse)
def mgr_project_detail(request: Request, project_id: int):
    user = require_role(request, "manager")
    conn = get_conn()
    project = conn.execute(
        "SELECT * FROM projects WHERE id=? AND department_id=?",
        (project_id, user["department_id"])
    ).fetchone()
    if not project:
        raise HTTPException(status_code=404)
    members = conn.execute(
        "SELECT u.* FROM users u "
        "JOIN project_members pm ON u.id = pm.user_id "
        "WHERE pm.project_id=? ORDER BY u.full_name",
        (project_id,)
    ).fetchall()
    kpis = conn.execute(
        "SELECT k.*, u.full_name as assignee_name, "
        "(SELECT value FROM kpi_updates WHERE kpi_id=k.id ORDER BY updated_at DESC LIMIT 1) as current_value, "
        "(SELECT COUNT(*) FROM kpi_updates WHERE kpi_id=k.id) as update_count "
        "FROM kpis k JOIN users u ON k.assigned_to = u.id "
        "WHERE k.project_id=? ORDER BY k.deadline",
        (project_id,)
    ).fetchall()
    conn.close()
    return templates.TemplateResponse("mgr_project.html",
                                      {"request": request, "user": user,
                                       "project": project, "members": members, "kpis": kpis})


@app.get("/manager/project/{project_id}/set-kpi", response_class=HTMLResponse)
def mgr_set_kpi_form(request: Request, project_id: int):
    user = require_role(request, "manager")
    conn = get_conn()
    project = conn.execute(
        "SELECT * FROM projects WHERE id=? AND department_id=?",
        (project_id, user["department_id"])
    ).fetchone()
    if not project:
        raise HTTPException(status_code=404)
    members = conn.execute(
        "SELECT u.* FROM users u "
        "JOIN project_members pm ON u.id = pm.user_id "
        "WHERE pm.project_id=? ORDER BY u.full_name",
        (project_id,)
    ).fetchall()
    conn.close()
    return templates.TemplateResponse("set_kpi.html",
                                      {"request": request, "user": user,
                                       "project": project, "members": members})


@app.post("/manager/project/{project_id}/set-kpi")
async def mgr_set_kpi(request: Request, project_id: int,
                       assigned_to: int = Form(...),
                       title: str = Form(...),
                       description: str = Form(""),
                       target_value: float = Form(...),
                       unit: str = Form(...),
                       deadline: str = Form(...)):
    user = require_role(request, "manager")
    conn = get_conn()
    project = conn.execute(
        "SELECT * FROM projects WHERE id=? AND department_id=?",
        (project_id, user["department_id"])
    ).fetchone()
    if not project:
        raise HTTPException(status_code=403)
    conn.execute(
        "INSERT INTO kpis (title,description,target_value,unit,deadline,"
        "created_by,assigned_to,project_id,department_id) VALUES (?,?,?,?,?,?,?,?,?)",
        (title, description, target_value, unit, deadline,
         user["id"], assigned_to, project_id, user["department_id"])
    )
    conn.commit()
    conn.close()
    return RedirectResponse(f"/manager/project/{project_id}", status_code=302)


@app.get("/manager/kpi/{kpi_id}", response_class=HTMLResponse)
def mgr_kpi_detail(request: Request, kpi_id: int):
    user = require_role(request, "manager")
    conn = get_conn()
    kpi = conn.execute(
        "SELECT k.*, u.full_name as assignee_name, p.name as project_name "
        "FROM kpis k "
        "JOIN users u ON k.assigned_to = u.id "
        "LEFT JOIN projects p ON k.project_id = p.id "
        "WHERE k.id=? AND k.department_id=?",
        (kpi_id, user["department_id"])
    ).fetchone()
    if not kpi:
        raise HTTPException(status_code=404)
    updates = conn.execute(
        "SELECT * FROM kpi_updates WHERE kpi_id=? ORDER BY updated_at", (kpi_id,)
    ).fetchall()
    conn.close()
    return templates.TemplateResponse("kpi_detail.html",
                                      {"request": request, "user": user,
                                       "kpi": kpi, "updates": updates})


# ── Admin ─────────────────────────────────────────────────────────────────────

@app.get("/admin/dashboard", response_class=HTMLResponse)
def admin_dashboard(request: Request):
    user = require_role(request, "admin")
    conn = get_conn()
    company = conn.execute("SELECT * FROM companies WHERE id=?",
                            (user["company_id"],)).fetchone()
    departments = conn.execute(
        "SELECT d.*, "
        "(SELECT COUNT(*) FROM users WHERE department_id=d.id) as member_count, "
        "(SELECT full_name FROM users WHERE department_id=d.id AND role='manager' LIMIT 1) as manager_name "
        "FROM departments d WHERE d.company_id=?",
        (user["company_id"],)
    ).fetchall()
    conn.close()
    return templates.TemplateResponse("admin.html",
                                      {"request": request, "user": user,
                                       "company": company, "departments": departments})


@app.get("/admin/department/{dept_id}", response_class=HTMLResponse)
def admin_dept(request: Request, dept_id: int):
    user = require_role(request, "admin")
    conn = get_conn()
    dept = conn.execute("SELECT * FROM departments WHERE id=? AND company_id=?",
                         (dept_id, user["company_id"])).fetchone()
    if not dept:
        raise HTTPException(status_code=404)
    members = conn.execute(
        "SELECT * FROM users WHERE department_id=? ORDER BY role, full_name", (dept_id,)
    ).fetchall()
    conn.close()
    return templates.TemplateResponse("admin_dept.html",
                                      {"request": request, "user": user,
                                       "dept": dept, "members": members})


@app.get("/admin/employee/{emp_id}", response_class=HTMLResponse)
def admin_view_employee(request: Request, emp_id: int):
    user = require_role(request, "admin")
    conn = get_conn()
    emp = conn.execute(
        "SELECT u.*, d.name as dept_name FROM users u "
        "JOIN departments d ON u.department_id = d.id "
        "WHERE u.id=? AND d.company_id=?",
        (emp_id, user["company_id"])
    ).fetchone()
    if not emp:
        raise HTTPException(status_code=404)
    kpis = conn.execute(
        "SELECT k.*, p.name as project_name, "
        "(SELECT value FROM kpi_updates WHERE kpi_id=k.id ORDER BY updated_at DESC LIMIT 1) as current_value, "
        "(SELECT COUNT(*) FROM kpi_updates WHERE kpi_id=k.id) as update_count "
        "FROM kpis k LEFT JOIN projects p ON k.project_id = p.id "
        "WHERE k.assigned_to=? ORDER BY k.deadline",
        (emp_id,)
    ).fetchall()
    conn.close()
    return templates.TemplateResponse("admin_emp_view.html",
                                      {"request": request, "user": user,
                                       "emp": emp, "kpis": kpis})


@app.get("/admin/kpi/{kpi_id}", response_class=HTMLResponse)
def admin_kpi_detail(request: Request, kpi_id: int):
    user = require_role(request, "admin")
    conn = get_conn()
    kpi = conn.execute(
        "SELECT k.*, u.full_name as assignee_name, p.name as project_name "
        "FROM kpis k "
        "JOIN users u ON k.assigned_to = u.id "
        "LEFT JOIN projects p ON k.project_id = p.id "
        "JOIN departments d ON k.department_id = d.id "
        "WHERE k.id=? AND d.company_id=?",
        (kpi_id, user["company_id"])
    ).fetchone()
    if not kpi:
        raise HTTPException(status_code=404)
    updates = conn.execute(
        "SELECT * FROM kpi_updates WHERE kpi_id=? ORDER BY updated_at", (kpi_id,)
    ).fetchall()
    conn.close()
    return templates.TemplateResponse("kpi_detail.html",
                                      {"request": request, "user": user,
                                       "kpi": kpi, "updates": updates})


@app.get("/admin/add-department", response_class=HTMLResponse)
def admin_add_dept_page(request: Request):
    user = require_role(request, "admin")
    return templates.TemplateResponse("add_department.html",
                                      {"request": request, "user": user, "error": None})


@app.post("/admin/add-department")
async def admin_add_dept(request: Request, dept_name: str = Form(...)):
    user = require_role(request, "admin")
    conn = get_conn()
    conn.execute("INSERT INTO departments (name, company_id) VALUES (?,?)",
                 (dept_name.strip(), user["company_id"]))
    conn.commit()
    conn.close()
    return RedirectResponse("/admin/dashboard", status_code=302)


@app.post("/admin/change-role")
async def admin_change_role(request: Request,
                             user_id: int = Form(...),
                             new_role: str = Form(...)):
    user = require_role(request, "admin")
    if new_role not in ("admin", "manager", "employee"):
        raise HTTPException(status_code=400)
    conn = get_conn()
    target = conn.execute("SELECT * FROM users WHERE id=? AND company_id=?",
                           (user_id, user["company_id"])).fetchone()
    if not target:
        raise HTTPException(status_code=404)
    if target["role"] == "admin" and new_role != "admin":
        count = conn.execute(
            "SELECT COUNT(*) FROM users WHERE company_id=? AND role='admin'",
            (user["company_id"],)
        ).fetchone()[0]
        if count <= 1:
            conn.close()
            return RedirectResponse(
                f"/admin/department/{target['department_id']}" if target["department_id"] else "/admin/dashboard",
                status_code=302
            )
    dept_id = target["department_id"]
    if new_role == "manager" and dept_id:
        conn.execute(
            "UPDATE users SET role='employee' WHERE department_id=? AND role='manager'", (dept_id,)
        )
    conn.execute("UPDATE users SET role=? WHERE id=?", (new_role, user_id))
    conn.commit()
    conn.close()
    return RedirectResponse(
        f"/admin/department/{dept_id}" if dept_id else "/admin/dashboard",
        status_code=302
    )


# ── Prediction APIs ───────────────────────────────────────────────────────────

def _get_kpi_for_user(conn, kpi_id: int, user):
    if user["role"] == "employee":
        return conn.execute("SELECT * FROM kpis WHERE id=? AND assigned_to=?",
                            (kpi_id, user["id"])).fetchone()
    elif user["role"] == "manager":
        return conn.execute("SELECT * FROM kpis WHERE id=? AND department_id=?",
                            (kpi_id, user["department_id"])).fetchone()
    else:
        return conn.execute(
            "SELECT k.* FROM kpis k "
            "JOIN departments d ON k.department_id = d.id "
            "WHERE k.id=? AND d.company_id=?",
            (kpi_id, user["company_id"])
        ).fetchone()


@app.get("/api/predict/{kpi_id}")
def api_predict(request: Request, kpi_id: int):
    user = current_user(request)
    if not user:
        raise HTTPException(status_code=401)
    conn = get_conn()
    kpi = _get_kpi_for_user(conn, kpi_id, user)
    if not kpi:
        conn.close()
        raise HTTPException(status_code=404)
    updates = conn.execute(
        "SELECT value, updated_at as date FROM kpi_updates WHERE kpi_id=? ORDER BY updated_at",
        (kpi_id,)
    ).fetchall()
    conn.close()
    update_list = [{"date": u["date"][:10], "value": float(u["value"])} for u in updates]
    return JSONResponse(predict_kpi(update_list, kpi["target_value"], kpi["deadline"], kpi["unit"]))


@app.get("/api/behaviour/{kpi_id}")
def api_behaviour(request: Request, kpi_id: int):
    user = current_user(request)
    if not user:
        raise HTTPException(status_code=401)
    conn = get_conn()
    kpi = _get_kpi_for_user(conn, kpi_id, user)
    if not kpi:
        conn.close()
        raise HTTPException(status_code=404)
    updates = conn.execute(
        "SELECT value, updated_at as date FROM kpi_updates WHERE kpi_id=? ORDER BY updated_at",
        (kpi_id,)
    ).fetchall()
    conn.close()
    update_list = [{"date": u["date"][:10], "value": float(u["value"])} for u in updates]
    return JSONResponse(predict_behaviour(update_list, kpi["target_value"], kpi["deadline"]))