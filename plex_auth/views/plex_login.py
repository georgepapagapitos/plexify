# plex_auth/views/plex_login.py

import logging
from typing import Any, Dict

from django.conf import settings
from django.views.generic import TemplateView

from plex_auth.utils import PlexManagerError, PlexOAuth

logger = logging.getLogger(__name__)


class PlexLoginView(TemplateView):
    """
    Initiates the Plex authentication flow.

    Displays the login page and generates the necessary Plex authentication
    URL and pin for the OAuth process.
    """

    template_name = "plex_auth/login.html"

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        try:
            pin_response = PlexOAuth.get_pin()

            if not pin_response:
                logger.error("Failed to get PIN from Plex")
                context["error"] = "Unable to initialize Plex authentication"
                return context

            # Generate auth URL from the pin code
            auth_url = PlexOAuth.get_auth_url(pin_response["code"])

            context.update(
                {
                    "auth_url": auth_url,
                    "pin_id": pin_response["id"],
                    "error": None,
                    "debug": settings.DEBUG,
                }
            )

            logger.info(f"Generated auth URL for PIN ID: {pin_response['id']}")
            return context

        except PlexManagerError as e:
            logger.error(f"Plex API error during login: {str(e)}")
            context["error"] = "Plex authentication service unavailable"
            return context
        except Exception as e:
            logger.exception("Unexpected error during login initialization")
            context["error"] = "An unexpected error occurred"
            context["debug"] = settings.DEBUG
            return context
