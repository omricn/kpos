import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('SECRET_KEY', 'pos-local-dev-secret-key-change-in-production')
DEBUG = os.environ.get('DEBUG', 'true').lower() == 'true'
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '*').split(',')
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'django_auth_adfs',
    'reports',
]

MIDDLEWARE = [
    'pos_project.middleware.ForceHttpsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_auth_adfs.middleware.LoginRequiredMiddleware',
]

ROOT_URLCONF = 'pos_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

if os.environ.get('DB_HOST'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME', 'kpos'),
            'USER': os.environ.get('DB_USER', 'kpos'),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'HOST': os.environ.get('DB_HOST'),
            'PORT': os.environ.get('DB_PORT', '5432'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'pos.db',
        }
    }

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

TIME_ZONE = 'Asia/Jerusalem'
USE_TZ = True
LANGUAGE_CODE = 'en-us'

# Azure AD SSO — only active when ADFS_TENANT_ID env var is set
if os.environ.get('ADFS_TENANT_ID'):
    AUTHENTICATION_BACKENDS = [
        'django_auth_adfs.backend.AdfsAuthCodeBackend',
    ]
    AUTH_ADFS = {
        'TENANT_ID': os.environ.get('ADFS_TENANT_ID'),
        'CLIENT_ID': os.environ.get('ADFS_CLIENT_ID'),
        'CLIENT_SECRET': os.environ.get('ADFS_CLIENT_SECRET'),
        'RELYING_PARTY_ID': os.environ.get('ADFS_CLIENT_ID'),
        'AUDIENCE': os.environ.get('ADFS_CLIENT_ID'),
        'CLAIM_MAPPING': {
            'first_name': 'given_name',
            'last_name': 'family_name',
            'email': 'upn',
        },
        'USERNAME_CLAIM': 'upn',
        'CREATE_NEW_USERS': True,
    }
    LOGIN_URL = 'django_auth_adfs:login'
    LOGIN_REDIRECT_URL = '/'
