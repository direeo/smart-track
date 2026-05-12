# SmartTrack KPI System - Railway Deployment Guide

## Executive Summary
SmartTrack KPI is a multi-tenant SaaS application for KPI tracking and forecasting. It combines a FastAPI backend, SQLite database, and machine learning models for predicting KPI completion and employee performance.

---

## 1. Technology Stack

### Backend Framework
- **FastAPI 0.115.0** - Modern async web framework with automatic OpenAPI documentation
- **Uvicorn 0.30.6** - ASGI server for running FastAPI
- **Python 3.11.7** - Programming language runtime

### Frontend
- **Jinja2 3.1.4** - Server-side templating engine for HTML rendering
- **Starlette 0.38.2** - ASGI framework (used by FastAPI as base)
- **Static Files** - CSS and JavaScript served via FastAPI's StaticFiles mount

### Database
- **SQLite (smarttrack.db)** - File-based relational database
  - Location: `./smarttrack.db` in the models directory
  - Multi-tenant support with companies, departments, users, projects, KPIs
  - Foreign key constraints enabled

### Machine Learning
- **scikit-learn 1.5.2** - Random Forest classifier for employee performance prediction
- **statsmodels 0.14.2** - ARIMA time-series forecasting for KPI completion
- **pandas 2.2.2** - Data manipulation and analysis
- **numpy 1.26.4** - Numerical computing

### Middleware & Utilities
- **python-multipart 0.0.9** - Form data parsing
- **SessionMiddleware** - Session management with secret key

---

## 2. Application Architecture

### Core Layers

#### 1. Web Layer (FastAPI)
- Routes defined in `models/app.py`
- Session-based authentication with hashed passwords (SHA256)
- Role-based access control (admin, manager, employee)
- Template rendering via Jinja2

#### 2. Database Layer (`models/database.py`)
- SQLite connection management
- Database initialization with schema creation
- Password hashing utility
- Company code generation for multi-tenancy

#### 3. ML Layer (`models/ml.py`)
- KPI forecasting using ARIMA models
- Employee performance prediction using Random Forest
- Integrates with historical KPI update data

#### 4. Model Files
- `arima_model.py` - ARIMA model training and evaluation
- `rf_model.py` - Random Forest classifier training
- Serialized model: `rf_kpi_model.pkl` (Random Forest binary)

---

## 3. Database Schema

### Tables Structure

#### `companies`
```
id (PK)          INTEGER PRIMARY KEY
name             TEXT NOT NULL
code             TEXT UNIQUE NOT NULL
```
Purpose: Multi-tenant organization container

#### `departments`
```
id (PK)          INTEGER PRIMARY KEY
name             TEXT NOT NULL
company_id (FK)  REFERENCES companies(id)
```
Purpose: Organizational units within companies

#### `users`
```
id (PK)            INTEGER PRIMARY KEY
username           TEXT UNIQUE NOT NULL
password           TEXT NOT NULL (SHA256 hashed)
full_name          TEXT NOT NULL
role               TEXT CHECK(role IN ('admin','manager','employee'))
department_id (FK) REFERENCES departments(id)
company_id (FK)    REFERENCES companies(id)
```
Purpose: System users with role-based access

#### `projects`
```
id (PK)            INTEGER PRIMARY KEY
name               TEXT NOT NULL
description        TEXT
start_date         TEXT NOT NULL
end_date           TEXT NOT NULL
status             TEXT CHECK(status IN ('active','completed','archived'))
created_by (FK)    REFERENCES users(id)
department_id (FK) REFERENCES departments(id)
company_id (FK)    REFERENCES companies(id)
created_at         TEXT DEFAULT (datetime('now'))
```
Purpose: Project container for KPIs

#### `project_members`
```
id (PK)        INTEGER PRIMARY KEY
project_id (FK) REFERENCES projects(id)
user_id (FK)   REFERENCES users(id)
added_at       TEXT DEFAULT (datetime('now'))
UNIQUE(project_id, user_id)
```
Purpose: Project membership assignments

#### `kpis`
```
id (PK)            INTEGER PRIMARY KEY
title              TEXT NOT NULL
description        TEXT
target_value       REAL NOT NULL
unit               TEXT NOT NULL
deadline           TEXT NOT NULL
created_by (FK)    REFERENCES users(id)
assigned_to (FK)   REFERENCES users(id)
project_id (FK)    REFERENCES projects(id)
department_id (FK) REFERENCES departments(id)
created_at         TEXT DEFAULT (datetime('now'))
```
Purpose: Key Performance Indicators

#### `kpi_updates`
```
id (PK)       INTEGER PRIMARY KEY
kpi_id (FK)   REFERENCES kpis(id)
value         REAL NOT NULL
note          TEXT
updated_at    TEXT DEFAULT (datetime('now'))
```
Purpose: Historical tracking of KPI progress

---

## 4. Key Features & Endpoints

