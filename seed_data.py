"""
SmartTrack KPI — Rich Test Data Seeder
Run from models/ folder after app has started once (to create the DB):
    python seed_data.py

Creates TWO separate organisations:
  1. Nexus Technologies Ltd  (code: NEXUS1) — Tech company
  2. Pinnacle Consulting Ltd (code: PINCO2) — Consulting company
"""

import os
import sqlite3, hashlib, sys
from pathlib import Path
from datetime import datetime, timedelta

DB_PATH = Path(os.getenv("DATABASE_PATH", Path(__file__).resolve().parent / "models" / "smarttrack.db"))

print(f"Using database: {DB_PATH}")

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

if not DB_PATH.exists():
    print("ERROR: smarttrack.db not found. Start the app once first, then run this.")
    sys.exit(1)

conn = get_conn()
if conn.execute("SELECT COUNT(*) FROM companies").fetchone()[0] > 0:
    print("Database already has data. Delete smarttrack.db, restart the app, then run this.")
    sys.exit(0)

today = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)

def add_dept(name, company_id):
    conn.execute("INSERT INTO departments (name, company_id) VALUES (?,?)", (name, company_id))
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]

def add_user(username, pw, full_name, role, dept_id, company_id):
    conn.execute(
        "INSERT INTO users (username,password,full_name,role,department_id,company_id) VALUES (?,?,?,?,?,?)",
        (username, hash_pw(pw), full_name, role, dept_id, company_id)
    )
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]

def add_project(name, desc, start, end, status, created_by, dept_id, company_id):
    conn.execute(
        "INSERT INTO projects (name,description,start_date,end_date,status,created_by,department_id,company_id) VALUES (?,?,?,?,?,?,?,?)",
        (name, desc, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"),
         status, created_by, dept_id, company_id)
    )
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]

def add_member(project_id, user_id):
    conn.execute(
        "INSERT OR IGNORE INTO project_members (project_id, user_id) VALUES (?,?)",
        (project_id, user_id)
    )

def add_kpi(title, desc, target, unit, deadline, created_by, assigned_to, project_id, dept_id):
    conn.execute(
        "INSERT INTO kpis (title,description,target_value,unit,deadline,created_by,"
        "assigned_to,project_id,department_id) VALUES (?,?,?,?,?,?,?,?,?)",
        (title, desc, target, unit, deadline.strftime("%Y-%m-%d"),
         created_by, assigned_to, project_id, dept_id)
    )
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]

def add_updates(kpi_id, entries):
    for value, date, note in entries:
        conn.execute(
            "INSERT INTO kpi_updates (kpi_id,value,note,updated_at) VALUES (?,?,?,?)",
            (kpi_id, value, note, date.strftime("%Y-%m-%d %H:%M:%S"))
        )

# ═══════════════════════════════════════════════════════
# ORGANISATION 1 — NEXUS TECHNOLOGIES LTD
# ═══════════════════════════════════════════════════════
print("\n── Organisation 1: Nexus Technologies Ltd ──")

conn.execute("INSERT INTO companies (name, code) VALUES (?,?)",
             ("Nexus Technologies Ltd", "NEXUS1"))
nex = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

nex_eng = add_dept("Engineering", nex)
nex_prd = add_dept("Product",     nex)

nex_admin  = add_user("nex_admin",  "admin123", "Sarah Okonkwo",   "admin",    None,    nex)
nex_mgr_e  = add_user("nex_mgr_e",  "mgr123",   "Tunde Bakare",    "manager",  nex_eng, nex)
nex_mgr_p  = add_user("nex_mgr_p",  "mgr123",   "Chidi Obi",       "manager",  nex_prd, nex)
nex_star   = add_user("nex_star",   "emp123",   "Esther Ojo",      "employee", nex_eng, nex)
nex_steady = add_user("nex_steady", "emp123",   "Kola Adebayo",    "employee", nex_eng, nex)
nex_risk   = add_user("nex_risk",   "emp123",   "Ngozi Ihejirika", "employee", nex_eng, nex)
nex_new    = add_user("nex_new",    "emp123",   "Femi Lawal",      "employee", nex_eng, nex)
nex_recov  = add_user("nex_recov",  "emp123",   "Ada Nwosu",       "employee", nex_prd, nex)
nex_done   = add_user("nex_done",   "emp123",   "Bola Adeleke",    "employee", nex_prd, nex)

