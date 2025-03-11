import os
import json
import time
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db.models import Q
from films_app.models import Film, PageTracker
from films_app.utils import fetch_and_update_film_from_tmdb, get_cache_directory
from films_app.tmdb_api import search_movies, get_now_playing_movies, get_upcoming_movies, get_movie_details
from datetime import datetime, date, timedelta

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
        parser.add_argument(
            '--batch-size',
            type=int,
            default=10,
            help='Number of films to process in each batch',
        )
        parser.add_argument(
            '--batch-delay',
            type=int,
            default=2,
            help='Delay in seconds between processing batches',
        )
        parser.add_argument(
            '--prioritize-flags',
            action='store_true',
            default=True,
            help='Prioritize films flagged for status checks',
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
            self.update_cinema_db_cache(force, max_pages, options)
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

    def update_cinema_db_cache(self, force, max_pages, options):
        """Update the database cache with current and upcoming cinema films."""
        self.stdout.write('Updating cinema films in database...')
        
        # Get batch processing options
        batch_size = options.get('batch_size', 10)
        batch_delay = options.get('batch_delay', 2)
        prioritize_flags = options.get('prioritize_flags', True)
        
        # Keep track of films that are currently in cinemas or upcoming
        processed_film_ids = set()
        
        # First, process films that need status checks if prioritize_flags is True
        if prioritize_flags:
            self.stdout.write('Processing films flagged for status checks...')
            flagged_films = Film.objects.filter(needs_status_check=True)
            flagged_count = flagged_films.count()
            
            if flagged_count > 0:
                self.stdout.write(f'Found {flagged_count} films flagged for status checks')
                
                # Process flagged films in batches
                for i in range(0, flagged_count, batch_size):
                    batch = flagged_films[i:i+batch_size]
                    self.stdout.write(f'Processing batch {i//batch_size + 1} of {(flagged_count-1)//batch_size + 1}')
                    
                    for film in batch:
                        try:
                            # Get updated film data from TMDB
                            updated = self.update_film_status(film)
                            if updated:
                                processed_film_ids.add(film.imdb_id)
                        except Exception as e:
                            self.stdout.write(self.style.ERROR(f'Error updating {film.title}: {str(e)}'))
                    
                    # Add delay between batches to avoid resource exhaustion
                    if i + batch_size < flagged_count:
                        self.stdout.write(f'Waiting {batch_delay} seconds before next batch...')
                        time.sleep(batch_delay)
        
        # Reset cinema status for all films if force is True
        if force:
            Film.objects.all().update(is_in_cinema=False)
            self.stdout.write('Reset cinema status for all films')
        
        # Process now playing movies with smarter pagination
        self.stdout.write('Fetching and processing now playing movies...')
        now_playing_films = self._process_movie_batch('now_playing', max_pages, batch_size, batch_delay)
        for film in now_playing_films:
            processed_film_ids.add(film.imdb_id)
        
        # Process upcoming movies with smarter pagination, prioritizing films with closer release dates
        self.stdout.write('Fetching and processing upcoming movies...')
        # First process films releasing in the next month
        upcoming_films_soon = self._process_movie_batch('upcoming', max_pages // 2, batch_size, batch_delay, time_window_months=1)
        for film in upcoming_films_soon:
            processed_film_ids.add(film.imdb_id)
        
        # Then process films releasing in the next 6 months
        upcoming_films_later = self._process_movie_batch('upcoming', max_pages // 2, batch_size, batch_delay, time_window_months=6)
        for film in upcoming_films_later:
            processed_film_ids.add(film.imdb_id)
        
        # Log the number of films processed
        self.stdout.write(f'Processed {len(processed_film_ids)} films in total')
        
        # Handle films that have left cinemas
        if force and processed_film_ids:
            # Find films that were previously in cinemas but are no longer in the processed list
            films_left_cinemas_count = Film.objects.filter(is_in_cinema=True).exclude(imdb_id__in=processed_film_ids).update(is_in_cinema=False)
            
            if films_left_cinemas_count > 0:
                self.stdout.write(f'Updated {films_left_cinemas_count} films that have left cinemas')
        
        # Handle films with past release dates that should be in classics
        today = date.today()
        past_release_films_count = Film.objects.filter(
            is_in_cinema=False,
            uk_release_date__lt=today
        ).exclude(imdb_id__in=processed_film_ids).count()
        
        if past_release_films_count > 0:
            self.stdout.write(f'Found {past_release_films_count} films with past release dates in classics section')
        
        self.stdout.write(self.style.SUCCESS('Cinema database cache update completed'))
    
    def update_film_status(self, film):
        """Update a single film's status by checking TMDB."""
        try:
            self.stdout.write(f'Checking status for {film.title} ({film.imdb_id})')
            
            # Extract TMDB ID if this is a TMDB-prefixed ID
            tmdb_id = None
            if film.imdb_id.startswith('tmdb-'):
                tmdb_id = film.imdb_id.replace('tmdb-', '')
            
            # Get movie details from TMDB
            if tmdb_id:
                movie_details = get_movie_details(tmdb_id)
            else:
                # For IMDb IDs, we need to search by ID
                # This is a simplified approach - in a real implementation, you'd need to search by IMDb ID
                movie_details = None
            
            if movie_details:
                # Check if the film is now playing
                now_playing, _ = get_now_playing_movies(page=1)
                for movie in now_playing:
                    if (tmdb_id and str(movie.get('id')) == tmdb_id) or movie.get('imdb_id') == film.imdb_id:
                        film.is_in_cinema = True
                        film.needs_status_check = False
                        film.save()
                        self.stdout.write(f'Updated {film.title} - now in cinemas')
                        return True
                
                # If not now playing, check if it's upcoming
                upcoming, _ = get_upcoming_movies(page=1)
                for movie in upcoming:
                    if (tmdb_id and str(movie.get('id')) == tmdb_id) or movie.get('imdb_id') == film.imdb_id:
                        film.is_in_cinema = False
                        film.needs_status_check = False
                        film.save()
                        self.stdout.write(f'Updated {film.title} - upcoming release')
                        return True
                
                # If neither now playing nor upcoming, it's a classic
                film.is_in_cinema = False
                film.needs_status_check = False
                film.save()
                self.stdout.write(f'Updated {film.title} - classic film')
                return True
            else:
                # If we couldn't get movie details, mark as checked but don't change status
                film.needs_status_check = False
                film.save()
                self.stdout.write(f'Could not get details for {film.title}, marked as checked')
                return False
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error checking status for {film.title}: {str(e)}'))
            return False

    def _process_movie_batch(self, movie_type, max_pages, batch_size=10, batch_delay=2, time_window_months=None):
        """Process a batch of movies to reduce memory usage and API calls.
        
        Args:
            movie_type (str): Type of movies to process ('now_playing' or 'upcoming')
            max_pages (int): Maximum number of pages to process
            batch_size (int): Number of films to process in each batch
            batch_delay (int): Delay in seconds between processing batches
            time_window_months (int, optional): For upcoming films, the time window in months
            
        Returns:
            list: List of Film objects that were processed
        """
        # Get the appropriate function based on movie type
        if movie_type == 'now_playing':
            get_movies_func = get_now_playing_movies
            is_in_cinema = True
        else:  # upcoming
            get_movies_func = get_upcoming_movies
            # Mark upcoming films as is_in_cinema=True so they appear in the cinema view
            is_in_cinema = True
        
        # Get the next page to process from the PageTracker
        page = PageTracker.get_next_page(movie_type)
        self.stdout.write(f'Starting with page {page} for {movie_type} movies')
        
        total_processed = 0
        pages_processed = 0
        processed_films = []
        
        while pages_processed < max_pages:
            # Get a batch of movies with popularity sorting
            if movie_type == 'upcoming' and time_window_months is not None:
                movies, total_pages = get_movies_func(time_window_months=time_window_months, page=page, sort_by='popularity.desc')
            else:
                movies, total_pages = get_movies_func(page=page, sort_by='popularity.desc')
            
            # If no movies returned, we've processed all pages
            if not movies:
                self.stdout.write(f'No more movies found for {movie_type} at page {page}')
                break
            
            self.stdout.write(f'Processing {len(movies)} {movie_type} movies (page {page} of {total_pages})')
            
            # Process movies in batches to avoid resource exhaustion
            for i in range(0, len(movies), batch_size):
                batch = movies[i:i+batch_size]
                self.stdout.write(f'Processing batch {i//batch_size + 1} of {(len(movies)-1)//batch_size + 1}')
                
                # Process each movie in the batch
                for movie_data in batch:
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
                                'needs_status_check': False,  # Reset the flag since we're updating now
                            }
                        )
                        
                        # Update film data if it already existed - only update fields that are present in movie_data
                        if not created:
                            # Create a dictionary of fields to update
                            update_fields = {}
                            
                            # Only include fields that have values in movie_data
                            for field in ['title', 'year', 'poster_url', 'director', 'plot', 'genres', 
                                         'runtime', 'actors', 'is_in_cinema', 'uk_certification', 'popularity']:
                                if field in movie_data and movie_data[field] is not None:
                                    update_fields[field] = movie_data[field]
                            
                            # Always reset the needs_status_check flag
                            update_fields['needs_status_check'] = False
                            
                            # Update the film with the fields that have values
                            for field, value in update_fields.items():
                                setattr(film, field, value)
                        
                        # Update UK release date if present
                        if movie_data.get('uk_release_date'):
                            try:
                                film.uk_release_date = datetime.strptime(movie_data['uk_release_date'], '%Y-%m-%d').date()
                            except ValueError:
                                self.stdout.write(self.style.WARNING(f'Invalid UK release date format: {movie_data["uk_release_date"]}'))
                        
                        film.save()
                        processed_films.append(film)
                        
                        total_processed += 1
                        status = 'Created' if created else 'Updated'
                        self.stdout.write(f'{status} {total_processed}: {film.title}')
                    
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'Error processing movie: {str(e)}'))
                
                # Add delay between batches to avoid resource exhaustion
                if i + batch_size < len(movies):
                    self.stdout.write(f'Waiting {batch_delay} seconds before next batch...')
                    time.sleep(batch_delay)
            
            # Update the page tracker
            PageTracker.update_tracker(movie_type, page, total_pages)
            
            # Move to the next page or wrap around to page 1 if we've reached the end
            page = page + 1 if page < total_pages else 1
            pages_processed += 1
            
            # If we've wrapped around to page 1, we've processed all available pages
            if page == 1 and pages_processed < max_pages:
                self.stdout.write(f'Processed all available pages for {movie_type} movies')
                break
            
            # Add delay between pages to avoid resource exhaustion
            if pages_processed < max_pages:
                self.stdout.write(f'Waiting {batch_delay} seconds before next page...')
                time.sleep(batch_delay)
        
        self.stdout.write(f'Processed {total_processed} {movie_type} movies')
        return processed_films

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