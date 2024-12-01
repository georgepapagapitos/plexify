# plex_auth/tests/views/test_plex_login.py

from unittest.mock import patch

from django.test import Client, TestCase
from django.urls import reverse

from plex_auth.utils import PlexManagerError


class TestPlexLoginView(TestCase):
    def setUp(self):
        self.client = Client()

    @patch("plex_auth.utils.PlexOAuth.get_pin")
    @patch("plex_auth.utils.PlexOAuth.get_auth_url")
    def test_login_view_success(self, mock_get_auth_url, mock_get_pin):
        """Test successful login view rendering"""
        mock_get_pin.return_value = {
            "id": "ABC123",
            "code": "12345",
            "expires_in": 1800,
        }
        mock_get_auth_url.return_value = "https://plex.tv/auth?code=12345"

        response = self.client.get(reverse("plex_auth:login"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "plex_auth/login.html")

        context = response.context[-1]
        self.assertIn("auth_url", context)
        self.assertEqual(context["auth_url"], "https://plex.tv/auth?code=12345")
        self.assertEqual(context["pin_id"], "ABC123")
        self.assertIsNone(context["error"])

    @patch("plex_auth.utils.PlexOAuth.get_pin")
    def test_login_view_pin_failure(self, mock_get_pin):
        """Test login view when PIN generation fails"""
        mock_get_pin.side_effect = PlexManagerError("PIN generation failed")

        response = self.client.get(reverse("plex_auth:login"))
        self.assertEqual(response.status_code, 200)  # We show error in the template
        self.assertTemplateUsed(response, "plex_auth/login.html")

        context = response.context[-1]
        self.assertEqual(context["error"], "Plex authentication service unavailable")

    @patch("plex_auth.utils.PlexOAuth.get_pin")
    def test_login_view_empty_pin(self, mock_get_pin):
        """Test login view when PIN response is empty"""
        mock_get_pin.return_value = None

        response = self.client.get(reverse("plex_auth:login"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "plex_auth/login.html")

        context = response.context[-1]
        self.assertEqual(context["error"], "Unable to initialize Plex authentication")
