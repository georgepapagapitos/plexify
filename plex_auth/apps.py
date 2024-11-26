# plex_auth/apps.py

from django.apps import AppConfig


class PlexAuthConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "plex_auth"
    verbose_name = "Plex Authentication"
