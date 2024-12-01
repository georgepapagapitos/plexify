# core/views/library.py

import logging
from typing import Dict, List

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.views.generic import TemplateView
from plexapi.library import LibrarySection
from plexapi.server import PlexServer

logger = logging.getLogger(__name__)


class LibraryView(LoginRequiredMixin, TemplateView):
    """
    Display contents of a specific Plex library section.
    """

    template_name = "core/library.html"
    login_url = "plex_auth:login"

    def get_context_data(self, **kwargs) -> Dict:
        context = super().get_context_data(**kwargs)
        user = self.request.user

        server_id = kwargs.get("server_id")
        library_key = kwargs.get("library_key")

        try:
            # Get server connection
            server_conn = user.plex_servers.get(
                machine_identifier=server_id, status="available"
            )

            # Use cache for library data
            cache_key = f"library_{server_id}_{library_key}_{user.id}"
            library_data = cache.get(cache_key)

            if not library_data:
                # Connect to Plex server
                server = PlexServer(server_conn.url, server_conn.token)
                library = server.library.sectionByID(library_key)

                # Get library contents with pagination
                page = self.request.GET.get("page", "1")
                try:
                    page = max(1, int(page))
                except ValueError:
                    page = 1

                items_per_page = 24
                start = (page - 1) * items_per_page

                library_data = {
                    "info": self._get_library_info(library),
                    "items": self._get_library_items(library, start, items_per_page),
                    "server_name": server_conn.name,
                    "current_page": page,
                    "has_next": len(library.all()) > (page * items_per_page),
                    "has_previous": page > 1,
                }

                # Cache for 5 minutes
                cache.set(cache_key, library_data, timeout=300)

            context.update(library_data)

        except Exception as e:
            logger.error(
                f"Error loading library {library_key} from server {server_id}: {str(e)}"
            )
            context.update(
                {
                    "error": "Unable to load library contents. Please try again later.",
                    "items": [],
                }
            )

        return context

    def _get_library_info(self, library: LibrarySection) -> Dict:
        """Get basic information about the library section."""
        return {
            "key": library.key,
            "title": library.title,
            "type": library.type,
            "total_items": len(library.all()),
            "agent": library.agent,
            "scanner": library.scanner,
            "language": library.language,
            "locations": library.locations,
            "empty": library.isEmpty(),
            "modified_at": library.updatedAt,
        }

    def _get_library_items(
        self, library: LibrarySection, start: int, limit: int
    ) -> List[Dict]:
        """Get paginated library items with metadata."""
        items = []
        all_items = library.all()[start : start + limit]

        for item in all_items:
            try:
                item_data = {
                    "key": item.key,
                    "rating_key": item.ratingKey,
                    "title": item.title,
                    "year": getattr(item, "year", None),
                    "thumb": getattr(item, "thumb", None),
                    "summary": getattr(item, "summary", ""),
                    "type": item.type,
                    "duration": getattr(item, "duration", 0),
                    "added_at": getattr(item, "addedAt", None),
                }

                # Add media-type specific information
                if library.type == "movie":
                    item_data.update(
                        {
                            "rating": getattr(item, "rating", None),
                            "content_rating": getattr(item, "contentRating", None),
                            "studio": getattr(item, "studio", None),
                            "genres": (
                                [g.tag for g in item.genres][:3]
                                if hasattr(item, "genres")
                                else []
                            ),
                            "directors": (
                                [d.tag for d in item.directors][:2]
                                if hasattr(item, "directors")
                                else []
                            ),
                            "resolution": self._get_video_resolution(item),
                        }
                    )
                elif library.type == "show":
                    item_data.update(
                        {
                            "rating": getattr(item, "rating", None),
                            "content_rating": getattr(item, "contentRating", None),
                            "studio": getattr(item, "studio", None),
                            "episode_count": getattr(item, "leafCount", 0),
                            "season_count": (
                                len(item.seasons()) if hasattr(item, "seasons") else 0
                            ),
                            "genres": (
                                [g.tag for g in item.genres][:3]
                                if hasattr(item, "genres")
                                else []
                            ),
                        }
                    )

                items.append(item_data)

            except Exception as e:
                logger.error(f"Error processing library item: {str(e)}")
                continue

        return items

    def _get_video_resolution(self, item) -> str:
        """Get video resolution for a media item."""
        try:
            media = item.media[0] if item.media else None
            if media:
                if media.height >= 2160:
                    return "4K"
                elif media.height >= 1080:
                    return "1080p"
                elif media.height >= 720:
                    return "720p"
                return f"{media.height}p"
        except:
            pass
        return "Unknown"
