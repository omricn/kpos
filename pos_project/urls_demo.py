"""Demo URL configuration.

Identical to pos_project/urls.py but WITHOUT the `oauth2/` Azure-AD (ADFS)
routes — importing django_auth_adfs's URLs requires live ADFS settings and
would crash offline. Plain Django admin login is used instead.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('reports.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
