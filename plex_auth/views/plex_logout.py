# plex_auth/views/plex_logout.py

import logging

from django.contrib.auth import logout
from django.http import HttpRequest
from django.shortcuts import redirect
from django.views.generic import View

logger = logging.getLogger(__name__)


class PlexLogoutView(View):
    """
    Handles user logout and cleanup.
    """

    def get(self, request: HttpRequest):
        if request.user.is_authenticated:
            username = request.user.username
            logout(request)
            logger.info(f"User logged out: {username}")
        return redirect("plex_auth:login")
