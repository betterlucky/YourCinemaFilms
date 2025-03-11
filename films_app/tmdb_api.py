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
        # Only append the specific data we need, not everything
        'append_to_response': 'credits,release_dates,external_ids'
    }
    
    try:
        logger.debug(f"Fetching details for TMDB ID {tmdb_id} from API")
        response = requests.get(url, params=params)
        data = response.json()
        
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
        logger.error(f"Error fetching details for TMDB ID {tmdb_id}: {e}")
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
    Efficiently extracts only the fields we need from the TMDB data.
    
    Args:
        tmdb_data (dict): The movie data from TMDB
        
    Returns:
        dict: Formatted data for our Film model
    """
    # Extract only the fields we need
    formatted_data = {
        'imdb_id': tmdb_data.get('external_ids', {}).get('imdb_id', ''),
        'title': tmdb_data.get('title', ''),
        'plot': tmdb_data.get('overview', ''),
        'popularity': tmdb_data.get('popularity', 0.0),
        'runtime': f"{tmdb_data.get('runtime', 0)} min" if tmdb_data.get('runtime') else "",
        'poster_url': f"https://image.tmdb.org/t/p/w500{tmdb_data['poster_path']}" if tmdb_data.get('poster_path') else None,
    }
    
    # Extract year from release date
    if tmdb_data.get('release_date'):
        formatted_data['year'] = tmdb_data['release_date'].split('-')[0]
        # Use the main release date as UK release date if no specific UK date is found
        formatted_data['uk_release_date'] = tmdb_data['release_date']
    else:
        formatted_data['year'] = ""
        formatted_data['uk_release_date'] = None
    
    # Extract director from credits - only if credits data exists
    if 'credits' in tmdb_data and 'crew' in tmdb_data['credits']:
        directors = [crew['name'] for crew in tmdb_data['credits']['crew'] if crew['job'] == 'Director']
        formatted_data['director'] = ', '.join(directors)
    else:
        formatted_data['director'] = ""
    
    # Extract actors from credits - only if credits data exists
    if 'credits' in tmdb_data and 'cast' in tmdb_data['credits']:
        cast = [cast['name'] for cast in tmdb_data['credits']['cast'][:10]]  # Limit to top 10 cast members
        formatted_data['actors'] = ', '.join(cast)
    else:
        formatted_data['actors'] = ""
    
    # Extract genres - only if genres data exists
    if 'genres' in tmdb_data:
        genre_names = [genre['name'] for genre in tmdb_data['genres']]
        formatted_data['genres'] = ', '.join(genre_names)
    else:
        formatted_data['genres'] = ""
    
    # Extract UK certification - only if release_dates data exists
    if 'release_dates' in tmdb_data:
        formatted_data['uk_certification'] = get_uk_certification(tmdb_data['release_dates'])
    else:
        formatted_data['uk_certification'] = None
    
    # Try to find UK-specific release date - only if release_dates data exists
    if 'release_dates' in tmdb_data and 'results' in tmdb_data['release_dates']:
        for country_data in tmdb_data['release_dates']['results']:
            if country_data['iso_3166_1'] == 'GB':
                # Get the most recent release date
                for release in country_data['release_dates']:
                    if release.get('release_date'):
                        # Convert to YYYY-MM-DD format
                        from datetime import datetime
                        date_obj = datetime.fromisoformat(release['release_date'].replace('Z', '+00:00'))
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
                'id': movie.get('id')
            }
            
            # Only make an additional API call if we need more detailed information
            # that's not available in the basic results
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
                'id': movie.get('id')
            }
            
            # Only make an additional API call if we need more detailed information
            # that's not available in the basic results
            movie_details = get_movie_details(movie['id'])
            if movie_details:
                formatted_data = format_tmdb_data_for_film(movie_details)
                # Mark upcoming films as is_in_cinema=True so they appear in the cinema view
                formatted_data['is_in_cinema'] = True
                # Add popularity from the original results
                formatted_data['popularity'] = movie.get('popularity', 0.0)
                movies.append(formatted_data)
        
        logger.info(f"Processed {len(movies)} upcoming movies from page {page}")
    except Exception as e:
        logger.error(f"Error fetching upcoming movies (page {page}): {e}")
    
    return movies, total_pages 