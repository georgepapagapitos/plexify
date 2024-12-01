# plex_auth/utils/plex_oauth.py

import logging
from typing import Any, Dict, Optional

import requests
from django.conf import settings

from plex_auth.utils.constants import (
    HTTP_CREATED,
    HTTP_OK,
    PLEX_PIN_URL,
    REQUEST_TIMEOUT,
)
from plex_auth.utils.exceptions import PlexManagerError

logger = logging.getLogger(__name__)


class PlexOAuth:
    """
    Handles Plex OAuth authentication flow using pin-based authentication.

    This class provides utility methods for initiating and managing the Plex
    OAuth process, including pin creation, authentication URL generation,
    and pin status checking.
    """

    @classmethod
    def get_headers(cls) -> Dict[str, str]:
        """
        Generate standard headers for Plex API requests.

        Returns:
            Dict containing required Plex API headers
        """

        return {
            "Accept": "application/json",
            "X-Plex-Product": "Plexify",
            "X-Plex-Client-Identifier": settings.PLEX_CLIENT_IDENTIFIER,
        }

    @classmethod
    def get_pin(cls) -> Optional[Dict[str, Any]]:
        """
        Request a new authentication pin from Plex.

        The pin is used to initiate the OAuth flow and track the
        authentication status.

        Returns:
            Dict containing pin data if successful, None otherwise
            Example: {'id': 12345, 'code': 'ABC123', 'expires_in': 1800}

        Raises:
            PlexManagerError: If the API request fails
        """
        try:
            data = {
                "strong": "true",
                "X-Plex-Product": "Plexify",
                "X-Plex-Client-Identifier": settings.PLEX_CLIENT_IDENTIFIER,
            }

            response = requests.post(
                PLEX_PIN_URL,
                headers=cls.get_headers(),
                data=data,  # Using form data as required by Plex API
                timeout=REQUEST_TIMEOUT,
            )

            if response.status_code == HTTP_CREATED:
                pin_data = response.json()
                logger.info(f"Successfully created pin: {pin_data.get('code')}")
                return pin_data

            error_msg = f"Pin creation failed: {response.status_code} - {response.text}"
            logger.error(error_msg)
            raise PlexManagerError(error_msg)

        except requests.RequestException as e:
            logger.exception("Network error during pin creation")
            raise PlexManagerError(f"Failed to contact Plex API: {str(e)}")
        except Exception as e:
            logger.exception("Unexpected error during pin creation")
            raise PlexManagerError(f"Unexpected error: {str(e)}")

    @classmethod
    def get_auth_url(cls, pin_code: str) -> str:
        """
        Generate the Plex authentication URL for the given pin code.

        Args:
            pin_code: The pin code received from get_pin()

        Returns:
            Fully formed authentication URL for redirecting users
        """

        base_url = "https://app.plex.tv/auth#!"

        params = {
            "clientID": settings.PLEX_CLIENT_IDENTIFIER,
            "code": pin_code,
            "context[device][product]": "Plexify",
        }

        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{base_url}?{query_string}"

    @classmethod
    def check_pin(cls, pin_id: str) -> Optional[Dict[str, Any]]:
        """
        Check the authentication status of a pin.

        Args:
            pin_id: The ID of the pin to check (not the pin code)

        Returns:
            Dict containing auth data if authenticated, None if pending
            Example: {'authToken': 'xxx', 'clientIdentifier': 'xxx'}

        Raises:
            PlexManagerError: If the API request fails
        """
        try:
            params = {
                "X-Plex-Client-Identifier": settings.PLEX_CLIENT_IDENTIFIER,
                "X-Plex-Product": "Plexify",
            }

            response = requests.get(
                f"{PLEX_PIN_URL}/{pin_id}",
                headers=cls.get_headers(),
                params=params,
                timeout=REQUEST_TIMEOUT,
            )

            if response.status_code == HTTP_OK:
                data = response.json()
                if auth_token := data.get("authToken"):
                    logger.info("Authentication token received")
                    return data
                logger.debug("Pin check successful but no auth token yet")
                return None

            error_msg = f"Pin check failed: {response.status_code} - {response.text}"
            logger.error(error_msg)
            raise PlexManagerError(error_msg)

        except requests.RequestException as e:
            logger.exception("Network error during pin check")
            raise PlexManagerError(f"Failed to contact Plex API: {str(e)}")
        except Exception as e:
            logger.exception("Unexpected error during pin check")
            raise PlexManagerError(f"Unexpected error: {str(e)}")
