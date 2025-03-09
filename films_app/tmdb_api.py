import requests
from django.conf import settings
import logging
import os
import json
import time

logger = logging.getLogger(__name__)

# In-memory cache for movie details to reduce API calls during a single run
_movie_details_cache = {}

def sort_and_limit_films(films, limit=None, sort_by='popularity'):
    """
    Sort a list of films by the specified attribute and limit the results.
    
    Args:
        films (list): List of film dictionaries
        limit (int, optional): Maximum number of films to return
        sort_by (str, optional): Attribute to sort by, defaults to 'popularity'
        
    Returns:
        list: Sorted and limited list of films
    """
    logger.info(f"Sorting {len(films)} films by {sort_by} and limiting to {limit if limit else 'all'}")
    
    # Sort the films by the specified attribute in descending order
    sorted_films = sorted(films, key=lambda x: x.get(sort_by, 0), reverse=True)
    
    # Limit the results if specified
    if limit and limit > 0:
        return sorted_films[:limit]
    
    return sorted_films

def get_api_url(endpoint):
    """
    Construct the full URL for a TMDB API endpoint.
    
    Args:
        endpoint (str): The API endpoint to access
        
    Returns:
        str: The full URL for the API request
    """
    base_url = "https://api.themoviedb.org/3"
    return f"{base_url}/{endpoint}"

def search_movies(query, sort_by=None):
    """
    Search for movies using the TMDB API with UK-specific parameters.
    
    Args:
        query (str): The search query
        sort_by (str, optional): Sort parameter (e.g., 'popularity.desc')
        
    Returns:
        dict: The search results from TMDB
    """
    # If query is empty and sort_by is provided, use discover endpoint for popular movies
    if not query and sort_by:
        url = get_api_url("discover/movie")
    else:
        url = get_api_url("search/movie")
    
    params = {
        'api_key': settings.TMDB_API_KEY,
        'language': 'en-GB',  # British English
        'region': 'GB',       # United Kingdom
        'page': 1,
        'include_adult': False
    }
    
    # Add query parameter for search
    if query:
        params['query'] = query
    
    # Add sort_by parameter if provided
    if sort_by:
        params['sort_by'] = sort_by
    
    response = requests.get(url, params=params)
    return response.json()

def get_movie_details(tmdb_id):
    """
    Get detailed information about a movie from TMDB API with UK-specific parameters.
    
    Args:
        tmdb_id (int): The TMDB ID of the movie
        
    Returns:
        dict: The movie details from TMDB
    """
    # Check in-memory cache first
    cache_key = f"tmdb_{tmdb_id}"
    if cache_key in _movie_details_cache:
        logger.debug(f"Using cached details for TMDB ID {tmdb_id}")
        return _movie_details_cache[cache_key]
    
    # Check disk cache
    cache_dir = os.path.join(settings.BASE_DIR, 'cache')
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = os.path.join(cache_dir, f"movie_{tmdb_id}.json")
    
    # If cache file exists and is less than 7 days old, use it
    if os.path.exists(cache_file):
        file_age = time.time() - os.path.getmtime(cache_file)
        if file_age < 7 * 24 * 60 * 60:  # 7 days in seconds
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    logger.debug(f"Using disk cache for TMDB ID {tmdb_id}")
                    data = json.load(f)
                    _movie_details_cache[cache_key] = data  # Update in-memory cache
                    return data
            except Exception as e:
                logger.warning(f"Error reading cache file for TMDB ID {tmdb_id}: {e}")
    
    # Fetch from API
    url = get_api_url(f"movie/{tmdb_id}")
    params = {
        'api_key': settings.TMDB_API_KEY,
        'language': 'en-GB',  # British English
        'append_to_response': 'credits,release_dates,external_ids'
    }
    
    try:
        logger.debug(f"Fetching details for TMDB ID {tmdb_id} from API")
        response = requests.get(url, params=params)
        data = response.json()
        
        # Save to cache
        _movie_details_cache[cache_key] = data  # Update in-memory cache
        
        # Save to disk cache
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Error writing cache file for TMDB ID {tmdb_id}: {e}")
        
        return data
    except Exception as e:
        logger.error(f"Error fetching details for TMDB ID {tmdb_id}: {e}")
        return None

