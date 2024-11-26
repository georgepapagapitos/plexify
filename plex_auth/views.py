import logging

from django.contrib.auth import login, logout
from django.http import JsonResponse
from django.shortcuts import redirect
from django.views.generic import TemplateView, View

from plex_auth.backends import PlexAuthenticationBackend
from plex_auth.utils import PlexOAuth

logger = logging.getLogger(__name__)


class PlexLoginView(TemplateView):
    template_name = "plex_auth/login.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get initial pin and create auth URL
        pin_response = PlexOAuth.get_pin()
        if pin_response:
            auth_url = PlexOAuth.get_auth_url(pin_response["code"])
            context["auth_url"] = auth_url
            context["pin_id"] = pin_response["id"]
            # Debug print
            logger.info(f"PIN Response: {pin_response}")
            logger.info(f"Generated auth URL: {auth_url}")
        return context


class PlexLogoutView(View):
    def get(self, request):
        logout(request)
        return redirect("login")


class PlexPinCheckView(View):
    def get(self, request):
        pin_id = request.GET.get("pin_id")
        if not pin_id:
            return JsonResponse({"status": "error", "message": "No pin ID provided"})

        logger.info(f"Checking pin {pin_id}")
        response = PlexOAuth.check_pin(pin_id)

        if response and response.get("authToken"):
            logger.info("Got auth token, attempting user creation/login")
            try:
                backend = PlexAuthenticationBackend()
                user = backend.authenticate(request, token=response["authToken"])
                if user:
                    # Specify the backend when logging in
                    login(
                        request,
                        user,
                        backend="plex_auth.backends.PlexAuthenticationBackend",
                    )
                    return JsonResponse(
                        {"status": "authenticated", "redirect_url": "/"}
                    )
            except Exception as e:
                logger.exception("Error during authentication")
                return JsonResponse(
                    {"status": "error", "message": "Authentication failed"}
                )

        return JsonResponse({"status": "pending"})


class PlexCallbackView(View):
    def get(self, request):
        """Handle the callback from Plex auth"""
        # The PIN ID might be included in the forward URL as a query parameter
        pin_id = request.GET.get("pin_id")

        if pin_id:
            # Check the pin one final time
            response = PlexOAuth.check_pin(pin_id)
            if response and response.get("authToken"):
                user = PlexAuthenticationBackend().authenticate(
                    request,
                    token=response["authToken"],
                    account_data=response.get("account", {}),
                )
                if user:
                    login(request, user)

        # Always redirect to home or another appropriate page
        return redirect("/")
