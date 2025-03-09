import os
import json
import time
from django.core.management.base import BaseCommand
from django.conf import settings
from films_app.models import Film
from films_app.utils import fetch_and_update_film_from_tmdb, get_cache_directory
from films_app.tmdb_api import search_movies, get_now_playing_movies, get_upcoming_movies
from datetime import datetime

class Command(BaseCommand):
    help = 'Update the film cache with data from TMDB API'

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            '--type',
            type=str,
            choices=['all', 'db', 'json', 'cinema'],
            default='all',
            help='Type of cache to update'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update even if cache is recent'
        )
        parser.add_argument(
            '--max-pages',
            type=int,
            default=2,
            help='Maximum number of pages to process per movie type'
        )
        parser.add_argument(
            '--cache-type',
            type=str,
            default='both',
            choices=['json', 'db', 'both'],
            help='Cache type: json, db, or both (default)',
        )
        parser.add_argument(
            '--cinema-only',
            action='store_true',
            help='Only update cinema films (now playing and upcoming)',
        )

    def handle(self, *args, **options):
        """Handle the command."""
        cache_type = options['type']
        force = options['force']
        max_pages = options['max_pages']
        
        self.stdout.write(f'Starting cache update (type: {cache_type})')
        
        if cache_type in ['all', 'db']:
            self.update_db_cache(force)
        
        if cache_type in ['all', 'json']:
            self.update_json_cache(force)
        
        if cache_type in ['all', 'cinema']:
            self.update_cinema_db_cache(force, max_pages)
            self.update_cinema_json_cache(force)
        
        self.stdout.write(self.style.SUCCESS('Cache update completed'))

    def update_db_cache(self, force):
        """Update the database cache by refreshing film data."""
        self.stdout.write('Updating database cache...')
        
        # Get all films in the database
        films = Film.objects.all()
        count = films.count()
        
        if count == 0:
            self.stdout.write('No films in database to update')
            return
        
        self.stdout.write(f'Updating {count} films in database')
        
        # Update each film
        for i, film in enumerate(films):
            try:
                # Update film data from TMDB
                fetch_and_update_film_from_tmdb(film.imdb_id, force_update=force)
                self.stdout.write(f'Updated {i+1}/{count}: {film.title}')
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error updating {film.title}: {str(e)}'))
        
        self.stdout.write(self.style.SUCCESS('Database cache update completed'))

    def update_cinema_db_cache(self, force, max_pages):
        """Update the database cache with current and upcoming cinema films."""
        self.stdout.write('Updating cinema films in database...')
        
        # Reset cinema status for all films
        if force:
            Film.objects.all().update(is_in_cinema=False)
            self.stdout.write('Reset cinema status for all films')
        
        # Process now playing movies
        self.stdout.write('Fetching and processing now playing movies...')
        self._process_movie_batch('now_playing', max_pages)
        
        # Process upcoming movies
        self.stdout.write('Fetching and processing upcoming movies...')
        self._process_movie_batch('upcoming', max_pages)
        
        self.stdout.write(self.style.SUCCESS('Cinema database cache update completed'))
    
    def _process_movie_batch(self, movie_type, max_pages):
        """Process a batch of movies to reduce memory usage.
        
        Args:
            movie_type (str): Type of movies to process ('now_playing' or 'upcoming')
            max_pages (int): Maximum number of pages to process
        """
        # Get the appropriate function based on movie type
        if movie_type == 'now_playing':
            get_movies_func = get_now_playing_movies
            is_in_cinema = True
        else:  # upcoming
            get_movies_func = get_upcoming_movies
            is_in_cinema = False
        
        # Get movies one page at a time
        page = 1
        total_processed = 0
        
        while True:
            # Get a batch of movies
            movies = get_movies_func(page=page)
            
            # If no movies returned, we've processed all pages
            if not movies:
                break
            
            self.stdout.write(f'Processing {len(movies)} {movie_type} movies (page {page})')
            
            # Process each movie in the batch
            for i, movie_data in enumerate(movies):
                try:
                    imdb_id = movie_data.get('imdb_id')
                    if not imdb_id:
                        self.stdout.write(self.style.WARNING(f'Skipping movie with no IMDb ID: {movie_data.get("title")}'))
                        continue
                    
                    # Set the is_in_cinema flag based on movie type
                    movie_data['is_in_cinema'] = is_in_cinema
                    
                    # Try to get existing film or create a new one
                    film, created = Film.objects.get_or_create(
                        imdb_id=imdb_id,
                        defaults={
                            'title': movie_data.get('title', ''),
                            'year': movie_data.get('year', ''),
                            'poster_url': movie_data.get('poster_url'),
                            'director': movie_data.get('director', ''),
                            'plot': movie_data.get('plot', ''),
                            'genres': movie_data.get('genres', ''),
                            'runtime': movie_data.get('runtime', ''),
                            'actors': movie_data.get('actors', ''),
                            'is_in_cinema': movie_data.get('is_in_cinema', False),
                            'uk_certification': movie_data.get('uk_certification'),
                            'popularity': movie_data.get('popularity', 0.0),
                        }
                    )
                    
                    # Update film data if it already existed
                    if not created:
                        film.title = movie_data.get('title', film.title)
                        film.year = movie_data.get('year', film.year)
                        film.poster_url = movie_data.get('poster_url', film.poster_url)
                        film.director = movie_data.get('director', film.director)
                        film.plot = movie_data.get('plot', film.plot)
                        film.genres = movie_data.get('genres', film.genres)
                        film.runtime = movie_data.get('runtime', film.runtime)
                        film.actors = movie_data.get('actors', film.actors)
                        film.is_in_cinema = movie_data.get('is_in_cinema', film.is_in_cinema)
                        film.uk_certification = movie_data.get('uk_certification', film.uk_certification)
                        film.popularity = movie_data.get('popularity', film.popularity)
                    
                    # Update UK release date
                    if movie_data.get('uk_release_date'):
                        try:
                            film.uk_release_date = datetime.strptime(movie_data['uk_release_date'], '%Y-%m-%d').date()
                        except ValueError:
                            self.stdout.write(self.style.WARNING(f'Invalid UK release date format: {movie_data["uk_release_date"]}'))
                    
                    film.save()
                    
                    total_processed += 1
                    status = 'Created' if created else 'Updated'
                    self.stdout.write(f'{status} {total_processed}: {film.title}')
                
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Error processing movie: {str(e)}'))
            
            # Move to the next page
            page += 1
            
            # Check if we've reached the maximum number of pages
            if page > max_pages:
                break
        
        self.stdout.write(f'Processed {total_processed} {movie_type} movies')

    def update_json_cache(self, force):
        """Update the JSON cache files."""
        self.stdout.write('Updating JSON cache...')
        
        # Get cache directory
        cache_dir = get_cache_directory()
        self.stdout.write(f'Cache directory: {cache_dir}')
        
        # Check if we need to update
        cache_info_file = os.path.join(cache_dir, 'cache_info.json')
        current_time = time.time()
        
        if os.path.exists(cache_info_file) and not force:
            try:
                with open(cache_info_file, 'r') as f:
                    cache_info = json.load(f)
                
                last_update = cache_info.get('last_update', 0)
                # If cache is less than 24 hours old, skip update
                if current_time - last_update < 86400:
                    self.stdout.write('JSON cache is recent, skipping update')
                    return
            except Exception:
                # If there's an error reading the cache info, proceed with update
                pass
        
        # Update popular movies cache
        self.update_popular_movies_cache()
        
        # Update cache info
        with open(cache_info_file, 'w') as f:
            json.dump({
                'last_update': current_time
            }, f)
        
        self.stdout.write(self.style.SUCCESS('JSON cache update completed'))

    def update_cinema_json_cache(self, force):
        """Update the JSON cache for cinema films."""
        self.stdout.write('Updating cinema JSON cache...')
        
        # Get cache directory
        cache_dir = get_cache_directory()
        
        # Check if we need to update
        cinema_cache_info_file = os.path.join(cache_dir, 'cinema_cache_info.json')
        current_time = time.time()
        
        if os.path.exists(cinema_cache_info_file) and not force:
            try:
                with open(cinema_cache_info_file, 'r') as f:
                    cache_info = json.load(f)
                
                last_update = cache_info.get('last_update', 0)
                # If cache is less than 24 hours old, skip update
                if current_time - last_update < 86400:
                    self.stdout.write('Cinema JSON cache is recent, skipping update')
                    return
            except Exception:
                # If there's an error reading the cache info, proceed with update
                pass
        
        # Update now playing movies cache
        self.update_now_playing_cache()
        
        # Update upcoming movies cache
        self.update_upcoming_movies_cache()
        
        # Update cache info
        with open(cinema_cache_info_file, 'w') as f:
            json.dump({
                'last_update': current_time
            }, f)
        
        self.stdout.write(self.style.SUCCESS('Cinema JSON cache update completed'))

    def update_popular_movies_cache(self):
        """Update the cache for popular movies."""
        self.stdout.write('Updating popular movies cache...')
        
        # Get cache directory
        cache_dir = get_cache_directory()
        
        # Search for popular movies
        try:
            # Use an empty query with sort_by=popularity.desc to get popular movies
            popular_data = search_movies('', sort_by='popularity.desc')
            
            if popular_data.get('results'):
                # Format results
                results = []
                for movie in popular_data['results']:
                    formatted_movie = {
                        'imdbID': movie.get('id'),  # Using TMDB ID temporarily
                        'Title': movie.get('title', ''),
                        'Year': movie.get('release_date', '')[:4] if movie.get('release_date') else '',
                        'Poster': f"https://image.tmdb.org/t/p/w500{movie.get('poster_path')}" if movie.get('poster_path') else '',
                        'tmdb_id': movie.get('id'),
                    }
                    results.append(formatted_movie)
                
                # Save to cache
                cache_file = os.path.join(cache_dir, 'popular_movies.json')
                with open(cache_file, 'w') as f:
                    json.dump(results, f)
                
                self.stdout.write(f'Cached {len(results)} popular movies')
            else:
                self.stdout.write(self.style.WARNING('No popular movies found'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error updating popular movies cache: {str(e)}'))

    def update_now_playing_cache(self):
        """Update the cache for now playing movies."""
        self.stdout.write('Updating now playing movies cache...')
        
        # Get cache directory
        cache_dir = get_cache_directory()
        
        try:
            # Get now playing movies
            now_playing = get_now_playing_movies()
            
            if now_playing:
                # Save to cache
                cache_file = os.path.join(cache_dir, 'now_playing_movies.json')
                with open(cache_file, 'w') as f:
                    json.dump(now_playing, f)
                
                self.stdout.write(f'Cached {len(now_playing)} now playing movies')
            else:
                self.stdout.write(self.style.WARNING('No now playing movies found'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error updating now playing movies cache: {str(e)}'))

    def update_upcoming_movies_cache(self):
        """Update the cache for upcoming movies."""
        self.stdout.write('Updating upcoming movies cache...')
        
        # Get cache directory
        cache_dir = get_cache_directory()
        
        try:
            # Get upcoming movies
            upcoming = get_upcoming_movies()
            
            if upcoming:
                # Save to cache
                cache_file = os.path.join(cache_dir, 'upcoming_movies.json')
                with open(cache_file, 'w') as f:
                    json.dump(upcoming, f)
                
                self.stdout.write(f'Cached {len(upcoming)} upcoming movies')
            else:
                self.stdout.write(self.style.WARNING('No upcoming movies found'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error updating upcoming movies cache: {str(e)}')) 