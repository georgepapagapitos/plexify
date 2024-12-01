# plex_auth/utils/plex_manager.py

import logging
from datetime import datetime
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

from plexapi.exceptions import NotFound, Unauthorized
from plexapi.myplex import MyPlexAccount
from plexapi.server import PlexServer
from plexapi.video import Episode, Movie, Show

from plex_auth.utils.exceptions import PlexManagerError

logger = logging.getLogger(__name__)


class PlexManager:
    """
    Enhanced utility class for interacting with the Plex API using plexapi library.
    Handles server discovery, content retrieval, and connection management.
    """

    def __init__(self, plex_token: str):
        self.plex_token = plex_token
        self._account = None
        self._servers: Dict[str, PlexServer] = {}  # Cache for server connections
        self._initialize_account()

    def _initialize_account(self) -> None:
        """Initialize Plex account connection."""
        try:
            self._account = MyPlexAccount(token=self.plex_token)
        except Unauthorized as e:
            logger.error(f"Invalid or expired Plex token: {str(e)}")
            raise PlexManagerError("Invalid Plex authentication token")
        except Exception as e:
            logger.error(f"Failed to initialize Plex account: {str(e)}")
            raise PlexManagerError(f"Could not connect to Plex: {str(e)}")

    @lru_cache(maxsize=8)
    def _get_server(self, server_conn) -> PlexServer:
        """
        Get or create a cached server connection using PlexAPI's built-in connection resolution.
        """
        cache_key = server_conn.machine_identifier
        if cache_key not in self._servers:
            try:
                # Use already initialized account instead of creating new one
                server_resource = self._account.resource(server_conn.machine_identifier)

                # First try local URL if available (faster)
                if server_conn.local_url:
                    try:
                        connection = PlexServer(
                            server_conn.local_url, self.plex_token, timeout=5
                        )
                        self._servers[cache_key] = connection
                        logger.info(
                            f"Connected to {server_conn.name} using local URL: {server_conn.local_url}"
                        )
                        return connection
                    except Exception as e:
                        logger.debug(
                            f"Local connection failed, falling back to Plex.tv: {str(e)}"
                        )

                # Fall back to PlexAPI connection resolution
                connection = server_resource.connect(timeout=5)
                logger.info(
                    f"Connected to {server_conn.name} using: {connection._baseurl}"
                )

                self._servers[cache_key] = connection
                return connection

            except Exception as e:
                logger.error(f"Failed to connect to {server_conn.name}: {str(e)}")
                raise PlexManagerError(f"Failed to connect to server: {str(e)}")

        return self._servers[cache_key]

    def discover_servers(self) -> List[Dict[str, Any]]:
        """
        Fetch available Plex servers from the Plex API.
        """
        try:
            logger.debug(
                "Starting server discovery with token: %s", self.plex_token[:4] + "..."
            )
            resources = self._account.resources()
            logger.debug("Found %d resources", len(resources))
            servers = []

            for resource in resources:
                logger.debug("Processing resource: %s", resource.name)
                if (
                    resource.product == "Plex Media Server"
                    and resource.provides == "server"
                ):
                    connections = resource.connections
                    connection = next(
                        (c for c in connections if c.local == False), connections[0]
                    )
                    logger.debug("Selected connection URL: %s", connection.uri)

                    servers.append(
                        {
                            "name": resource.name,
                            "url": connection.uri,
                            "machine_identifier": resource.clientIdentifier,
                            "version": resource.productVersion,
                            "token": self.plex_token,
                            "owned": resource.owned,
                            "local": connection.local,
                            "status": "available",
                        }
                    )

            logger.debug("Discovered %d servers", len(servers))
            return servers

        except Exception as e:
            logger.error("Error discovering servers: %s", str(e), exc_info=True)
            return []

    def get_libraries(self, server_conn) -> List[Dict[str, Any]]:
        """Fetch libraries with basic metadata - no expensive search operations."""
        try:
            logger.debug(
                "Attempting to get libraries from server: %s", server_conn.name
            )
            server = self._get_server(server_conn)
            logger.debug("Successfully connected to server")
            libraries = []

            # Helper function to create full URLs
            def make_url(path: str) -> str:
                if not path:
                    return ""
                if path.startswith("http"):
                    return path
                return f"{server._baseurl.rstrip('/')}{path}"

            for section in server.library.sections():
                base_info = {
                    "key": section.key,
                    "title": section.title,
                    "type": section.type,
                    "count": section.totalSize,
                    "thumb": (
                        make_url(section.thumb) if hasattr(section, "thumb") else ""
                    ),
                    "art": make_url(section.art) if hasattr(section, "art") else "",
                    "agent": section.agent,
                    "scanner": section.scanner,
                    "language": section.language,
                    "locations": [loc for loc in section.locations],
                    "refreshing": section.refreshing,
                    "updated_at": (
                        section.updatedAt if hasattr(section, "updatedAt") else None
                    ),
                }

                # Add type-specific data
                if section.type == "movie":
                    base_info.update(
                        {
                            "unwatched_count": (
                                section.unwatchedCount
                                if hasattr(section, "unwatchedCount")
                                else 0
                            ),
                            "total_duration": (
                                section.duration if hasattr(section, "duration") else 0
                            ),
                        }
                    )
                elif section.type == "show":
                    base_info.update(
                        {
                            "total_episodes": (
                                section.leafCount
                                if hasattr(section, "leafCount")
                                else 0
                            ),
                            "unwatched_episodes": (
                                section.unwatchedLeafCount
                                if hasattr(section, "unwatchedLeafCount")
                                else 0
                            ),
                        }
                    )
                elif section.type == "artist":
                    base_info.update(
                        {
                            "total_albums": (
                                section.albumCount
                                if hasattr(section, "albumCount")
                                else 0
                            ),
                            "total_tracks": (
                                section.leafCount
                                if hasattr(section, "leafCount")
                                else 0
                            ),
                        }
                    )

                libraries.append(base_info)
                logger.debug(f"Processed library section: {section.title}")

            return libraries

        except Exception as e:
            logger.error(f"Error fetching libraries: {str(e)}")
            raise PlexManagerError(f"Failed to fetch libraries: {str(e)}")

    def get_library_contents(
        self,
        server_url: str,
        library_key: str,
        sort: str = "titleSort",
        limit: int = 50,
        offset: int = 0,
        filters: Optional[Dict] = None,
    ) -> Tuple[List[Dict], int]:
        """
        Fetch paginated contents of a specific library with optional filtering.

        Args:
            server_url: URL of the Plex server
            library_key: Library section key
            sort: Sort field (default: titleSort)
            limit: Number of items to return
            offset: Starting offset for pagination
            filters: Optional dictionary of filters (e.g., {'year': 2024, 'genre': 'Action'})

        Returns:
            Tuple of (items list, total count)
        """
        try:
            server = self._get_server(server_url)
            library = server.library.sectionByID(library_key)

            # Apply filters if provided
            items = library.all()
            if filters:
                for key, value in filters.items():
                    items = [
                        item for item in items if getattr(item, key, None) == value
                    ]

            total_count = len(items)
            items = items[offset : offset + limit]

            return ([self._format_media_item(item) for item in items], total_count)

        except NotFound:
            logger.error(f"Library section {library_key} not found")
            raise PlexManagerError("Library section not found")
        except Exception as e:
            logger.error(f"Error fetching library contents: {str(e)}")
            raise PlexManagerError(f"Failed to fetch library contents: {str(e)}")

    def _format_media_item(self, item: Any) -> Dict[str, Any]:
        """Format a media item into a standardized dictionary."""
        try:
            # Get the server base URL
            server = item._server
            base_url = server._baseurl.rstrip("/")

            # Helper function to create full URLs
            def make_url(path: str) -> str:
                if not path:
                    return ""
                if path.startswith("http"):
                    return path
                return f"{base_url}{path}"

            base_info = {
                "key": item.ratingKey,
                "title": item.title,
                "type": item.type,
                "thumb": make_url(item.thumb) if hasattr(item, "thumb") else "",
                "art": make_url(item.art) if hasattr(item, "art") else "",
                "added_at": (
                    item.addedAt.timestamp() if hasattr(item, "addedAt") else None
                ),
                "updated_at": (
                    item.updatedAt.timestamp() if hasattr(item, "updatedAt") else None
                ),
                "year": item.year if hasattr(item, "year") else None,
                "rating": item.rating if hasattr(item, "rating") else None,
                "summary": item.summary if hasattr(item, "summary") else "",
                "duration": item.duration if hasattr(item, "duration") else None,
                "view_count": item.viewCount if hasattr(item, "viewCount") else 0,
                "view_offset": item.viewOffset if hasattr(item, "viewOffset") else 0,
            }

            # Add media-type specific information
            if isinstance(item, Movie):
                base_info.update(
                    {
                        "studio": item.studio if hasattr(item, "studio") else "",
                        "content_rating": (
                            item.contentRating if hasattr(item, "contentRating") else ""
                        ),
                        "genres": (
                            [genre.tag for genre in item.genres]
                            if hasattr(item, "genres")
                            else []
                        ),
                        "directors": (
                            [director.tag for director in item.directors]
                            if hasattr(item, "directors")
                            else []
                        ),
                        "actors": (
                            [actor.tag for actor in item.roles][:5]
                            if hasattr(item, "roles")
                            else []
                        ),
                    }
                )
            elif isinstance(item, (Show, Episode)):
                base_info.update(
                    {
                        "show_title": (
                            item.grandparentTitle
                            if isinstance(item, Episode)
                            else item.title
                        ),
                        "season_number": (
                            item.parentIndex if isinstance(item, Episode) else None
                        ),
                        "episode_number": (
                            item.index if isinstance(item, Episode) else None
                        ),
                        "episode_title": (
                            item.title if isinstance(item, Episode) else None
                        ),
                    }
                )

            return base_info

        except Exception as e:
            logger.error(f"Error formatting media item: {str(e)}")
            return None

    def get_recently_added(self, server_conn, limit: int = 12) -> List[Dict[str, Any]]:
        """Get recently added items from a server.

        Args:
            server_conn: PlexServerConnection model instance
            limit: Maximum number of items to return

        Returns:
            List of recently added items with metadata
        """
        try:
            server = self._get_server(server_conn)
            items = server.library.recentlyAdded()
            if not items:
                return []

            recent = []
            for item in items[:limit]:
                item_data = self._format_media_item(item)
                if item_data:
                    recent.append(item_data)

            return recent

        except Exception as e:
            logger.error(f"Error fetching recent items: {str(e)}")
            raise PlexManagerError(f"Failed to fetch recent items: {str(e)}")

    def get_on_deck(self, server_conn, limit: int = 10) -> List[Dict[str, Any]]:
        """Get on deck items from a server.

        Args:
            server_conn: PlexServerConnection model instance
            limit: Maximum number of items to return

        Returns:
            List of on deck items with metadata
        """
        try:
            server = self._get_server(server_conn)
            items = server.library.onDeck()
            if not items:
                return []

            on_deck = []
            for item in items[:limit]:
                item_data = self._format_media_item(item)
                if item_data:
                    # Add progress information
                    progress = 0
                    if hasattr(item, "viewOffset") and hasattr(item, "duration"):
                        if item.duration > 0:
                            progress = (item.viewOffset / item.duration) * 100
                    item_data["progress"] = round(progress, 1)
                    on_deck.append(item_data)

            return on_deck

        except Exception as e:
            logger.error(f"Error fetching on deck items: {str(e)}")
            raise PlexManagerError(f"Failed to fetch on deck items: {str(e)}")

    def clear_cache(self) -> None:
        """Clear the server connection cache."""
        self._servers.clear()
        self._get_server.cache_clear()
