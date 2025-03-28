import requests
from datetime import timedelta
from django.conf import settings
from django.db.models import Count
from django.http import JsonResponse
from django.utils import timezone
from django.contrib.auth.models import User
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.core.cache import cache

from ..models import Film, Vote, UserProfile, GenreTag
from ..utils import validate_genre_tag, filter_votes_by_period, get_cached_search_results, cache_search_results
from ..tmdb_api import search_movies
from .serializers import FilmSerializer, VoteSerializer, UserProfileSerializer, GenreTagSerializer


class FilmListAPIView(generics.ListAPIView):
    """API view to list films."""
    queryset = Film.objects.all()
    serializer_class = FilmSerializer
    permission_classes = [permissions.AllowAny]


class FilmDetailAPIView(generics.RetrieveAPIView):
    """API view to retrieve a film by IMDB ID."""
    queryset = Film.objects.all()
    serializer_class = FilmSerializer
    lookup_field = 'imdb_id'
    permission_classes = [permissions.AllowAny]


class VoteListCreateAPIView(generics.ListCreateAPIView):
    """API view to list and create votes."""
    serializer_class = VoteSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Return votes for the current user."""
        return Vote.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        """Create a new vote."""
        # Check if user has reached the maximum number of votes
        user_votes_count = Vote.objects.filter(user=self.request.user).count()
        if user_votes_count >= 10:
            return Response(
                {'error': 'You have reached the maximum number of votes (10)'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer.save(user=self.request.user)


class VoteDetailAPIView(generics.RetrieveDestroyAPIView):
    """API view to retrieve and delete a vote."""
    serializer_class = VoteSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Return votes for the current user."""
        return Vote.objects.filter(user=self.request.user)


class UserProfileAPIView(generics.RetrieveUpdateAPIView):
    """API view to retrieve and update user profile."""
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        """Return the user's profile."""
        return self.request.user.profile


class GenreTagListCreateAPIView(generics.ListCreateAPIView):
    """API view to list and create genre tags."""
    serializer_class = GenreTagSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Return genre tags for the current user."""
        return GenreTag.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        """Create a new genre tag with validation."""
        film_id = self.request.data.get('film')
        tag = self.request.data.get('tag', '').strip()
        
        # Validate tag
        is_valid, error_message = validate_genre_tag(tag)
        if not is_valid:
            return Response({'error': error_message}, status=status.HTTP_400_BAD_REQUEST)
        
        # Capitalize the first letter of each word for consistency
        tag = ' '.join(word.capitalize() for word in tag.split())
        
        # Check if tag already exists for this film and user
        film = Film.objects.get(id=film_id)
        existing_tag = GenreTag.objects.filter(film=film, user=self.request.user, tag=tag).first()
        if existing_tag:
            return Response({'error': 'You have already added this genre tag'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if tag is already an official genre
        if tag in film.genre_list:
            return Response({'error': 'This genre is already listed for this film'}, status=status.HTTP_400_BAD_REQUEST)
        
        serializer.save(user=self.request.user, tag=tag)


class GenreTagDetailAPIView(generics.RetrieveDestroyAPIView):
    """API view to retrieve and delete a genre tag."""
    serializer_class = GenreTagSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Return genre tags for the current user."""
        return GenreTag.objects.filter(user=self.request.user)


