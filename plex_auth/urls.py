# plex_auth/urls.py

from django.urls import path

from .views import PlexCallbackView, PlexLoginView, PlexLogoutView, PlexPinCheckView

app_name = "plex_auth"

urlpatterns = [
    path("login/", PlexLoginView.as_view(), name="login"),
    path("logout/", PlexLogoutView.as_view(), name="logout"),
    path("callback/", PlexCallbackView.as_view(), name="callback"),
    path("check-pin/", PlexPinCheckView.as_view(), name="check_pin"),
]
