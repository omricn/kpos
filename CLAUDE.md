# POS Analytics — Project Context

## What this is
A Django web app that replaces the manual process of reviewing Excel POS (Point of Sale) reports from Kramer distributors. Built for Kramer Electronics by Omri Cohen (IT lead).

## Run locally
```
python manage.py runserver 8001
```
Or double-click `run.bat`. Opens at http://localhost:8001. Admin: http://localhost:8001/admin (admin/admin).

## Stack
- Django 4.2 + SQLite (local) — will move to Azure with SSO later
- Bootstrap 5 + Kramer brand purple (#8205B4)
- openpyxl for Excel parsing

## Key files
- `reports/models.py` — Distributor, POSUpload, POSRecord
- `reports/parsers.py` — Excel parsers per distributor (PARSERS dict maps code → function)
- `reports/views.py` — dashboard, distributor_records, upload_file, export_csv
- `reports/forms.py` — UploadForm
- `reports/urls.py` — URL routes
- `templates/base.html` — Kramer-branded navbar
- `static/css/custom.css` — Kramer brand styles
- `pos_project/settings.py` — Django config

## Current data
- CDEV distributor seeded (French, code=`cdev`)
- 66 records imported from April 2026 report

## Planned features (not yet built)
1. **Email polling** — poll a shared mailbox (Microsoft Graph API, same pattern as KDesk) to auto-import Excel attachments from distributors
2. **Analysis views** — Aviva (business owner) will define what analysis/summaries are needed per report
3. **More distributors** — add parser functions in `reports/parsers.py` as each distributor's format is mapped
4. **Azure deployment + SSO** — same stack as KDesk (kdeskregistry.azurecr.io)

## Context from business meeting
- Distributors send weekly/monthly POS reports in non-uniform Excel formats
- Data needed: who goods were sold to, what was sold, quantities, inventory on shelf
- Goal: replace Boomisco external processing (~$3k/month) with internal tool
- Phase 2: Power BI integration + fuzzy customer name matching