print("  Users created")

# ── Active project: Q2 Platform Sprint (45 days in, 30 days left) ────────────
p1s = today - timedelta(days=45)
p1e = today + timedelta(days=30)

proj_eng = add_project(
    "Q2 Platform Sprint",
    "Deliver core platform features and resolve the critical backlog for Q2 release.",
    p1s, p1e, "active", nex_mgr_e, nex_eng, nex
)
for uid in [nex_mgr_e, nex_star, nex_steady, nex_risk, nex_new]:
    add_member(proj_eng, uid)

# ESTHER — Star: 55/60 reviews, way ahead, will finish early
k = add_kpi("Complete code reviews",
    "Review all pull requests assigned during the sprint.",
    60, "reviews", p1e, nex_mgr_e, nex_star, proj_eng, nex_eng)
add_updates(k, [
    (6,  p1s+timedelta(days=4),  "Cleared first batch — strong start"),
    (14, p1s+timedelta(days=10), "Kept the pace up, reviewed design PRs"),
    (23, p1s+timedelta(days=16), "Strong week — big backend batch done"),
    (33, p1s+timedelta(days=22), "Ahead of schedule, helping others"),
    (42, p1s+timedelta(days=29), "Over 70% done, very comfortable"),
    (50, p1s+timedelta(days=36), "Almost there"),
    (55, p1s+timedelta(days=42), "5 left with a month to spare"),
])
print("  KPI: Esther (star) — 55/60 reviews, will exceed")

# KOLA — Steady: 28/40 features, exactly on pace
k = add_kpi("Deliver product features",
    "Ship all assigned feature tickets to production.",
    40, "features", p1e, nex_mgr_e, nex_steady, proj_eng, nex_eng)
add_updates(k, [
    (3,  p1s+timedelta(days=5),  "Auth module shipped"),
    (7,  p1s+timedelta(days=11), "Dashboard and settings done"),
    (11, p1s+timedelta(days=17), "API endpoints merged"),
    (16, p1s+timedelta(days=24), "Notification system complete"),
    (20, p1s+timedelta(days=30), "Mid-point — exactly on track"),
    (24, p1s+timedelta(days=37), "Refactor slowed things slightly"),
    (28, p1s+timedelta(days=43), "Back on pace — 12 left, 30 days to go"),
])
print("  KPI: Kola (steady) — 28/40 features, on pace")

# NGOZI — At risk: 25/80 bugs, will miss
k = add_kpi("Resolve bug tickets",
    "Clear all assigned critical and high-priority bugs from the backlog.",
    80, "bugs", p1e, nex_mgr_e, nex_risk, proj_eng, nex_eng)
add_updates(k, [
    (2,  p1s+timedelta(days=7),  "Still ramping up on the codebase"),
    (5,  p1s+timedelta(days=14), "Slow progress — some blockers"),
    (9,  p1s+timedelta(days=21), "Cleared some easy ones"),
    (13, p1s+timedelta(days=28), "Blocked awaiting third party"),
    (17, p1s+timedelta(days=35), "Unblocked but still far behind"),
    (21, p1s+timedelta(days=41), "Pace not improving enough"),
    (25, p1s+timedelta(days=44), "Need 55 more bugs in 30 days — very unlikely"),
])
print("  KPI: Ngozi (at risk) — 25/80 bugs, WILL MISS")

# FEMI — New employee, no updates yet
add_kpi("Complete onboarding checklist",
    "Finish all onboarding tasks, tool setup, and first code contribution.",
    15, "tasks", p1e, nex_mgr_e, nex_new, proj_eng, nex_eng)
print("  KPI: Femi (new) — 0/15 tasks, no updates")

# ── Active project: Mobile Redesign (20 days in, 40 left) ────────────────────
p2s = today - timedelta(days=20)
p2e = today + timedelta(days=40)

proj_prd = add_project(
    "Mobile App Redesign",
    "Redesign and ship the updated mobile app with improved UI and performance.",
    p2s, p2e, "active", nex_mgr_p, nex_prd, nex
)
for uid in [nex_mgr_p, nex_recov]:
    add_member(proj_prd, uid)