@api_view(['GET'])
def search_films(request):
    """API endpoint to search films using TMDB API."""
    query = request.query_params.get('query', '')
    
    if not query or len(query) < 3:
        return Response({'results': []})
    
    # Try to get cached results first
    cached_results = get_cached_search_results(query)
    if cached_results:
        return Response({'results': cached_results})
    
    # Fetch from TMDB API
    try:
        tmdb_data = search_movies(query)
        
        if tmdb_data.get('results'):
            # Format results to match the expected structure in templates
            results = []
            for movie in tmdb_data['results']:
                # Format each movie to match the structure expected by the client
                formatted_movie = {
                    'imdbID': movie.get('id'),  # Using TMDB ID temporarily
                    'Title': movie.get('title', ''),
                    'Year': movie.get('release_date', '')[:4] if movie.get('release_date') else '',
                    'Poster': f"https://image.tmdb.org/t/p/w500{movie.get('poster_path')}" if movie.get('poster_path') else '',
                    'tmdb_id': movie.get('id'),  # Store TMDB ID for later use
                }
                results.append(formatted_movie)
            
            # Cache the results
            cache_search_results(query, results)
            return Response({'results': results})
        else:
            return Response({'results': []})
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def charts_data(request):
    """API endpoint to get chart data."""
    # Get time period from request
    period = request.query_params.get('period', 'all')
    genre = request.query_params.get('genre', None)
    
    # Get votes filtered by period
    votes_query = filter_votes_by_period(period)
    
    # Get top films
    films_query = Film.objects.filter(votes__in=votes_query).distinct()
    
    # Filter by genre if specified
    if genre:
        # Get films with official genre
        official_genre_films = films_query.filter(genres__icontains=genre)
        
        # Get films with user tag
        user_tag_films = films_query.filter(tags__tag=genre, tags__is_approved=True)
        
        # Combine and remove duplicates
        films_query = (official_genre_films | user_tag_films).distinct()
    
    # Annotate with vote count and get top 10
    top_films = films_query.annotate(
        total_votes=Count('votes')
    ).order_by('-total_votes')[:10]
    
    # Prepare data for charts
    data = {
        'labels': [film.title for film in top_films],
        'data': [film.total_votes for film in top_films],
    }
    
    # If no films found, return empty arrays instead of null
    if not top_films:
        data = {
            'labels': [],
            'data': [],
        }
    
    return Response(data)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def genre_data(request):
    """API endpoint to get genre distribution data."""
    # Get time period from request
    period = request.query_params.get('period', 'all')
    
    # Try to get from cache first
    cache_key = f'genre_distribution_{period}'
    cached_data = cache.get(cache_key)
    if cached_data:
        return Response(cached_data)
    
    # Get votes filtered by period
    votes_query = filter_votes_by_period(period)
    
    # Get genre distribution
    genre_counts = {}
    
    # Get all films from votes
    films = Film.objects.filter(votes__in=votes_query).distinct()
    
    # Count genres (including approved user tags)
    for film in films:
        # Make sure all_genres property is available
        if not hasattr(film, 'all_genres'):
            film_genres = []
            # Add official genres
            if film.genres:
                film_genres.extend([g.strip() for g in film.genres.split(',')])
            # Add approved user tags
            film_genres.extend([tag.tag for tag in film.tags.filter(is_approved=True)])
            # Remove duplicates
            film_genres = list(set(film_genres))
        else:
            film_genres = film.all_genres
            
        for genre in film_genres:
            if genre in genre_counts:
                genre_counts[genre] += 1
            else:
                genre_counts[genre] = 1
    
    # Sort by count (descending)
    sorted_genres = dict(sorted(genre_counts.items(), key=lambda item: item[1], reverse=True))
    
    # Return top 10 genres
    top_genres = dict(list(sorted_genres.items())[:10])
    
    data = {
        'labels': list(top_genres.keys()),
        'data': list(top_genres.values()),
    }
    
    # If no genres found, return empty arrays instead of null
    if not top_genres:
        data = {
            'labels': [],
            'data': [],
        }
    
    # Cache the result for 15 minutes (900 seconds)
    cache.set(cache_key, data, 900)
    
    return Response(data)


@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def demographic_data(request):
    """API endpoint to get demographic data (admin only)."""
    # Get gender distribution
    gender_data = UserProfile.objects.exclude(gender='NS').values('gender').annotate(
        count=Count('gender')
    ).order_by('gender')
    
    # Get age distribution
    age_data = UserProfile.objects.exclude(age_range='NS').values('age_range').annotate(
        count=Count('age_range')
    ).order_by('age_range')
    
    # Prepare data for response
    gender_dict = dict(UserProfile.GENDER_CHOICES)
    age_dict = dict(UserProfile.AGE_RANGE_CHOICES)
    
    data = {
        'gender': {
            'labels': [gender_dict[g['gender']] for g in gender_data],
            'data': [g['count'] for g in gender_data],
        },
        'age': {
            'labels': [age_dict[a['age_range']] for a in age_data],
            'data': [a['count'] for a in age_data],
        }
    }
    
    return Response(data)


@api_view(['GET'])
def film_recommendations(request):
    """API endpoint to get film recommendations based on user votes."""
    if not request.user.is_authenticated:
        return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
    
    # Get user's voted films
    user_votes = Vote.objects.filter(user=request.user).select_related('film')
    
    if not user_votes:
        return Response({'message': 'Vote for some films to get recommendations'})
    
    # Get genres from user's voted films
    user_genres = {}
    for vote in user_votes:
        film = vote.film
        for genre in film.all_genres:
            if genre in user_genres:
                user_genres[genre] += 1
            else:
                user_genres[genre] = 1
    
    # Sort genres by frequency
    sorted_genres = sorted(user_genres.items(), key=lambda x: x[1], reverse=True)
    top_genres = [genre for genre, count in sorted_genres[:3]]
    
    # Get films with these genres that user hasn't voted for
    voted_film_ids = [vote.film.id for vote in user_votes]
    
    recommended_films = []
    for genre in top_genres:
        # Get films with official genre
        official_genre_films = Film.objects.filter(
            genres__icontains=genre
        ).exclude(
            id__in=voted_film_ids
        )
        
        # Get films with user tag
        user_tag_films = Film.objects.filter(
            tags__tag=genre, 
            tags__is_approved=True
        ).exclude(
            id__in=voted_film_ids
        )
        
        # Combine and remove duplicates
        genre_films = (official_genre_films | user_tag_films).distinct().annotate(
            total_votes=Count('votes')
        ).order_by('-total_votes')[:5]
        
        for film in genre_films:
            if film not in recommended_films:
                recommended_films.append(film)
    
    # Limit to 10 recommendations
    recommended_films = recommended_films[:10]
    
    # Serialize the films
    serializer = FilmSerializer(recommended_films, many=True)
    
    return Response({
        'top_genres': top_genres,
        'recommendations': serializer.data
    }) 