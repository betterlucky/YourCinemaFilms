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
        parser.add_argument(
            '--cinema-only',
            action='store_true',
            help='Only update cinema films (now playing and upcoming)',
        )

    def handle(self, *args, **options):
        force = options['force']
        cache_type = options['cache_type']
        cinema_only = options['cinema_only']
        
        self.stdout.write(self.style.SUCCESS(f'Starting cache update (type: {cache_type})'))
        
        # Update database cache if requested
        if cache_type in ['db', 'both']:
            if cinema_only:
                self.update_cinema_db_cache(force)
            else:
                self.update_db_cache(force)
                self.update_cinema_db_cache(force)
        
        # Update JSON cache if requested
        if cache_type in ['json', 'both']:
            if cinema_only:
                self.update_cinema_json_cache(force)
            else:
                self.update_json_cache(force)
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

    def update_cinema_db_cache(self, force):
        """Update the database cache with current and upcoming cinema films."""
        self.stdout.write('Updating cinema films in database...')
        
        # Reset cinema status for all films
        if force:
            Film.objects.all().update(is_in_cinema=False)
            self.stdout.write('Reset cinema status for all films')
        
        # Get now playing movies
        self.stdout.write('Fetching now playing movies...')
        now_playing = get_now_playing_movies()
        self.stdout.write(f'Found {len(now_playing)} now playing movies')
        
        # Get upcoming movies
        self.stdout.write('Fetching upcoming movies...')
        upcoming = get_upcoming_movies()
        self.stdout.write(f'Found {len(upcoming)} upcoming movies')
        
        # Combine and process all movies
        all_movies = now_playing + upcoming
        self.stdout.write(f'Processing {len(all_movies)} total cinema films')
        
        for i, movie_data in enumerate(all_movies):
            try:
                imdb_id = movie_data.get('imdb_id')
                if not imdb_id:
                    self.stdout.write(self.style.WARNING(f'Skipping movie with no IMDb ID: {movie_data.get("title")}'))
                    continue
                
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
                
                # Update UK release date
                if movie_data.get('uk_release_date'):
                    try:
                        film.uk_release_date = datetime.strptime(movie_data['uk_release_date'], '%Y-%m-%d').date()
                    except ValueError:
                        self.stdout.write(self.style.WARNING(f'Invalid UK release date format: {movie_data["uk_release_date"]}'))
                
                film.save()
                
                status = 'Created' if created else 'Updated'
                self.stdout.write(f'{status} {i+1}/{len(all_movies)}: {film.title}')
            
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error processing movie: {str(e)}'))
        
        self.stdout.write(self.style.SUCCESS('Cinema database cache update completed'))

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