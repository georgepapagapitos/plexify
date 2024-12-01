# plex_auth/views/plex_callback.py

import logging
from typing import Optional

from django.contrib.auth import login
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import View
from plexapi.myplex import MyPlexAccount

from plex_auth.backends import PlexAuthenticationBackend
from plex_auth.utils.exceptions import PlexManagerError
from plex_auth.utils.plex_oauth import PlexOAuth

logger = logging.getLogger(__name__)


class PlexCallbackView(View):
    """
    Handles the callback from Plex after successful authentication.
    This view processes the final step of the OAuth flow when Plex
    redirects back to our application.
    """

    def get(self, request: HttpRequest) -> HttpResponse:
        pin_id = request.GET.get("pin_id")
        if not pin_id:
            logger.warning("Callback received without PIN ID")
            return redirect(reverse("plex_auth:login"))

        try:
            # Get authentication token
            response = PlexOAuth.check_pin(pin_id)
            if not response or not response.get("authToken"):
                logger.error("No auth token in callback response")
                return redirect(reverse("plex_auth:login"))

            # Validate token and get account info directly from Plex
            account_data = self._validate_plex_token(response["authToken"])
            if not account_data:
                logger.error("Could not validate Plex token")
                return redirect(reverse("plex_auth:login"))

            # Authenticate user with validated data
            user = PlexAuthenticationBackend().authenticate(
                request, token=response["authToken"], account_data=account_data
            )

            if not user:
                logger.error("User authentication failed in callback")
                return redirect(reverse("plex_auth:login"))

            login(request, user, backend="plex_auth.backends.PlexAuthenticationBackend")
            logger.info(f"User authenticated via callback: {user.username}")

            return redirect(reverse("core:home"))

        except PlexManagerError as e:
            logger.error(f"Plex API error in callback: {str(e)}")
            return redirect(reverse("plex_auth:login"))
        except Exception as e:
            logger.exception("Error processing authentication callback")
            return redirect(reverse("plex_auth:login"))

    def _validate_plex_token(self, token: str) -> Optional[dict]:
        """
        Validate Plex token by attempting to create a MyPlexAccount instance
        and return normalized account data.
        """
        try:
            account = MyPlexAccount(token=token)
            return {
                "id": account.uuid,
                "username": account.username,
                "email": account.email,
                "thumb": account.thumb,
                "title": account.title,
                "home": account.home,
                "subscription": account.subscription,
                "roles": account.roles,
            }
        except Exception as e:
            logger.error(f"Error validating Plex token: {str(e)}")
            return None
