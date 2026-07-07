"""
Demo-mode authentication for KPos.
Navigating to /demo-login/ creates a superuser session automatically.
No Azure AD, no password required.
"""
from django.contrib.auth import get_user_model, login
from django.shortcuts import redirect
from django.views import View

User = get_user_model()


class DemoLoginView(View):
    def get(self, request):
        user, _ = User.objects.get_or_create(
            username='demo',
            defaults={
                'email': 'demo@demo.com',
                'first_name': 'Demo',
                'last_name': 'User',
                'is_staff': True,
                'is_superuser': True,
            },
        )
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        return redirect('/')