# ADA — Slow starter who recovered: was behind at halfway, caught up
k = add_kpi("Design and deliver UI screens",
    "Produce and deliver all approved UI screens for the redesigned app.",
    50, "screens", p2e, nex_mgr_p, nex_recov, proj_prd, nex_prd)
add_updates(k, [
    (2,  p2s+timedelta(days=3),  "Started with wireframes — taking time"),
    (4,  p2s+timedelta(days=7),  "Still in planning phase, behind schedule"),
    (7,  p2s+timedelta(days=11), "Design system finalised — can move faster now"),
    (13, p2s+timedelta(days=15), "Picked up pace significantly"),
    (20, p2s+timedelta(days=19), "Recovered — now back on track"),
])
print("  KPI: Ada (slow starter recovered) — 20/50 screens, back on track")

# ── Completed project: Q1 Docs Sprint (deadline passed, Bola missed) ─────────
p3s = today - timedelta(days=50)
p3e = today - timedelta(days=6)

proj_old = add_project(
    "Q1 Documentation Sprint",
    "Complete all developer docs, API guides, and release notes for Q1.",
    p3s, p3e, "completed", nex_mgr_p, nex_prd, nex
)
for uid in [nex_mgr_p, nex_done]:
    add_member(proj_old, uid)

k = add_kpi("Write technical documentation",
    "Complete all developer docs, API guides, and release notes.",
    40, "pages", p3e, nex_mgr_p, nex_done, proj_old, nex_prd)
add_updates(k, [
    (3,  p3s+timedelta(days=6),  "Started with API docs"),
    (7,  p3s+timedelta(days=13), "Slow going — complex endpoints"),
    (11, p3s+timedelta(days=20), "Behind pace"),
    (16, p3s+timedelta(days=28), "Tried to catch up"),
    (20, p3s+timedelta(days=36), "Still significantly behind"),
    (24, p3s+timedelta(days=43), "Deadline approaching fast"),
    (28, p3s+timedelta(days=49), "Deadline passed — only 28 of 40 pages done"),
])
print("  KPI: Bola (deadline passed) — 28/40 pages, MISSED")

# ═══════════════════════════════════════════════════════
# ORGANISATION 2 — PINNACLE CONSULTING LTD
# ═══════════════════════════════════════════════════════
print("\n── Organisation 2: Pinnacle Consulting Ltd ──")

conn.execute("INSERT INTO companies (name, code) VALUES (?,?)",
             ("Pinnacle Consulting Ltd", "PINCO2"))
pin = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

pin_sal = add_dept("Sales",      pin)
pin_ops = add_dept("Operations", pin)

pin_admin  = add_user("pin_admin",  "admin123", "James Adeyemi",  "admin",    None,    pin)
pin_mgr_s  = add_user("pin_mgr_s",  "mgr123",   "Amaka Eze",      "manager",  pin_sal, pin)
pin_mgr_o  = add_user("pin_mgr_o",  "mgr123",   "Emeka Okafor",   "manager",  pin_ops, pin)
pin_ace    = add_user("pin_ace",    "emp123",   "Zainab Musa",    "employee", pin_sal, pin)
pin_onpace = add_user("pin_onpace", "emp123",   "David Eze",      "employee", pin_sal, pin)
pin_behind = add_user("pin_behind", "emp123",   "Chioma Obi",     "employee", pin_sal, pin)
pin_great  = add_user("pin_great",  "emp123",   "Temi Adesanya",  "employee", pin_sal, pin)
pin_ops1   = add_user("pin_ops1",   "emp123",   "Kunle Salami",   "employee", pin_ops, pin)
pin_ops2   = add_user("pin_ops2",   "emp123",   "Ngozi Eze",      "employee", pin_ops, pin)

print("  Users created")

# ── Active project: Q2 Revenue Drive (38 days in, 22 days left) ──────────────
p4s = today - timedelta(days=38)
p4e = today + timedelta(days=22)

proj_sal = add_project(
    "Q2 Revenue Drive",
    "Hit Q2 sales targets — close new deals and build the Q3 pipeline.",
    p4s, p4e, "active", pin_mgr_s, pin_sal, pin
)
for uid in [pin_mgr_s, pin_ace, pin_onpace, pin_behind]:
    add_member(proj_sal, uid)

