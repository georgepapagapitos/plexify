# core/views/media.py

import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

logger = logging.getLogger(__name__)


class MediaView(LoginRequiredMixin, TemplateView):
    """
    Protected view for displaying user's media libraries and content.

    This view requires authentication and shows the user's Plex media content,
    including movies, TV shows, and other media types they have access to.
    """

    template_name = "core/media.html"
    login_url = "plex_auth:login"

    def get_context_data(self, **kwargs):
        """
        Enhance the template context with media-related data.

        Fetches and organizes the user's media content from their connected
        Plex servers and libraries.

        Returns:
            dict: Context dictionary containing:
                - plex_servers: List of user's connected Plex servers
                - libraries: List of available media libraries
                - recent_items: List of recently added media items
                - on_deck: List of items in the user's 'On Deck' section
        """

        context = super().get_context_data(**kwargs)
        user = self.request.user

        logger.debug(f"Fetching media context for user {user.username}")
        try:
            # Get user's connected Plex servers
            plex_servers = user.plex_servers.all()
            context["plex_servers"] = plex_servers

            # Example structure for libraries and media items
            # This should be replaced with actual Plex API calls
            context.update(
                {
                    "libraries": [],  # Fetch from Plex API
                    "recent_items": [],  # Fetch from Plex API
                    "on_deck": [],  # Fetch from Plex API
                }
            )

            logger.info(
                f"Successfully retrieved media context for user {user.username}"
            )

        except Exception as e:
            logger.error(
                f"Error fetching media context for user {user.username}: {str(e)}"
            )
            context["error"] = "Unable to load media content. Please try again later."

        return context
