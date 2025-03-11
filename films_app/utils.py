import re
import requests
import json
import os
import time
from django.conf import settings
from django.http import HttpResponse
from .models import Film, GenreTag, Vote
from .tmdb_api import get_movie_by_imdb_id, search_movies, format_tmdb_data_for_film

# List of common profanity words to filter
# This is a basic list - in a production environment, you would use a more comprehensive list
# or a dedicated profanity filter library
PROFANITY_LIST = [
    'ass', 'asshole', 'bastard', 'bitch', 'bollocks', 'bullshit',
    'cock', 'crap', 'cunt', 'damn', 'dick', 'douche', 'fag', 'faggot',
    'fuck', 'fucking', 'motherfucker', 'nigger', 'piss', 'pussy',
    'shit', 'slut', 'twat', 'wanker', 'whore'
]

def contains_profanity(text):
    """
    Check if the given text contains profanity.
    
    Args:
        text (str): The text to check for profanity
        
    Returns:
        bool: True if profanity is found, False otherwise
    """
    if not text:
        return False
    
    # Convert to lowercase for case-insensitive matching
    text_lower = text.lower()
    
    # Check for exact matches and word boundaries
    for word in PROFANITY_LIST:
        pattern = r'\b' + re.escape(word) + r'\b'
        if re.search(pattern, text_lower):
            return True
    
    return False

def filter_profanity(text):
    """
    Replace profanity in the given text with asterisks.
    
    Args:
        text (str): The text to filter
        
    Returns:
        str: The filtered text with profanity replaced by asterisks
    """
    if not text:
        return text
    
    # Convert to lowercase for case-insensitive matching
    text_lower = text.lower()
    result = text
    
    # Replace profanity with asterisks
    for word in PROFANITY_LIST:
        pattern = r'\b' + re.escape(word) + r'\b'
        matches = re.finditer(pattern, text_lower)
        
        # Process matches in reverse order to avoid index issues
        for match in reversed(list(matches)):
            start, end = match.span()
            replacement = '*' * (end - start)
            result = result[:start] + replacement + result[end:]
    
    return result

def validate_genre_tag(tag):
    """
    Validate a genre tag.
    
    Args:
        tag (str): The genre tag to validate
        
    Returns:
        tuple: (is_valid, error_message)
    """
    # Check for empty tag
    if not tag or not tag.strip():
        return False, "Genre tag cannot be empty"
    
    # Check length
    if len(tag) < 2:
        return False, "Genre tag must be at least 2 characters long"
    
    if len(tag) > 50:
        return False, "Genre tag must be at most 50 characters long"
    
    # Check for valid characters
    if not re.match(r'^[A-Za-z0-9\s\-]+$', tag):
        return False, "Genre tag can only contain letters, numbers, spaces, and hyphens"
    
    # Check for profanity
    tag_lower = tag.lower()
    for word in PROFANITY_LIST:
        if word in tag_lower:
            return False, "Genre tag contains inappropriate language"
    
    return True, ""

