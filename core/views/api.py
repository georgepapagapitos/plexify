# core/views/api.py

import json
import logging
from typing import Any, Dict

import pytz
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import ensure_csrf_cookie

from core.models import UserActivity, UserPreference
from plex_auth.tasks import sync_plex_libraries
from plex_auth.utils.exceptions import PlexManagerError

logger = logging.getLogger(__name__)


class APIView(LoginRequiredMixin, View):
    """Base API view with common functionality."""

    def json_response(self, data: Dict[str, Any], status: int = 200) -> JsonResponse:
        """Helper method to return JSON responses."""
        return JsonResponse(data, status=status)

    def error_response(self, message: str, status: int = 400) -> JsonResponse:
        """Helper method to return error responses."""
        return self.json_response(
            {"status": "error", "message": message}, status=status
        )

    def success_response(
        self, message: str, data: Dict[str, Any] = None
    ) -> JsonResponse:
        """Helper method to return success responses."""
        response_data = {"status": "success", "message": message}
        if data:
            response_data.update(data)
        return self.json_response(response_data)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class LibrarySyncView(APIView):
    """Handle manual library sync requests."""

    def post(self, request, *args, **kwargs) -> JsonResponse:
        """Start a manual sync of Plex libraries."""
        try:
            # Record the sync attempt
            UserActivity.log_activity(
                request.user, "sync", "Started manual library sync"
            )

            # Start the sync
            request.user.sync_servers()

            return self.success_response("Sync started successfully")

        except PlexManagerError as e:
            logger.error(f"Sync error for user {request.user.username}: {str(e)}")
            return self.error_response(str(e), status=500)
        except Exception as e:
            logger.exception(
                f"Unexpected error during sync for user {request.user.username}"
            )
            return self.error_response("An unexpected error occurred", status=500)


class PreferenceUpdateView(APIView):
    """Handle user preference updates."""

    def post(self, request, *args, **kwargs) -> JsonResponse:
        """Update user preferences."""
        try:
            data = json.loads(request.body)
            theme = data.get("theme")

            if not theme:
                return self.error_response("Theme preference is required")

            if theme not in dict(UserPreference.THEME_CHOICES):
                return self.error_response(
                    f'Invalid theme choice. Must be one of: {", ".join(dict(UserPreference.THEME_CHOICES).keys())}'
                )

            prefs, _ = UserPreference.objects.get_or_create(user=request.user)
            prefs.theme = theme
            prefs.save()

            # Log the preference change
            UserActivity.log_activity(
                request.user, "settings", f"Updated theme preference to {theme}"
            )

            return self.success_response("Theme updated successfully", {"theme": theme})

        except json.JSONDecodeError:
            return self.error_response("Invalid JSON data", status=400)
        except ValidationError as e:
            return self.error_response(str(e), status=400)
        except Exception as e:
            logger.exception(
                f"Error updating preferences for user {request.user.username}"
            )
            return self.error_response("Failed to update preferences", status=500)


class UserActivityView(APIView):
    """Handle user activity retrieval."""

    def get(self, request, *args, **kwargs) -> JsonResponse:
        """Get user's recent activities."""
        try:
            limit = int(request.GET.get("limit", 10))
            activities = (
                UserActivity.objects.filter(user=request.user)
                .select_related("user")
                .order_by("-timestamp")[:limit]
            )

            activity_data = [
                {
                    "timestamp": activity.timestamp.isoformat(),
                    "type": activity.activity_type,
                    "description": activity.description,
                    "metadata": activity.metadata,
                }
                for activity in activities
            ]

            return self.success_response(
                "Activities retrieved successfully", {"activities": activity_data}
            )

        except Exception as e:
            logger.exception(
                f"Error fetching activities for user {request.user.username}"
            )
            return self.error_response("Failed to fetch activities", status=500)


