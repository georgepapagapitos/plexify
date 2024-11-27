# media_manager/models.py

import logging

from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from plex_auth.models import PlexServer

logger = logging.getLogger(__name__)


class MediaLibrary(models.Model):
    """
    Represents a Plex library section (e.g., Movies, TV Shows).
    Maps to Plex's library sections and manages the synchronization state.
    """

    class LibraryType(models.TextChoices):
        MOVIE = "movie", "Movie"
        SHOW = "show", "TV Show"

    name = models.CharField(max_length=255)
    server = models.ForeignKey(
        PlexServer, on_delete=models.CASCADE, related_name="libraries"
    )
    section_id = models.IntegerField()
    library_type = models.CharField(max_length=10, choices=LibraryType.choices)
    last_synced = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name_plural = "Media Libraries"
        unique_together = ["server", "section_id"]

    def __str__(self) -> str:
        return f"{self.name} ({self.server.name})"

    def mark_synced(self) -> None:
        """Update the last_synced timestamp."""
        self.last_synced = timezone.now()
        self.save(update_fields=["last_synced"])
        logger.info(f"Library {self.name} marked as synced")


class Genre(models.Model):
    """
    Represents media genres for filtering and categorization.
    Shared between movies and TV shows.
    """

    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, blank=True)

    class Meta:
        unique_together = ["name", "slug"]

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class BaseMedia(models.Model):
    """
    Abstract base class for all media types.
    Contains common fields used by both movies and TV shows.
    """

    title = models.CharField(max_length=255)
    sort_title = models.CharField(max_length=255, blank=True)
    slug = models.SlugField(max_length=255, blank=True)
    library = models.ForeignKey(MediaLibrary, on_delete=models.CASCADE)
    plex_key = models.CharField(max_length=100)
    date_added = models.DateTimeField()
    last_updated = models.DateTimeField(auto_now=True)

    # Media details
    summary = models.TextField(blank=True)
    rating = models.FloatField(null=True, blank=True)
    content_rating = models.CharField(max_length=20, blank=True)
    studio = models.CharField(max_length=255, blank=True)
    genres = models.ManyToManyField(Genre, related_name="%(class)ss")
    originally_available = models.DateField(null=True, blank=True)

    # Media assets
    thumb_url = models.URLField(blank=True)
    art_url = models.URLField(blank=True)
    banner_url = models.URLField(blank=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            self.slug = slugify(self.title)
        if not self.sort_title:
            self.sort_title = self.title
        super().save(*args, **kwargs)


class Movie(BaseMedia):
    """
    Represents a movie in the Plex library.
    """

    duration = models.IntegerField(help_text="Duration in milliseconds")

    # Cast and crew
    directors = models.JSONField(default=list)
    writers = models.JSONField(default=list)
    actors = models.JSONField(default=list)

    # Additional metadata
    tagline = models.TextField(blank=True)

    class Meta:
        unique_together = ["library", "plex_key"]
        indexes = [
            models.Index(fields=["title"]),
            models.Index(fields=["sort_title"]),
            models.Index(fields=["date_added"]),
            models.Index(fields=["rating"]),
        ]

    def __str__(self) -> str:
        year = (
            self.originally_available.year
            if self.originally_available
            else "Unknown Year"
        )
        return f"{self.title} ({year})"


class TVShow(BaseMedia):
    """
    Represents a TV show in the Plex library.
    """

    total_seasons = models.IntegerField(default=0)
    total_episodes = models.IntegerField(default=0)
    show_status = models.CharField(max_length=50, blank=True)

    class Meta:
        unique_together = ["library", "plex_key"]
        indexes = [
            models.Index(fields=["title"]),
            models.Index(fields=["sort_title"]),
            models.Index(fields=["date_added"]),
        ]


class Season(BaseMedia):
    """
    Represents a TV show season.
    """

    show = models.ForeignKey(TVShow, on_delete=models.CASCADE, related_name="seasons")
    season_number = models.IntegerField()
    episode_count = models.IntegerField(default=0)

    class Meta:
        unique_together = ["show", "season_number"]
        ordering = ["season_number"]

    def __str__(self) -> str:
        return f"{self.show.title} - Season {self.season_number}"


class Episode(BaseMedia):
    """
    Represents a TV show episode.
    """

    season = models.ForeignKey(
        Season, on_delete=models.CASCADE, related_name="episodes"
    )
    episode_number = models.IntegerField()
    duration = models.IntegerField(help_text="Duration in milliseconds")

    # Episode-specific metadata
    directors = models.JSONField(default=list)
    writers = models.JSONField(default=list)

    class Meta:
        unique_together = ["season", "episode_number"]
        ordering = ["episode_number"]
        indexes = [
            models.Index(fields=["title"]),
            models.Index(fields=["date_added"]),
        ]

    def __str__(self) -> str:
        return f"{self.season.show.title} - S{self.season.season_number:02d}E{self.episode_number:02d} - {self.title}"
