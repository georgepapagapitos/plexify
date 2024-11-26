# plex_auth/tests/views/test_plex_logout.py

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse


class TestPlexLogoutView(TestCase):
    def setUp(self):
        self.client = Client()
        self.User = get_user_model()
        self.user = self.User.objects.create_user(
            username="test_user", password="test_pass"
        )

    def test_logout_success(self):
        """Test successful logout"""
        self.client.login(username="test_user", password="test_pass")

        response = self.client.get(reverse("plex_auth:logout"))

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("plex_auth:login"))
