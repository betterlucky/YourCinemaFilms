import requests
from django.conf import settings
import logging
import os
import json
import time
from datetime import datetime, timedelta

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

def get_movie_details(tmdb_id, include_raw=False):
    """
    Get detailed information about a movie from TMDB API with UK-specific parameters.
    
    Args:
        tmdb_id (int): The TMDB ID of the movie
        include_raw (bool): Whether to include the raw API response
        
    Returns:
        dict: The movie details from TMDB
    """
    # Check in-memory cache first
    cache_key = f"tmdb_{tmdb_id}"
    if cache_key in _movie_details_cache and not include_raw:
        logger.debug(f"Using cached details for TMDB ID {tmdb_id}")
        return _movie_details_cache[cache_key]
    
    # Check disk cache
    cache_dir = os.path.join(settings.BASE_DIR, 'cache')
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = os.path.join(cache_dir, f"movie_{tmdb_id}.json")
    
    # If cache file exists and is less than 7 days old, use it
    if os.path.exists(cache_file) and not include_raw:
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
    
    # Fetch from API - Only request the fields we actually need
    url = get_api_url(f"movie/{tmdb_id}")
    params = {
        'api_key': settings.TMDB_API_KEY,
        'language': 'en-GB',  # British English
        # Always include release_dates to get certification information
        'append_to_response': 'credits,release_dates,external_ids'
    }
    
    try:
        logger.debug(f"Fetching details for TMDB ID {tmdb_id} from API")
        response = requests.get(url, params=params)
        response.raise_for_status()  # Raise an exception for HTTP errors
        data = response.json()
        
        # Log release dates information for debugging
        if 'release_dates' in data:
            logger.debug(f"Release dates data received for TMDB ID {tmdb_id}")
            if 'results' in data['release_dates']:
                gb_data = None
                for country_data in data['release_dates']['results']:
                    if country_data['iso_3166_1'] == 'GB':
                        gb_data = country_data
                        logger.debug(f"GB release data found: {gb_data}")
                        break
                
                if not gb_data:
                    logger.debug(f"No GB release data found in {[c['iso_3166_1'] for c in data['release_dates']['results']]}")
            else:
                logger.debug(f"No 'results' key in release_dates data")
        else:
            logger.debug(f"No release_dates data received for TMDB ID {tmdb_id}")
        
        # If include_raw is True, add the raw response data
        if include_raw:
            data['_raw_response'] = response.text
            data['_raw_url'] = url
            data['_raw_params'] = params
        else:
            # Only save to cache if not including raw data
            _movie_details_cache[cache_key] = data  # Update in-memory cache
            
            # Save to disk cache
            try:
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False)
            except Exception as e:
                logger.warning(f"Error writing cache file for TMDB ID {tmdb_id}: {e}")
        
        return data
    except Exception as e:
        logger.error(f"Error fetching movie details for TMDB ID {tmdb_id}: {e}")
        return None