def fetch_and_update_film_from_tmdb(imdb_id, force_update=False):
    """
    Fetch film details from TMDB API and update or create the film in the database.
    
    Args:
        imdb_id (str): The IMDb ID of the film
        force_update (bool): Whether to force update even if the film exists
        
    Returns:
        tuple: (film, created) where film is the Film object and created is a boolean
               indicating whether the film was created
    """
    # Check if film exists in database
    film = Film.objects.filter(imdb_id=imdb_id).first()
    created = False
    
    # If film exists and we're not forcing an update, return it
    if film and not force_update:
        return film, created
    
    try:
        # Fetch from TMDB API using IMDb ID
        tmdb_data = get_movie_by_imdb_id(imdb_id)
        
        if tmdb_data:
            # Format the TMDB data for our Film model
            formatted_data = format_tmdb_data_for_film(tmdb_data)
            
            if film:
                # Update existing film
                film.title = formatted_data.get('title', film.title)
                film.year = formatted_data.get('year', film.year)
                film.poster_url = formatted_data.get('poster_url', film.poster_url)
                film.director = formatted_data.get('director', film.director)
                film.plot = formatted_data.get('plot', film.plot)
                film.genres = formatted_data.get('genres', film.genres)
                film.runtime = formatted_data.get('runtime', film.runtime)
                film.actors = formatted_data.get('actors', film.actors)
                # Add missing fields
                film.uk_certification = formatted_data.get('uk_certification', film.uk_certification)
                film.uk_release_date = formatted_data.get('uk_release_date', film.uk_release_date)
                film.popularity = formatted_data.get('popularity', film.popularity)
                film.save()
            else:
                # Create new film
                film = Film(
                    imdb_id=imdb_id,
                    title=formatted_data.get('title', ''),
                    year=formatted_data.get('year', ''),
                    poster_url=formatted_data.get('poster_url', ''),
                    director=formatted_data.get('director', ''),
                    plot=formatted_data.get('plot', ''),
                    genres=formatted_data.get('genres', ''),
                    runtime=formatted_data.get('runtime', ''),
                    actors=formatted_data.get('actors', ''),
                    uk_certification=formatted_data.get('uk_certification'),
                    uk_release_date=formatted_data.get('uk_release_date'),
                    popularity=formatted_data.get('popularity', 0)
                )
                film.save()
                created = True
                
            return film, created
        else:
            raise ValueError(f"Film not found in TMDB with IMDb ID: {imdb_id}")
    except Exception as e:
        raise ValueError(f"Error fetching film from TMDB: {str(e)}")

# Cache functions for TMDB data
def get_cache_directory():
    """Get or create the cache directory."""
    cache_dir = os.path.join(settings.BASE_DIR, 'cache')
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir

# In-memory cache for search results with timestamp
_search_results_cache = {}
# Cache expiration time in seconds (7 days)
CACHE_EXPIRATION = 7 * 86400

def get_cached_search_results(query):
    """Get cached search results if available."""
    # Check in-memory cache first (fastest)
    cache_entry = _search_results_cache.get(query)
    if cache_entry:
        timestamp, results = cache_entry
        # Check if in-memory cache is still valid
        if time.time() - timestamp < CACHE_EXPIRATION:
            return results
    
    # Check disk cache only if in-memory cache is not available or expired
    cache_dir = get_cache_directory()
    cache_file = os.path.join(cache_dir, f"search_{query.replace(' ', '_')}.json")
    
    if os.path.exists(cache_file):
        # Check if cache is fresh (less than 7 days old)
        if (os.path.getmtime(cache_file) > (time.time() - CACHE_EXPIRATION)):
            try:
                with open(cache_file, 'r') as f:
                    results = json.load(f)
                    # Update in-memory cache with timestamp
                    _search_results_cache[query] = (time.time(), results)
                    return results
            except Exception:
                # If there's an error reading the cache, return None
                return None
    
    return None

def cache_search_results(query, results):
    """Cache search results to a JSON file and in-memory."""
    # Update in-memory cache with current timestamp
    _search_results_cache[query] = (time.time(), results)
    
    # Update disk cache in a separate thread to avoid blocking
    try:
        import threading
        threading.Thread(target=_write_cache_to_disk, args=(query, results)).start()
    except ImportError:
        # If threading is not available, write directly
        _write_cache_to_disk(query, results)

def _write_cache_to_disk(query, results):
    """Write cache to disk in a separate function that can be run in a thread."""
    cache_dir = get_cache_directory()
    cache_file = os.path.join(cache_dir, f"search_{query.replace(' ', '_')}.json")
    
    try:
        with open(cache_file, 'w') as f:
            json.dump(results, f)
    except Exception:
        # Log the error but continue
        pass

def require_http_method(request, method='POST'):
    """
    Check if the request method matches the required method.
    
    Args:
        request: The HTTP request object
        method (str): The required HTTP method (default: 'POST')
        
    Returns:
        HttpResponse or None: HttpResponse with error if method doesn't match, None otherwise
    """
    if request.method != method:
        return HttpResponse(f"Method not allowed. Expected {method}.", status=405)
    return None

