import os
import json
import time
import concurrent.futures
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from films_app.models import Film, PageTracker
from films_app.utils import fetch_and_update_film_from_tmdb, get_cache_directory
from films_app.tmdb_api import search_movies, get_now_playing_movies, get_upcoming_movies, get_movie_details, get_movie_by_imdb_id, format_tmdb_data_for_film
from datetime import datetime, date, timedelta
from django.core.cache import cache

# Add locks for page processing
PAGE_LOCK_PREFIX = 'movie_page_lock_'
PAGE_LOCK_TIMEOUT = 300  # 5 minutes

class Command(BaseCommand):
    help = 'Update the movie cache for cinema films'

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update all films regardless of status',
        )
        parser.add_argument(
            '--max-pages',
            type=int,
            default=10,
            help='Maximum number of pages to process (0 for all)',
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
            '--time-window-months',
            type=int,
            default=6,
            help='Time window in months for upcoming films',
        )
        parser.add_argument(
            '--prioritize-flags',
            action='store_true',
            default=True,
            help='Prioritize films flagged for status checks',
        )
        parser.add_argument(
            '--use_parallel',
            action='store_true',
            default=False,
            help='Use parallel processing for API calls and database operations',
        )
        parser.add_argument(
            '--max_workers',
            type=int,
            default=None,
            help='Maximum number of worker threads for parallel processing',
        )

    def handle(self, *args, **options):
        """Handle the command."""
        # Get the options
        max_pages = options['max_pages']
        batch_size = options['batch_size']
        batch_delay = options['batch_delay']
        time_window_months = options['time_window_months']
        prioritize_flags = options['prioritize_flags']
        use_parallel = options['use_parallel']
        max_workers = options['max_workers']
        
        self.options = options  # Store options for use in other methods
        
        self.stdout.write(f'Starting update_movie_cache command with max_pages={max_pages}, batch_size={batch_size}, batch_delay={batch_delay}, time_window_months={time_window_months}, prioritize_flags={prioritize_flags}, use_parallel={use_parallel}')
        
        # Update the cinema database cache
        self.update_cinema_db_cache(
            max_pages=max_pages, 
            batch_size=batch_size, 
            batch_delay=batch_delay, 
            time_window_months=time_window_months,
            prioritize_flags=prioritize_flags,
            use_parallel=use_parallel
        )
        
        self.stdout.write(self.style.SUCCESS('Successfully updated cinema database cache'))
        return

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

    def update_cinema_db_cache(self, max_pages, batch_size, batch_delay, time_window_months, prioritize_flags, use_parallel):
        """Update the database cache with current and upcoming cinema films."""
        self.stdout.write('Updating cinema films in database...')
        
        # Calculate cutoff date for upcoming films
        today = date.today()
        cutoff_date = today + timedelta(days=30 * time_window_months)
        self.stdout.write(f'Using cutoff date: {cutoff_date} for upcoming films')
        
        # Reset cinema status for all films if force is True
        if self.options.get('force', False):
            self.stdout.write('Force reset requested - resetting cinema status for all films')
            Film.objects.all().update(is_in_cinema=False, is_upcoming=False)
        
        # Process films that need status check first if prioritize_flags is True
        if prioritize_flags:
            self.stdout.write('Prioritizing films that need status check')
            
            # Get films that need status check
            flagged_films = Film.objects.filter(needs_status_check=True)
            flagged_count = flagged_films.count()
            self.stdout.write(f'Found {flagged_count} films that need status check')
            
            if flagged_count > 0:
                # Process flagged films in batches
                processed_count = 0
                
                # Use parallel processing if enabled and there are enough films
                if use_parallel and flagged_count > 5:
                    self.stdout.write(f'Using parallel processing for {flagged_count} flagged films')
                    
                    # Process films in batches to avoid resource exhaustion
                    for i in range(0, flagged_count, batch_size):
                        batch = flagged_films[i:i+batch_size]
                        self.stdout.write(f'Processing batch {i//batch_size + 1} of {(flagged_count-1)//batch_size + 1} ({len(batch)} films)')
                        
                        # Use ThreadPoolExecutor for parallel processing
                        max_workers = self.options.get('max_workers') or max(1, min(8, len(batch)))  # Use provided max_workers or calculate based on batch size
                        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                            # Submit all films for processing
                            future_to_film = {executor.submit(self.update_film_status, film, self.options.get('force', False)): film for film in batch}
                            
                            # Process results as they complete
                            for future in concurrent.futures.as_completed(future_to_film):
                                film = future_to_film[future]
                                try:
                                    updated = future.result()
                                    processed_count += 1
                                    if processed_count % 10 == 0:
                                        self.stdout.write(f'Processed {processed_count}/{flagged_count} flagged films')
                                except Exception as e:
                                    self.stdout.write(self.style.ERROR(f'Error processing film {film.title}: {str(e)}'))
                        
                        # Add delay between batches to avoid resource exhaustion
                        if i + batch_size < flagged_count:
                            self.stdout.write(f'Waiting {batch_delay} seconds before next batch...')
                            time.sleep(batch_delay)
                else:
                    # Process films sequentially
                    for i, film in enumerate(flagged_films):
                        self.update_film_status(film, self.options.get('force', False))
                        processed_count += 1
                        
                        if processed_count % 10 == 0:
                            self.stdout.write(f'Processed {processed_count}/{flagged_count} flagged films')
                        
                        # Add delay between films to avoid resource exhaustion
                        if i < flagged_count - 1:
                            time.sleep(1)  # Short delay between individual films
                
                self.stdout.write(f'Processed {processed_count} flagged films')
        
        # Process now playing films
        self.stdout.write('Processing now playing films...')
        now_playing_films = self._process_movie_batch('now_playing', max_pages, batch_size, batch_delay)
        
        # Process upcoming films
        self.stdout.write('Processing upcoming films...')
        upcoming_films = self._process_movie_batch('upcoming', max_pages, batch_size, batch_delay, time_window_months)
        
        # Combine processed film IDs
        processed_film_ids = [film.imdb_id for film in now_playing_films + upcoming_films]
        
        # Handle films that have left cinemas or are no longer upcoming
        if self.options.get('force', False) and processed_film_ids:
            # Find films that were previously in cinemas but are no longer in the processed list
            films_left_cinemas_count = Film.objects.filter(is_in_cinema=True).exclude(imdb_id__in=processed_film_ids).update(is_in_cinema=False)
            
            # Find films that were previously upcoming but are no longer in the processed list
            films_no_longer_upcoming_count = Film.objects.filter(is_upcoming=True).exclude(imdb_id__in=processed_film_ids).update(is_upcoming=False)
            
            self.stdout.write(f'{films_left_cinemas_count} films have left cinemas')
            self.stdout.write(f'{films_no_longer_upcoming_count} films are no longer upcoming')
        
        self.stdout.write(self.style.SUCCESS('Cinema database cache update completed'))
    
    def update_film_status(self, film, force=False):
        """Update the status of a film by checking if it's in cinema or upcoming.
        
        Args:
            film (Film): The film to update
            force (bool): Whether to force update regardless of last check time
            
        Returns:
            bool: True if the film's status was updated, False otherwise
        """
        # Skip if the film was checked recently and force is False
        if not force and film.last_status_check and (timezone.now() - film.last_status_check).days < 3:
            self.stdout.write(f'Skipping status check for {film.title} - checked recently on {film.last_status_check}')
            return False
            
        try:
            # Get the IMDb ID or TMDB ID
            imdb_id = film.imdb_id
            tmdb_id = None
            
            # Check if it's a TMDB ID
            if imdb_id.startswith('tmdb-'):
                tmdb_id = imdb_id.replace('tmdb-', '')
            
            # If we have a regular IMDb ID, try to get the TMDB ID
            if not tmdb_id and not imdb_id.startswith('tmdb-'):
                # Try to get the TMDB ID from the IMDb ID
                movie_details = get_movie_by_imdb_id(imdb_id)
                if movie_details:
                    tmdb_id = movie_details.get('id')
            
            # If we have a TMDB ID, check if the film is in cinema or upcoming
            if tmdb_id:
                # Get the movie details
                movie_details = get_movie_details(tmdb_id)
                if not movie_details:
                    self.stdout.write(self.style.WARNING(f'Could not get movie details for {film.title} (TMDB ID: {tmdb_id})'))
                    film.last_status_check = timezone.now()
                    film.save(update_fields=['last_status_check'])
                    return False
                
                # Check if the film is in cinema or upcoming
                is_in_cinema = False
                is_upcoming = False
                
                # Check if the film is in cinema
                page = 1
                while page <= 5:  # Limit to 5 pages to avoid excessive API calls
                    now_playing, total_pages = get_now_playing_movies(page=page)
                    if not now_playing:
                        break
                    
                    for movie in now_playing:
                        if movie.get('id') == int(tmdb_id):
                            is_in_cinema = True
                            break
                    
                    if is_in_cinema or page >= total_pages:
                        break
                    
                    page += 1
                
                # Check if the film is upcoming
                if not is_in_cinema:
                    page = 1
                    while page <= 5:  # Limit to 5 pages to avoid excessive API calls
                        upcoming, total_pages = get_upcoming_movies(page=page)
                        if not upcoming:
                            break
                        
                        for movie in upcoming:
                            if movie.get('id') == int(tmdb_id):
                                is_upcoming = True
                                break
                        
                        if is_upcoming or page >= total_pages:
                            break
                        
                        page += 1
                
                # Update the film's status
                if film.is_in_cinema != is_in_cinema or film.is_upcoming != is_upcoming:
                    film.is_in_cinema = is_in_cinema
                    film.is_upcoming = is_upcoming
                    film.needs_status_check = False
                    film.last_status_check = timezone.now()
                    film.save()
                    
                    status = "In Cinema" if is_in_cinema else "Upcoming" if is_upcoming else "Not in Cinema"
                    self.stdout.write(f'Updated status for {film.title} to {status}')
                    return True
                else:
                    film.needs_status_check = False
                    film.last_status_check = timezone.now()
                    film.save(update_fields=['needs_status_check', 'last_status_check'])
                    self.stdout.write(f'Status unchanged for {film.title}')
                    return False
            else:
                self.stdout.write(self.style.WARNING(f'Could not get TMDB ID for {film.title} (IMDb ID: {imdb_id})'))
                film.last_status_check = timezone.now()
                film.save(update_fields=['last_status_check'])
                return False
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error updating status for {film.title}: {str(e)}'))
            film.last_status_check = timezone.now()
            film.save(update_fields=['last_status_check'])
            return False

    def get_page_lock(self, movie_type, page):
        """Get a lock for processing a specific page."""
        lock_key = f"{PAGE_LOCK_PREFIX}{movie_type}_{page}"
        if cache.add(lock_key, True, PAGE_LOCK_TIMEOUT):
            return True
        return False

    def release_page_lock(self, movie_type, page):
        """Release the lock for a specific page."""
        lock_key = f"{PAGE_LOCK_PREFIX}{movie_type}_{page}"
        cache.delete(lock_key)

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
        # Check if parallel processing is enabled
        use_parallel = self.options.get('use_parallel', False)
        
        # Calculate cutoff date for upcoming films
        today = date.today()
        cutoff_date = today + timedelta(days=30 * (time_window_months or 6))
        self.stdout.write(f'Using cutoff date: {cutoff_date} for {movie_type} movies')
        
        # Get the appropriate function based on movie type
        if movie_type == 'now_playing':
            get_movies_func = get_now_playing_movies
            is_in_cinema = True
            is_upcoming = False
        else:  # upcoming
            get_movies_func = get_upcoming_movies
            is_in_cinema = False
            is_upcoming = True
        
        # Get the first page to determine total_pages
        if movie_type == 'upcoming' and time_window_months is not None:
            first_page_movies, total_pages = get_movies_func(time_window_months=time_window_months, page=1, sort_by='popularity.desc')
        else:
            first_page_movies, total_pages = get_movies_func(page=1, sort_by='popularity.desc')
        
        self.stdout.write(f'Found {total_pages} total pages for {movie_type} movies')
        
        # Process all pages instead of a limited number
        # Use the smaller of max_pages or total_pages
        pages_to_process = min(max_pages, total_pages) if max_pages > 0 else total_pages
        self.stdout.write(f'Will process {pages_to_process} pages for {movie_type} movies')
        
        # Get the next page to process from the PageTracker
        page = 1  # Always start from page 1 to ensure we get all films
        self.stdout.write(f'Starting with page {page} for {movie_type} movies')
        
        total_processed = 0
        pages_processed = 0
        processed_films = []
        
        while pages_processed < pages_to_process:
            # Try to get a lock for this page
            if not self.get_page_lock(movie_type, page):
                self.stdout.write(f"Page {page} is already being processed, skipping...")
                time.sleep(1)
                continue

            try:
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

                    # Use parallel processing if enabled and batch is large enough
                    if use_parallel and len(batch) > 3:
                        self.stdout.write(f'Using parallel processing for batch of {len(batch)} movies')
                        max_workers = self.options.get('max_workers') or max(1, min(8, len(batch)))

                        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                            future_to_movie = {executor.submit(self.process_single_movie, movie_data, movie_type, cutoff_date): movie_data for movie_data in batch}

                            for future in concurrent.futures.as_completed(future_to_movie):
                                movie_data = future_to_movie[future]
                                try:
                                    film = future.result()
                                    if film:
                                        processed_films.append(film)
                                except Exception as e:
                                    self.stdout.write(self.style.ERROR(f'Error processing movie {movie_data.get("title", "Unknown")}: {str(e)}'))

                    # Add delay between batches
                    if i + batch_size < len(movies):
                        self.stdout.write(f'Waiting {batch_delay} seconds before next batch...')
                        time.sleep(batch_delay)

                # Update the page tracker
                PageTracker.update_tracker(movie_type, page, total_pages)

                # Move to the next page
                page = page + 1 if page < total_pages else 1
                pages_processed += 1

            finally:
                # Always release the page lock
                self.release_page_lock(movie_type, page)

            # Add delay between pages
            if pages_processed < pages_to_process and page <= total_pages:
                self.stdout.write(f'Waiting {batch_delay} seconds before next page...')
                time.sleep(batch_delay)

        self.stdout.write(f'Processed {len(processed_films)} {movie_type} movies across {pages_processed} pages')
        return processed_films

    def process_single_movie(self, movie_data, movie_type, cutoff_date):
        """Process a single movie with proper error handling."""
        try:
            # Check if the release date is beyond our cutoff
            release_date = movie_data.get('release_date')
            if release_date:
                release_date = datetime.strptime(release_date, '%Y-%m-%d').date()
                if movie_type == 'upcoming' and release_date > cutoff_date:
                    self.stdout.write(f'Skipping {movie_data.get("title")} - release date {release_date} is beyond cutoff {cutoff_date}')
                    return None

            # Get the IMDb ID or TMDB ID
            imdb_id = movie_data.get('imdb_id')
            tmdb_id = movie_data.get('id')

            # Always fetch complete movie details
            if tmdb_id:
                try:
                    complete_details = get_movie_details(tmdb_id)
                    if complete_details:
                        imdb_id = complete_details.get('imdb_id') or complete_details.get('external_ids', {}).get('imdb_id')
                        formatted_data = format_tmdb_data_for_film(complete_details)
                        movie_data.update(formatted_data)
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'Error fetching complete details for {movie_data.get("title")}: {str(e)}'))

            if not imdb_id and tmdb_id:
                imdb_id = f"tmdb-{tmdb_id}"

            if not imdb_id:
                self.stdout.write(self.style.WARNING(f'Skipping movie with no IMDb ID: {movie_data.get("title")}'))
                return None

            # Set cinema status flags
            movie_data['is_in_cinema'] = (movie_type == 'now_playing')
            movie_data['is_upcoming'] = (movie_type == 'upcoming')

            # Create or update film
            film, created = Film.objects.get_or_create(
                imdb_id=imdb_id,
                defaults=self.get_film_defaults(movie_data)
            )

            if not created:
                self.update_existing_film(film, movie_data)

            action = 'Created' if created else 'Updated'
            cert_info = f" with certification {film.uk_certification}" if film.uk_certification else " (no certification)"
            self.stdout.write(f'{action} {film.title} ({film.imdb_id}){cert_info} - {"In Cinema" if film.is_in_cinema else "Upcoming" if film.is_upcoming else "Not in Cinema"}')

            return film

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error processing movie: {str(e)}'))
            return None

    def get_film_defaults(self, movie_data):
        """Get default values for creating a new film."""
        return {
            'title': movie_data.get('title', ''),
            'year': movie_data.get('year', ''),
            'poster_url': movie_data.get('poster_url'),
            'director': movie_data.get('director', ''),
            'plot': movie_data.get('plot', ''),
            'genres': movie_data.get('genres', ''),
            'runtime': movie_data.get('runtime', ''),
            'actors': movie_data.get('actors', ''),
            'is_in_cinema': movie_data.get('is_in_cinema', False),
            'is_upcoming': movie_data.get('is_upcoming', False),
            'uk_certification': movie_data.get('uk_certification'),
            'popularity': movie_data.get('popularity', 0.0),
            'vote_count': movie_data.get('vote_count', 0),
            'vote_average': movie_data.get('vote_average', 0.0),
            'revenue': movie_data.get('revenue', 0),
            'needs_status_check': False,
            'last_status_check': timezone.now(),
        }

    def update_existing_film(self, film, movie_data):
        """Update an existing film with new data."""
        update_fields = {}
        
        for field in ['title', 'year', 'poster_url', 'director', 'plot', 'genres',
                     'runtime', 'actors', 'is_in_cinema', 'is_upcoming', 'uk_certification',
                     'popularity', 'vote_count', 'vote_average', 'revenue']:
            if field in movie_data and movie_data[field] is not None:
                update_fields[field] = movie_data[field]

        update_fields['needs_status_check'] = False
        update_fields['last_status_check'] = timezone.now()

        for field, value in update_fields.items():
            setattr(film, field, value)

        if movie_data.get('uk_release_date'):
            film.uk_release_date = movie_data['uk_release_date']

        film.save()

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

    def update_last_update_timestamp(self):
        """Update the last update timestamp."""
        self.stdout.write('Updating last update timestamp...')
        
        # Get cache directory
        cache_dir = get_cache_directory()
        
        # Check if we need to update
        cache_info_file = os.path.join(cache_dir, 'cache_info.json')
        current_time = time.time()
        
        if os.path.exists(cache_info_file):
            try:
                with open(cache_info_file, 'r') as f:
                    cache_info = json.load(f)
                
                cache_info['last_update'] = current_time
                
                with open(cache_info_file, 'w') as f:
                    json.dump(cache_info, f)
            except Exception:
                # If there's an error updating the cache info, proceed with the update
                pass
        
        self.stdout.write(self.style.SUCCESS('Last update timestamp updated')) 