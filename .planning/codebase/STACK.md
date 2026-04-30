# Technology Stack

**Analysis Date:** 2026-04-30

## Languages

**Primary:**
- Python 3.x - All backend logic, models, views, parsers

**Secondary:**
- HTML/CSS - Django templates and Kramer-branded UI
- JavaScript - Minimal; Bootstrap bundle only (no custom JS)

## Runtime

**Environment:**
- Python (version managed by system install; no `.python-version` or `.nvmrc` present)

**Package Manager:**
- pip
- Lockfile: Not present (`requirements.txt` only, no `requirements.lock` or `pip.lock`)

## Frameworks

**Core:**
- Django >=4.2,<5.0 - Full web framework: ORM, routing, views, templates, admin

**Build/Dev:**
- None - No build pipeline; static files served directly by Django in dev

## Key Dependencies

**Critical:**
- `django>=4.2,<5.0` - Entire web application framework; ORM, routing, admin interface
- `openpyxl>=3.1` - Excel file parsing; reads `.xlsx`/`.xls` distributor reports

**Infrastructure:**
- SQLite (built into Python stdlib) - Local database; `pos.db` at project root

## Configuration

**Environment:**
- `pos_project/settings.py` - Single settings file, no environment-based splitting
- `DEBUG = True` hardcoded; `ALLOWED_HOSTS = ['*']`; `SECRET_KEY` is a hardcoded dev value
- `.claude/settings.local.json` - Claude Code editor settings (not app config)
- No `.env` file detected

**Build:**
- No build config files (no webpack, vite, etc.)
- `run.bat` - Windows convenience launcher; runs `python manage.py runserver 8001`

## Platform Requirements

**Development:**
- Python with pip
- Windows (has `run.bat`); also runnable on any OS via `python manage.py runserver 8001`
- No Node.js required
- Bootstrap 5.3.3 and Bootstrap Icons 1.11.3 loaded from CDN (jsDelivr) — requires internet in dev

**Production:**
- Planned: Azure deployment with SSO (not yet implemented)
- Current: Local-only; `pos.db` SQLite file at `C:/Users/ocohen/pos/pos.db`

---

*Stack analysis: 2026-04-30*
