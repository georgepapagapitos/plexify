from django.urls import path

from . import views

app_name = "plex_auth"

urlpatterns = [
    path("login/", views.PlexLoginView.as_view(), name="login"),
    path("logout/", views.PlexLogoutView.as_view(), name="logout"),
    path("callback/", views.PlexCallbackView.as_view(), name="callback"),
    path("check-pin/", views.PlexPinCheckView.as_view(), name="check_pin"),
]