def validate_and_format_genre_tag(tag, user, film):
    """
    Validate and format a genre tag, checking for duplicates and existing genres.
    
    Args:
        tag (str): The genre tag to validate
        user: The user adding the tag
        film: The film to add the tag to
        
    Returns:
        tuple: (is_valid, result_or_error)
            - is_valid (bool): Whether the tag is valid
            - result_or_error: Formatted tag if valid, error message if invalid
    """
    # Basic validation
    is_valid, error_message = validate_genre_tag(tag)
    if not is_valid:
        return False, error_message
    
    # Capitalize the first letter of each word for consistency
    formatted_tag = ' '.join(word.capitalize() for word in tag.split())
    
    # Check if tag already exists for this film and user
    existing_tag = GenreTag.objects.filter(film=film, user=user, tag=formatted_tag).first()
    if existing_tag:
        return False, 'You have already added this genre tag'
    
    # Check if tag is already an official genre
    if formatted_tag in film.genre_list:
        return False, 'This genre is already listed for this film'
    
    return True, formatted_tag

def count_film_votes(film):
    """
    Get the vote count for a film.
    
    Args:
        film: The Film object
        
    Returns:
        int: The number of votes for the film
    """
    return Vote.objects.filter(film=film).count()

def get_date_range_from_period(period):
    """
    Get start and end dates based on a time period.
    
    Args:
        period (str): The time period ('week', 'month', 'year', or 'all')
        
    Returns:
        tuple: (start_date, end_date) where start_date may be None for 'all'
    """
    from django.utils import timezone
    from datetime import timedelta
    
    end_date = timezone.now()
    start_date = None
    
    if period == 'week':
        start_date = end_date - timedelta(days=7)
    elif period == 'month':
        start_date = end_date - timedelta(days=30)
    elif period == 'year':
        start_date = end_date - timedelta(days=365)
    
    return start_date, end_date

def filter_votes_by_period(period):
    """
    Filter votes based on a time period.
    
    Args:
        period (str): The time period ('week', 'month', 'year', or 'all')
        
    Returns:
        QuerySet: Filtered Vote queryset
    """
    from .models import Vote
    
    # For 'all' period, return all votes without filtering
    if period == 'all':
        return Vote.objects.all()
    
    start_date, _ = get_date_range_from_period(period)
    votes_query = Vote.objects.all()
    
    if start_date:
        votes_query = votes_query.filter(created_at__gte=start_date)
    
    return votes_query

def get_top_films_data(limit=10):
    """
    Get top films based on vote count.
    
    Args:
        limit (int): Maximum number of films to return
        
    Returns:
        QuerySet: Films ordered by vote count
    """
    from django.db.models import Count
    from .models import Film
    
    # Get films with votes, annotate with vote count, and order by vote count
    top_films = Film.objects.annotate(
        total_votes=Count('votes')
    ).filter(total_votes__gt=0).order_by('-total_votes')
    
    # Limit the results if specified
    if limit and limit > 0:
        top_films = top_films[:limit]
    
    return top_films

def get_user_votes_and_remaining(user):
    """
    Get a user's votes and the number of votes remaining.
    
    Args:
        user: The user to get votes for
        
    Returns:
        tuple: (user_votes, votes_remaining) where user_votes is a queryset of Vote objects
               and votes_remaining is an integer
    """
    from .models import Vote
    
    # Get the user's votes
    user_votes = Vote.objects.filter(user=user).select_related('film')
    
    # Calculate votes remaining (maximum 10 votes per user)
    votes_remaining = 10 - user_votes.count()
    
    return user_votes, votes_remaining

def user_can_vote(user, film):
    """
    Check if a user can vote for a film.
    
    Args:
        user: The user who wants to vote
        film: The film to vote for
        
    Returns:
        tuple: (can_vote, reason) where can_vote is a boolean and reason is a string
               explaining why the user can't vote (if applicable)
    """
    from .models import Vote
    
    # Check if user has already voted for this film
    if Vote.objects.filter(user=user, film=film).exists():
        return False, "already_voted"
    
    # Check if user has reached the maximum number of votes (10)
    if Vote.objects.filter(user=user).count() >= 10:
        return False, "max_votes_reached"
    
    # User can vote
    return True, None 