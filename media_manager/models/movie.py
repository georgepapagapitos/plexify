# media_manager/models/movie.py

from django.db import models
from django.utils import timezone

from plex_auth.models import PlexServerConnection


class Movie(models.Model):
    # Core Plex fields
    plex_key = models.CharField(max_length=50)
    server = models.ForeignKey(
        PlexServerConnection, on_delete=models.CASCADE, related_name="movies"
    )
    title = models.CharField(max_length=255)
    year = models.IntegerField(null=True, blank=True)
    summary = models.TextField(blank=True)

    # Technical details
    duration = models.IntegerField(help_text="Duration in milliseconds")
    content_rating = models.CharField(max_length=10, blank=True)
    video_resolution = models.CharField(max_length=20, blank=True)

    # Media info
    studio = models.CharField(max_length=100, blank=True)
    rating = models.FloatField(null=True, blank=True)
    genres = models.JSONField(default=list, blank=True)
    directors = models.JSONField(default=list, blank=True)
    actors = models.JSONField(default=list, blank=True)

    # Metadata
    added_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    last_viewed_at = models.DateTimeField(null=True, blank=True)
    view_count = models.IntegerField(default=0)
    thumb_url = models.URLField(max_length=1024, blank=True)

    # Internal fields
    created_at = models.DateTimeField(default=timezone.now)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["server", "plex_key"]
        indexes = [
            models.Index(fields=["server", "plex_key"]),
            models.Index(fields=["title"]),
            models.Index(fields=["year"]),
            models.Index(fields=["content_rating"]),
            models.Index(fields=["rating"]),
            models.Index(fields=["duration"]),
            models.Index(fields=["added_at"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.year or 'N/A'})"
