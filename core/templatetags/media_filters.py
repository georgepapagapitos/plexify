# core/templatetags/media_filters.py

from datetime import timedelta

from django import template
from django.utils.timezone import datetime, make_aware

register = template.Library()


@register.filter
def duration_format(milliseconds):
    """Convert milliseconds to human-readable format using timedelta"""
    if not milliseconds:
        return ""

    # Convert milliseconds to timedelta
    duration = timedelta(milliseconds=int(milliseconds))

    # Extract hours and minutes
    total_seconds = duration.total_seconds()
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)

    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


@register.filter
def timestamp_to_datetime(timestamp):
    """Convert a Unix timestamp to a timezone-aware datetime object."""
    if not timestamp:
        return None

    try:
        # Convert timestamp to datetime using timedelta
        dt = datetime.fromtimestamp(0) + timedelta(seconds=float(timestamp))
        # Make timezone-aware
        return make_aware(dt)
    except (ValueError, TypeError):
        return None
