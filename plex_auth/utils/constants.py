# plex_auth/utils/constants.py

from typing import Final

# API endpoints
PLEX_API_BASE: Final = "https://plex.tv/api/v2"
PLEX_AUTH_URL: Final = "https://app.plex.tv/auth#?"
PLEX_PIN_URL: Final = f"{PLEX_API_BASE}/pins"
PLEX_RESOURCES_URL: Final = f"{PLEX_API_BASE}/resources"

# Request timeouts (in seconds)
REQUEST_TIMEOUT: Final = 10

# HTTP Status codes
HTTP_CREATED: Final = 201
HTTP_OK: Final = 200
