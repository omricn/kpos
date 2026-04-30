<!-- refreshed: 2026-04-30 -->
# Architecture

**Analysis Date:** 2026-04-30

## System Overview

```text
┌─────────────────────────────────────────────────────────────┐
│                     Browser (HTTP)                          │
└──────────────┬──────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────┐
│                  Django URL Router                           │
│  `pos_project/urls.py`  →  `reports/urls.py`                │
└──────┬────────────┬────────────────┬────────────────────────┘
       │            │                │
       ▼            ▼                ▼
┌──────────┐  ┌──────────┐  ┌─────────────────┐
│dashboard │  │distributor│  │  upload_file /   │
│view      │  │_records   │  │  export_csv      │
│          │  │view       │  │  distributor_list│
│`views.py`│  │`views.py` │  │  `views.py`      │
└────┬─────┘  └─────┬─────┘  └────────┬────────┘
     │              │                  │
     │              │         ┌────────▼────────┐
     │              │         │   parsers.py     │
     │              │         │  (openpyxl parse)│
     │              │         └────────┬─────────┘
     │              │                  │
     ▼              ▼                  ▼
┌─────────────────────────────────────────────────────────────┐
│               Django ORM  (`reports/models.py`)             │
│    Distributor  →  POSUpload  →  POSRecord                  │
└─────────────────────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────┐
│              SQLite  (`pos.db`)                             │
└─────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| URL Router | Maps URL patterns to views | `pos_project/urls.py`, `reports/urls.py` |
| Views | HTTP request handling, query logic, response rendering | `reports/views.py` |
| Models | Data schema, ORM queries, business helpers | `reports/models.py` |
| Parsers | Distributor-specific Excel-to-dict translation | `reports/parsers.py` |
| Forms | Upload form definition and validation | `reports/forms.py` |
| Admin | Django admin registration for all three models | `reports/admin.py` |
| Templates | HTML rendering with Bootstrap 5 | `templates/base.html`, `templates/reports/` |
| Settings | All app configuration | `pos_project/settings.py` |

## Pattern Overview

**Overall:** Standard Django MTV (Model-Template-View) — single Django app named `reports` inside project `pos_project`.

**Key Characteristics:**
- No service layer; business logic lives directly in views
- No REST API; all responses are full HTML renders or file downloads (CSV)
- Parser registry pattern for extensible distributor format support
- `bulk_create` for performant batch record import

## Layers

**URL Layer:**
- Purpose: Route incoming HTTP requests to view functions
- Location: `pos_project/urls.py` (project root), `reports/urls.py` (app routes)
- Contains: `urlpatterns` lists
- Depends on: Views
- Used by: Django request cycle

**View Layer:**
- Purpose: Handle requests, apply filters, aggregate stats, render templates or return responses
- Location: `reports/views.py`
- Contains: `dashboard`, `distributor_records`, `upload_file`, `export_csv`, `distributor_list`
- Depends on: Models, Forms, Parsers
- Used by: URL layer

**Model Layer:**
- Purpose: Define database schema and provide query helpers
- Location: `reports/models.py`
- Contains: `Distributor`, `POSUpload`, `POSRecord`
- Depends on: Django ORM, SQLite
- Used by: Views, Admin, Forms

**Parser Layer:**
- Purpose: Translate raw openpyxl worksheet rows into dicts matching `POSRecord` field names
- Location: `reports/parsers.py`
- Contains: `parse_cdev`, type-coercion helpers (`_to_str`, `_to_decimal`, `_to_int`, `_to_date`, `_to_post_code`), `PARSERS` registry dict, `get_parser` lookup
- Depends on: openpyxl (worksheet objects passed in from views)
- Used by: `upload_file` view only

**Form Layer:**
- Purpose: Validate file upload inputs
- Location: `reports/forms.py`
- Contains: `UploadForm` (distributor choice, report period, file, replace flag, notes)
- Depends on: Models (`Distributor` queryset)
- Used by: `upload_file` view

**Template Layer:**
- Purpose: HTML presentation
- Location: `templates/base.html` (base layout), `templates/reports/dashboard.html`, `templates/reports/records.html`, `templates/reports/upload.html`, `templates/reports/distributor_list.html`
- Contains: Kramer-branded Bootstrap 5 layouts
- Depends on: `static/css/custom.css`, CDN Bootstrap/Icons
- Used by: Views via `render()`

## Data Flow

### Excel Upload Flow

1. User submits `UploadForm` via POST to `/upload/` — `upload_file` view (`reports/views.py:100`)
2. `get_parser(distributor.code)` looks up function from `PARSERS` dict (`reports/parsers.py:138`)
3. `openpyxl.load_workbook(excel_file, data_only=True)` opens the file; parser iterates rows from row 2 (`reports/parsers.py:108`)
4. Parser returns `list[dict]` with keys matching `POSRecord` field names
5. Optional: `POSRecord.objects.filter(distributor=distributor).delete()` if replace flag set
6. `POSUpload` record created, then `POSRecord.objects.bulk_create(bulk_records)` (`reports/views.py:131-143`)
7. Redirect to `distributor_records` view for that distributor

### Dashboard / Read Flow

1. `GET /` → `dashboard` view aggregates per-distributor stats via Django ORM `aggregate()` (`reports/views.py:14`)
2. `GET /distributor/<pk>/` → `distributor_records` applies GET-param filters (`q`, `date_from`, `date_to`, `category`, `upload`) via chained `QuerySet.filter()` calls
3. Template renders filtered records table; no pagination implemented

### CSV Export Flow

1. `GET /distributor/<pk>/export/` → `export_csv` applies same filter params as records view
2. Returns `HttpResponse` with `content_type='text/csv'` and `Content-Disposition` attachment header
3. Writes rows directly to response using `csv.writer`

**State Management:**
- No client-side state; all state is database-backed
- Filter state passed as GET query parameters; re-applied on each request

## Key Abstractions

**PARSERS Registry:**
- Purpose: Maps distributor code strings to parser functions; decouples format knowledge from upload logic
- Location: `reports/parsers.py:133`
- Pattern: `PARSERS = {'cdev': parse_cdev}` — add new distributors by adding key/function pairs here

**POSRecord (flat denormalised record):**
- Purpose: Single table holding all sales line data regardless of distributor; nullable fields accommodate format variation
- Location: `reports/models.py:39`
- Pattern: All 26 distributor fields stored flat; product hierarchy encoded as `product_level_1/2/3`

## Entry Points

**Web application:**
- Location: `manage.py` (Django management entrypoint)
- Triggers: `python manage.py runserver 8001` or `run.bat`
- Responsibilities: Bootstraps Django, serves HTTP on port 8001

**Root URL:**
- Location: `pos_project/urls.py`
- Triggers: All HTTP requests
- Responsibilities: Routes `/admin/` to Django admin, everything else to `reports.urls`

## Architectural Constraints

- **Authentication:** No login required on any view — all pages are publicly accessible. Django admin at `/admin/` uses built-in session auth.
- **Threading:** Django dev server is single-threaded by default. No async views; no Celery or task queues.
- **Global state:** `PARSERS` dict in `reports/parsers.py` is module-level; functionally read-only after import.
- **No pagination:** `distributor_records` view returns all matching records — will degrade with large datasets.
- **Circular imports:** None detected; imports flow one direction (urls → views → models/forms/parsers).

## Anti-Patterns

### Filter logic duplicated between views

**What happens:** The query filter block (q, date_from, date_to, category) is copy-pasted between `distributor_records` and `export_csv` in `reports/views.py`.
**Why it's wrong:** Any change to filtering logic must be made in two places; they can diverge silently.
**Do this instead:** Extract a `apply_record_filters(queryset, request)` helper function in `reports/views.py` and call it from both views.

### No authentication on any view

**What happens:** All five views in `reports/views.py` are accessible without login.
**Why it's wrong:** Any user with network access can view, upload, and export sensitive distributor sales data.
**Do this instead:** Add `@login_required` decorator to all views; configure `LOGIN_URL` in settings.

## Error Handling

**Strategy:** Django `messages` framework for user-facing errors on upload; bare `except Exception` on Excel parse failure.

**Patterns:**
- Parser not found → `messages.error()` + re-render upload form (`reports/views.py:112`)
- Excel parse failure → `messages.error()` with exception message + re-render (`reports/views.py:119`)
- No rows parsed → `messages.error()` + re-render (`reports/views.py:124`)
- No try/except in read views; ORM errors surface as 500

## Cross-Cutting Concerns

**Logging:** None beyond Django default console output; no structured logging configured.
**Validation:** File input validated via Django `UploadForm`; row-level data coerced with silent `None` fallback in parser helpers.
**Authentication:** Not implemented (see Anti-Patterns above).

---

*Architecture analysis: 2026-04-30*
