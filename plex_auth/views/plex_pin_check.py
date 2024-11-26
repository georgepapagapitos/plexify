# plex_auth/views/plex_pin_check.py

import logging

from django.contrib.auth import login
from django.http import HttpRequest, JsonResponse
from django.urls import reverse
from django.views.generic import View

from plex_auth.backends import PlexAuthenticationBackend
from plex_auth.utils import PlexAPIError, PlexOAuth

logger = logging.getLogger(__name__)


class PlexPinCheckView(View):
    """
    Checks the status of a Plex authentication PIN.

    This view is called periodically by the frontend to check if the user
    has completed the Plex authentication process.
    """

    def get(self, request: HttpRequest):
        pin_id = request.GET.get("pin_id")
        if not pin_id:
            logger.warning("Pin check attempted without PIN ID")
            return JsonResponse(
                {"status": "error", "message": "No PIN ID provided"}, status=400
            )

        try:
            logger.debug(f"Checking PIN status: {pin_id}")
            response = PlexOAuth.check_pin(pin_id)

            if not response:
                return JsonResponse({"status": "pending"})

            auth_token = response.get("authToken")
            if not auth_token:
                return JsonResponse({"status": "pending"})

            # Attempt authentication with the token
            logger.info(f"Authenticating user with PIN: {pin_id}")
            backend = PlexAuthenticationBackend()
            user = backend.authenticate(
                request, token=auth_token, account_data=response.get("account", {})
            )

            if not user:
                logger.error("User authentication failed")
                return JsonResponse(
                    {"status": "error", "message": "Authentication failed"}, status=401
                )

            # Log the user in
            login(request, user, backend="plex_auth.backends.PlexAuthenticationBackend")

            logger.info(f"User authenticated successfully: {user.username}")
            return JsonResponse(
                {"status": "authenticated", "redirect_url": reverse("core:home")}
            )

        except PlexAPIError as e:
            logger.error(f"Plex API error during pin check: {str(e)}")
            return JsonResponse(
                {"status": "error", "message": "Failed to check authentication status"},
                status=503,
            )
        except Exception as e:
            logger.exception("Unexpected error during pin check")
            return JsonResponse(
                {"status": "error", "message": "An unexpected error occurred"},
                status=500,
            )