# ZAINAB — Ace: 27/30 deals, will exceed
k = add_kpi("Close new client deals",
    "Convert qualified leads into signed contracts.",
    30, "deals", p4e, pin_mgr_s, pin_ace, proj_sal, pin_sal)
add_updates(k, [
    (3,  p4s+timedelta(days=4),  "Warm leads converting well"),
    (6,  p4s+timedelta(days=8),  "Referral network paying off"),
    (10, p4s+timedelta(days=13), "Strong pipeline"),
    (15, p4s+timedelta(days=19), "Well ahead at halfway"),
    (19, p4s+timedelta(days=25), "Closing in fast"),
    (23, p4s+timedelta(days=31), "One push left"),
    (27, p4s+timedelta(days=36), "3 left with 22 days — easy finish"),
])
print("  KPI: Zainab (ace) — 27/30 deals, will exceed")

# DAVID — On pace: 52/80 calls, comfortable
k = add_kpi("Conduct discovery calls",
    "Run structured discovery calls with qualified prospects.",
    80, "calls", p4e, pin_mgr_s, pin_onpace, proj_sal, pin_sal)
add_updates(k, [
    (7,  p4s+timedelta(days=5),  "Good start — booked well in advance"),
    (14, p4s+timedelta(days=11), "Maintained cadence"),
    (22, p4s+timedelta(days=17), "On track at midpoint"),
    (30, p4s+timedelta(days=23), "Steady as always"),
    (39, p4s+timedelta(days=29), "Consistent week"),
    (46, p4s+timedelta(days=34), "Slightly ahead"),
    (52, p4s+timedelta(days=37), "52 done — 28 remaining, 22 days. Comfortable."),
])
print("  KPI: David (on pace) — 52/80 calls, on track")

# CHIOMA — Struggling: 14/50 proposals, will miss badly
k = add_kpi("Submit sales proposals",
    "Prepare and submit tailored proposals to qualified prospects.",
    50, "proposals", p4e, pin_mgr_s, pin_behind, proj_sal, pin_sal)
add_updates(k, [
    (1,  p4s+timedelta(days=8),  "Starting slowly — building templates"),
    (3,  p4s+timedelta(days=15), "Templates done but volume still low"),
    (6,  p4s+timedelta(days=22), "Picking up slightly"),
    (9,  p4s+timedelta(days=29), "Not enough — need to push much harder"),
    (12, p4s+timedelta(days=35), "Improved slightly but still far off"),
    (14, p4s+timedelta(days=37), "14 of 50 with 22 days left — very unlikely"),
])
print("  KPI: Chioma (struggling) — 14/50 proposals, WILL MISS")

# ── Completed project: April Demo Campaign (Temi exceeded target) ────────────
p5s = today - timedelta(days=45)
p5e = today - timedelta(days=5)

proj_old_sal = add_project(
    "April Demo Campaign",
    "Run product demos for all warm prospects in the April pipeline.",
    p5s, p5e, "completed", pin_mgr_s, pin_sal, pin
)
for uid in [pin_mgr_s, pin_great]:
    add_member(proj_old_sal, uid)

k = add_kpi("Run product demos",
    "Deliver live product demonstrations to qualified prospects.",
    20, "demos", p5e, pin_mgr_s, pin_great, proj_old_sal, pin_sal)
add_updates(k, [
    (2,  p5s+timedelta(days=6),  "First demos booked and delivered"),
    (5,  p5s+timedelta(days=13), "Getting smoother each time"),
    (9,  p5s+timedelta(days=20), "Very positive feedback from prospects"),
    (13, p5s+timedelta(days=28), "Ahead of schedule"),
    (17, p5s+timedelta(days=36), "Almost done"),
    (22, p5s+timedelta(days=43), "Exceeded target — 22 demos delivered"),
])
print("  KPI: Temi (deadline passed) — 22/20 demos, EXCEEDED TARGET")

# ── Active project: Client Success Sprint (30 days in, 30 left) ──────────────
p6s = today - timedelta(days=30)
p6e = today + timedelta(days=30)

