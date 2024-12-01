# plex_auth/tests/views/test_plex_callback.py

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from plex_auth.utils import PlexManagerError


class TestPlexCallbackView(TestCase):
    def setUp(self):
        self.client = Client()
        self.User = get_user_model()

    def test_callback_no_pin_id(self):
        """Test callback without PIN ID"""
        response = self.client.get(reverse("plex_auth:callback"))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("plex_auth:login"))

    @patch("plex_auth.utils.PlexOAuth.check_pin")
    def test_callback_no_auth_token(self, mock_check_pin):
        """Test callback when pin check returns no auth token"""
        mock_check_pin.return_value = None  # Simulates pending authentication

        response = self.client.get(reverse("plex_auth:callback"), {"pin_id": "12345"})
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("plex_auth:login"))

    @patch("plex_auth.utils.PlexOAuth.check_pin")
    @patch("plex_auth.backends.PlexAuthenticationBackend.authenticate")
    def test_callback_success(self, mock_authenticate, mock_check_pin):
        """Test successful authentication callback"""
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

        response = self.client.get(reverse("plex_auth:callback"), {"pin_id": "12345"})

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("core:home"))

        # Verify authenticate was called with correct args
        mock_authenticate.assert_called_once_with(
            response.wsgi_request,
            token="xyz789",
            account_data={"username": "test_user", "id": "12345"},
        )

    @patch("plex_auth.utils.PlexOAuth.check_pin")
    def test_callback_pin_check_error(self, mock_check_pin):
        """Test callback when pin check fails"""
        mock_check_pin.side_effect = PlexManagerError("PIN check failed")

        response = self.client.get(reverse("plex_auth:callback"), {"pin_id": "12345"})
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("plex_auth:login"))

    @patch("plex_auth.utils.PlexOAuth.check_pin")
    @patch("plex_auth.backends.PlexAuthenticationBackend.authenticate")
    def test_callback_auth_failure(self, mock_authenticate, mock_check_pin):
        """Test callback when authentication fails"""
        mock_check_pin.return_value = {
            "authToken": "xyz789",
            "account": {"username": "test_user", "id": "12345"},
        }
        mock_authenticate.return_value = None  # Authentication fails

        response = self.client.get(reverse("plex_auth:callback"), {"pin_id": "12345"})
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("plex_auth:login"))
