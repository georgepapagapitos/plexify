# plex_auth/tests/views/test_plex_login.py

from unittest.mock import patch

from django.test import Client, TestCase
from django.urls import reverse

from plex_auth.utils import PlexAPIError


class TestPlexLoginView(TestCase):
    def setUp(self):
        self.client = Client()

    @patch("plex_auth.utils.PlexOAuth.get_pin")
    @patch("plex_auth.utils.PlexOAuth.get_auth_url")
    def test_login_view_success(self, mock_get_auth_url, mock_get_pin):
        """Test successful login view rendering"""
        mock_get_pin.return_value = ("12345", "ABC123")
        mock_get_auth_url.return_value = "https://plex.tv/auth?code=ABC123"

        response = self.client.get(reverse("plex_auth:login"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "plex_auth/login.html")
        self.assertIn("auth_url", response.context[-1])
        self.assertIn("pin_id", response.context[-1])

    @patch("plex_auth.utils.PlexOAuth.get_pin")
    def test_login_view_pin_failure(self, mock_get_pin):
        """Test login view when PIN generation fails"""
        mock_get_pin.side_effect = PlexAPIError("PIN generation failed")

        response = self.client.get(reverse("plex_auth:login"))

        self.assertEqual(response.status_code, 500)
        self.assertTemplateUsed(response, "plex_auth/error.html")
