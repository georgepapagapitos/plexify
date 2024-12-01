# core/views/media.py

import logging
from datetime import datetime
from typing import Dict

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.views.generic import TemplateView

from plex_auth.utils.exceptions import PlexManagerError
from plex_auth.utils.plex_manager import PlexManager

logger = logging.getLogger(__name__)


class MediaView(LoginRequiredMixin, TemplateView):
    template_name = "core/media.html"
    login_url = "plex_auth:login"

    def get_context_data(self, **kwargs) -> Dict:
        context = super().get_context_data(**kwargs)
        user = self.request.user

        logger.info(f"Starting MediaView for user: {user.username}")
        try:
            # Get cached data with longer timeout
            cache_key = f"media_data_{user.id}"
            media_data = cache.get(cache_key)

            if not media_data:
                # Fetch all required data
                media_data = self._fetch_libraries_data(user)
                if media_data["has_content"]:
                    # Add recent and on deck items if we have libraries
                    media_data.update(self._fetch_additional_content(user))

                logger.info(f"Media data fetched: {media_data}")
                if media_data["has_content"]:
                    cache.set(cache_key, media_data, timeout=300)  # 5 minute cache

            context.update(media_data)

        except Exception as e:
            logger.error(f"Error in MediaView for user {user.username}: {str(e)}")
            context.update(self._get_error_context(str(e)))

        return context

    def _fetch_additional_content(self, user) -> Dict:
        """Fetch recently added and on deck items."""
        logger.info(f"Fetching additional content for user: {user.username}")
        recent_items = []
        on_deck_items = []
        plex_manager = PlexManager(user.plex_token)

        for server_conn in user.plex_servers.all():
            try:
                # Get recently added items
                recent_cache_key = f"recent_{server_conn.machine_identifier}"
                server_recent = cache.get(recent_cache_key)

                if not server_recent:
                    logger.info(f"Fetching recent items from {server_conn.name}")
                    # Pass the server_conn object instead of just the URL
                    server_recent = plex_manager.get_recently_added(
                        server_conn, limit=12
                    )
                    if server_recent:
                        # Add server context to each item
                        for item in server_recent:
                            item.update(
                                {
                                    "server_name": server_conn.name,
                                    "server_id": server_conn.machine_identifier,
                                }
                            )
                        cache.set(recent_cache_key, server_recent, timeout=300)

                if server_recent:
                    recent_items.extend(server_recent)

                # Get on deck items
                deck_cache_key = f"deck_{server_conn.machine_identifier}"
                server_deck = cache.get(deck_cache_key)

                if not server_deck:
                    logger.info(f"Fetching on deck items from {server_conn.name}")
                    # Pass the server_conn object instead of just the URL
                    server_deck = plex_manager.get_on_deck(server_conn, limit=10)
                    if server_deck:
                        # Add server context to each item
                        for item in server_deck:
                            item.update(
                                {
                                    "server_name": server_conn.name,
                                    "server_id": server_conn.machine_identifier,
                                }
                            )
                        cache.set(deck_cache_key, server_deck, timeout=300)

                if server_deck:
                    on_deck_items.extend(server_deck)

            except PlexManagerError as e:
                logger.error(
                    f"Error fetching additional content from {server_conn.name}: {str(e)}"
                )
                continue

        # Sort and limit the results
        recent_items.sort(key=lambda x: x.get("added_at", 0), reverse=True)
        on_deck_items.sort(key=lambda x: x.get("view_offset", 0), reverse=True)

        return {
            "recent_items": recent_items[:12],  # Limit to 12 most recent
            "on_deck": on_deck_items[:10],  # Limit to 10 on deck items
        }

    def _fetch_libraries_data(self, user) -> Dict:
        """Fetch only library data initially."""
        logger.info(f"Fetching libraries for user: {user.username}")
        all_libraries = []
        stats = self._get_empty_stats()
        errors = []

        plex_manager = PlexManager(user.plex_token)

        # Log server count
        servers = user.plex_servers.all()
        logger.info(f"Found {servers.count()} servers")

        for server_conn in user.plex_servers.all():
            logger.info(f"Processing server: {server_conn.name} ({server_conn.url})")
            try:
                cache_key = f"server_libraries_{server_conn.machine_identifier}"
                libraries = cache.get(cache_key)

                if not libraries:
                    logger.info(f"Cache miss for {cache_key}, fetching fresh data")
                    libraries = plex_manager.get_libraries(server_conn)
                    if libraries:
                        logger.info(f"Found {len(libraries)} libraries")
                        cache.set(cache_key, libraries, timeout=600)
                else:
                    logger.info(f"Using cached data for {cache_key}")

                for library in libraries:
                    logger.info(f"Processing library: {library.get('title')}")
                    library_data = {
                        **library,
                        "server_name": server_conn.name,
                        "server_id": server_conn.machine_identifier,
                    }
                    all_libraries.append(library_data)
                    self._update_stats(stats, library_data)

                server_conn.mark_available()

            except PlexManagerError as e:
                error_msg = f"Error connecting to server {server_conn.name}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
                server_conn.mark_unreachable(str(e))
                continue

        return {
            "libraries": all_libraries,
            "stats": stats,
            "has_content": bool(all_libraries),
            "errors": errors if errors else None,
        }

    def _update_stats(self, stats: Dict, library: Dict) -> None:
        """Update stats dictionary with library information.

        Args:
            stats: Dictionary containing accumulated statistics
            library: Library data from PlexManager containing counts and metadata
        """
        lib_type = library["type"]

        if lib_type == "movie":
            # Update movie stats
            total_movies = library.get("count", 0)
            stats["movies"]["total"] += total_movies
            stats["movies"]["unwatched"] += library.get("unwatched_count", 0)
            # Convert total duration from milliseconds to hours
            total_duration_ms = library.get("total_duration", 0)
            stats["movies"]["duration"] += total_duration_ms

        elif lib_type == "show":
            # Update TV show stats
            stats["shows"]["total"] += library.get("count", 0)  # Number of shows
            stats["shows"]["episodes"] += library.get("total_episodes", 0)
            stats["shows"]["unwatched"] += library.get("unwatched_episodes", 0)

        elif lib_type == "artist":
            # Update music stats
            stats["music"]["artists"] += library.get("count", 0)  # Number of artists
            stats["music"]["albums"] += library.get("total_albums", 0)
            stats["music"]["tracks"] += library.get("total_tracks", 0)

    def _get_empty_stats(self) -> Dict:
        """Return empty stats structure."""
        return {
            "movies": {"total": 0, "unwatched": 0, "duration": 0},
            "shows": {"total": 0, "episodes": 0, "unwatched": 0},
            "music": {"artists": 0, "albums": 0, "tracks": 0},
        }

    def _get_error_context(self, error_message: str) -> Dict:
        """Return context for error state."""
        return {
            "error": "Unable to load media content. Please try again later.",
            "error_detail": error_message,
            "libraries": [],
            "recent_items": [],
            "on_deck": [],
            "stats": self._get_empty_stats(),
            "has_content": False,
        }
