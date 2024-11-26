# core/templatetags/core_filters.py

from datetime import datetime

from django import template
from django.utils import timezone

register = template.Library()


@register.filter
def timesince_hours(value):
    """
    Returns the number of hours since the given datetime.

    Args:
        value: A datetime object

    Returns:
        float: Number of hours since the given datetime
    """
    if not value:
        return 0

    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except (ValueError, TypeError):
            return 0

    now = timezone.now()
    if timezone.is_naive(value):
        value = timezone.make_aware(value)

    diff = now - value
    return diff.total_seconds() / 3600
