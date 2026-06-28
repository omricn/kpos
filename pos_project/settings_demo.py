"""
Offline demo settings for KPOS Analytics.

Run with:  --settings=pos_project.settings_demo

This module reuses everything from the production settings module and then
overrides only what is unsafe or impossible to run offline:

  * Database  -> local SQLite file (demo.db) instead of Azure-bound Postgres
  * Auth      -> plain Django username/password instead of Azure AD / ADFS SSO
  * Storage   -> local filesystem (no Azure Blob)
  * Secrets   -> harmless placeholders
  * External  -> Claude AI + HTTPS-forcing disabled so nothing reaches the network

Nothing real ships here. See DEMO_README.md and DEMO_NOTES (.demoignore-style
list) for the full inventory of what was stripped.
"""

import os

# Pull in the full production configuration as a baseline.
from .settings import *  # noqa: F401,F403

# ── Core flags ──────────────────────────────────────────────────────────────
DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# Placeholder secret — fine for a throwaway local demo, never for production.
SECRET_KEY = 'demo-only-insecure-key-do-not-use-in-production'

# ── Database: force local SQLite, ignore any DB_HOST / Azure Postgres env ─────
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'demo.db',  # noqa: F405 (BASE_DIR from base settings)
    }
}

# ── Authentication: plain Django auth instead of Azure AD / ADFS SSO ──────────
# Drop the ADFS auth middleware (the SSO login wall) and the HTTPS-forcing
# middleware (which breaks CSRF over plain http on the dev server).
MIDDLEWARE = [
    m for m in MIDDLEWARE  # noqa: F405
    if 'auth_adfs' not in m and 'ForceHttpsMiddleware' not in m
]

# Standard username/password backend only — no ADFS / OAuth backends.
AUTHENTICATION_BACKENDS = ['django.contrib.auth.backends.ModelBackend']

# Drop the ADFS app entirely so nothing tries to load live SSO config offline.
INSTALLED_APPS = [a for a in INSTALLED_APPS if a != 'django_auth_adfs']  # noqa: F405

# Use the demo URLconf, which omits the django_auth_adfs `oauth2/` routes
# (importing them requires live ADFS settings and crashes offline).
ROOT_URLCONF = 'pos_project.urls_demo'

# Send unauthenticated users to the built-in Django login form.
LOGIN_URL = '/admin/login/'
LOGIN_REDIRECT_URL = '/'

# Belt-and-suspenders: ensure no ADFS config object lingers.
AUTH_ADFS = {}

# ── Local filesystem storage (no Azure Blob) ──────────────────────────────────
# MEDIA_ROOT / STATIC_ROOT are already local in base settings; make the storage
# backends explicit so nothing can fall back to a cloud object store.
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

# ── Disable / neutralise external service integrations ────────────────────────
# Claude AI assistant: empty key makes the assistant view return a friendly
# "not configured" message instead of calling the Anthropic API.
CLAUDE_API_KEY = ''

# No real mail server offline — print any email to the console.
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Undo the production proxy/HTTPS assumptions so plain http://localhost works.
USE_X_FORWARDED_HOST = False
SECURE_PROXY_SSL_HEADER = None
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
CSRF_TRUSTED_ORIGINS = ['http://localhost:8000', 'http://127.0.0.1:8000']

# Make sure no Azure / Postgres / ADFS env vars leaking into the process can
# alter the branches in the base settings module on a re-import.
for _var in ('DB_HOST', 'ADFS_TENANT_ID', 'ADFS_CLIENT_ID', 'ADFS_CLIENT_SECRET'):
    os.environ.pop(_var, None)
