# plex_auth/tasks.py

import logging
from datetime import timedelta

from celery import shared_task
from celery.schedules import crontab
from celery.utils.log import get_task_logger
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone
from plexapi.myplex import MyPlexAccount

from media_manager.tasks import sync_all_movie_libraries

from .utils.exceptions import PlexManagerError

logger = get_task_logger(__name__)
User = get_user_model()
logger = logging.getLogger(__name__)


@shared_task
def update_server_connections(user_id: int) -> dict:
    """Update server connection URLs for a user."""
    logger.info(f"Starting server connection update for user_id: {user_id}")

    try:
        user = get_user_model().objects.get(id=user_id)
        logger.info(f"Found user: {user.username}")

        account = MyPlexAccount(token=user.plex_token)
        resources = account.resources()
        logger.info(f"Found {len(resources)} Plex resources")

        updated_count = 0
        for resource in resources:
            try:
                # Skip non-server devices
                if not resource.provides == "server":
                    continue

                server_conn = user.plex_servers.get(
                    machine_identifier=resource.clientIdentifier
                )

                # Get external URL first (usually ends with the public IP)
                external_url = next(
                    (
                        conn.uri
                        for conn in resource.connections
                        if "174-20-197-189" in conn.uri
                    ),
                    None,
                )

                # If no external URL, get any URL
                if not external_url and resource.connections:
                    external_url = resource.connections[0].uri

                if external_url:
                    logger.info(f"Updating {resource.name} with URL: {external_url}")
                    server_conn.url = external_url
                    server_conn.save()
                    updated_count += 1

            except Exception as e:
                logger.error(f"Error updating server {resource.name}: {str(e)}")
                continue

        return {
            "status": "success",
            "updated_count": updated_count,
            "message": f"Updated {updated_count} servers",
        }

    except Exception as e:
        logger.error(f"Error updating server connections: {str(e)}")
        return {"status": "error", "error": str(e)}


@shared_task(bind=True, max_retries=3)
def sync_plex_libraries(self, user_id: int) -> dict:
    """
    Synchronize Plex libraries for a specific user.

    Args:
        user_id: ID of the user whose libraries need syncing

    Returns:
        dict: Result of the sync operation
    """
    logger.info(f"Starting library sync for user_id: {user_id}")

    try:
        # Get cache lock to prevent multiple syncs
        lock_id = f"plex_sync_{user_id}"
        if cache.get(lock_id):
            logger.warning(f"Sync already in progress for user_id: {user_id}")
            return {"status": "skipped", "message": "Sync already in progress"}

        # Set lock for 30 minutes
        cache.set(lock_id, True, timeout=1800)

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            logger.error(f"User {user_id} not found")
            return {"status": "error", "message": "User not found"}

        # Perform the sync
        user.sync_servers()

        # Update last_synced timestamp
        user.last_synced = timezone.now()
        user.save(update_fields=["last_synced"])

        logger.info(f"Successfully completed sync for user_id: {user_id}")
        return {
            "status": "success",
            "message": "Library sync completed successfully",
            "timestamp": user.last_synced.isoformat(),
        }

    except PlexManagerError as e:
        logger.error(f"Plex sync error for user {user_id}: {str(e)}")
        # Retry with exponential backoff if it's a Plex-related error
        retry_in = (2**self.request.retries) * 60  # 1min, 2min, 4min
        self.retry(exc=e, countdown=retry_in)

    except Exception as e:
        logger.exception(f"Unexpected error during sync for user {user_id}")
        return {"status": "error", "message": f"Sync failed: {str(e)}"}

    finally:
        # Always clear the lock
        cache.delete(lock_id)


@shared_task
def schedule_user_syncs():
    """
    Schedule sync tasks for all users based on their preferences.
    Runs periodically to ensure sync schedules are up to date.
    """
    logger.info("Scheduling user sync tasks")

    try:
        for user in User.objects.select_related("preferences"):
            try:
                prefs = user.preferences
                if not prefs.auto_sync_enabled:
                    continue

                # Calculate next sync time based on interval
                last_sync = user.last_synced or timezone.now()
                interval_hours = {"hourly": 1, "daily": 24, "weekly": 168}.get(
                    prefs.sync_interval
                )

                next_sync = last_sync + timedelta(hours=interval_hours)

                # If next sync is in the past, sync now
                if next_sync <= timezone.now():
                    sync_plex_libraries.delay(user.id)
                    logger.info(f"Triggered immediate sync for user {user.id}")

            except Exception as e:
                logger.error(f"Error scheduling sync for user {user.id}: {str(e)}")
                continue

        return {"status": "success", "message": "Sync scheduling completed"}

    except Exception as e:
        logger.exception("Error in schedule_user_syncs")
        return {"status": "error", "message": str(e)}


# Register periodic tasks
def setup_periodic_tasks(sender, **kwargs):
    """
    Set up periodic tasks using Celery beat.
    """
    # Check and schedule user syncs every 15 minutes
    sender.add_periodic_task(
        900.0,  # 15 minutes in seconds
        schedule_user_syncs.s(),
        name="schedule_user_syncs",
    )

    # Add movie sync task - run daily during off-peak hours
    sender.add_periodic_task(
        crontab(hour=3, minute=0),  # Run at 3 AM
        sync_all_movie_libraries.s(),
        name="daily_movie_sync",
    )