### Authentication
- POST `/login` - User login with session creation
- GET `/logout` - Session destruction
- POST `/register` - Company registration and first admin creation

### Role-Based Dashboards
- `/{role}/dashboard` - Role-specific dashboard (admin/manager/employee)

### Admin Functions
- Department management
- Employee management
- KPI setup and monitoring
- System administration

### Manager Functions
- Employee oversight
- Project management
- KPI monitoring within department scope

### Employee Functions
- Project participation
- KPI progress updates
- Personal KPI tracking

### ML Features
- KPI Forecasting (ARIMA)
  - Requires minimum 3 historical updates
  - Predicts completion probability
  - Provides confidence intervals
- Employee Performance Prediction
  - Random Forest classification
  - SHAP explainability outputs in HTML

---

## 5. File Structure for Deployment

### Required Directories
```
models/
├── app.py                      (Main FastAPI app)
├── database.py                 (SQLite schema & connection)
├── ml.py                       (Prediction functions)
├── arima_model.py              (ARIMA training)
├── rf_model.py                 (Random Forest training)
├── seed_data.py                (Data seeding utility)
├── rf_kpi_model.pkl            (Serialized RF model)
├── smarttrack.db               (SQLite database file - created at runtime)
├── static/
│   └── style.css               (CSS styling)
├── templates/                  (19 HTML Jinja2 templates)
│   ├── login.html
│   ├── register.html
│   ├── admin.html
│   ├── manager.html
│   ├── employee.html
│   └── ... (13 more)
├── arima_outputs/              (ARIMA model outputs)
└── rf_outputs/                 (Random Forest outputs)

Root:
├── requirements.txt            (Python dependencies)
├── runtime.txt                 (Python 3.11.7)
├── Procfile                    (Process definition for Railway)
├── railway.json                (Railway platform config)
├── evaluate.py                 (Evaluation script)
├── synthetic_data.py           (Test data generation)
└── data/                        (CSV data files)
```

---

## 6. Startup & Initialization Flow

### On First Deployment
1. **Python 3.11.7 runtime** loads
2. **Dependencies install** from requirements.txt
3. **Procfile command executes**:
   ```
   cd models && uvicorn app:app --host 0.0.0.0 --port $PORT
   ```
4. **FastAPI initialization** (`app = FastAPI()`)
5. **Database initialization** - `init_db()` creates tables if they don't exist
6. **SessionMiddleware** initialized with secret key
7. **Static files & templates** mounted
8. **Random Forest model** loads into memory on first prediction
9. **App listens** on port specified by $PORT environment variable

### Database Persistence
- SQLite database file (`smarttrack.db`) is created in the `models/` directory
- **IMPORTANT**: On Railway, this means data will NOT persist between deployments unless you configure SQLite persistence or migrate to a persistent database (PostgreSQL recommended for production)

---

## 7. Environment Configuration

### Required Environment Variables
- **$PORT** - (Automatically provided by Railway) Port to run on

### Recommended for Production
- `SESSION_SECRET` - Session middleware secret (currently hardcoded: "smarttrack-kpi-secret-2025")
- `DATABASE_URL` - If migrating to PostgreSQL

### Current Hardcoded Values (Should Externalize)
- Session secret: "smarttrack-kpi-secret-2025"
- Database path: `./smarttrack.db` (relative to models/)

---

## 8. Critical Deployment Considerations

### 1. Database Persistence ⚠️
**Issue**: SQLite is file-based. Railway containers are ephemeral - files don't persist between deployments.

**Solutions**:
- **Option A** (Recommended): Migrate to PostgreSQL
  - Update `database.py` to use `psycopg2`
  - Store DATABASE_URL as environment variable
  - Add PostgreSQL plugin in Railway dashboard
  
- **Option B**: Use Railway Volumes
  - Configure persistent volume mount for `models/smarttrack.db`
  - Limited to single instance deployments

- **Option C**: Add backup mechanism
  - Periodically backup to cloud storage (S3)
  - Restore on startup

### 2. Static Assets
- CSS files in `static/` directory are properly mounted
- Ensure `style.css` exists before deployment

### 3. Template Rendering
- 19 HTML templates in `templates/` directory must all be present
- Jinja2 requires templates at runtime (not compiled)

### 4. ML Model Serialization
- `rf_kpi_model.pkl` is required for employee performance predictions
- Must be present in `models/` directory
- Loaded lazily on first prediction request

### 5. Memory & Performance
- ARIMA forecasting (statsmodels) can be memory-intensive with large datasets
- Random Forest prediction is relatively fast
- Recommend: Monitor memory usage if many concurrent users

### 6. Port Configuration
- Uvicorn configured to listen on `0.0.0.0` (all interfaces)
- Port dynamically set via `$PORT` environment variable
- Railway automatically assigns and exposes this

---

## 9. Data Flow

