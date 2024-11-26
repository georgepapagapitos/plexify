# plex_auth/tests/models/test_plex_user.py

from django.db import IntegrityError
from django.test import TestCase

from plex_auth.models import PlexUser


class PlexUserModelTests(TestCase):
    """Test suite for the PlexUser model"""

    def setUp(self):
        """Create a basic user for tests"""
        self.user_data = {
            "plex_username": "testuser",
            "plex_token": "test-token-123",
            "plex_account_id": "test-account-123",
            "email": "test@example.com",
            "thumb_url": "https://plex.tv/users/avatar/testuser",
        }
        self.user = PlexUser.objects.create(**self.user_data)

    def test_create_user(self):
        """Test basic user creation"""
        self.assertEqual(self.user.plex_username, "testuser")
        self.assertEqual(self.user.username, "testuser")  # Check username sync
        self.assertEqual(self.user.plex_token, "test-token-123")
        self.assertEqual(self.user.plex_account_id, "test-account-123")

    def test_username_sync(self):
        """Test that plex_username syncs to username field"""
        new_user = PlexUser.objects.create(
            plex_username="newuser", plex_account_id="new-account-456"
        )
        self.assertEqual(new_user.username, "newuser")

    def test_unique_plex_username(self):
        """Test that duplicate plex_usernames are not allowed"""
        with self.assertRaises(IntegrityError):
            PlexUser.objects.create(
                plex_username="testuser",  # Duplicate username
                plex_account_id="different-account-123",
            )

    def test_unique_plex_account_id(self):
        """Test that duplicate plex_account_ids are not allowed"""
        with self.assertRaises(IntegrityError):
            PlexUser.objects.create(
                plex_username="different_user",
                plex_account_id="test-account-123",  # Duplicate account ID
            )

    def test_str_representation(self):
        """Test the string representation of the user"""
        self.assertEqual(str(self.user), "testuser")
