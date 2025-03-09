# TMDB UK Cinema Explorer - Project Context

## Project Overview
This Django application connects to The Movie Database (TMDB) API to retrieve and display information about films that are currently in UK theaters or scheduled for UK release within the next 6 months. The application includes a caching system to reduce API calls and improve performance.

## Key Features
- Displays films currently in UK theaters
- Shows films scheduled for UK release in the next 6 months
- Provides detailed film information including UK release dates and certifications
- Includes IMDB links when available
- Caches API data with both JSON and database options
- Includes a management command for scheduled daily updates

## Technical Implementation
- Django 5.1.7
- TMDB API with UK-specific parameters (region=GB, language=en-GB)
- Bootstrap 5 for responsive UI
- Two-tier caching system (JSON files and database)
- Custom management command for scheduled updates

## Project Structure
- `cinema/` - Main Django app
  - `tmdb_api.py` - API interaction functions with UK-specific parameters
  - `views.py` - View controllers with caching logic
  - `models.py` - Database models for caching
  - `urls.py` - URL routing for the cinema app
  - `templates/cinema/` - HTML templates
  - `management/commands/` - Custom commands for cache updates
- `tmdb_project/` - Django project settings
  - `settings.py` - Project settings including API keys and cache preferences
  - `urls.py` - Main URL routing

## API Configuration
- TMDB API key stored in settings.py
- UK-specific parameters:
  - `region=GB` for UK releases
  - `language=en-GB` for British English
  - `with_release_type=3` for theatrical releases
- Retrieves UK-specific release dates and certifications

## Caching System
- Two caching methods available:
  - JSON caching: Stores data in JSON files in a `cache/` directory
  - Database caching: Stores data in Django models
- Cache is updated once per day
- Cache preference configurable in settings.py
- Management command for manual or scheduled updates

## Installation and Setup
1. Create and activate a virtual environment
2. Install dependencies: `pip install django requests`
3. Configure TMDB API key in settings.py
4. Run migrations: `python manage.py migrate`
5. Update the cache: `python manage.py update_movie_cache`
6. Run the server: `python manage.py runserver`

## Next Steps/Future Improvements
- Add search functionality
- Implement filtering by genre, rating, etc.
- Add historic film browsing capabilities
- Consider supplementary data sources for additional information

---

## Appendix: Key Files and Their Paths

### Project Configuration
- `/tmdb_project/settings.py` - Main settings including API keys and cache preferences
- `/tmdb_project/urls.py` - Main URL routing

### Core Application Files
- `/cinema/apps.py` - App configuration
- `/cinema/urls.py` - URL patterns for the cinema app
- `/cinema/views.py` - View functions with caching logic
- `/cinema/models.py` - Database models for caching
- `/cinema/tmdb_api.py` - TMDB API interaction with UK-specific parameters

### Templates
- `/cinema/templates/cinema/base.html` - Base template with common elements
- `/cinema/templates/cinema/index.html` - Home page showing current and upcoming films
- `/cinema/templates/cinema/movie_detail.html` - Detailed view for a specific film
- `/cinema/templates/cinema/api_key_missing.html` - Error page for missing API key
- `/cinema/templates/cinema/movie_not_found.html` - Error page for film not found

### Management Command
- `/cinema/management/commands/update_movie_cache.py` - Command to update the cache

### Key Code Snippets

#### TMDB API UK Configuration (tmdb_api.py)
```python
def get_now_playing_movies():
    """
    Get movies that are currently playing in theaters in the UK
    """
    url = get_api_url("movie/now_playing")
    params = {
        'api_key': settings.TMDB_API_KEY,
        'language': 'en-GB',  # British English
        'region': 'GB',       # United Kingdom
        'page': 1
    }
    
    # ... rest of function
```

#### Cache Configuration (settings.py)
```python
# TMDB API Settings
TMDB_API_KEY = '6db1bf64b6f5206f5938ee20f2327f09'
TMDB_API_BASE_URL = 'https://api.themoviedb.org/3'

# Movie Cache Settings
MOVIE_CACHE_PREFERENCE = 'json'  # Options: 'json', 'db'
```

#### Cache Update Command (update_movie_cache.py)
```python
class Command(BaseCommand):
    help = 'Update the film cache with data from TMDB API'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update even if cache is recent',
        )
        parser.add_argument(
            '--cache-type',
            type=str,
            default='both',
            choices=['json', 'db', 'both'],
            help='Cache type: json, db, or both (default)',
        )
    
    # ... rest of command
```

#### UK-Specific Film Details (movie_detail.html)
```html
<div class="mb-4">
    <h5>UK Release Date:</h5>
    <p>{% if movie.uk_release_date %}{{ movie.uk_release_date }}{% else %}{{ movie.release_date }}{% endif %}</p>
    
    {% if movie.uk_certification %}
        <h5>UK Certification:</h5>
        <p>{{ movie.uk_certification }}</p>
    {% endif %}
    
    <!-- ... other details -->
</div>
``` 