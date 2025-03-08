import re
import requests
from django.conf import settings
from .models import Film

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

def fetch_and_update_film_from_omdb(imdb_id, force_update=False):
    """
    Fetch film details from OMDB API and update or create the film in the database.
    
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
    
    # Fetch from OMDB API
    api_key = settings.OMDB_API_KEY
    url = f"http://www.omdbapi.com/?apikey={api_key}&i={imdb_id}&plot=full"
    
    try:
        response = requests.get(url)
        data = response.json()
        
        if data.get('Response') == 'True':
            if film:
                # Update existing film
                film.title = data.get('Title', film.title)
                film.year = data.get('Year', film.year)
                film.poster_url = data.get('Poster', film.poster_url)
                film.director = data.get('Director', film.director)
                film.plot = data.get('Plot', film.plot)
                film.genres = data.get('Genre', film.genres)
                film.runtime = data.get('Runtime', film.runtime)
                film.actors = data.get('Actors', film.actors)
                film.save()
            else:
                # Create new film
                film = Film(
                    imdb_id=imdb_id,
                    title=data.get('Title', ''),
                    year=data.get('Year', ''),
                    poster_url=data.get('Poster', ''),
                    director=data.get('Director', ''),
                    plot=data.get('Plot', ''),
                    genres=data.get('Genre', ''),
                    runtime=data.get('Runtime', ''),
                    actors=data.get('Actors', '')
                )
                film.save()
                created = True
                
            return film, created
        else:
            raise ValueError(f"Film not found: {data.get('Error', 'Unknown error')}")
    except Exception as e:
        raise ValueError(f"Error fetching film from OMDB: {str(e)}") 