# media_manager/tasks.py

import logging
from typing import Dict, List

from celery import shared_task
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from media_manager.utils import MovieManager
from plex_auth.utils.exceptions import PlexManagerError

logger = logging.getLogger(__name__)
User = get_user_model()


@shared_task(bind=True, max_retries=3)
def sync_movie_library(self, user_id: int, server_id: str, library_key: str) -> Dict:
    """
    Sync movies from a specific Plex library.
    Uses server_id (machine_identifier) and library_key to identify the library.
    """
    logger.info(
        f"Starting movie sync for user {user_id}, server {server_id}, library {library_key}"
    )

    # Create lock key for this specific library
    lock_id = f"movie_sync_{server_id}_{library_key}"

    try:
        # Check if sync is already running for this library
        if cache.get(lock_id):
            logger.warning(f"Sync already in progress for library {library_key}")
            return {"status": "skipped", "message": "Sync already in progress"}

        # Set lock for 2 hours (large libraries might take time)
        cache.set(lock_id, True, timeout=7200)

        user = User.objects.get(id=user_id)
        server_conn = user.plex_servers.get(machine_identifier=server_id)

        movie_manager = MovieManager(user.plex_token)

        with transaction.atomic():
            result = movie_manager.sync_movies_from_library(server_conn, library_key)

            logger.info(
                f"Sync completed - Added: {result['added']}, "
                f"Updated: {result['updated']}, Total: {result['total']}"
            )

            return {
                "status": "success",
                "server_name": server_conn.name,
                "library_key": library_key,
                **result,
            }

    except PlexManagerError as e:
        logger.error(f"Plex error during movie sync: {str(e)}")
        retry_in = (2**self.request.retries) * 60  # 1min, 2min, 4min
        self.retry(exc=e, countdown=retry_in)

    except Exception as e:
        logger.exception(f"Error syncing movies for library {library_key}")
        return {"status": "error", "message": str(e)}

    finally:
        cache.delete(lock_id)


@shared_task(bind=True)
def sync_all_movie_libraries(self, user_id: int) -> List[Dict]:
    """
    Sync all movie libraries for a user.
    Identifies movie libraries and triggers individual sync tasks for each.
    """
    logger.info(f"Starting sync of all movie libraries for user {user_id}")

    try:
        user = User.objects.get(id=user_id)
        results = []

        for server_conn in user.plex_servers.all():
            try:
                movie_manager = MovieManager(user.plex_token)
                libraries = movie_manager.plex_manager.get_libraries(server_conn)

                # Filter for movie libraries
                movie_libraries = [lib for lib in libraries if lib["type"] == "movie"]

                for library in movie_libraries:
                    # Trigger sync task for each movie library
                    task = sync_movie_library.delay(
                        user_id, server_conn.machine_identifier, library["key"]
                    )

                    results.append(
                        {
                            "server_name": server_conn.name,
                            "library_name": library["title"],
                            "task_id": task.id,
                        }
                    )

            except Exception as e:
                logger.error(f"Error processing server {server_conn.name}: {str(e)}")
                continue

        return results

    except Exception as e:
        logger.exception(f"Error in sync_all_movie_libraries for user {user_id}")
        return []
