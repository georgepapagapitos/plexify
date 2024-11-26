# core/views/home.py

import logging

from django.views.generic import TemplateView

logger = logging.getLogger(__name__)


class HomeView(TemplateView):
    """
    Home page view for the application.

    Displays the landing page with general information about the application
    and calls-to-action for both authenticated and unauthenticated users.
    """

    template_name = "core/home.html"

    def get_context_data(self, **kwargs):
        """
        Enhance the template context with additional data.

        Returns:
            dict: Context dictionary containing:
                - is_authenticated: Boolean indicating user authentication status
                - username: User's display name if authenticated
        """

        context = super().get_context_data(**kwargs)

        if self.request.user.is_authenticated:
            logger.debug(
                f"Authenticated user {self.request.user.username} accessing home page"
            )
            context.update(
                {"username": self.request.user.plex_username, "is_authenticated": True}
            )
        else:
            logger.debug("Anonymous user accessing home page")
            context["is_authenticated"] = False

        return context
