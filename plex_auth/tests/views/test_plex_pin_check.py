# plex_auth/tests/views/test_plex_pin_check.py

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from plex_auth.utils import PlexAPIError


class TestPlexPinCheckView(TestCase):
    def setUp(self):
        self.client = Client()
        self.User = get_user_model()

    def test_pin_check_missing_pin(self):
        """Test PIN check without providing a PIN ID"""
        response = self.client.get(reverse("plex_auth:check_pin"))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["status"], "error")
        self.assertEqual(response.json()["message"], "No PIN ID provided")

    @patch("plex_auth.utils.PlexOAuth.check_pin")
    def test_pin_check_pending(self, mock_check_pin):
        """Test PIN check when authentication is pending"""
        mock_check_pin.return_value = None  # PlexOAuth returns None when pending

        response = self.client.get(reverse("plex_auth:check_pin"), {"pin_id": "12345"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "pending")

    @patch("plex_auth.utils.PlexOAuth.check_pin")
    @patch("plex_auth.backends.PlexAuthenticationBackend.authenticate")
    def test_pin_check_authenticated(self, mock_authenticate, mock_check_pin):
        """Test PIN check when authentication is successful"""
        # Create test user
        user = self.User.objects.create(
            username="test_user", plex_username="test_user", plex_account_id="12345"
        )

        # Mock successful PIN check
        mock_check_pin.return_value = {
            "authToken": "xyz789",
            "account": {"username": "test_user", "id": "12345"},
        }

        # Mock successful authentication
        mock_authenticate.return_value = user

        response = self.client.get(reverse("plex_auth:check_pin"), {"pin_id": "12345"})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "authenticated")
        self.assertEqual(data["redirect_url"], reverse("core:home"))

    @patch("plex_auth.utils.PlexOAuth.check_pin")
    def test_pin_check_api_error(self, mock_check_pin):
        """Test PIN check when Plex API returns an error"""
        mock_check_pin.side_effect = PlexAPIError("API Error")

        response = self.client.get(reverse("plex_auth:check_pin"), {"pin_id": "12345"})

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["status"], "error")
        self.assertEqual(
            response.json()["message"], "Failed to check authentication status"
        )

    @patch("plex_auth.utils.PlexOAuth.check_pin")
    @patch("plex_auth.backends.PlexAuthenticationBackend.authenticate")
    def test_pin_check_auth_failure(self, mock_authenticate, mock_check_pin):
        """Test PIN check when authentication fails"""
        mock_check_pin.return_value = {
            "authToken": "xyz789",
            "account": {"username": "test_user", "id": "12345"},
        }
        mock_authenticate.return_value = None  # Authentication fails

        response = self.client.get(reverse("plex_auth:check_pin"), {"pin_id": "12345"})

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["status"], "error")
        self.assertEqual(response.json()["message"], "Authentication failed")
