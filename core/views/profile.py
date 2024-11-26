# core/views/profile.py

import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.views.generic import TemplateView

logger = logging.getLogger(__name__)


class ProfileView(LoginRequiredMixin, TemplateView):
    """
    Protected view for user profile management.

    Displays user information, preferences, and settings for their
    Plex integration and application experience.
    """

    template_name = "core/profile.html"
    login_url = "plex_auth:login"

    def get_context_data(self, **kwargs):
        """
        Enhance the template context with user profile data.

        Retrieves and organizes user's profile information, preferences,
        and Plex account details.

        Returns:
            dict: Context dictionary containing:
                - user_info: Basic user information
                - plex_info: Plex account details
                - preferences: User's application preferences
                - servers: Connected Plex servers
        """

        context = super().get_context_data(**kwargs)
        user = self.request.user

        logger.debug(f"Fetching profile context for user {user.username}")

        try:
            # Get servers and add their status
            servers = user.plex_servers.all()
            for server in servers:
                # A server is considered active if seen in last 5 minutes
                time_diff = timezone.now() - server.last_seen
                server.is_active = time_diff.total_seconds() < 300  # 5 minutes

            context.update(
                {
                    "user_info": {
                        "username": user.plex_username,
                        "email": user.email,
                        "date_joined": user.date_joined,
                        "last_login": user.last_login,
                    },
                    "plex_info": {
                        "account_id": user.plex_account_id,
                        "thumb_url": user.thumb_url,
                        "last_synced": user.last_synced,
                    },
                    "servers": servers,
                }
            )

            logger.info(
                f"Successfully retrieved profile context for user {user.username}"
            )

        except Exception as e:
            logger.error(
                f"Error fetching profile context for user {user.username}: {str(e)}"
            )
            context["error"] = (
                "Unable to load profile information. Please try again later."
            )

        return context
