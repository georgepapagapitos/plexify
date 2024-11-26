# plex_auth/tests/views/test_plex_callback.py

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse


class TestPlexCallbackView(TestCase):
    def setUp(self):
        self.client = Client()
        self.User = get_user_model()

    def test_callback_missing_token(self):
        """Test callback without auth token"""
        session = self.client.session
        session["pin_id"] = "12345"
        session.save()

        response = self.client.get(reverse("plex_auth:callback"))

        self.assertEqual(response.status_code, 400)

    @patch("plex_auth.backends.PlexAuthenticationBackend.authenticate")
    def test_callback_success(self, mock_authenticate):
        """Test successful authentication callback"""
        user = self.User.objects.create(
            username="test_user", plex_username="test_user", plex_account_id="12345"
        )

        session = self.client.session
        session["pin_id"] = "12345"
        session.save()

        mock_authenticate.return_value = user

        response = self.client.get(
            reverse("plex_auth:callback"), {"auth_token": "xyz789"}
        )

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, "/")
