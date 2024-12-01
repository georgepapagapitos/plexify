# core/views/profile.py

import logging
from datetime import timedelta
from typing import Any, Dict, List

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.db.models import Q
from django.utils import timezone
from django.views.generic import TemplateView
import pytz

from core.models import UserActivity, UserPreference
from plex_auth.utils.exceptions import PlexManagerError
from plex_auth.utils.plex_manager import PlexManager

logger = logging.getLogger(__name__)


class ProfileView(LoginRequiredMixin, TemplateView):
    """Protected view for user profile management."""

    template_name = "core/profile.html"
    login_url = "plex_auth:login"

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """Enhance template context with comprehensive user profile data."""
        context = super().get_context_data(**kwargs)
        context["timezone_choices"] = [(tz, tz) for tz in pytz.common_timezones]
        user = self.request.user

        try:
            self._maybe_sync_servers(user)

            # Get cached server stats or compute them
            cache_key = f"server_stats_{user.id}"
            server_stats = cache.get(cache_key)

            if not server_stats:
                server_stats = self._compute_server_stats(user)
                cache.set(cache_key, server_stats, timeout=300)  # 5 minutes

            # Get user preferences
            preferences = self._get_user_preferences(user)

            # Get recent activities
            activities = self._get_recent_activities(user)

            # Format user info with proper datetime handling
            user_info = {
                "Username": user.plex_username,
                "Email": user.email,
                "Member Since": timezone.localtime(user.date_joined).strftime(
                    "%B %d, %Y"
                ),
                "Last Login": (
                    timezone.localtime(user.last_login).strftime("%B %d, %Y %I:%M %p")
                    if user.last_login
                    else "Never"
                ),
                "Account Status": "Active" if user.is_active else "Inactive",
            }

            context.update(
                {
                    "user_info": user_info,
                    "plex_info": {
                        "account_id": user.plex_account_id,
                        "thumb_url": user.thumb_url,
                        "last_synced": (
                            timezone.localtime(user.last_synced)
                            if user.last_synced
                            else None
                        ),
                        "total_servers": len(user.plex_servers.all()),
                        "active_servers": sum(
                            1
                            for s in user.plex_servers.all()
                            if s.status == "available"
                        ),
                    },
                    "server_stats": server_stats,
                    "servers": self._get_server_details(user),
                    "activities": activities,
                    "preferences": preferences,
                    "sync_status": self._get_sync_status(user),
                }
            )

            logger.info(f"Profile context retrieved for user {user.username}")

        except Exception as e:
            logger.error(f"Error fetching profile context: {str(e)}", exc_info=True)
            context["error"] = (
                "Unable to load profile information. Please try again later."
            )

        return context

    def _get_user_preferences(self, user) -> Dict[str, Any]:
        """Get user preferences including theme settings."""
        prefs, _ = UserPreference.objects.get_or_create(user=user)
        return {
            "theme": prefs.theme or "system",
            "auto_sync": prefs.auto_sync_enabled,
            "sync_interval": prefs.sync_interval,
            "notification_enabled": prefs.notification_enabled,
        }

    def _get_recent_activities(self, user, limit: int = 10) -> List[Dict[str, Any]]:
        """Get user's recent activities."""
        activities = UserActivity.objects.filter(user=user).order_by("-timestamp")[
            :limit
        ]
        return [
            {
                "timestamp": timezone.localtime(activity.timestamp),
                "description": activity.description,
                "activity_type": activity.activity_type,
            }
            for activity in activities
        ]

    def _get_sync_status(self, user) -> Dict[str, Any]:
        """Get current sync status information."""
        return {
            "is_syncing": cache.get(f"sync_in_progress_{user.id}", False),
            "last_sync": (
                timezone.localtime(user.last_synced) if user.last_synced else None
            ),
            "next_sync": self._calculate_next_sync_time(user),
        }

    def _calculate_next_sync_time(self, user) -> timezone.datetime:
        """Calculate next scheduled sync time based on user preferences."""
        prefs, _ = UserPreference.objects.get_or_create(user=user)
        if not prefs.auto_sync_enabled or not user.last_synced:
            return None

        interval_minutes = {
            "hourly": 60,
            "daily": 1440,
            "weekly": 10080,
        }.get(prefs.sync_interval, 60)

        return timezone.localtime(user.last_synced) + timedelta(
            minutes=interval_minutes
        )

    def _get_server_details(self, user) -> List[Dict[str, Any]]:
        """Get detailed information for each server."""
        servers = []
        for server in user.plex_servers.all():
            time_diff = timezone.now() - server.last_seen
            is_active = time_diff < timedelta(minutes=5)

            servers.append(
                {
                    "name": server.name,
                    "url": server.url,
                    "version": server.version,
                    "is_owned": server.is_owned,
                    "is_local": server.is_local,
                    "status": server.status,
                    "is_active": is_active,
                    "last_seen": timezone.localtime(server.last_seen),
                    "last_error": (
                        server.last_connection_error if not is_active else None
                    ),
                }
            )

        return sorted(servers, key=lambda x: (not x["is_active"], x["name"]))

    def _compute_server_stats(self, user) -> Dict[str, Any]:
        """Compute aggregate statistics across all servers."""
        stats = {
            "total_libraries": 0,
            "total_items": 0,
            "library_types": {},
            "connection_types": {"local": 0, "remote": 0},
        }

        plex_manager = PlexManager(user.plex_token)

        for server in user.plex_servers.filter(status="available"):
            try:
                libraries = plex_manager.get_libraries(server)
                stats["total_libraries"] += len(libraries)

                for lib in libraries:
                    stats["total_items"] += lib.get("count", 0)
                    lib_type = lib.get("type", "other")
                    stats["library_types"][lib_type] = (
                        stats["library_types"].get(lib_type, 0) + 1
                    )

                if server.is_local:
                    stats["connection_types"]["local"] += 1
                else:
                    stats["connection_types"]["remote"] += 1

            except PlexManagerError:
                continue

        return stats

    def _maybe_sync_servers(self, user) -> None:
        """Sync servers if needed based on last sync time."""
        if not user.last_synced or (timezone.now() - user.last_synced) > timedelta(
            minutes=5
        ):
            try:
                logger.debug(f"Syncing servers for {user.username}")
                user.sync_servers()
            except PlexManagerError as e:
                logger.warning(f"Server sync failed: {str(e)}")
