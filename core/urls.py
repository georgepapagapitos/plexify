# core/urls.py

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from .views import HomeView, MediaView, ProfileView

app_name = "core"

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),
    # Core views
    path("", HomeView.as_view(), name="home"),
    path("media/", MediaView.as_view(), name="media"),
    path("profile/", ProfileView.as_view(), name="profile"),
    # Auth URLs
    path("auth/", include("plex_auth.urls", namespace="plex_auth")),
]

if settings.DEBUG:
    urlpatterns += [
        path("__debug__/", include("debug_toolbar.urls")),
    ]
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
