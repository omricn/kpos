# External Integrations

**Analysis Date:** 2026-04-30

## APIs & External Services

**CDN (Frontend assets only):**
- jsDelivr CDN - Delivers Bootstrap 5.3.3 CSS/JS and Bootstrap Icons 1.11.3
  - Loaded in: `templates/base.html` (lines 7-8, 67)
  - No API key required; public CDN
  - Risk: Dev and prod both depend on CDN availability

**Planned (not yet implemented):**
- Microsoft Graph API - Email polling of a shared mailbox to auto-import Excel attachments
  - Pattern: same approach as internal "KDesk" tool
  - Trigger: distributors send reports as email attachments
  - No code exists yet; noted in `CLAUDE.md` as Phase 2

## Data Storage

**Databases:**
- SQLite (local file)
  - File path: `pos.db` at project root (`BASE_DIR / 'pos.db'` in `pos_project/settings.py`)
  - Client: Django ORM (no third-party ORM)
  - No connection string env var; path is hardcoded in settings

**File Storage:**
- Local filesystem only
  - Uploaded Excel files stored at `media/uploads/` (Django `MEDIA_ROOT`)
  - Served via Django dev server at `/media/`
  - No cloud object storage (S3, Azure Blob, etc.) currently configured

**Caching:**
- None; no cache backend configured

## Authentication & Identity

**Auth Provider:**
- Django built-in auth (`django.contrib.auth`)
  - Single superuser account: `admin / admin` (dev only)
  - No login required for any view — all views are publicly accessible without authentication
  - Planned: Azure SSO (same pattern as KDesk deployment)

## Monitoring & Observability

**Error Tracking:**
- None; no Sentry, Rollbar, or equivalent configured

**Logs:**
- Django default console logging only; no structured log config in `settings.py`

## CI/CD & Deployment

**Hosting:**
- Current: Local only (Windows workstation, port 8001)
- Planned: Azure Container Registry (`kdeskregistry.azurecr.io`) — not yet implemented

**CI Pipeline:**
- None; no GitHub Actions, Azure DevOps pipelines, or other CI configured

## Environment Configuration

**Required env vars:**
- None currently required; all config is hardcoded in `pos_project/settings.py`
- Production will require: `SECRET_KEY`, database connection string, Azure SSO credentials

**Secrets location:**
- Dev: hardcoded `SECRET_KEY` in `pos_project/settings.py` (line 6) — must be changed before any deployment
- No `.env` file present

## Webhooks & Callbacks

**Incoming:**
- None currently implemented

**Outgoing:**
- None currently implemented

---

*Integration audit: 2026-04-30*
