# core/models/user_activity.py

from django.conf import settings
from django.db import models
from django.utils import timezone


class UserActivity(models.Model):
    """Track user activities within the application."""

    ACTIVITY_TYPES = [
        ("sync", "Library Sync"),
        ("login", "User Login"),
        ("server", "Server Action"),
        ("settings", "Settings Change"),
        ("other", "Other Activity"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="activities"
    )
    timestamp = models.DateTimeField(default=timezone.now)
    activity_type = models.CharField(
        max_length=20, choices=ACTIVITY_TYPES, default="other"
    )
    description = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "User Activity"
        verbose_name_plural = "User Activities"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["-timestamp"]),
            models.Index(fields=["user", "-timestamp"]),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.activity_type} - {self.timestamp}"

    @classmethod
    def log_activity(cls, user, activity_type, description, metadata=None):
        """
        Convenience method to log a new activity.

        Args:
            user: The user performing the activity
            activity_type: Type of activity from ACTIVITY_TYPES
            description: Human-readable description of the activity
            metadata: Optional JSON-serializable dict of additional data
        """
        return cls.objects.create(
            user=user,
            activity_type=activity_type,
            description=description,
            metadata=metadata or {},
        )
