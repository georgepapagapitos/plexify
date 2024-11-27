# plex_auth/views/plex_callback.py

import logging

from django.contrib.auth import login
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import View

from plex_auth.backends import PlexAuthenticationBackend
from plex_auth.utils import PlexAPIError, PlexOAuth

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
            response = PlexOAuth.check_pin(pin_id)

            if not response or not response.get("authToken"):
                logger.error("No auth token in callback response")
                return redirect(reverse("plex_auth:login"))

            user = PlexAuthenticationBackend().authenticate(
                request,
                token=response["authToken"],
                account_data=response.get("account", {}),
            )

            if not user:
                logger.error("User authentication failed in callback")
                return redirect(reverse("plex_auth:login"))

            login(request, user, backend="plex_auth.backends.PlexAuthenticationBackend")
            logger.info(f"User authenticated via callback: {user.username}")
            return redirect(reverse("core:home"))

        except PlexAPIError as e:
            logger.error(f"Plex API error in callback: {str(e)}")
            return redirect(reverse("plex_auth:login"))
        except Exception as e:
            logger.exception("Error processing authentication callback")
            return redirect(reverse("plex_auth:login"))
