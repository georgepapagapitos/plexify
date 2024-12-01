# media_manager/views/sync.py

from celery.result import AsyncResult
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views import View
from django.views.generic import TemplateView

from media_manager.tasks import sync_all_movie_libraries, sync_movie_library
from media_manager.utils import MovieManager


class MovieSyncView(LoginRequiredMixin, TemplateView):
    template_name = "media_manager/sync.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["csrf_token"] = get_token(self.request)

        # Get all movie libraries for the user
        movie_manager = MovieManager(self.request.user.plex_token)
        server_libraries = []

        for server in self.request.user.plex_servers.all():
            try:
                libraries = movie_manager.plex_manager.get_libraries(server)
                movie_libs = [lib for lib in libraries if lib["type"] == "movie"]

                if movie_libs:
                    server_libraries.append({"server": server, "libraries": movie_libs})
            except Exception as e:
                messages.error(
                    self.request,
                    f"Error fetching libraries from {server.name}: {str(e)}",
                )

        context["server_libraries"] = server_libraries
        return context


class TriggerSyncView(LoginRequiredMixin, View):
    def post(self, request):
        sync_type = request.POST.get("sync_type")
        server_id = request.POST.get("server_id")
        library_key = request.POST.get("library_key")

        try:
            if sync_type == "all":
                task = sync_all_movie_libraries.delay(request.user.id)
                return JsonResponse(
                    {
                        "status": "success",
                        "message": "Full sync started",
                        "task_id": task.id,
                    }
                )

            elif sync_type == "library" and server_id and library_key:
                task = sync_movie_library.delay(request.user.id, server_id, library_key)
                return JsonResponse(
                    {
                        "status": "success",
                        "message": "Library sync started",
                        "task_id": task.id,
                    }
                )

            else:
                return JsonResponse(
                    {"status": "error", "message": "Invalid sync parameters"},
                    status=400,
                )

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)


class SyncStatusView(LoginRequiredMixin, View):
    def get(self, request):
        task_id = request.GET.get("task_id")
        if not task_id:
            return JsonResponse(
                {"status": "error", "message": "No task ID provided"}, status=400
            )

        result = AsyncResult(task_id)

        if result.ready():
            return JsonResponse(
                {
                    "status": "completed",
                    "result": result.get() if result.successful() else None,
                    "error": str(result.result) if result.failed() else None,
                }
            )

        return JsonResponse({"status": "pending"})
