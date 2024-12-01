# plex_auth/models/plex_account.py

import logging
from typing import List

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

from plex_auth.utils.exceptions import PlexManagerError
from plex_auth.utils.plex_manager import PlexManager

logger = logging.getLogger(__name__)


class PlexAccount(AbstractUser):
    """
    Custom user model for Plex authentication.
    Extends Django's AbstractUser to store Plex-specific user information and manage
    authentication state.
    """

    plex_username = models.CharField(max_length=255, unique=True)
    plex_token = models.CharField(max_length=255, blank=True)
    plex_account_id = models.CharField(max_length=255, unique=True)
    thumb_url = models.URLField(blank=True)
    last_synced = models.DateTimeField(null=True, blank=True)

    # New fields for enhanced user management
    email_verified = models.BooleanField(default=False)
    subscription_status = models.CharField(
        max_length=20,
        choices=[
            ("active", "Active"),
            ("inactive", "Inactive"),
            ("unknown", "Unknown"),
        ],
        default="unknown",
    )
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)

    backend = "plex_auth.backends.PlexAuthenticationBackend"

    class Meta:
        verbose_name = "Plex User"
        verbose_name_plural = "Plex Users"

    def __str__(self):
        return self.plex_username

    def save(self, *args, **kwargs):
        """Ensure username consistency with plex_username."""
        if self.plex_username and not self.username:
            logger.debug(
                f"Setting username to match plex_username: {self.plex_username}"
            )
            self.username = self.plex_username
        super().save(*args, **kwargs)

    def sync_servers(self) -> List[str]:
        """
        Synchronize Plex servers for this user.

        Returns:
            List[str]: List of machine identifiers for synchronized servers

        Raises:
            PlexManagerError: If there's an error communicating with Plex API
        """
        logger.debug(f"Starting server sync for user {self.plex_username}")
        synchronized_servers = []

        try:
            # Discover available servers
            plex_manager = PlexManager(self.plex_token)
            available_servers = plex_manager.discover_servers()

            # Update or create server records
            for server_data in available_servers:
                server, created = self.plex_servers.update_or_create(
                    machine_identifier=server_data["machine_identifier"],
                    defaults={
                        "name": server_data["name"],
                        "url": server_data["url"],
                        "token": server_data["token"],
                        "version": server_data["version"],
                        "is_owned": server_data.get("owned", False),
                        "is_local": server_data.get("local", False),
                        "status": server_data.get("status", "available"),
                        "last_seen": timezone.now(),
                    },
                )

                if not created:
                    server.update_from_resource(server_data)

                synchronized_servers.append(server.machine_identifier)

            # Mark missing servers as unavailable
            self.plex_servers.exclude(
                machine_identifier__in=synchronized_servers
            ).update(status="unavailable")

            # Update sync timestamp
            self.last_synced = timezone.now()
            self.save(update_fields=["last_synced"])

            logger.info(
                f"Successfully synced {len(available_servers)} servers for user {self.plex_username}"
            )

            return synchronized_servers

        except Exception as e:
            logger.error(
                f"Failed to sync servers for user {self.plex_username}: {str(e)}"
            )
            raise PlexManagerError(f"Failed to sync servers: {str(e)}")

    # def get_preferred_server(self) -> Optional["PlexServer"]:
    def get_preferred_server(self):
        """
        Get the user's preferred server (owned or most recently accessed).
        """
        owned_server = self.plex_servers.filter(
            is_owned=True, status="available"
        ).first()

        if owned_server:
            return owned_server

        return (
            self.plex_servers.filter(status="available").order_by("-last_seen").first()
        )
