#!/usr/bin/env python3
"""
Test script to verify app can be imported and started
This simulates what happens on Render when the app starts
"""
import sys
import os

# Set up environment like Render does
os.environ.setdefault('SESSION_SECRET', 'test-secret-key-for-testing')
os.environ.setdefault('DATABASE_PATH', '/tmp/test_smarttrack.db')
os.environ.setdefault('PORT', '8000')
os.environ.setdefault('PYTHONUNBUFFERED', 'true')

print("[TEST] Starting app import test...")
print(f"[TEST] Python version: {sys.version}")
print(f"[TEST] SESSION_SECRET: {'set' if os.getenv('SESSION_SECRET') else 'not set'}")
print(f"[TEST] DATABASE_PATH: {os.getenv('DATABASE_PATH')}")

sys.path.insert(0, 'models')

try:
    print("[*] Importing FastAPI app...")
    from app import app
    print("[OK] FastAPI app imported successfully")
    
    print("[*] Checking app routes...")
    routes = [route.path for route in app.routes]
    print(f"[OK] App has {len(routes)} routes")
    print(f"[ROUTES] Sample routes: {routes[:5]}")
    
    print("[*] Checking database initialization...")
    from database import init_db, get_conn
    init_db()
    print("[OK] Database initialized")
    
    conn = get_conn()
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    conn.close()
    table_names = [t[0] for t in tables]
    print(f"[OK] Database has {len(table_names)} tables: {', '.join(table_names)}")
    
    print("\n" + "="*50)
    print("SUCCESS! App is ready to run on Render")
    print("="*50)
    
except Exception as e:
    print(f"\n[ERROR] {e}", file=sys.stderr)
    import traceback
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)
