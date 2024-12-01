# core/middleware.py

from django.utils import timezone


class TimezoneMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            try:
                user_timezone = request.user.preferences.timezone
                timezone.activate(user_timezone)
            except Exception:
                timezone.deactivate()
        return self.get_response(request)
