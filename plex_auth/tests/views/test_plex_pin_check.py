# plex_auth/tests/views/test_plex_pin_check.py

import json
from unittest.mock import patch

from django.test import Client, TestCase
from django.urls import reverse


class TestPlexPinCheckView(TestCase):
    def setUp(self):
        self.client = Client()

    @patch("plex_auth.utils.PlexOAuth.check_pin")
    def test_pin_check_not_authenticated(self, mock_check_pin):
        """Test PIN check when not authenticated"""
        mock_check_pin.return_value = {"authenticated": False, "auth_token": None}

        response = self.client.get(reverse("plex_auth:check_pin"), {"pin_id": "12345"})

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["status"], "pending")

    @patch("plex_auth.utils.PlexOAuth.check_pin")
    def test_pin_check_authenticated(self, mock_check_pin):
        """Test PIN check when authenticated"""
        mock_check_pin.return_value = {"authenticated": True, "auth_token": "xyz789"}

        response = self.client.get(reverse("plex_auth:check_pin"), {"pin_id": "12345"})

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["status"], "authenticated")
