import sqlite3
import hashlib
import random
import string
import os
from pathlib import Path

DB_PATH = Path(os.getenv("DATABASE_PATH", "./smarttrack.db"))


def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


def generate_code(length: int = 6) -> str:
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choices(chars, k=length))


def get_conn():
    # Ensure parent directory exists when we actually need to connect
    try:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"[ERROR] Failed to create database directory {DB_PATH.parent}: {e}")
        raise
    
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS companies (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT NOT NULL,
            code       TEXT UNIQUE NOT NULL
        );

        CREATE TABLE IF NOT EXISTS departments (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT NOT NULL,
            company_id INTEGER REFERENCES companies(id)
        );

        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT UNIQUE NOT NULL,
            password      TEXT NOT NULL,
            full_name     TEXT NOT NULL,
            role          TEXT NOT NULL CHECK(role IN ('admin','manager','employee')),
            department_id INTEGER REFERENCES departments(id),
            company_id    INTEGER NOT NULL REFERENCES companies(id)
        );

        CREATE TABLE IF NOT EXISTS projects (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT NOT NULL,
            description   TEXT,
            start_date    TEXT NOT NULL,
            end_date      TEXT NOT NULL,
            status        TEXT NOT NULL DEFAULT 'active'
                              CHECK(status IN ('active','completed','archived')),
            created_by    INTEGER REFERENCES users(id),
            department_id INTEGER REFERENCES departments(id),
            company_id    INTEGER NOT NULL REFERENCES companies(id),
            created_at    TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS project_members (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL REFERENCES projects(id),
            user_id    INTEGER NOT NULL REFERENCES users(id),
            added_at   TEXT DEFAULT (datetime('now')),
            UNIQUE(project_id, user_id)
        );

        CREATE TABLE IF NOT EXISTS kpis (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            title         TEXT NOT NULL,
            description   TEXT,
            target_value  REAL NOT NULL,
            unit          TEXT NOT NULL,
            deadline      TEXT NOT NULL,
            created_by    INTEGER REFERENCES users(id),
            assigned_to   INTEGER REFERENCES users(id),
            project_id    INTEGER REFERENCES projects(id),
            department_id INTEGER REFERENCES departments(id),
            created_at    TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS kpi_updates (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            kpi_id     INTEGER REFERENCES kpis(id),
            value      REAL NOT NULL,
            note       TEXT,
            updated_at TEXT DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
    conn.close()