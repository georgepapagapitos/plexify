# plex_auth/utils/plex_api.py

import logging

import requests
from django.conf import settings
from django.utils import timezone

from plex_auth.utils.constants import PLEX_RESOURCES_URL, REQUEST_TIMEOUT
from plex_auth.utils.exceptions import PlexAPIError

logger = logging.getLogger(__name__)


class PlexAPI:
    """
    Utility class for interacting with the Plex API.
    Handles server discovery and synchronization.
    """

    def __init__(self, plex_token: str):
        """Initialize PlexAPI with user's authentication token"""
        self.plex_token = plex_token
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json",
                "X-Plex-Token": plex_token,
                "X-Plex-Client-Identifier": settings.PLEX_CLIENT_IDENTIFIER,
                "X-Plex-Product": "Plexify",
                "X-Plex-Version": "1.0",
            }
        )

    def discover_servers(self):
        """
        Fetch available Plex servers from the Plex API.

        Returns:
            list: List of dictionaries containing server information

        Raises:
            PlexAPIError: If there's an error communicating with Plex API
        """
        try:
            response = self.session.get(
                PLEX_RESOURCES_URL,
                params={"includeHttps": 1, "includeRelay": 1},
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()

            servers = []
            for resource in response.json():
                if resource.get("product") == "Plex Media Server":
                    connections = resource.get("connections", [])
                    server_url = next(
                        (
                            conn["uri"]
                            for conn in connections
                            if conn.get("local") == 0
                        ),  # Prefer remote connections
                        connections[0]["uri"] if connections else None,
                    )

                    if server_url:
                        servers.append(
                            {
                                "name": resource["name"],
                                "url": server_url,
                                "machine_identifier": resource["clientIdentifier"],
                                "version": resource.get("productVersion", ""),
                                "token": self.plex_token,
                            }
                        )

            return servers

        except requests.exceptions.RequestException as e:
            logger.error(f"Error discovering Plex servers: {str(e)}")
            raise PlexAPIError(f"Failed to discover Plex servers: {str(e)}")
