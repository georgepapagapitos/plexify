from django.contrib.auth.models import AbstractUser
from django.db import models


class PlexUser(AbstractUser):
    """Custom user model for Plex authentication"""

    plex_username = models.CharField(max_length=255, unique=True)
    plex_token = models.CharField(max_length=255, blank=True)
    plex_account_id = models.CharField(max_length=255, unique=True)
    thumb_url = models.URLField(blank=True)
    last_synced = models.DateTimeField(null=True, blank=True)

    backend = "plex_auth.backends.PlexAuthenticationBackend"

    class Meta:
        verbose_name = "Plex User"
        verbose_name_plural = "Plex Users"

    def __str__(self):
        return self.plex_username

    def save(self, *args, **kwargs):
        # Ensure username matches plex_username
        if self.plex_username and not self.username:
            self.username = self.plex_username
        super().save(*args, **kwargs)


class PlexServer(models.Model):
    """Store connected Plex server information"""

    name = models.CharField(max_length=255)
    url = models.URLField()
    token = models.CharField(max_length=255)
    machine_identifier = models.CharField(max_length=255, unique=True)
    version = models.CharField(max_length=50)
    owner = models.ForeignKey(
        PlexUser, on_delete=models.CASCADE, related_name="plex_servers"
    )
    last_seen = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["owner", "machine_identifier"]
        verbose_name = "Plex Server"
        verbose_name_plural = "Plex Servers"

    def __str__(self):
        return f"{self.name} ({self.owner.plex_username})"
