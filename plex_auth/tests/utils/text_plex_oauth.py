# plex_auth/tests/utils/test_plex_oauth.py

from unittest.mock import MagicMock, patch

from django.conf import settings
from django.test import RequestFactory, TestCase

from plex_auth.utils import PlexAPIError, PlexOAuth


class TestPlexOAuth(TestCase):
    """Test the PlexOAuth utility class"""

    def setUp(self):
        self.factory = RequestFactory()

    def test_get_headers(self):
        """Test that get_headers returns correct Plex API headers"""
        headers = PlexOAuth.get_headers()
        self.assertEqual(headers["X-Plex-Product"], "Plexify")
        self.assertEqual(
            headers["X-Plex-Client-Identifier"], settings.PLEX_CLIENT_IDENTIFIER
        )
        self.assertEqual(headers["Accept"], "application/json")

    @patch("requests.post")
    def test_get_pin_success(self, mock_post):
        """Test successful PIN generation with correct API response"""
        mock_response = MagicMock()
        mock_response.status_code = 201  # Plex API returns 201 on success
        mock_response.json.return_value = {
            "id": 12345,
            "code": "ABC123",
            "expires_in": 1800,
            "clientIdentifier": settings.PLEX_CLIENT_IDENTIFIER,
        }
        mock_post.return_value = mock_response

        pin_data = PlexOAuth.get_pin()

        self.assertIsNotNone(pin_data)
        self.assertEqual(pin_data["id"], 12345)
        self.assertEqual(pin_data["code"], "ABC123")
        self.assertEqual(pin_data["expires_in"], 1800)

        # Verify the correct data was sent to Plex
        mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs["data"]["strong"], "true")
        self.assertEqual(kwargs["data"]["X-Plex-Product"], "Plexify")

    @patch("requests.post")
    def test_get_pin_failure(self, mock_post):
        """Test PIN generation with API failure response"""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Error creating PIN"
        mock_post.return_value = mock_response

        with self.assertRaises(PlexAPIError) as context:
            PlexOAuth.get_pin()

        self.assertIn("Pin creation failed: 400", str(context.exception))

    def test_get_auth_url(self):
        """Test authentication URL generation with correct format"""
        pin_code = "ABC123"
        auth_url = PlexOAuth.get_auth_url(pin_code)

        # Test URL structure
        self.assertTrue(auth_url.startswith("https://app.plex.tv/auth#!?"))
        self.assertIn(f"code={pin_code}", auth_url)
        self.assertIn("clientID=" + settings.PLEX_CLIENT_IDENTIFIER, auth_url)
        self.assertIn("context[device][product]=Plexify", auth_url)

    @patch("requests.get")
    def test_check_pin_not_authenticated(self, mock_get):
        """Test PIN status check when authentication is pending"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": 12345,
            "code": "ABC123",
            "clientIdentifier": settings.PLEX_CLIENT_IDENTIFIER,
            "trusted": False,
            "authToken": None,
        }
        mock_get.return_value = mock_response

        result = PlexOAuth.check_pin("12345")
        self.assertIsNone(result)  # Should return None when not authenticated

    @patch("requests.get")
    def test_check_pin_authenticated(self, mock_get):
        """Test PIN status check when authentication is complete"""
        auth_token = "xyz789"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": 12345,
            "code": "ABC123",
            "trusted": True,
            "authToken": auth_token,
            "clientIdentifier": settings.PLEX_CLIENT_IDENTIFIER,
        }
        mock_get.return_value = mock_response

        result = PlexOAuth.check_pin("12345")

        self.assertIsNotNone(result)
        self.assertEqual(result["authToken"], auth_token)
        self.assertEqual(result["clientIdentifier"], settings.PLEX_CLIENT_IDENTIFIER)

    @patch("requests.get")
    def test_check_pin_api_error(self, mock_get):
        """Test PIN status check with API error response"""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "PIN not found"
        mock_get.return_value = mock_response

        with self.assertRaises(PlexAPIError) as context:
            PlexOAuth.check_pin("12345")

        self.assertIn("Pin check failed: 404", str(context.exception))
