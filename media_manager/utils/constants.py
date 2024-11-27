# media_manager/utils/constants.py

from typing import Final

# API Endpoints
PLEX_LIBRARY_SECTIONS_URL: Final = "{server_url}/library/sections"
PLEX_LIBRARY_SECTION_URL: Final = "{server_url}/library/sections/{section_id}"
PLEX_LIBRARY_ITEMS_URL: Final = "{server_url}/library/sections/{section_id}/all"
PLEX_METADATA_URL: Final = "{server_url}/library/metadata/{key}/children"

# Content Types
MOVIE_SECTION_TYPE: Final = "movie"
SHOW_SECTION_TYPE: Final = "show"

# Sync Batch Size
SYNC_BATCH_SIZE: Final = 50

# Request Parameters
METADATA_PARAMS: Final = {
    "includeGuids": 1,
    "includeMarkers": 1,
    "includeChapters": 1,
    "includeChildren": 1,
}
