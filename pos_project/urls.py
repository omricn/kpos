from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from pos_project.demo_auth import DemoLoginView

urlpatterns = [
    path('demo-login/', DemoLoginView.as_view(), name='demo-login'),

    path('admin/', admin.site.urls),
    *([path('oauth2/', include('django_auth_adfs.urls'))] if __import__('os').environ.get('ADFS_TENANT_ID') else []),
    path('', include('reports.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
