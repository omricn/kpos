# Running KPos Locally (Demo Mode)

**Stack:** Django · SQLite (local) / PostgreSQL (production) · Anthropic Claude API

## Prerequisites
- Python 3.11+

## Quick start

```bash
git clone https://github.com/omricn/kpos.git
cd kpos

pip install -r requirements.txt

cp .env.example .env
# Optionally add CLAUDE_API_KEY for the AI assistant feature

python manage.py migrate
python manage.py runserver

open http://localhost:8000/demo-login/
```

You'll be logged in automatically as demo admin — no Azure AD needed.
Uses SQLite by default — no database installation required.

## What works in demo mode
- Upload POS Excel files and explore sales analytics
- Distributor/customer/product breakdowns
- VIR rebates module
- AI assistant (add `CLAUDE_API_KEY` to `.env`)

## What's mocked
- Azure AD SSO → replaced by `/demo-login/` auto-login
- PostgreSQL → SQLite (data resets on `python manage.py flush`)
