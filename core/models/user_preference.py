# core/models/user_preference.py

import pytz
from django.conf import settings
from django.db import models
from django.utils import timezone


class UserPreference(models.Model):
    """Store user preferences for application settings."""

    TIMEZONE_CHOICES = [(tz, tz) for tz in pytz.common_timezones]

    THEME_CHOICES = [
        ("system", "System"),
        ("light", "Light"),
        ("dark", "Dark"),
    ]

    SYNC_INTERVAL_CHOICES = [
        ("hourly", "Every Hour"),
        ("daily", "Daily"),
        ("weekly", "Weekly"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="preferences"
    )
    timezone = models.CharField(max_length=50, choices=TIMEZONE_CHOICES, default="UTC")
    theme = models.CharField(max_length=10, choices=THEME_CHOICES, default="system")
    auto_sync_enabled = models.BooleanField(default=True)
    sync_interval = models.CharField(
        max_length=10, choices=SYNC_INTERVAL_CHOICES, default="daily"
    )
    notification_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "User Preference"
        verbose_name_plural = "User Preferences"

    def __str__(self):
        return f"Preferences for {self.user.username}"

    def save(self, *args, **kwargs):
        if not self.timezone:
            self.timezone = "UTC"
        super().save(*args, **kwargs)
