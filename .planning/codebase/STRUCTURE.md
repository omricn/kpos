# Codebase Structure

**Analysis Date:** 2026-04-30

## Directory Layout

```
pos/                            # Project root
├── manage.py                   # Django management entrypoint
├── run.bat                     # Windows convenience launcher (port 8001)
├── requirements.txt            # Python dependencies (django, openpyxl)
├── pos.db                      # SQLite database (local, not committed to VCS)
├── CLAUDE.md                   # Project context and planned features
│
├── pos_project/                # Django project package (settings, root URLs)
│   ├── settings.py             # All app configuration
│   ├── urls.py                 # Root URL conf (admin + reports app)
│   └── wsgi.py / asgi.py       # (standard Django, not customised)
│
├── reports/                    # Single Django app — all feature code lives here
│   ├── models.py               # Distributor, POSUpload, POSRecord
│   ├── views.py                # dashboard, distributor_records, upload_file, export_csv, distributor_list
│   ├── urls.py                 # App URL patterns (5 routes)
│   ├── forms.py                # UploadForm
│   ├── parsers.py              # Excel parsers + PARSERS registry
│   ├── admin.py                # Admin registrations for all three models
│   └── migrations/
│       └── 0001_initial.py     # Single migration (full schema)
│
├── templates/                  # Django templates (project-level, not app-level)
│   ├── base.html               # Kramer-branded base layout (Bootstrap 5, navbar)
│   └── reports/                # App-specific templates
│       ├── dashboard.html      # Distributor summary cards
│       ├── distributor_list.html
│       ├── records.html        # Filtered records table + stats
│       └── upload.html         # Excel upload form
│
├── static/                     # Static assets (served by Django in dev)
│   ├── css/
│   │   └── custom.css          # Kramer brand variables and component styles
│   └── img/
│       ├── kramer_logo.png
│       └── kramer_logo_footer.png
│
├── media/                      # User-uploaded files (runtime, not committed)
│   └── uploads/                # Uploaded Excel reports land here
│
└── .planning/                  # GSD planning documents
    └── codebase/               # Codebase map documents (this directory)
```

## Directory Purposes

**`pos_project/`:**
- Purpose: Django project configuration package
- Contains: `settings.py`, root `urls.py`
- Key files: `pos_project/settings.py` — single config file for all environments

**`reports/`:**
- Purpose: The entire application — models, views, URLs, parsers, admin
- Contains: All Python feature code
- Key files: `reports/parsers.py` (add new distributors here), `reports/models.py` (schema), `reports/views.py` (all request handlers)

**`templates/`:**
- Purpose: HTML templates; project-level directory (not inside the app)
- Contains: `base.html` shared layout + `reports/` subfolder for app templates
- Key files: `templates/base.html` — all pages extend this

**`static/`:**
- Purpose: CSS and image assets committed to source control
- Contains: `css/custom.css` (Kramer brand), `img/` (logos)

**`media/`:**
- Purpose: Runtime upload storage; auto-created by Django; not committed
- Contains: Excel files uploaded by users

## Key File Locations

**Entry Points:**
- `manage.py`: Django CLI entrypoint; `runserver`, `migrate`, `createsuperuser`
- `run.bat`: Windows double-click launcher

**Configuration:**
- `pos_project/settings.py`: All Django settings (database, static/media paths, timezone, installed apps)
- `requirements.txt`: Python package requirements

**Core Logic:**
- `reports/models.py`: Data models and schema
- `reports/views.py`: All request handling and business logic
- `reports/parsers.py`: Excel parsing — add new distributors here
- `reports/urls.py`: App URL routing

**Templates:**
- `templates/base.html`: Base layout extended by all pages
- `templates/reports/records.html`: Main data view (filtering + table)

## Naming Conventions

**Files:**
- Python modules: `snake_case.py` (e.g., `parsers.py`, `views.py`)
- Templates: `snake_case.html` under `templates/reports/`
- Migrations: `NNNN_description.py` (e.g., `0001_initial.py`)

**Directories:**
- App directory: singular noun matching Django app name (`reports/`)
- Template subdirectory: matches app name (`templates/reports/`)

## Where to Add New Code

**New distributor parser:**
- Implementation: Add `parse_<code>(worksheet)` function to `reports/parsers.py`
- Registration: Add `'<code>': parse_<code>` entry to `PARSERS` dict in `reports/parsers.py:133`
- No other files need changing for a new parser

**New view / page:**
- View function: Add to `reports/views.py`
- URL: Add `path(...)` entry to `reports/urls.py`
- Template: Add `templates/reports/<name>.html` extending `{% extends "base.html" %}`

**New model field:**
- Schema: Add field to appropriate model in `reports/models.py`
- Migration: `python manage.py makemigrations` → new file in `reports/migrations/`

**New form:**
- Add to `reports/forms.py`

**CSS / brand styles:**
- Add to `static/css/custom.css`; use existing CSS variables (`--kramer-purple`, etc.)

**Utilities / helpers:**
- Currently no `utils.py`; shared helpers should go in a new `reports/utils.py`

## Special Directories

**`media/`:**
- Purpose: User-uploaded Excel files at runtime
- Generated: Yes (created by Django on first upload)
- Committed: No (should be in `.gitignore`)

**`pos_project/__pycache__/`, `reports/__pycache__/`, `reports/migrations/__pycache__/`:**
- Purpose: Python bytecode cache
- Generated: Yes
- Committed: No

**`.planning/`:**
- Purpose: GSD planning and codebase map documents
- Generated: By GSD tooling
- Committed: Yes (planning artefacts tracked in VCS)

---

*Structure analysis: 2026-04-30*
