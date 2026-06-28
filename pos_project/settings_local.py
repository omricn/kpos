"""Local development settings — ADFS-free, uses the real pos.db database."""
from .settings_demo import *  # noqa: F401,F403

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'pos.db',  # noqa: F405
    }
}
