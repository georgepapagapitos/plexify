# plex_auth/models/user.py

import logging

from django.contrib.auth.models import AbstractUser
from django.db import models

logger = logging.getLogger(__name__)


class PlexUser(AbstractUser):
    """
    Custom user model for Plex authentication.

    Extends Django's AbstractUser to store Plex-specific user information and manage
    authentication state. This model serves as the primary user model for the application,
    linking Django's authentication system with Plex accounts.

    Attributes:
        plex_username (str): Unique username from Plex account, used for identification
        plex_token (str): Authentication token received from Plex
        plex_account_id (str): Unique identifier assigned by Plex
        thumb_url (str): URL to user's Plex avatar/thumbnail
        last_synced (datetime): Timestamp of last successful sync with Plex
        backend (str): Default authentication backend path
    """

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
        """
        Override save method to ensure username consistency.

        Sets the username field to match plex_username if not already set,
        maintaining consistency between Django and Plex identifiers.
        """
        if self.plex_username and not self.username:
            logger.debug(
                f"Setting username to match plex_username: {self.plex_username}"
            )
            self.username = self.plex_username
        super().save(*args, **kwargs)