### KPI Forecasting Request
1. User submits KPI progress data via form
2. `predict_kpi()` in `ml.py` receives update history
3. ARIMA model fits to historical data
4. Forecast generated to deadline date
5. Probability of completion calculated
6. Result displayed in UI

### Employee Performance Prediction
1. Employee data collected from HR system
2. Features preprocessed and normalized
3. Random Forest classifier predicts performance category
4. SHAP values computed for explainability
5. Visualization saved to `rf_outputs/fig6_shap_force.html`

---

## 10. Deployment Checklist

- [ ] Python 3.11.7 runtime configured
- [ ] requirements.txt includes all dependencies (currently complete)
- [ ] Procfile specifies correct start command
- [ ] railway.json configured with deploy parameters
- [ ] All template files present in `models/templates/`
- [ ] Static CSS file present at `models/static/style.css`
- [ ] `rf_kpi_model.pkl` present in `models/` (if using RF predictions)
- [ ] Data CSV files present (if using historical data)
- [ ] Session secret key externalized to environment variable (security)
- [ ] Database strategy decided (SQLite vs PostgreSQL)
- [ ] $PORT environment variable properly wired
- [ ] HTTPS/SSL configured at Railway level
- [ ] Domain configured (if using custom domain)
- [ ] Monitoring alerts set up for crashes/memory

---

## 11. Scaling Considerations

### Current Limitations
- Single-process Uvicorn (no load balancing)
- SQLite cannot handle concurrent writes reliably
- No background job queue (tasks run synchronously)

### For Production Scaling
1. **Horizontal Scaling**: Switch to PostgreSQL, use Railway's multi-replica feature
2. **Background Jobs**: Add Celery + Redis for async task processing
3. **Caching**: Add Redis layer for session/query caching
4. **Load Balancing**: Railway handles this automatically with multiple instances
5. **Database Replication**: PostgreSQL with automated backups

---

## 12. Expected Directory Layout at Runtime

```
/app/                              (Railway working directory)
├── models/
│   ├── app.py
│   ├── database.py
│   ├── ml.py
│   ├── smarttrack.db              (Created on first run)
│   ├── rf_kpi_model.pkl           (Loaded at runtime)
│   ├── static/
│   │   └── style.css
│   └── templates/                 (19 HTML files)
├── data/                          (CSV files, read-only)
├── requirements.txt
├── runtime.txt
├── railway.json
├── Procfile
└── [app runs from root, cd to models in Procfile]
```

---

## 13. Build & Deployment Commands

### Railway Deployment
Railway automatically:
1. Detects Python project (via `runtime.txt` and `requirements.txt`)
2. Creates Python 3.11.7 environment
3. Installs dependencies: `pip install -r requirements.txt`
4. Executes Procfile command: `cd models && uvicorn app:app --host 0.0.0.0 --port $PORT`
5. Exposes service via Railway proxy

No additional build steps needed.

---

## 14. Monitoring & Logging

### Application Logs
- Uvicorn outputs request logs to stdout
- FastAPI error logs to stderr
- Railway captures all output

### Key Metrics to Monitor
- HTTP request latency
- Database query performance
- Memory usage (especially during ARIMA fitting)
- Number of active sessions
- ML model prediction latency

### Health Check
- GET `/` returns login page or redirects to dashboard
- Use as health check endpoint
- Add explicit health check: could add `GET /health` endpoint

---

## 15. Security Considerations

### Current Implementation
- ✅ Password hashing with SHA256
- ✅ Session-based authentication
- ✅ Role-based access control
- ✅ SQL injection prevention (parameterized queries)

### Recommended Improvements
- [ ] Migrate from SHA256 to bcrypt/argon2 for password hashing
- [ ] Use environment variables for session secret (currently hardcoded)
- [ ] Add CORS configuration if exposing API
- [ ] Implement rate limiting
- [ ] Add HTTPS enforcement
- [ ] Implement CSRF protection (currently depends on session)
- [ ] Add request validation and sanitization
- [ ] Implement audit logging

---

## Summary for AI/Deployment Tool

**To properly generate Railway deployment files for this system, the tool needs to know:**

1. **Runtime**: Python 3.11.7
2. **Package Manager**: pip with requirements.txt
3. **Process Type**: Single web dyno/service running Uvicorn
4. **Port**: Dynamic ($PORT environment variable)
5. **Working Directory**: Root project directory, but cd to models/ before running app
6. **Database**: SQLite (models/smarttrack.db) - file-based, NOT PERSISTENT without config
7. **ML Models**: Pre-trained Random Forest pickle file required
8. **Static Assets**: CSS and 19 Jinja2 templates required at runtime
9. **Environment Variables**: Minimal (just $PORT), but should externalize session secret
10. **Scaling**: Currently single-process; upgrade to PostgreSQL + multi-replica for production
11. **Health Check**: GET / endpoint (returns login/redirect)
12. **Startup Time**: ~3-5 seconds (includes DB init, template loading)
