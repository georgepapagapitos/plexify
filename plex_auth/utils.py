import logging
from urllib.parse import urlencode

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class PlexOAuth:
    AUTH_URL = "https://app.plex.tv/auth#?"
    PIN_URL = "https://plex.tv/api/v2/pins"

    @classmethod
    def get_headers(cls):
        return {
            "Accept": "application/json",
            "X-Plex-Product": "Plexify",
            "X-Plex-Client-Identifier": settings.PLEX_CLIENT_IDENTIFIER,
        }

    @classmethod
    def get_pin(cls):
        """Request a new pin from Plex"""
        try:
            # Create data as form fields, not JSON
            data = {
                "strong": "true",
                "X-Plex-Product": "Plexify",
                "X-Plex-Client-Identifier": settings.PLEX_CLIENT_IDENTIFIER,
            }

            # Send the request
            response = requests.post(
                cls.PIN_URL,
                headers=cls.get_headers(),
                data=data,  # Using data instead of json
            )

            logger.info(f"Pin creation response: {response.text}")

            if response.status_code == 201:
                return response.json()
            logger.error(f"Pin creation failed: {response.status_code}")
            return None
        except Exception as e:
            logger.exception("Error getting pin")
            return None

    @classmethod
    def get_auth_url(cls, pin_code):
        """Generate the Plex authentication URL with proper encoding"""
        base_url = "https://app.plex.tv/auth#!"

        # Simplify the params to match working example
        params = {
            "clientID": settings.PLEX_CLIENT_IDENTIFIER,
            "code": pin_code,
            "context[device][product]": "Plexify",
        }

        # Join with regular ampersands
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{base_url}?{query_string}"

    @classmethod
    def check_pin(cls, pin_id):
        """Check the status of a pin"""
        try:
            # Add the headers as query parameters
            params = {
                "X-Plex-Client-Identifier": settings.PLEX_CLIENT_IDENTIFIER,
                "X-Plex-Product": "Plexify",
            }

            response = requests.get(
                f"{cls.PIN_URL}/{pin_id}", headers=cls.get_headers(), params=params
            )

            logger.info(f"Pin check response: {response.text}")

            if response.status_code == 200:
                data = response.json()
                if data.get("authToken"):
                    logger.info("Auth token received!")
                    return data
                logger.debug("No auth token yet")
                return None

            logger.error(f"Pin check failed: {response.status_code}")
            return None
        except Exception as e:
            logger.exception("Error checking pin")
            return None
