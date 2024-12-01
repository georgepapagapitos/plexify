# media_manager/utils.py

import logging
from typing import Dict

from django.utils import timezone
from plexapi.exceptions import NotFound

from media_manager.models import Movie
from plex_auth.utils.plex_manager import PlexManager

logger = logging.getLogger(__name__)


class MovieManager:
    def __init__(self, plex_token: str):
        self.plex_manager = PlexManager(plex_token)

    def sync_movies_from_library(self, server_conn, library_key: str) -> Dict[str, int]:
        """
        Syncs all movies from a specific Plex library to our database.
        """
        try:
            # Get server connection using PlexManager
            server = self.plex_manager._get_server(server_conn)
            logger.info(f"Connected to server: {server._baseurl}")

            # First, get all library sections
            sections = server.library.sections()
            logger.info(f"Found sections: {[f'{s.key}: {s.title}' for s in sections]}")

            # Find the section we want
            library_section = None
            for section in sections:
                if str(section.key) == str(library_key):
                    library_section = section
                    break

            if not library_section:
                available_sections = [f"{s.key}: {s.title}" for s in sections]
                error_msg = f"Library with ID {library_key} not found. Available sections: {available_sections}"
                logger.error(error_msg)
                raise NotFound(error_msg)

            logger.info(f"Found library: {library_section.title}")

            # Get all movies
            movies = library_section.all()
            logger.info(f"Found {len(movies)} items in library")

            added_count = 0
            updated_count = 0

            for movie in movies:
                # Skip non-movie items
                if not hasattr(movie, "type") or movie.type != "movie":
                    logger.debug(
                        f"Skipping non-movie item: {getattr(movie, 'title', 'Unknown')}"
                    )
                    continue

                try:
                    movie_data = self.plex_manager._format_media_item(movie)
                    if not movie_data:
                        logger.warning(
                            f"Failed to format movie data for: {movie.title}"
                        )
                        continue

                    # Update or create movie record
                    movie_obj, created = Movie.objects.update_or_create(
                        server=server_conn,
                        plex_key=str(movie_data["key"]),
                        defaults={
                            "title": movie_data["title"],
                            "year": movie_data.get("year"),
                            "summary": movie_data.get("summary", ""),
                            "duration": movie_data.get("duration", 0),
                            "content_rating": movie_data.get("content_rating", ""),
                            "rating": movie_data.get("rating"),
                            "studio": movie_data.get("studio", ""),
                            "genres": movie_data.get("genres", []),
                            "directors": movie_data.get("directors", []),
                            "actors": movie_data.get("actors", []),
                            "added_at": (
                                timezone.datetime.fromtimestamp(
                                    movie_data["added_at"]
                                ).astimezone(timezone.get_current_timezone())
                                if movie_data.get("added_at")
                                else timezone.now()
                            ),
                            "updated_at": (
                                timezone.datetime.fromtimestamp(
                                    movie_data["updated_at"]
                                ).astimezone(timezone.get_current_timezone())
                                if movie_data.get("updated_at")
                                else timezone.now()
                            ),
                            "thumb_url": movie_data.get("thumb", ""),
                            "view_count": movie_data.get("view_count", 0),
                        },
                    )
                    if created:
                        logger.debug(f"Created new movie record: {movie_data['title']}")
                        added_count += 1
                    else:
                        logger.debug(
                            f"Updated existing movie record: {movie_data['title']}"
                        )
                        updated_count += 1

                except Exception as e:
                    logger.error(f"Error processing movie {movie.title}: {str(e)}")
                    continue

            logger.info(
                f"Sync complete - Added: {added_count}, Updated: {updated_count}, Total: {len(movies)}"
            )
            return {
                "added": added_count,
                "updated": updated_count,
                "total": len(movies),
            }

        except Exception as e:
            logger.error(f"Error syncing movies: {str(e)}")
            raise
