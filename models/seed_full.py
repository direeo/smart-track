"""
Full idempotent seed — creates Nexus Technologies Ltd + Pinnacle Consulting Ltd
with departments, users (correct org assignments), projects, KPIs, and updates.
Called by app.py on every startup; safe to run repeatedly.
"""
from datetime import datetime, timedelta
from database import get_conn, hash_pw


def ensure_full_seed():
    conn = get_conn()
    today = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)

    # ── helpers ──────────────────────────────────────────────────────────────

    def _company(name, code):
        row = conn.execute("SELECT id FROM companies WHERE code=?", (code,)).fetchone()
        if row:
            return row[0]
        conn.execute("INSERT INTO companies (name, code) VALUES (?,?)", (name, code))
        return conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    def _dept(name, cid):
        row = conn.execute(
            "SELECT id FROM departments WHERE name=? AND company_id=?", (name, cid)
        ).fetchone()
        if row:
            return row[0]
        conn.execute("INSERT INTO departments (name, company_id) VALUES (?,?)", (name, cid))
        return conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    def _user(uname, pw, full, role, did, cid):
        row = conn.execute("SELECT id FROM users WHERE username=?", (uname,)).fetchone()
        if row:
            # Always update to correct org + password (fixes SEED-company corruption)
            conn.execute(
                "UPDATE users SET password=?,full_name=?,role=?,department_id=?,company_id=? WHERE username=?",
                (hash_pw(pw), full, role, did, cid, uname)
            )
            return row[0]
        conn.execute(
            "INSERT INTO users (username,password,full_name,role,department_id,company_id)"
            " VALUES (?,?,?,?,?,?)",
            (uname, hash_pw(pw), full, role, did, cid)
        )
        return conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    def _project(name, desc, start, end, status, by, did, cid):
        row = conn.execute(
            "SELECT id FROM projects WHERE name=? AND company_id=?", (name, cid)
        ).fetchone()
        if row:
            return row[0], False
        conn.execute(
            "INSERT INTO projects (name,description,start_date,end_date,status,"
            "created_by,department_id,company_id) VALUES (?,?,?,?,?,?,?,?)",
            (name, desc, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"),
             status, by, did, cid)
        )
        return conn.execute("SELECT last_insert_rowid()").fetchone()[0], True

    def _member(pid, uid):
        conn.execute(
            "INSERT OR IGNORE INTO project_members (project_id, user_id) VALUES (?,?)",
            (pid, uid)
        )

    def _kpi(title, desc, target, unit, deadline, by, assigned, pid, did):
        row = conn.execute(
            "SELECT id FROM kpis WHERE title=? AND project_id=? AND assigned_to=?",
            (title, pid, assigned)
        ).fetchone()
        if row:
            return row[0], False
        conn.execute(
            "INSERT INTO kpis (title,description,target_value,unit,deadline,"
            "created_by,assigned_to,project_id,department_id) VALUES (?,?,?,?,?,?,?,?,?)",
            (title, desc, target, unit, deadline.strftime("%Y-%m-%d"),
             by, assigned, pid, did)
        )
        return conn.execute("SELECT last_insert_rowid()").fetchone()[0], True

    def _updates(kid, entries):
        if conn.execute("SELECT COUNT(*) FROM kpi_updates WHERE kpi_id=?", (kid,)).fetchone()[0]:
            return  # already seeded
        for val, dt, note in entries:
            conn.execute(
                "INSERT INTO kpi_updates (kpi_id,value,note,updated_at) VALUES (?,?,?,?)",
                (kid, val, note, dt.strftime("%Y-%m-%d %H:%M:%S"))
            )

    # ═════════════════════════════════════════════════════════════════
    # NEXUS TECHNOLOGIES LTD
    # ═════════════════════════════════════════════════════════════════
    nex = _company("Nexus Technologies Ltd", "NEXUS1")
    eng = _dept("Engineering", nex)
    prd = _dept("Product", nex)

    n_admin  = _user("nex_admin",  "admin123", "Sarah Okonkwo",   "admin",    None, nex)
    n_mgr_e  = _user("nex_mgr_e",  "mgr123",   "Tunde Bakare",    "manager",  eng,  nex)
    n_mgr_p  = _user("nex_mgr_p",  "mgr123",   "Chidi Obi",       "manager",  prd,  nex)
    n_star   = _user("nex_star",   "emp123",   "Esther Ojo",      "employee", eng,  nex)
    n_steady = _user("nex_steady", "emp123",   "Kola Adebayo",    "employee", eng,  nex)
    n_risk   = _user("nex_risk",   "emp123",   "Ngozi Ihejirika", "employee", eng,  nex)
    n_new    = _user("nex_new",    "emp123",   "Femi Lawal",      "employee", eng,  nex)
    n_recov  = _user("nex_recov",  "emp123",   "Ada Nwosu",       "employee", prd,  nex)
    n_done   = _user("nex_done",   "emp123",   "Bola Adeleke",    "employee", prd,  nex)

    # ── Q2 Platform Sprint (active) ──────────────────────────────────
    p1s = today - timedelta(days=45)
    p1e = today + timedelta(days=30)
    p1, _ = _project("Q2 Platform Sprint",
        "Deliver core platform features and resolve the critical backlog for Q2 release.",
        p1s, p1e, "active", n_mgr_e, eng, nex)
    for u in [n_mgr_e, n_star, n_steady, n_risk, n_new]:
        _member(p1, u)

    k, new = _kpi("Complete code reviews",
        "Review all pull requests assigned during the sprint.",
        60, "reviews", p1e, n_mgr_e, n_star, p1, eng)
    if new:
        _updates(k, [
            (6,  p1s+timedelta(days=4),  "Cleared first batch - strong start"),
            (14, p1s+timedelta(days=10), "Kept the pace up, reviewed design PRs"),
            (23, p1s+timedelta(days=16), "Strong week - big backend batch done"),
            (33, p1s+timedelta(days=22), "Ahead of schedule, helping others"),
            (42, p1s+timedelta(days=29), "Over 70% done, very comfortable"),
            (50, p1s+timedelta(days=36), "Almost there"),
            (55, p1s+timedelta(days=42), "5 left with a month to spare"),
        ])

    k, new = _kpi("Deliver product features",
        "Ship all assigned feature tickets to production.",
        40, "features", p1e, n_mgr_e, n_steady, p1, eng)
    if new:
        _updates(k, [
            (3,  p1s+timedelta(days=5),  "Auth module shipped"),
            (7,  p1s+timedelta(days=11), "Dashboard and settings done"),
            (11, p1s+timedelta(days=17), "API endpoints merged"),
            (16, p1s+timedelta(days=24), "Notification system complete"),
            (20, p1s+timedelta(days=30), "Mid-point - exactly on track"),
            (24, p1s+timedelta(days=37), "Refactor slowed things slightly"),
            (28, p1s+timedelta(days=43), "Back on pace - 12 left, 30 days to go"),
        ])

    k, new = _kpi("Resolve bug tickets",
        "Clear all assigned critical and high-priority bugs from the backlog.",
        80, "bugs", p1e, n_mgr_e, n_risk, p1, eng)
    if new:
        _updates(k, [
            (2,  p1s+timedelta(days=7),  "Still ramping up on the codebase"),
            (5,  p1s+timedelta(days=14), "Slow progress - some blockers"),
            (9,  p1s+timedelta(days=21), "Cleared some easy ones"),
            (13, p1s+timedelta(days=28), "Blocked awaiting third party"),
            (17, p1s+timedelta(days=35), "Unblocked but still far behind"),
            (21, p1s+timedelta(days=41), "Pace not improving enough"),
            (25, p1s+timedelta(days=44), "Need 55 more in 30 days - very unlikely"),
        ])

    _kpi("Complete onboarding checklist",
        "Finish all onboarding tasks, tool setup, and first code contribution.",
        15, "tasks", p1e, n_mgr_e, n_new, p1, eng)  # no updates — new employee

    # ── Mobile App Redesign (active) ─────────────────────────────────
    p2s = today - timedelta(days=20)
    p2e = today + timedelta(days=40)
    p2, _ = _project("Mobile App Redesign",
        "Redesign and ship the updated mobile app with improved UI and performance.",
        p2s, p2e, "active", n_mgr_p, prd, nex)
    for u in [n_mgr_p, n_recov]:
        _member(p2, u)

    k, new = _kpi("Design and deliver UI screens",
        "Produce and deliver all approved UI screens for the redesigned app.",
        50, "screens", p2e, n_mgr_p, n_recov, p2, prd)
    if new:
        _updates(k, [
            (2,  p2s+timedelta(days=3),  "Started with wireframes - taking time"),
            (4,  p2s+timedelta(days=7),  "Still in planning phase, behind schedule"),
            (7,  p2s+timedelta(days=11), "Design system finalised - can move faster now"),
            (13, p2s+timedelta(days=15), "Picked up pace significantly"),
            (20, p2s+timedelta(days=19), "Recovered - now back on track"),
        ])

    # ── Q1 Documentation Sprint (completed) ──────────────────────────
    p3s = today - timedelta(days=50)
    p3e = today - timedelta(days=6)
    p3, _ = _project("Q1 Documentation Sprint",
        "Complete all developer docs, API guides, and release notes for Q1.",
        p3s, p3e, "completed", n_mgr_p, prd, nex)
    for u in [n_mgr_p, n_done]:
        _member(p3, u)

    k, new = _kpi("Write technical documentation",
        "Complete all developer docs, API guides, and release notes.",
        40, "pages", p3e, n_mgr_p, n_done, p3, prd)
    if new:
        _updates(k, [
            (3,  p3s+timedelta(days=6),  "Started with API docs"),
            (7,  p3s+timedelta(days=13), "Slow going - complex endpoints"),
            (11, p3s+timedelta(days=20), "Behind pace"),
            (16, p3s+timedelta(days=28), "Tried to catch up"),
            (20, p3s+timedelta(days=36), "Still significantly behind"),
            (24, p3s+timedelta(days=43), "Deadline approaching fast"),
            (28, p3s+timedelta(days=49), "Deadline passed - only 28 of 40 pages done"),
        ])

    # ═════════════════════════════════════════════════════════════════
    # PINNACLE CONSULTING LTD
    # ═════════════════════════════════════════════════════════════════
    pin = _company("Pinnacle Consulting Ltd", "PINCO2")
    sal = _dept("Sales",      pin)
    ops = _dept("Operations", pin)

    p_admin   = _user("pin_admin",  "admin123", "James Adeyemi",  "admin",    None, pin)
    p_mgr_s   = _user("pin_mgr_s",  "mgr123",   "Amaka Eze",      "manager",  sal,  pin)
    p_mgr_o   = _user("pin_mgr_o",  "mgr123",   "Emeka Okafor",   "manager",  ops,  pin)
    p_ace     = _user("pin_ace",    "emp123",   "Zainab Musa",    "employee", sal,  pin)
    p_onpace  = _user("pin_onpace", "emp123",   "David Eze",      "employee", sal,  pin)
    p_behind  = _user("pin_behind", "emp123",   "Chioma Obi",     "employee", sal,  pin)
    p_great   = _user("pin_great",  "emp123",   "Temi Adesanya",  "employee", sal,  pin)
    p_ops1    = _user("pin_ops1",   "emp123",   "Kunle Salami",   "employee", ops,  pin)
    p_ops2    = _user("pin_ops2",   "emp123",   "Ngozi Eze",      "employee", ops,  pin)

    # ── Q2 Revenue Drive (active) ─────────────────────────────────────
    p4s = today - timedelta(days=38)
    p4e = today + timedelta(days=22)
    p4, _ = _project("Q2 Revenue Drive",
        "Hit Q2 sales targets - close new deals and build the Q3 pipeline.",
        p4s, p4e, "active", p_mgr_s, sal, pin)
    for u in [p_mgr_s, p_ace, p_onpace, p_behind]:
        _member(p4, u)

    k, new = _kpi("Close new client deals",
        "Convert qualified leads into signed contracts.",
        30, "deals", p4e, p_mgr_s, p_ace, p4, sal)
    if new:
        _updates(k, [
            (3,  p4s+timedelta(days=4),  "Warm leads converting well"),
            (6,  p4s+timedelta(days=8),  "Referral network paying off"),
            (10, p4s+timedelta(days=13), "Strong pipeline"),
            (15, p4s+timedelta(days=19), "Well ahead at halfway"),
            (19, p4s+timedelta(days=25), "Closing in fast"),
            (23, p4s+timedelta(days=31), "One push left"),
            (27, p4s+timedelta(days=36), "3 left with 22 days - easy finish"),
        ])

    k, new = _kpi("Conduct discovery calls",
        "Run structured discovery calls with qualified prospects.",
        80, "calls", p4e, p_mgr_s, p_onpace, p4, sal)
    if new:
        _updates(k, [
            (7,  p4s+timedelta(days=5),  "Good start - booked well in advance"),
            (14, p4s+timedelta(days=11), "Maintained cadence"),
            (22, p4s+timedelta(days=17), "On track at midpoint"),
            (30, p4s+timedelta(days=23), "Steady as always"),
            (39, p4s+timedelta(days=29), "Consistent week"),
            (46, p4s+timedelta(days=34), "Slightly ahead"),
            (52, p4s+timedelta(days=37), "52 done - 28 remaining, 22 days. Comfortable."),
        ])

    k, new = _kpi("Submit sales proposals",
        "Prepare and submit tailored proposals to qualified prospects.",
        50, "proposals", p4e, p_mgr_s, p_behind, p4, sal)
    if new:
        _updates(k, [
            (1,  p4s+timedelta(days=8),  "Starting slowly - building templates"),
            (3,  p4s+timedelta(days=15), "Templates done but volume still low"),
            (6,  p4s+timedelta(days=22), "Picking up slightly"),
            (9,  p4s+timedelta(days=29), "Not enough - need to push much harder"),
            (12, p4s+timedelta(days=35), "Improved slightly but still far off"),
            (14, p4s+timedelta(days=37), "14 of 50 with 22 days left - very unlikely"),
        ])

    # ── April Demo Campaign (completed) ──────────────────────────────
    p5s = today - timedelta(days=45)
    p5e = today - timedelta(days=5)
    p5, _ = _project("April Demo Campaign",
        "Run product demos for all warm prospects in the April pipeline.",
        p5s, p5e, "completed", p_mgr_s, sal, pin)
    for u in [p_mgr_s, p_great]:
        _member(p5, u)

    k, new = _kpi("Run product demos",
        "Deliver live product demonstrations to qualified prospects.",
        20, "demos", p5e, p_mgr_s, p_great, p5, sal)
    if new:
        _updates(k, [
            (2,  p5s+timedelta(days=6),  "First demos booked and delivered"),
            (5,  p5s+timedelta(days=13), "Getting smoother each time"),
            (9,  p5s+timedelta(days=20), "Very positive feedback from prospects"),
            (13, p5s+timedelta(days=28), "Ahead of schedule"),
            (17, p5s+timedelta(days=36), "Almost done"),
            (22, p5s+timedelta(days=43), "Exceeded target - 22 demos delivered"),
        ])

    # ── Client Success Sprint (active) ────────────────────────────────
    p6s = today - timedelta(days=30)
    p6e = today + timedelta(days=30)
    p6, _ = _project("Client Success Sprint",
        "Onboard new clients, resolve support tickets, and hit satisfaction targets.",
        p6s, p6e, "active", p_mgr_o, ops, pin)
    for u in [p_mgr_o, p_ops1, p_ops2]:
        _member(p6, u)

    k, new = _kpi("Onboard new clients",
        "Complete the full onboarding process for each assigned new client.",
        25, "clients", p6e, p_mgr_o, p_ops1, p6, ops)
    if new:
        _updates(k, [
            (2,  p6s+timedelta(days=4),  "First two onboardings complete"),
            (5,  p6s+timedelta(days=9),  "Streamlined the process"),
            (8,  p6s+timedelta(days=14), "Solid week"),
            (11, p6s+timedelta(days=19), "On track"),
            (14, p6s+timedelta(days=27), "Halfway through, exactly on pace"),
        ])

    k, new = _kpi("Resolve support tickets",
        "Clear assigned support tickets within agreed SLA response times.",
        150, "tickets", p6e, p_mgr_o, p_ops2, p6, ops)
    if new:
        _updates(k, [
            (18,  p6s+timedelta(days=4),  "Strong start - cleared backlog"),
            (35,  p6s+timedelta(days=9),  "High volume week"),
            (55,  p6s+timedelta(days=14), "Consistently above target rate"),
            (78,  p6s+timedelta(days=19), "Over halfway with time to spare"),
            (100, p6s+timedelta(days=23), "100 done - impressive pace"),
            (130, p6s+timedelta(days=28), "Will definitely exceed 150"),
        ])

    conn.commit()
    conn.close()
    print("[OK] Full seed data ensured (Nexus + Pinnacle)", flush=True)