class AutoSyncSettingsView(APIView):
    """Handle auto-sync settings updates."""

    def post(self, request, *args, **kwargs) -> JsonResponse:
        """Update auto-sync settings and manage sync tasks."""
        try:
            data = json.loads(request.body)
            auto_sync_enabled = data.get("auto_sync_enabled", False)
            sync_interval = data.get("sync_interval", "daily")

            if sync_interval not in dict(UserPreference.SYNC_INTERVAL_CHOICES):
                return self.error_response(
                    f'Invalid sync interval. Must be one of: {", ".join(dict(UserPreference.SYNC_INTERVAL_CHOICES).keys())}'
                )

            prefs, _ = UserPreference.objects.get_or_create(user=request.user)

            # Store previous state to check if we need to handle task changes
            previous_enabled = prefs.auto_sync_enabled
            previous_interval = prefs.sync_interval

            # Update preferences
            prefs.auto_sync_enabled = auto_sync_enabled
            prefs.sync_interval = sync_interval
            prefs.save()

            # Handle task scheduling
            if auto_sync_enabled:
                if not previous_enabled or previous_interval != sync_interval:
                    self._schedule_sync_task(request.user)
            else:
                self._remove_sync_task(request.user)

            # Log the settings change
            UserActivity.log_activity(
                request.user,
                "settings",
                f'Updated auto-sync settings: {"enabled" if auto_sync_enabled else "disabled"}, {sync_interval} interval',
            )

            return self.success_response(
                "Auto-sync settings updated successfully",
                {
                    "auto_sync_enabled": auto_sync_enabled,
                    "sync_interval": sync_interval,
                    "next_sync": (
                        self._get_next_sync_time(request.user)
                        if auto_sync_enabled
                        else None
                    ),
                },
            )

        except json.JSONDecodeError:
            return self.error_response("Invalid JSON data", status=400)
        except Exception as e:
            logger.exception(
                f"Error updating auto-sync settings for user {request.user.username}"
            )
            return self.error_response(
                "Failed to update auto-sync settings", status=500
            )

    def _schedule_sync_task(self, user) -> None:
        """Schedule the next sync task based on user preferences."""
        try:
            # Clear any existing sync lock
            lock_id = f"plex_sync_{user.id}"
            cache.delete(lock_id)

            # If we've never synced or it's been longer than the interval, sync now
            should_sync_now = False
            if not user.last_synced:
                should_sync_now = True
            else:
                interval_hours = {"hourly": 1, "daily": 24, "weekly": 168}.get(
                    user.preferences.sync_interval
                )

                time_since_sync = timezone.now() - user.last_synced
                if time_since_sync.total_seconds() > (interval_hours * 3600):
                    should_sync_now = True

            if should_sync_now:
                sync_plex_libraries.delay(user.id)
                logger.info(f"Scheduled immediate sync for user {user.id}")

        except Exception as e:
            logger.error(f"Error scheduling sync task for user {user.id}: {str(e)}")
            raise

    def _remove_sync_task(self, user) -> None:
        """Remove any scheduled sync tasks for the user."""
        try:
            # Clear any existing sync lock
            lock_id = f"plex_sync_{user.id}"
            cache.delete(lock_id)

            logger.info(f"Removed sync tasks for user {user.id}")

        except Exception as e:
            logger.error(f"Error removing sync tasks for user {user.id}: {str(e)}")
            raise

    def _get_next_sync_time(self, user) -> str:
        """Calculate and return the next sync time based on settings."""
        try:
            last_sync = user.last_synced or timezone.now()
            interval_hours = {"hourly": 1, "daily": 24, "weekly": 168}.get(
                user.preferences.sync_interval
            )

            next_sync = last_sync + timezone.timedelta(hours=interval_hours)
            return next_sync.isoformat()

        except Exception as e:
            logger.error(
                f"Error calculating next sync time for user {user.id}: {str(e)}"
            )
            return None


class TimezoneUpdateView(LoginRequiredMixin, View):
    """API endpoint for updating user timezone preferences."""

    def post(self, request, *args, **kwargs):
        """Handle timezone update requests."""
        try:
            data = json.loads(request.body)
            new_timezone = data.get("timezone")

            if not new_timezone or new_timezone not in pytz.common_timezones:
                return JsonResponse(
                    {"status": "error", "message": "Invalid timezone specified"},
                    status=400,
                )

            preferences, _ = UserPreference.objects.get_or_create(user=request.user)
            preferences.timezone = new_timezone
            preferences.save()

            logger.info(
                f"User {request.user.username} updated timezone to {new_timezone}"
            )

            return JsonResponse(
                {
                    "status": "success",
                    "message": "Timezone updated successfully",
                    "data": {
                        "timezone": new_timezone,
                        "current_time": timezone.now()
                        .astimezone(pytz.timezone(new_timezone))
                        .strftime("%Y-%m-%d %I:%M %p"),
                    },
                }
            )

        except json.JSONDecodeError:
            return JsonResponse(
                {"status": "error", "message": "Invalid request data"}, status=400
            )
        except Exception as e:
            logger.error(f"Error updating timezone: {str(e)}", exc_info=True)
            return JsonResponse(
                {"status": "error", "message": "Failed to update timezone"}, status=500
            )
