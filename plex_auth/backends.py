import logging

import requests
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend

logger = logging.getLogger(__name__)


class PlexAuthenticationBackend(BaseBackend):
    def authenticate(self, request, token=None, account_data=None):
        logger.info("PlexAuthenticationBackend.authenticate called")
        logger.info(f"Token present: {bool(token)}")
        logger.info(f"Account data: {account_data}")

        if not token:
            logger.error("No token provided")
            return None

        # If no account data provided, fetch it from Plex
        if not account_data:
            try:
                headers = {
                    "Accept": "application/json",
                    "X-Plex-Token": token,
                }
                response = requests.get("https://plex.tv/api/v2/user", headers=headers)
                response.raise_for_status()
                account_data = response.json()
                logger.info(f"Fetched account data: {account_data}")
            except Exception as e:
                logger.error(f"Error fetching user data: {e}")
                return None

        # Get required fields from account data
        username = account_data.get("username")
        email = account_data.get("email")

        if not username:
            logger.error("No username in account data")
            return None

        User = get_user_model()

        try:
            # Try to get existing user
            user = User.objects.get(username=username)
            user.plex_token = token
            user.save()
            logger.info(f"Updated existing user: {username}")
            return user
        except User.DoesNotExist:
            # Create new user
            user = User.objects.create_user(
                username=username,
                email=email or "",
                plex_token=token,
            )
            logger.info(f"Created new user: {username}")
            return user
        except Exception as e:
            logger.error(f"Error creating/updating user: {e}")
            return None

    def get_user(self, user_id):
        User = get_user_model()
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
