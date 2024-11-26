# plex_auth/models/server.py

import logging

from django.contrib.auth.models import AbstractUser
from django.db import models

logger = logging.getLogger(__name__)


class PlexServer(models.Model):
    """
    Store connected Plex server information.

    Maintains the relationship between users and their Plex servers, storing
    necessary connection and authentication details for server access.

    Attributes:
        name (str): Display name of the Plex server
        url (str): Base URL for server access
        token (str): Authentication token for this specific server
        machine_identifier (str): Unique identifier assigned by Plex
        version (str): Server software version
        owner (PlexUser): Reference to the user who owns this server
        last_seen (datetime): Timestamp of last successful connection
    """

    name = models.CharField(max_length=255)
    url = models.URLField()
    token = models.CharField(max_length=255)
    machine_identifier = models.CharField(max_length=255, unique=True)
    version = models.CharField(max_length=50)
    owner = models.ForeignKey(
        "plex_auth.PlexUser", on_delete=models.CASCADE, related_name="plex_servers"
    )
    last_seen = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["owner", "machine_identifier"]
        verbose_name = "Plex Server"
        verbose_name_plural = "Plex Servers"

    def __str__(self):
        return f"{self.name} ({self.owner.plex_username})"
