# plex_auth/models/plex_server_connection.py

import logging
from typing import List
from urllib.parse import urlparse

from django.db import models
from django.utils import timezone

logger = logging.getLogger(__name__)


class PlexServerConnection(models.Model):
    """
    Store connected Plex server information.
    Maintains the relationship between users and their Plex servers, storing
    necessary connection and authentication details for server access.
    """

    name = models.CharField(max_length=255)
    url = models.URLField()
    # Store alternative connection URLs
    local_url = models.URLField(blank=True)
    direct_url = models.URLField(blank=True)
    token = models.CharField(max_length=255)
    machine_identifier = models.CharField(max_length=255, unique=True)
    version = models.CharField(max_length=50)
    owner = models.ForeignKey(
        "plex_auth.PlexAccount", on_delete=models.CASCADE, related_name="plex_servers"
    )
    last_seen = models.DateTimeField(auto_now=True)
    # Server management fields
    is_owned = models.BooleanField(default=False)
    is_local = models.BooleanField(default=False)
    status = models.CharField(
        max_length=20,
        choices=[
            ("available", "Available"),
            ("unavailable", "Unavailable"),
            ("unreachable", "Unreachable"),
        ],
        default="available",
    )
    last_connection_error = models.TextField(blank=True)

    class Meta:
        unique_together = ["owner", "machine_identifier"]
        verbose_name = "Plex Server"
        verbose_name_plural = "Plex Servers"

    def __str__(self):
        return f"{self.name} ({self.owner.plex_username})"

    def update_from_resource(self, server_data: dict) -> None:
        """Update server information from Plex API response."""
        self.name = server_data["name"]
        self.url = server_data["url"]
        self.version = server_data["version"]
        self.is_owned = server_data.get("owned", False)
        self.is_local = server_data.get("local", False)
        self.status = server_data.get("status", "available")
        self.last_seen = timezone.now()

        # Automatically set up alternative URLs
        if "plex.direct" in self.url:
            try:
                ip = self.url.split("://")[1].split(".")[0].replace("-", ".")
                self.local_url = f"http://{ip}:32400"
                self.direct_url = f"https://{ip}:32400"
                logger.debug(
                    f"Set alternative URLs for {self.name}: local={self.local_url}, direct={self.direct_url}"
                )
            except Exception as e:
                logger.error(f"Error setting alternative URLs: {e}")

        self.save()

    def update_connection_urls(
        self, claimed_url: str = None, direct_url: str = None, local_url: str = None
    ) -> None:
        """Update server URLs and save if any have changed."""
        changed = False

        if claimed_url and claimed_url != self.url:
            self.url = claimed_url
            changed = True

        if direct_url and direct_url != self.direct_url:
            self.direct_url = direct_url
            changed = True

        if local_url and local_url != self.local_url:
            self.local_url = local_url
            changed = True

        if changed:
            self.save(update_fields=["url", "direct_url", "local_url"])

    def get_connection_urls(self) -> List[str]:
        """Get all available connection URLs."""
        urls = []
        if self.url:
            urls.append(self.url)
        if self.direct_url:
            urls.append(self.direct_url)
        if self.local_url:
            urls.append(self.local_url)
        return urls

    def mark_unreachable(self, error_message: str) -> None:
        """Mark server as temporarily unreachable with error message."""
        logger.warning(f"Marking server {self.name} as unreachable: {error_message}")
        self.status = "unreachable"
        self.last_connection_error = error_message
        self.save(update_fields=["status", "last_connection_error"])

    def mark_available(self) -> None:
        """Mark server as available and clear error message."""
        logger.info(f"Marking server {self.name} as available")
        self.status = "available"
        self.last_connection_error = ""  # Clear any previous error
        self.save(update_fields=["status", "last_connection_error"])

    def mark_unavailable(self) -> None:
        """Mark server as unavailable (offline but expected)."""
        logger.info(f"Marking server {self.name} as unavailable")
        self.status = "unavailable"
        self.save(update_fields=["status"])

    def update_connection_status(
        self, available: bool, error_message: str = ""
    ) -> None:
        """
        Update server connection status.

        Args:
            available: Whether the server is available
            error_message: Optional error message if server is unavailable
        """
        if available:
            self.mark_available()
        else:
            self.mark_unreachable(error_message)