def get_movie_by_imdb_id(imdb_id):
    """
    Find a movie in TMDB using its IMDb ID.
    
    Args:
        imdb_id (str): The IMDb ID of the movie
        
    Returns:
        dict: The movie details from TMDB
    """
    url = get_api_url("find/" + imdb_id)
    params = {
        'api_key': settings.TMDB_API_KEY,
        'language': 'en-GB',  # British English
        'external_source': 'imdb_id'
    }
    
    response = requests.get(url, params=params)
    data = response.json()
    
    # The find endpoint returns results categorized by media type
    movie_results = data.get('movie_results', [])
    
    if movie_results:
        # Get the first movie result's TMDB ID
        tmdb_id = movie_results[0]['id']
        # Get full movie details using the TMDB ID
        return get_movie_details(tmdb_id)
    
    return None

def get_uk_certification(release_dates):
    """
    Extract the UK certification from release dates data.
    
    Args:
        release_dates (dict): The release dates data from TMDB
        
    Returns:
        str: The UK certification or None if not found
    """
    if not release_dates or 'results' not in release_dates:
        return None
    
    # Find the UK release data
    for country_data in release_dates['results']:
        if country_data['iso_3166_1'] == 'GB':
            # Get the certification from the most recent release date
            for release in country_data['release_dates']:
                if release.get('certification'):
                    return release['certification']
    
    return None

def format_tmdb_data_for_film(tmdb_data):
    """
    Format TMDB movie data to match our Film model structure.
    
    Args:
        tmdb_data (dict): The movie data from TMDB
        
    Returns:
        dict: Formatted data for our Film model
    """
    # Extract IMDb ID from external IDs
    imdb_id = tmdb_data.get('external_ids', {}).get('imdb_id', '')
    
    # Extract director from credits
    director = ""
    if 'credits' in tmdb_data and 'crew' in tmdb_data['credits']:
        directors = [crew['name'] for crew in tmdb_data['credits']['crew'] if crew['job'] == 'Director']
        director = ', '.join(directors)
    
    # Extract actors from credits
    actors = ""
    if 'credits' in tmdb_data and 'cast' in tmdb_data['credits']:
        cast = [cast['name'] for cast in tmdb_data['credits']['cast'][:10]]  # Limit to top 10 cast members
        actors = ', '.join(cast)
    
    # Extract genres
    genres = ""
    if 'genres' in tmdb_data:
        genre_names = [genre['name'] for genre in tmdb_data['genres']]
        genres = ', '.join(genre_names)
    
    # Extract UK certification
    uk_certification = None
    if 'release_dates' in tmdb_data:
        uk_certification = get_uk_certification(tmdb_data['release_dates'])
    
    # Format runtime
    runtime = f"{tmdb_data.get('runtime', 0)} min" if tmdb_data.get('runtime') else ""
    
    # Construct poster URL
    poster_url = None
    if tmdb_data.get('poster_path'):
        poster_url = f"https://image.tmdb.org/t/p/w500{tmdb_data['poster_path']}"
    
    # Format year from release date
    year = ""
    uk_release_date = None
    if tmdb_data.get('release_date'):
        year = tmdb_data['release_date'].split('-')[0]
        # Use the main release date as UK release date if no specific UK date is found
        uk_release_date = tmdb_data['release_date']
    
    # Try to find UK-specific release date
    if 'release_dates' in tmdb_data and 'results' in tmdb_data['release_dates']:
        for country_data in tmdb_data['release_dates']['results']:
            if country_data['iso_3166_1'] == 'GB':
                # Get the most recent release date
                for release in country_data['release_dates']:
                    if release.get('release_date'):
                        # Convert to YYYY-MM-DD format
                        from datetime import datetime
                        date_obj = datetime.fromisoformat(release['release_date'].replace('Z', '+00:00'))
                        uk_release_date = date_obj.strftime('%Y-%m-%d')
                        break
    
    # Extract popularity score
    popularity = tmdb_data.get('popularity', 0.0)
    
    return {
        'imdb_id': imdb_id,
        'title': tmdb_data.get('title', ''),
        'year': year,
        'poster_url': poster_url,
        'director': director,
        'plot': tmdb_data.get('overview', ''),
        'genres': genres,
        'runtime': runtime,
        'actors': actors,
        'uk_certification': uk_certification,
        'uk_release_date': uk_release_date,
        'popularity': popularity
    }