proj_ops = add_project(
    "Client Success Sprint",
    "Onboard new clients, resolve support tickets, and hit satisfaction targets.",
    p6s, p6e, "active", pin_mgr_o, pin_ops, pin
)
for uid in [pin_mgr_o, pin_ops1, pin_ops2]:
    add_member(proj_ops, uid)

# KUNLE — On track: 14/25 clients onboarded
k = add_kpi("Onboard new clients",
    "Complete the full onboarding process for each assigned new client.",
    25, "clients", p6e, pin_mgr_o, pin_ops1, proj_ops, pin_ops)
add_updates(k, [
    (2,  p6s+timedelta(days=4),  "First two onboardings complete"),
    (5,  p6s+timedelta(days=9),  "Streamlined the process"),
    (8,  p6s+timedelta(days=14), "Solid week"),
    (11, p6s+timedelta(days=19), "On track"),
    (14, p6s+timedelta(days=27), "Halfway through, exactly on pace"),
])
print("  KPI: Kunle (ops) — 14/25 clients, on track")

# NGOZI OPS — Overperforming: 130/150 tickets, will exceed
k = add_kpi("Resolve support tickets",
    "Clear assigned support tickets within agreed SLA response times.",
    150, "tickets", p6e, pin_mgr_o, pin_ops2, proj_ops, pin_ops)
add_updates(k, [
    (18,  p6s+timedelta(days=4),  "Strong start — cleared backlog"),
    (35,  p6s+timedelta(days=9),  "High volume week"),
    (55,  p6s+timedelta(days=14), "Consistently above target rate"),
    (78,  p6s+timedelta(days=19), "Over halfway with time to spare"),
    (100, p6s+timedelta(days=23), "100 done — impressive pace"),
    (130, p6s+timedelta(days=28), "Will definitely exceed 150"),
])
print("  KPI: Ngozi-Ops (overperforming) — 130/150 tickets, will exceed")

conn.commit()
conn.close()

print()
print("=" * 65)
print("SEED COMPLETE")
print("=" * 65)
print()
print("ORGANISATION 1 — Nexus Technologies Ltd  (code: NEXUS1)")
print("-" * 65)
print("  Admin:     nex_admin  / admin123")
print("  Managers:  nex_mgr_e  / mgr123   Engineering")
print("             nex_mgr_p  / mgr123   Product")
print()
print("  Engineering — Q2 Platform Sprint (active, 30 days left)")
print("    nex_star   / emp123  Esther Ojo       55/60 reviews   STAR — will exceed")
print("    nex_steady / emp123  Kola Adebayo     28/40 features  STEADY — on pace")
print("    nex_risk   / emp123  Ngozi Ihejirika  25/80 bugs      AT RISK — will miss")
print("    nex_new    / emp123  Femi Lawal        0/15 tasks     NEW — no updates")
print()
print("  Product — Mobile Redesign (active, 40 days left)")
print("    nex_recov  / emp123  Ada Nwosu        20/50 screens   RECOVERED")
print()
print("  Product — Q1 Docs Sprint (completed)")
print("    nex_done   / emp123  Bola Adeleke     28/40 pages     MISSED")
print()
print("ORGANISATION 2 — Pinnacle Consulting Ltd (code: PINCO2)")
print("-" * 65)
print("  Admin:     pin_admin  / admin123")
print("  Managers:  pin_mgr_s  / mgr123   Sales")
print("             pin_mgr_o  / mgr123   Operations")
print()
print("  Sales — Q2 Revenue Drive (active, 22 days left)")
print("    pin_ace    / emp123  Zainab Musa      27/30 deals     ACE — will exceed")
print("    pin_onpace / emp123  David Eze        52/80 calls     ON PACE")
print("    pin_behind / emp123  Chioma Obi       14/50 proposals STRUGGLING — will miss")
print()
print("  Sales — April Demo Campaign (completed)")
print("    pin_great  / emp123  Temi Adesanya    22/20 demos     EXCEEDED TARGET")
print()
print("  Operations — Client Success Sprint (active, 30 days left)")
print("    pin_ops1   / emp123  Kunle Salami     14/25 clients   ON TRACK")
print("    pin_ops2   / emp123  Ngozi Eze       130/150 tickets  OVERPERFORMING")
print("=" * 65)