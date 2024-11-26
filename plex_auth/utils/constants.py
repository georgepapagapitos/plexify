# plex_auth/utils/constants.py

from typing import Final

# API endpoints
PLEX_AUTH_URL: Final = "https://app.plex.tv/auth#?"
PLEX_PIN_URL: Final = "https://plex.tv/api/v2/pins"

# Request timeouts (in seconds)
REQUEST_TIMEOUT: Final = 10

# HTTP Status codes
HTTP_CREATED: Final = 201
HTTP_OK: Final = 200
