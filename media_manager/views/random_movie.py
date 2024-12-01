# media_manager/views/random_movie.py

import logging
import random

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import JsonResponse
from django.views import View
from django.views.generic import TemplateView

from media_manager.models import Movie
from media_manager.utils import MovieManager

logger = logging.getLogger(__name__)


class RandomMovieView(LoginRequiredMixin, TemplateView):
    template_name = "media_manager/random_movie.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["genres"] = Movie.objects.values_list("genres", flat=True).distinct()
        return context


class RandomMovieSelectView(LoginRequiredMixin, View):
    def get(self, request):
        try:
            # Get filter parameters
            min_rating = float(request.GET.get("min_rating", 0))
            max_duration = int(request.GET.get("max_duration", 0))
            genres = request.GET.getlist("genres", [])
            unwatched_only = request.GET.get("unwatched_only") == "true"

            # Build query
            query = Q()

            if min_rating:
                query &= Q(rating__gte=min_rating)

            if max_duration:
                query &= Q(
                    duration__lte=max_duration * 60 * 1000
                )  # Convert minutes to milliseconds

            if genres:
                genre_query = Q()
                for genre in genres:
                    genre_query |= Q(genres__contains=[genre])
                query &= genre_query

            if unwatched_only:
                query &= Q(view_count=0)

            # Get random movie
            movies = list(Movie.objects.filter(query))

            if not movies:
                return JsonResponse(
                    {
                        "status": "error",
                        "message": "No movies found matching your criteria",
                    },
                    status=404,
                )

            movie = random.choice(movies)

            return JsonResponse(
                {
                    "status": "success",
                    "movie": {
                        "title": movie.title,
                        "year": movie.year,
                        "summary": movie.summary,
                        "duration": movie.duration,
                        "rating": movie.rating,
                        "genres": movie.genres,
                        "directors": movie.directors,
                        "actors": movie.actors,
                        "thumb_url": movie.thumb_url,
                        "content_rating": movie.content_rating,
                        "view_count": movie.view_count,
                    },
                }
            )

        except Exception as e:
            logger.error(f"Error selecting random movie: {str(e)}")
            return JsonResponse(
                {"status": "error", "message": "Error selecting random movie"},
                status=500,
            )