def get_now_playing_movies(page=1, sort_by='popularity.desc'):
    """
    Get movies that are currently playing in theaters in the UK.
    
    Args:
        page (int, optional): Page number to fetch. Defaults to 1.
        sort_by (str, optional): How to sort the results. Defaults to 'popularity.desc'.
    
    Returns:
        list: List of movies currently in UK theaters for the specified page
        int: Total number of pages available
    """
    import logging
    logger = logging.getLogger(__name__)
    
    url = get_api_url("movie/now_playing")
    params = {
        'api_key': settings.TMDB_API_KEY,
        'language': 'en-GB',  # British English
        'region': 'GB',       # United Kingdom
        'page': page,
        'sort_by': sort_by    # Sort by popularity by default
    }
    
    movies = []
    total_pages = 1
    
    try:
        logger.info(f"Fetching now playing movies page {page} (sort: {sort_by})")
        response = requests.get(url, params=params)
        data = response.json()
        
        # Store total pages
        total_pages = data.get('total_pages', 1)
        
        # If we've gone beyond the available pages, return empty list
        if page > total_pages:
            logger.info(f"No more pages available (requested page {page}, total pages {total_pages})")
            return [], total_pages
        
        logger.info(f"Processing {len(data.get('results', []))} movies from page {page} of {total_pages}")
        
        # Process each movie to get full details
        for movie in data.get('results', []):
            movie_details = get_movie_details(movie['id'])
            if movie_details:
                formatted_data = format_tmdb_data_for_film(movie_details)
                formatted_data['is_in_cinema'] = True
                # Add popularity from the original results
                formatted_data['popularity'] = movie.get('popularity', 0.0)
                movies.append(formatted_data)
        
        logger.info(f"Processed {len(movies)} now playing movies from page {page}")
    except Exception as e:
        logger.error(f"Error fetching now playing movies (page {page}): {e}")
    
    return movies, total_pages

def get_upcoming_movies(time_window_months=None, page=1, sort_by='popularity.desc'):
    """
    Get movies scheduled for UK release in the next X months.
    
    Args:
        time_window_months (int, optional): Number of months to look ahead.
            If None, uses the UPCOMING_FILMS_MONTHS setting.
        page (int, optional): Page number to fetch. Defaults to 1.
        sort_by (str, optional): How to sort the results. Defaults to 'popularity.desc'.
        
    Returns:
        list: List of upcoming movies for the specified page
        int: Total number of pages available
    """
    from datetime import datetime, timedelta
    import logging
    logger = logging.getLogger(__name__)
    
    # Use the setting if time_window_months is not provided
    if time_window_months is None:
        time_window_months = settings.UPCOMING_FILMS_MONTHS
    
    url = get_api_url("movie/upcoming")
    
    # Calculate date range (today to X months from now)
    today = datetime.now().strftime('%Y-%m-%d')
    future_date = (datetime.now() + timedelta(days=30*time_window_months)).strftime('%Y-%m-%d')
    
    params = {
        'api_key': settings.TMDB_API_KEY,
        'language': 'en-GB',  # British English
        'region': 'GB',       # United Kingdom
        'page': page,
        'release_date.gte': today,
        'release_date.lte': future_date,
        'sort_by': sort_by    # Sort by popularity by default
    }
    
    movies = []
    total_pages = 1
    
    try:
        logger.info(f"Fetching upcoming movies page {page} (window: {time_window_months} months, sort: {sort_by})")
        response = requests.get(url, params=params)
        data = response.json()
        
        # Store total pages
        total_pages = data.get('total_pages', 1)
        
        # If we've gone beyond the available pages, return empty list
        if page > total_pages:
            logger.info(f"No more pages available (requested page {page}, total pages {total_pages})")
            return [], total_pages
        
        logger.info(f"Processing {len(data.get('results', []))} movies from page {page} of {total_pages}")
        
        # Process each movie to get full details
        for movie in data.get('results', []):
            movie_details = get_movie_details(movie['id'])
            if movie_details:
                formatted_data = format_tmdb_data_for_film(movie_details)
                formatted_data['is_in_cinema'] = False  # Not in cinema yet
                # Add popularity from the original results
                formatted_data['popularity'] = movie.get('popularity', 0.0)
                movies.append(formatted_data)
        
        logger.info(f"Processed {len(movies)} upcoming movies from page {page}")
    except Exception as e:
        logger.error(f"Error fetching upcoming movies (page {page}): {e}")
    
    return movies, total_pages 