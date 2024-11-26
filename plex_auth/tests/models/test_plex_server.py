# plex_auth/tests/models/test_plex_server.py

from django.db import IntegrityError
from django.test import TestCase

from plex_auth.models import PlexServer, PlexUser


class PlexServerModelTests(TestCase):
    """Test suite for the PlexServer model"""

    def setUp(self):
        """Create a basic user and server for tests"""
        self.user = PlexUser.objects.create(
            plex_username="testuser", plex_account_id="test-account-123"
        )
        self.server_data = {
            "name": "Test Server",
            "url": "http://test.server:32400",
            "token": "server-token-123",
            "machine_identifier": "test-machine-123",
            "version": "1.31.3",
            "owner": self.user,
        }
        self.server = PlexServer.objects.create(**self.server_data)

    def test_create_server(self):
        """Test basic server creation"""
        self.assertEqual(self.server.name, "Test Server")
        self.assertEqual(self.server.url, "http://test.server:32400")
        self.assertEqual(self.server.token, "server-token-123")
        self.assertEqual(self.server.machine_identifier, "test-machine-123")
        self.assertEqual(self.server.version, "1.31.3")
        self.assertEqual(self.server.owner, self.user)

    def test_unique_machine_identifier(self):
        """Test that duplicate machine_identifiers are not allowed"""
        with self.assertRaises(IntegrityError):
            PlexServer.objects.create(
                name="Another Server",
                url="http://another.server:32400",
                token="different-token",
                machine_identifier="test-machine-123",  # Duplicate identifier
                version="1.31.3",
                owner=self.user,
            )

    def test_unique_together_constraint(self):
        """Test that the same user cannot have duplicate machine identifiers"""
        # Create another user
        other_user = PlexUser.objects.create(
            plex_username="otheruser", plex_account_id="other-account-123"
        )

        # Should succeed - same machine_identifier but different owner
        PlexServer.objects.create(
            name="Other Server",
            url="http://other.server:32400",
            token="other-token",
            machine_identifier="different-machine-123",
            version="1.31.3",
            owner=other_user,
        )

        # Should fail - same owner and machine_identifier
        with self.assertRaises(IntegrityError):
            PlexServer.objects.create(
                name="Duplicate Server",
                url="http://duplicate.server:32400",
                token="other-token",
                machine_identifier="test-machine-123",  # Same as first server
                version="1.31.3",
                owner=self.user,  # Same as first server
            )

    def test_str_representation(self):
        """Test the string representation of the server"""
        expected_str = f"Test Server (testuser)"
        self.assertEqual(str(self.server), expected_str)

    def test_last_seen_auto_update(self):
        """Test that last_seen is automatically updated"""
        original_last_seen = self.server.last_seen

        # Wait a small amount of time
        import time

        time.sleep(0.1)

        # Update the server
        self.server.name = "Updated Name"
        self.server.save()

        self.assertGreater(self.server.last_seen, original_last_seen)