def get_movie_by_imdb_id(imdb_id, include_raw=False):
    """
    Find a movie in TMDB using its IMDb ID.
    
    Args:
        imdb_id (str): The IMDb ID of the movie
        include_raw (bool): Whether to include the raw API response
        
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
        movie_details = get_movie_details(tmdb_id, include_raw=include_raw)
        
        if include_raw:
            # Add the find API response to the raw data
            movie_details['_raw_find_response'] = data
        
        return movie_details
    
    return None

def get_uk_certification(release_dates):
    """
    Extract the UK certification from release dates data.
    
    Args:
        release_dates (dict): The release dates data from TMDB
        
    Returns:
        str: The UK certification or None if not found
    """
    if not release_dates:
        logger.debug("No release_dates data provided")
        return None
    
    if 'results' not in release_dates:
        logger.debug("No 'results' key in release_dates data")
        return None
    
    # Log the structure of release_dates for debugging
    logger.debug(f"Release dates data contains {len(release_dates['results'])} country entries")
    
    # Find the UK release data
    uk_data = None
    for country_data in release_dates['results']:
        if country_data['iso_3166_1'] == 'GB':
            uk_data = country_data
            logger.debug(f"Found UK release data: {uk_data}")
            break
    
    if not uk_data:
        logger.debug("No UK (GB) release data found")
        return None
    
    if 'release_dates' not in uk_data or not uk_data['release_dates']:
        logger.debug("No release_dates in UK data")
        return None
    
    logger.debug(f"UK release dates: {uk_data['release_dates']}")
    
    # First try to find theatrical release certification (type 3)
    for release in uk_data['release_dates']:
        if release.get('type') == 3 and release.get('certification'):
            logger.debug(f"Found theatrical release certification: {release['certification']}")
            return release['certification']
    
    # If no theatrical release, try digital release (type 4)
    for release in uk_data['release_dates']:
        if release.get('type') == 4 and release.get('certification'):
            logger.debug(f"Found digital release certification: {release['certification']}")
            return release['certification']
    
    # If no theatrical or digital release, try physical release (type 5)
    for release in uk_data['release_dates']:
        if release.get('type') == 5 and release.get('certification'):
            logger.debug(f"Found physical release certification: {release['certification']}")
            return release['certification']
    
    # If no theatrical, digital, or physical release, try premiere (type 1)
    for release in uk_data['release_dates']:
        if release.get('type') == 1 and release.get('certification'):
            logger.debug(f"Found premiere certification: {release['certification']}")
            return release['certification']
    
    # If still no certification, try any certification
    for release in uk_data['release_dates']:
        if release.get('certification'):
            logger.debug(f"Found non-theatrical certification: {release['certification']}")
            return release['certification']
    
    logger.debug("No certification found in UK release data")
    return None

def format_tmdb_data_for_film(tmdb_data):
    """
    Format TMDB data into a dictionary suitable for creating/updating a Film model.
    
    Args:
        tmdb_data (dict): The movie details from TMDB
        
    Returns:
        dict: Formatted data for Film model
    """
    formatted_data = {
        'imdb_id': tmdb_data.get('imdb_id', ''),
        'title': tmdb_data.get('title', ''),
        'plot': tmdb_data.get('overview', ''),
        'popularity': tmdb_data.get('popularity', 0.0),
        'vote_count': tmdb_data.get('vote_count', 0),
        'vote_average': tmdb_data.get('vote_average', 0.0),
        'revenue': tmdb_data.get('revenue', 0),
    }
    
    # Extract year from release date
    release_date = tmdb_data.get('release_date', '')
    if release_date and len(release_date) >= 4:
        formatted_data['year'] = release_date[:4]
    else:
        formatted_data['year'] = ''
    
    # Format poster URL
    poster_path = tmdb_data.get('poster_path')
    if poster_path:
        formatted_data['poster_url'] = f"https://image.tmdb.org/t/p/w500{poster_path}"
    else:
        formatted_data['poster_url'] = None
    
    # Extract runtime
    runtime = tmdb_data.get('runtime')
    if runtime:
        formatted_data['runtime'] = f"{runtime} min"
    else:
        formatted_data['runtime'] = None
    
    # Extract genres
    genres = tmdb_data.get('genres', [])
    if genres:
        genre_names = [genre['name'] for genre in genres]
        formatted_data['genres'] = ', '.join(genre_names)
    else:
        formatted_data['genres'] = None
    
    # Extract director and actors from credits
    credits = tmdb_data.get('credits', {})
    
    # Get director
    directors = []
    if 'crew' in credits:
        directors = [crew['name'] for crew in credits['crew'] if crew['job'] == 'Director']
    
    if directors:
        formatted_data['director'] = ', '.join(directors)
    else:
        formatted_data['director'] = None
    
    # Get actors (top 5)
    actors = []
    if 'cast' in credits:
        actors = [cast['name'] for cast in credits['cast'][:5]]
    
    if actors:
        formatted_data['actors'] = ', '.join(actors)
    else:
        formatted_data['actors'] = None
    
    # Extract UK certification
    release_dates = tmdb_data.get('release_dates')
    uk_certification = get_uk_certification(release_dates)
    if uk_certification:
        formatted_data['uk_certification'] = uk_certification
    
    # Extract UK release date
    if release_dates and 'results' in release_dates:
        for release in release_dates['results']:
            if release.get('iso_3166_1') == 'GB':
                for release_type in release.get('release_dates', []):
                    if release_type.get('type') in [2, 3]:  # Theatrical release types
                        if release_type.get('release_date'):
                            # Convert to YYYY-MM-DD format
                            date_obj = datetime.fromisoformat(release_type['release_date'].replace('Z', '+00:00'))
                            formatted_data['uk_release_date'] = date_obj.strftime('%Y-%m-%d')
                            break
    
    return formatted_data

def get_now_playing_movies(page=1, sort_by='popularity.desc'):
    """
    Get movies that are currently playing in theaters in the UK.
    Optimized to reduce API calls and improve efficiency.
    
    Args:
        page (int, optional): Page number to fetch. Defaults to 1.
        sort_by (str, optional): How to sort the results. Defaults to 'popularity.desc'.
    
    Returns:
        list: List of movies currently in UK theaters for the specified page
        int: Total number of pages available
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Use discover endpoint for more sorting flexibility
    url = get_api_url("discover/movie")
    
    # Get current date for release date filtering
    today = datetime.now().strftime("%Y-%m-%d")
    three_months_ago = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
    
    params = {
        'api_key': settings.TMDB_API_KEY,
        'language': 'en-GB',  # British English
        'region': 'GB',       # United Kingdom
        'page': page,
        'sort_by': sort_by,   # Sort by specified parameter
        'with_release_type': '2|3',  # Theatrical release
        'release_date.lte': today,
        'release_date.gte': three_months_ago,  # Only films released in the last 3 months
        'vote_count.gte': 10  # Ensure some minimum votes for quality results
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
        
        results = data.get('results', [])
        logger.info(f"Processing {len(results)} movies from page {page} of {total_pages}")
        
        # Process each movie to get full details
        for movie in results:
            # Extract basic information from the results to avoid additional API calls when possible
            basic_data = {
                'title': movie.get('title', ''),
                'overview': movie.get('overview', ''),
                'release_date': movie.get('release_date', ''),
                'poster_path': movie.get('poster_path'),
                'popularity': movie.get('popularity', 0.0),
                'vote_count': movie.get('vote_count', 0),
                'vote_average': movie.get('vote_average', 0.0),
                'id': movie.get('id')
            }
            
            # Only make an additional API call if we need more detailed information
            # that's not available in the basic results
            movie_details = get_movie_details(movie['id'])
            if movie_details:
                formatted_data = format_tmdb_data_for_film(movie_details)
                formatted_data['is_in_cinema'] = True
                # Add popularity and vote metrics from the original results
                formatted_data['popularity'] = movie.get('popularity', 0.0)
                formatted_data['vote_count'] = movie.get('vote_count', 0)
                formatted_data['vote_average'] = movie.get('vote_average', 0.0)
                movies.append(formatted_data)
        
        logger.info(f"Processed {len(movies)} now playing movies from page {page}")
        
    except Exception as e:
        logger.error(f"Error fetching now playing movies (page {page}): {e}")
    
    return movies, total_pages

def get_upcoming_movies(time_window_months=None, page=1, sort_by='popularity.desc'):
    """
    Get movies scheduled for UK release in the next X months.
    Optimized to reduce API calls and improve efficiency.
    
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
        time_window_months = getattr(settings, 'UPCOMING_FILMS_MONTHS', 6)
    
    # Use discover endpoint for more sorting flexibility
    url = get_api_url("discover/movie")
    
    # Calculate date range for upcoming movies
    today = datetime.now().strftime("%Y-%m-%d")
    end_date = (datetime.now() + timedelta(days=30 * time_window_months)).strftime("%Y-%m-%d")
    
    params = {
        'api_key': settings.TMDB_API_KEY,
        'language': 'en-GB',  # British English
        'region': 'GB',       # United Kingdom
        'page': page,
        'sort_by': sort_by,
        'with_release_type': '2|3',  # Theatrical release
        'release_date.gte': today,
        'release_date.lte': end_date,
        'vote_count.gte': 0   # Include films with no votes yet (they're upcoming)
    }
    
    movies = []
    total_pages = 1
    
    try:
        logger.info(f"Fetching upcoming movies for next {time_window_months} months (page {page}, sort: {sort_by})")
        response = requests.get(url, params=params)
        data = response.json()
        
        # Store total pages
        total_pages = data.get('total_pages', 1)
        
        # If we've gone beyond the available pages, return empty list
        if page > total_pages:
            logger.info(f"No more pages available (requested page {page}, total pages {total_pages})")
            return [], total_pages
        
        results = data.get('results', [])
        logger.info(f"Processing {len(results)} upcoming movies from page {page} of {total_pages}")
        
        # Process each movie to get full details
        for movie in results:
            # Extract basic information from the results to avoid additional API calls when possible
            basic_data = {
                'title': movie.get('title', ''),
                'overview': movie.get('overview', ''),
                'release_date': movie.get('release_date', ''),
                'poster_path': movie.get('poster_path'),
                'popularity': movie.get('popularity', 0.0),
                'vote_count': movie.get('vote_count', 0),
                'vote_average': movie.get('vote_average', 0.0),
                'id': movie.get('id')
            }
            
            # Only make an additional API call if we need more detailed information
            movie_details = get_movie_details(movie['id'])
            if movie_details:
                formatted_data = format_tmdb_data_for_film(movie_details)
                formatted_data['is_in_cinema'] = True  # Mark as in cinema so it appears in the cinema view
                # Add popularity and vote metrics from the original results
                formatted_data['popularity'] = movie.get('popularity', 0.0)
                formatted_data['vote_count'] = movie.get('vote_count', 0)
                formatted_data['vote_average'] = movie.get('vote_average', 0.0)
                movies.append(formatted_data)
        
        logger.info(f"Processed {len(movies)} upcoming movies from page {page}")
        
    except Exception as e:
        logger.error(f"Error fetching upcoming movies (page {page}): {e}")
    
    return movies, total_pages 