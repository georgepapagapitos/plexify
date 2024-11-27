# media_manager/utils/plex_media.py

import logging
from typing import Dict, List
from urllib.parse import urljoin

import requests
from django.utils import timezone

from media_manager.models import Episode, Genre, MediaLibrary, Movie, Season, TVShow
from media_manager.utils.constants import (
    METADATA_PARAMS,
    MOVIE_SECTION_TYPE,
    PLEX_LIBRARY_ITEMS_URL,
    PLEX_LIBRARY_SECTIONS_URL,
    PLEX_METADATA_URL,
    SHOW_SECTION_TYPE,
)
from plex_auth.models import PlexServer
from plex_auth.utils.exceptions import PlexAPIError

logger = logging.getLogger(__name__)


class PlexMediaAPI:
    """
    Handles interaction with Plex Media Server for library and media operations.

    This class manages library discovery, media synchronization, and metadata updates
    for movies and TV shows from connected Plex servers.
    """

    def __init__(self, server: PlexServer):
        """Initialize PlexMediaAPI with a specific server instance."""
        self.server = server
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json",
                "X-Plex-Token": server.token,
                "X-Plex-Client-Identifier": server.machine_identifier,
            }
        )

    def discover_libraries(self) -> List[Dict]:
        """
        Fetch all library sections from the Plex server.

        Returns:
            List of library section dictionaries

        Raises:
            PlexAPIError: If there's an error communicating with Plex
        """
        try:
            url = PLEX_LIBRARY_SECTIONS_URL.format(server_url=self.server.url)
            response = self.session.get(url)
            response.raise_for_status()

            data = response.json()
            libraries = []

            for directory in data["MediaContainer"].get("Directory", []):
                if directory["type"] in [MOVIE_SECTION_TYPE, SHOW_SECTION_TYPE]:
                    libraries.append(
                        {
                            "name": directory["title"],
                            "section_id": directory["key"],
                            "library_type": directory["type"],
                        }
                    )

            return libraries

        except requests.RequestException as e:
            logger.error(f"Error discovering libraries: {str(e)}")
            raise PlexAPIError(f"Failed to discover libraries: {str(e)}")

    def sync_library(self, library: MediaLibrary) -> None:
        """
        Synchronize all media items from a specific library section.

        Args:
            library: MediaLibrary instance to sync

        Raises:
            PlexAPIError: If there's an error communicating with Plex
        """
        try:
            url = PLEX_LIBRARY_ITEMS_URL.format(
                server_url=self.server.url, section_id=library.section_id
            )

            response = self.session.get(url, params=METADATA_PARAMS)
            response.raise_for_status()

            data = response.json()
            items = data["MediaContainer"].get("Metadata", [])

            for item in items:
                if library.library_type == MOVIE_SECTION_TYPE:
                    self._sync_movie(library, item)
                elif library.library_type == SHOW_SECTION_TYPE:
                    self._sync_show(library, item)

            library.mark_synced()
            logger.info(f"Successfully synced library: {library.name}")

        except requests.RequestException as e:
            logger.error(f"Error syncing library {library.name}: {str(e)}")
            raise PlexAPIError(f"Failed to sync library: {str(e)}")

    def _sync_movie(self, library: MediaLibrary, data: Dict) -> Movie:
        """Create or update a movie from Plex metadata."""
        try:
            movie, created = Movie.objects.update_or_create(
                library=library,
                plex_key=data["ratingKey"],
                defaults={
                    "title": data["title"],
                    "sort_title": data.get("titleSort", ""),
                    "summary": data.get("summary", ""),
                    "duration": int(data.get("duration", 0)),
                    "content_rating": data.get("contentRating", ""),
                    "rating": float(data["rating"]) if "rating" in data else None,
                    "studio": data.get("studio", ""),
                    "originally_available": data.get("originallyAvailable"),
                    "thumb_url": (
                        urljoin(self.server.url, data["thumb"])
                        if "thumb" in data
                        else ""
                    ),
                    "art_url": (
                        urljoin(self.server.url, data["art"]) if "art" in data else ""
                    ),
                    "tagline": data.get("tagline", ""),
                    "directors": [d["tag"] for d in data.get("Director", [])],
                    "writers": [w["tag"] for w in data.get("Writer", [])],
                    "actors": [a["tag"] for a in data.get("Role", [])],
                    "date_added": timezone.datetime.fromtimestamp(
                        int(data["addedAt"]), tz=timezone.utc
                    ),
                },
            )

            # Sync genres
            genres = []
            for genre_data in data.get("Genre", []):
                genre, _ = Genre.objects.get_or_create(name=genre_data["tag"])
                genres.append(genre)
            movie.genres.set(genres)

            action = "Created" if created else "Updated"
            logger.info(f"{action} movie: {movie.title}")
            return movie

        except Exception as e:
            logger.error(f"Error syncing movie {data.get('title')}: {str(e)}")
            raise

    def _sync_show(self, library: MediaLibrary, data: Dict) -> TVShow:
        """Create or update a TV show and its seasons/episodes from Plex metadata."""
        try:
            show, created = TVShow.objects.update_or_create(
                library=library,
                plex_key=data["ratingKey"],
                defaults={
                    "title": data["title"],
                    "sort_title": data.get("titleSort", ""),
                    "summary": data.get("summary", ""),
                    "content_rating": data.get("contentRating", ""),
                    "rating": float(data["rating"]) if "rating" in data else None,
                    "studio": data.get("studio", ""),
                    "originally_available": data.get("originallyAvailable"),
                    "thumb_url": (
                        urljoin(self.server.url, data["thumb"])
                        if "thumb" in data
                        else ""
                    ),
                    "art_url": (
                        urljoin(self.server.url, data["art"]) if "art" in data else ""
                    ),
                    "total_seasons": data.get("childCount", 0),
                    "show_status": data.get("status", ""),
                    "date_added": timezone.datetime.fromtimestamp(
                        int(data["addedAt"]), tz=timezone.utc
                    ),
                },
            )

            # Sync genres
            genres = []
            for genre_data in data.get("Genre", []):
                genre, _ = Genre.objects.get_or_create(name=genre_data["tag"])
                genres.append(genre)
            show.genres.set(genres)

            # Sync seasons and episodes
            self._sync_seasons(show, data["ratingKey"])

            action = "Created" if created else "Updated"
            logger.info(f"{action} show: {show.title}")
            return show

        except Exception as e:
            logger.error(f"Error syncing show {data.get('title')}: {str(e)}")
            raise

    def _sync_seasons(self, show: TVShow, show_key: str) -> None:
        """Sync all seasons for a TV show."""
        try:
            url = PLEX_METADATA_URL.format(server_url=self.server.url, key=show_key)
            response = self.session.get(url, params=METADATA_PARAMS)
            response.raise_for_status()

            data = response.json()
            for season_data in data["MediaContainer"].get("Metadata", []):
                season = self._sync_season(show, season_data)
                self._sync_episodes(season, season_data["ratingKey"])

        except requests.RequestException as e:
            logger.error(f"Error syncing seasons for {show.title}: {str(e)}")
            raise PlexAPIError(f"Failed to sync seasons: {str(e)}")

    def _sync_season(self, show: TVShow, data: Dict) -> Season:
        """Create or update a season from Plex metadata."""
        try:
            season, created = Season.objects.update_or_create(
                show=show,
                season_number=int(data["index"]),
                defaults={
                    "title": data["title"],
                    "library": show.library,
                    "plex_key": data["ratingKey"],
                    "summary": data.get("summary", ""),
                    "thumb_url": (
                        urljoin(self.server.url, data["thumb"])
                        if "thumb" in data
                        else ""
                    ),
                    "episode_count": data.get("leafCount", 0),
                    "date_added": timezone.datetime.fromtimestamp(
                        int(data["addedAt"]), tz=timezone.utc
                    ),
                },
            )

            action = "Created" if created else "Updated"
            logger.info(f"{action} season {season.season_number} of {show.title}")
            return season

        except Exception as e:
            logger.error(
                f"Error syncing season {data.get('index')} of {show.title}: {str(e)}"
            )
            raise

    def _sync_episodes(self, season: Season, season_key: str) -> None:
        """Sync all episodes for a season."""
        try:
            url = PLEX_METADATA_URL.format(server_url=self.server.url, key=season_key)
            response = self.session.get(url, params=METADATA_PARAMS)
            response.raise_for_status()

            data = response.json()
            for episode_data in data["MediaContainer"].get("Metadata", []):
                self._sync_episode(season, episode_data)

        except requests.RequestException as e:
            logger.error(
                f"Error syncing episodes for season {season.season_number}: {str(e)}"
            )
            raise PlexAPIError(f"Failed to sync episodes: {str(e)}")

    def _sync_episode(self, season: Season, data: Dict) -> Episode:
        """Create or update an episode from Plex metadata."""
        try:
            episode, created = Episode.objects.update_or_create(
                season=season,
                episode_number=int(data["index"]),
                defaults={
                    "title": data["title"],
                    "library": season.library,
                    "plex_key": data["ratingKey"],
                    "summary": data.get("summary", ""),
                    "duration": int(data.get("duration", 0)),
                    "thumb_url": (
                        urljoin(self.server.url, data["thumb"])
                        if "thumb" in data
                        else ""
                    ),
                    "directors": [d["tag"] for d in data.get("Director", [])],
                    "writers": [w["tag"] for w in data.get("Writer", [])],
                    "date_added": timezone.datetime.fromtimestamp(
                        int(data["addedAt"]), tz=timezone.utc
                    ),
                },
            )

            action = "Created" if created else "Updated"
            logger.info(
                f"{action} S{season.season_number:02d}E{episode.episode_number:02d} "
                f"of {season.show.title}"
            )
            return episode

        except Exception as e:
            logger.error(
                f"Error syncing episode {data.get('index')} of season "
                f"{season.season_number}: {str(e)}"
            )
            raise
