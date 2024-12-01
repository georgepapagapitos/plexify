# media_manager/urls.py

from django.urls import path

from media_manager.views.random_movie import RandomMovieSelectView, RandomMovieView
from media_manager.views.sync import MovieSyncView, SyncStatusView, TriggerSyncView

app_name = "media_manager"

urlpatterns = [
    path("random/", RandomMovieView.as_view(), name="random_movie"),
    path("random/select/", RandomMovieSelectView.as_view(), name="random_movie_select"),
    path("sync/", MovieSyncView.as_view(), name="movie_sync"),
    path("sync/trigger/", TriggerSyncView.as_view(), name="trigger_sync"),
    path("sync/status/", SyncStatusView.as_view(), name="sync_status"),
]
