from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class HomeView(TemplateView):
    template_name = "core/home.html"


class MediaView(LoginRequiredMixin, TemplateView):
    template_name = "core/media.html"
    login_url = "plex_auth:login"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add any media-related context here
        return context


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = "core/profile.html"
    login_url = "plex_auth:login"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add any additional profile context here
        return context
