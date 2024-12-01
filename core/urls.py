# core/urls.py

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from .views import (
    AutoSyncSettingsView,
    HomeView,
    LibrarySyncView,
    LibraryView,
    MediaView,
    PreferenceUpdateView,
    ProfileView,
    TimezoneUpdateView,
    UserActivityView,
)

app_name = "core"

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),
    # Core views
    path("", HomeView.as_view(), name="home"),
    path("media/", MediaView.as_view(), name="media"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path(
        "library/<str:server_id>/<str:library_key>/",
        LibraryView.as_view(),
        name="library",
    ),
    # Auth URLs
    path("auth/", include("plex_auth.urls", namespace="plex_auth")),
    # API endpoints
    path("api/sync/", LibrarySyncView.as_view(), name="api-sync"),
    path(
        "api/preferences/theme/",
        PreferenceUpdateView.as_view(),
        name="api-preferences-theme",
    ),
    path("api/activities/", UserActivityView.as_view(), name="api-activities"),
    path(
        "api/settings/auto-sync/",
        AutoSyncSettingsView.as_view(),
        name="api-auto-sync-settings",
    ),
    path(
        "api/settings/timezone/",
        TimezoneUpdateView.as_view(),
        name="api-timezone-update",
    ),
]
