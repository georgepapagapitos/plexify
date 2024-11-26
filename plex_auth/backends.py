# plex_auth/backends.py

import logging
from typing import Any, Dict, Optional

import requests
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend
from django.core.exceptions import ObjectDoesNotExist

logger = logging.getLogger(__name__)


class PlexAuthenticationBackend(BaseBackend):
    """
    Custom authentication backend for Plex SSO integration.

    This backend handles authentication of users via Plex's OAuth system,
    creating or updating local user accounts based on Plex account data.

    Methods:
        authenticate: Validates Plex token and creates/updates local user
        get_user: Retrieves user by ID from database
    """

    PLEX_USER_API = "https://plex.tv/api/v2/user"

    def authenticate(
        self,
        request,
        token: Optional[str] = None,
        account_data: Optional[Dict[str, Any]] = None,
    ) -> Optional[Any]:
        """
        Authenticate a user using Plex token and account data.

        Args:
            request: The HTTP request (may be None)
            token: Plex authentication token
            account_data: Optional pre-fetched Plex account data

        Returns:
            User object if authentication successful, None otherwise
        """

        logger.info("Starting Plex authentication process")

        if not token:
            logger.error("Authentication failed: No token provided")
            return None

        # Fetch account data from Plex if not provided
        account_data = account_data or self._fetch_plex_account_data(token)
        if not account_data:
            return None

        try:
            return self._get_or_create_user(token, account_data)
        except Exception as e:
            logger.error(
                f"Unexpected error during authentication: {str(e)}", exc_info=True
            )
            return None

    def _fetch_plex_account_data(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Fetch user account data from Plex API.

        Args:
            token: Plex authentication token

        Returns:
            Dict containing user data if successful, None otherwise
        """
        try:
            headers = {
                "Accept": "application/json",
                "X-Plex-Token": token,
            }
            response = requests.get(self.PLEX_USER_API, headers=headers)
            response.raise_for_status()
            account_data = response.json()
            logger.info("Successfully fetched Plex account data")
            return account_data
        except requests.RequestException as e:
            logger.error(f"Failed to fetch Plex account data: {str(e)}", exc_info=True)
            return None

    def _get_or_create_user(
        self, token: str, account_data: Dict[str, Any]
    ) -> Optional[Any]:
        """
        Get existing user or create new one based on Plex account data.

        Args:
            token: Plex authentication token
            account_data: Plex account data

        Returns:
            User object if successful, None otherwise
        """
        User = get_user_model()

        # Extract required data
        username = account_data.get("username")
        email = account_data.get("email", "")
        account_id = str(account_data.get("id"))
        thumb_url = account_data.get("thumb")

        if not username or not account_id:
            logger.error("Missing required fields in account data")
            return None

        try:
            # Try to find user by Plex account ID first
            user = User.objects.get(plex_account_id=account_id)
            logger.info(f"Found existing user by Plex account ID: {username}")
        except User.DoesNotExist:
            try:
                # Try finding by username as fallback
                user = User.objects.get(username=username)
                logger.info(f"Found existing user by username: {username}")
            except User.DoesNotExist:
                # Create new user
                user = User(username=username)
                logger.info(f"Creating new user: {username}")

        # Update user data
        user.plex_username = username
        user.plex_token = token
        user.plex_account_id = account_id
        user.email = email
        if thumb_url:
            user.thumb_url = thumb_url

        try:
            user.save()
            logger.info(f"Successfully updated user data for: {username}")
            return user
        except Exception as e:
            logger.error(f"Failed to save user data: {str(e)}", exc_info=True)
            return None

    def get_user(self, user_id: int) -> Optional[Any]:
        """
        Retrieve user by ID from database.

        Args:
            user_id: Database ID of the user

        Returns:
            User object if found, None otherwise
        """
        User = get_user_model()
        try:
            return User.objects.get(pk=user_id)
        except ObjectDoesNotExist:
            logger.warning(f"User not found with ID: {user_id}")
            return None