def ensure_test_accounts():
    """
    Create 20 isolated tester accounts (4 per scenario A–E) so each person
    works with their own clean data and cannot affect other testers.

    Scenario A (nex_star_a/b/c/d)  — Employee on track
    Scenario B (nex_risk_a/b/c/d)  — Employee at risk
    Scenario C (nex_done_a/b/c/d)  — Employee, deadline passed
    Scenario D (nex_mgr_a/b/c/d)   — Manager (each gets own mini-company)
    Scenario E (admin_alpha/beta/gamma/delta) — Admin (each gets own mini-company)
    """
    conn = get_conn()
    today = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)

    # ── helpers ──────────────────────────────────────────────────────────────

    def _company(name, code):
        row = conn.execute("SELECT id FROM companies WHERE code=?", (code,)).fetchone()
        if row:
            return row[0]
        conn.execute("INSERT INTO companies (name, code) VALUES (?,?)", (name, code))
        return conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    def _dept(name, cid):
        row = conn.execute(
            "SELECT id FROM departments WHERE name=? AND company_id=?", (name, cid)
        ).fetchone()
        if row:
            return row[0]
        conn.execute("INSERT INTO departments (name, company_id) VALUES (?,?)", (name, cid))
        return conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    def _user(uname, pw, full, role, did, cid):
        row = conn.execute("SELECT id FROM users WHERE username=?", (uname,)).fetchone()
        if row:
            conn.execute(
                "UPDATE users SET password=?,full_name=?,role=?,department_id=?,company_id=?"
                " WHERE username=?",
                (hash_pw(pw), full, role, did, cid, uname)
            )
            return row[0]
        conn.execute(
            "INSERT INTO users (username,password,full_name,role,department_id,company_id)"
            " VALUES (?,?,?,?,?,?)",
            (uname, hash_pw(pw), full, role, did, cid)
        )
        return conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    def _project(name, desc, start, end, status, by, did, cid):
        row = conn.execute(
            "SELECT id FROM projects WHERE name=? AND company_id=? AND created_by=?",
            (name, cid, by)
        ).fetchone()
        if row:
            return row[0], False
        conn.execute(
            "INSERT INTO projects (name,description,start_date,end_date,status,"
            "created_by,department_id,company_id) VALUES (?,?,?,?,?,?,?,?)",
            (name, desc, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"),
             status, by, did, cid)
        )
        return conn.execute("SELECT last_insert_rowid()").fetchone()[0], True

    def _member(pid, uid):
        conn.execute(
            "INSERT OR IGNORE INTO project_members (project_id, user_id) VALUES (?,?)",
            (pid, uid)
        )

    def _kpi(title, desc, target, unit, deadline, by, assigned, pid, did):
        row = conn.execute(
            "SELECT id FROM kpis WHERE title=? AND project_id=? AND assigned_to=?",
            (title, pid, assigned)
        ).fetchone()
        if row:
            return row[0], False
        conn.execute(
            "INSERT INTO kpis (title,description,target_value,unit,deadline,"
            "created_by,assigned_to,project_id,department_id) VALUES (?,?,?,?,?,?,?,?,?)",
            (title, desc, target, unit, deadline.strftime("%Y-%m-%d"),
             by, assigned, pid, did)
        )
        return conn.execute("SELECT last_insert_rowid()").fetchone()[0], True

    def _updates(kid, entries):
        if conn.execute(
            "SELECT COUNT(*) FROM kpi_updates WHERE kpi_id=?", (kid,)
        ).fetchone()[0]:
            return
        for val, dt, note in entries:
            conn.execute(
                "INSERT INTO kpi_updates (kpi_id,value,note,updated_at) VALUES (?,?,?,?)",
                (kid, val, note, dt.strftime("%Y-%m-%d %H:%M:%S"))
            )

    # ── Look up existing Nexus IDs ────────────────────────────────────────────
    nex_row = conn.execute("SELECT id FROM companies WHERE code='NEXUS1'").fetchone()
    if not nex_row:
        conn.close()
        print("[WARNING] Nexus not seeded yet — skipping test accounts", flush=True)
        return
    nex = nex_row[0]
    eng = conn.execute(
        "SELECT id FROM departments WHERE name='Engineering' AND company_id=?", (nex,)
    ).fetchone()[0]
    prd = conn.execute(
        "SELECT id FROM departments WHERE name='Product' AND company_id=?", (nex,)
    ).fetchone()[0]
    n_mgr_e = conn.execute("SELECT id FROM users WHERE username='nex_mgr_e'").fetchone()[0]
    n_mgr_p = conn.execute("SELECT id FROM users WHERE username='nex_mgr_p'").fetchone()[0]

    p1_row = conn.execute(
        "SELECT id FROM projects WHERE name='Q2 Platform Sprint' AND company_id=?", (nex,)
    ).fetchone()
    p3_row = conn.execute(
        "SELECT id FROM projects WHERE name='Q1 Documentation Sprint' AND company_id=?", (nex,)
    ).fetchone()
    if not p1_row or not p3_row:
        conn.close()
        print("[WARNING] Nexus projects not found — skipping test accounts", flush=True)
        return
    p1_id = p1_row[0]
    p3_id = p3_row[0]

    # ── Reference dates ───────────────────────────────────────────────────────
    p1s = today - timedelta(days=45)
    p1e = today + timedelta(days=30)
    p3s = today - timedelta(days=50)
    p3e = today - timedelta(days=6)

    # ── Shared update sequences ───────────────────────────────────────────────
    STAR_UPDATES = [
        (6,  p1s+timedelta(days=4),  "Cleared first batch - strong start"),
        (14, p1s+timedelta(days=10), "Kept the pace up, reviewed design PRs"),
        (23, p1s+timedelta(days=16), "Strong week - big backend batch done"),
        (33, p1s+timedelta(days=22), "Ahead of schedule, helping others"),
        (42, p1s+timedelta(days=29), "Over 70% done, very comfortable"),
        (50, p1s+timedelta(days=36), "Almost there"),
        (55, p1s+timedelta(days=42), "5 left with a month to spare"),
    ]
    RISK_UPDATES = [
        (2,  p1s+timedelta(days=7),  "Still ramping up on the codebase"),
        (5,  p1s+timedelta(days=14), "Slow progress - some blockers"),
        (9,  p1s+timedelta(days=21), "Cleared some easy ones"),
        (13, p1s+timedelta(days=28), "Blocked awaiting third party"),
        (17, p1s+timedelta(days=35), "Unblocked but still far behind"),
        (21, p1s+timedelta(days=41), "Pace not improving enough"),
        (25, p1s+timedelta(days=44), "Need 55 more in 30 days - very unlikely"),
    ]
    DONE_UPDATES = [
        (3,  p3s+timedelta(days=6),  "Started with API docs"),
        (7,  p3s+timedelta(days=13), "Slow going - complex endpoints"),
        (11, p3s+timedelta(days=20), "Behind pace"),
        (16, p3s+timedelta(days=28), "Tried to catch up"),
        (20, p3s+timedelta(days=36), "Still significantly behind"),
        (24, p3s+timedelta(days=43), "Deadline approaching fast"),
        (28, p3s+timedelta(days=49), "Deadline passed - only 28 of 40 pages done"),
    ]

    # ═════════════════════════════════════════════════════════════════════════
    # SCENARIOS A / B / C  — employee accounts in existing Nexus projects
    # ═════════════════════════════════════════════════════════════════════════

    for s in ['a', 'b', 'c', 'd']:
        # Scenario A — Esther (on track)
        uid = _user(f"nex_star_{s}", "emp123", "Esther Ojo", "employee", eng, nex)
        _member(p1_id, uid)
        k, new = _kpi("Complete code reviews",
                      "Review all pull requests assigned during the sprint.",
                      60, "reviews", p1e, n_mgr_e, uid, p1_id, eng)
        if new:
            _updates(k, STAR_UPDATES)

        # Scenario B — Ngozi (at risk)
        uid = _user(f"nex_risk_{s}", "emp123", "Ngozi Ihejirika", "employee", eng, nex)
        _member(p1_id, uid)
        k, new = _kpi("Resolve bug tickets",
                      "Clear all assigned critical and high-priority bugs from the backlog.",
                      80, "bugs", p1e, n_mgr_e, uid, p1_id, eng)
        if new:
            _updates(k, RISK_UPDATES)

        # Scenario C — Bola (deadline passed)
        uid = _user(f"nex_done_{s}", "emp123", "Bola Adeleke", "employee", prd, nex)
        _member(p3_id, uid)
        k, new = _kpi("Write technical documentation",
                      "Complete all developer docs, API guides, and release notes.",
                      40, "pages", p3e, n_mgr_p, uid, p3_id, prd)
        if new:
            _updates(k, DONE_UPDATES)

    # ═════════════════════════════════════════════════════════════════════════
    # SCENARIO D — 4 manager mini-companies (each tester owns their own sprint)
    # ═════════════════════════════════════════════════════════════════════════

    MGR_COS = [
        ("Nexus Engineering A", "MGRA01", "nex_mgr_a"),
        ("Nexus Engineering B", "MGRB02", "nex_mgr_b"),
        ("Nexus Engineering C", "MGRC03", "nex_mgr_c"),
        ("Nexus Engineering D", "MGRD04", "nex_mgr_d"),
    ]
    for cname, ccode, mgr_uname in MGR_COS:
        cid  = _company(cname, ccode)
        dept = _dept("Engineering", cid)

        mgr   = _user(mgr_uname,           "mgr123", "Tunde Bakare",    "manager",  dept, cid)
        star  = _user(f"star_{ccode.lower()}", "emp123", "Esther Ojo",   "employee", dept, cid)
        risk  = _user(f"risk_{ccode.lower()}", "emp123", "Ngozi Ihejirika", "employee", dept, cid)
        femi  = _user(f"femi_{ccode.lower()}", "emp123", "Femi Lawal",   "employee", dept, cid)

        ps = today - timedelta(days=45)
        pe = today + timedelta(days=30)

        proj_id, _ = _project(
            "Q2 Platform Sprint",
            "Deliver core platform features and resolve the critical backlog for Q2 release.",
            ps, pe, "active", mgr, dept, cid
        )
        for uid in [mgr, star, risk, femi]:
            _member(proj_id, uid)

        k1, n1 = _kpi("Complete code reviews",
                      "Review all pull requests assigned during the sprint.",
                      60, "reviews", pe, mgr, star, proj_id, dept)
        if n1:
            _updates(k1, [
                (6,  ps+timedelta(days=4),  "Cleared first batch - strong start"),
                (14, ps+timedelta(days=10), "Kept the pace up, reviewed design PRs"),
                (23, ps+timedelta(days=16), "Strong week - big backend batch done"),
                (33, ps+timedelta(days=22), "Ahead of schedule, helping others"),
                (42, ps+timedelta(days=29), "Over 70% done, very comfortable"),
                (50, ps+timedelta(days=36), "Almost there"),
                (55, ps+timedelta(days=42), "5 left with a month to spare"),
            ])

        k2, n2 = _kpi("Resolve bug tickets",
                      "Clear all assigned critical and high-priority bugs from the backlog.",
                      80, "bugs", pe, mgr, risk, proj_id, dept)
        if n2:
            _updates(k2, [
                (2,  ps+timedelta(days=7),  "Still ramping up on the codebase"),
                (5,  ps+timedelta(days=14), "Slow progress - some blockers"),
                (9,  ps+timedelta(days=21), "Cleared some easy ones"),
                (13, ps+timedelta(days=28), "Blocked awaiting third party"),
                (17, ps+timedelta(days=35), "Unblocked but still far behind"),
                (21, ps+timedelta(days=41), "Pace not improving enough"),
                (25, ps+timedelta(days=44), "Need 55 more in 30 days - very unlikely"),
            ])
        # femi has NO KPI — manager creates "Complete security review" during the test

    # ═════════════════════════════════════════════════════════════════════════
    # SCENARIO E — 4 admin mini-companies (each tester is admin of their own org)
    # ═════════════════════════════════════════════════════════════════════════

    ADM_COS = [
        ("Alpha Solutions Ltd",  "ADMA01", "admin_alpha"),
        ("Beta Solutions Ltd",   "ADMB02", "admin_beta"),
        ("Gamma Solutions Ltd",  "ADMC03", "admin_gamma"),
        ("Delta Solutions Ltd",  "ADMD04", "admin_delta"),
    ]
    for cname, ccode, adm_uname in ADM_COS:
        cid   = _company(cname, ccode)
        dept  = _dept("Engineering", cid)
        _dept("Operations", cid)   # second dept for admin to see — no Customer Success yet

        adm    = _user(adm_uname,                 "admin123", "Sarah Okonkwo",    "admin",    None, cid)
        mgr    = _user(f"mgr_{ccode.lower()}",    "mgr123",   "Tunde Bakare",     "manager",  dept, cid)
        ngozi  = _user(f"ngozi_{ccode.lower()}",  "emp123",   "Ngozi Ihejirika",  "employee", dept, cid)
        femi   = _user(f"femi_{ccode.lower()}",   "emp123",   "Femi Lawal",       "employee", dept, cid)
        esther = _user(f"esther_{ccode.lower()}", "emp123",   "Esther Ojo",       "employee", dept, cid)

        ps = today - timedelta(days=30)
        pe = today + timedelta(days=30)

        proj_id, _ = _project(
            "Q2 Platform Sprint",
            "Deliver core platform features and resolve the critical backlog for Q2 release.",
            ps, pe, "active", mgr, dept, cid
        )
        for uid in [mgr, ngozi, femi, esther]:
            _member(proj_id, uid)

        k1, n1 = _kpi("Complete code reviews",
                      "Review all pull requests assigned during the sprint.",
                      60, "reviews", pe, mgr, esther, proj_id, dept)
        if n1:
            _updates(k1, [
                (6,  ps+timedelta(days=4),  "Strong start - on track"),
                (14, ps+timedelta(days=10), "Consistent pace"),
                (23, ps+timedelta(days=17), "Ahead of schedule"),
                (33, ps+timedelta(days=24), "Comfortable position"),
                (42, ps+timedelta(days=29), "Almost there"),
            ])

        k2, n2 = _kpi("Resolve bug tickets",
                      "Clear all assigned critical and high-priority bugs from the backlog.",
                      80, "bugs", pe, mgr, ngozi, proj_id, dept)
        if n2:
            _updates(k2, [
                (2,  ps+timedelta(days=5),  "Slow start"),
                (5,  ps+timedelta(days=10), "Some blockers encountered"),
                (9,  ps+timedelta(days=17), "Picking up slightly"),
                (13, ps+timedelta(days=24), "Still significantly behind"),
                (17, ps+timedelta(days=29), "Needs urgent support"),
            ])
        # femi has NO KPI — just an employee the admin can view
        # NO "Customer Success" department — admin creates it during the test

    conn.commit()
    conn.close()
    print("[OK] Test accounts ensured (20 isolated tester accounts)", flush=True)
