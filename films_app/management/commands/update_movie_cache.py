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
    help = 'Update the movie cache for cinema films'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update all films',
        )
        parser.add_argument(
            '--max-pages',
            type=int,
            default=10,
            help='Maximum number of pages to process (0 for all pages)',
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
            '--time-window',
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
            '--all-pages',
            action='store_true',
            help='Process all available pages (overrides max-pages)',
        )

    def handle(self, *args, **options):
        """Handle the command execution."""
        force = options.get('force', False)
        max_pages = options.get('max_pages', 10)
        all_pages = options.get('all_pages', False)
        
        # If all_pages is True, set max_pages to 0 to process all pages
        if all_pages:
            max_pages = 0
            self.stdout.write('All pages option selected - will process all available pages')
        
        # Calculate dynamic max_pages based on the current date
        # More pages during peak movie seasons (summer and winter holidays)
        current_month = datetime.now().month
        if current_month in [5, 6, 7, 8, 11, 12] and max_pages > 0:  # Summer and winter months
            max_pages = max(max_pages, 15)  # Increase pages during peak seasons
            self.stdout.write(f'Peak movie season detected - increasing max pages to {max_pages}')
        
        # Check if we're near the beginning of the month when new releases often come out
        current_day = datetime.now().day
        if current_day <= 7 and max_pages > 0:  # First week of the month
            max_pages = max(max_pages, 12)  # Increase pages for new releases
            self.stdout.write(f'Beginning of month detected - increasing max pages to {max_pages}')
        
        # Check if it's a weekend when more people watch movies
        if datetime.now().weekday() >= 4 and max_pages > 0:  # Friday, Saturday, Sunday
            max_pages = max(max_pages, 10)  # Increase pages for weekends
            self.stdout.write(f'Weekend detected - increasing max pages to {max_pages}')
        
        if max_pages == 0:
            self.stdout.write('Using unlimited pages - will process all available pages')
        else:
            self.stdout.write(f'Using max_pages: {max_pages}')
        
        # Update the database cache
        self.update_cinema_db_cache(force, max_pages, options)
        
        # Update the last update timestamp
        self.update_last_update_timestamp()
        
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

    def update_cinema_db_cache(self, force, max_pages, options):
        """Update the database cache with current and upcoming cinema films."""
        self.stdout.write('Updating cinema films in database...')
        
        # Get batch processing options
        batch_size = options.get('batch_size', 10)
        batch_delay = options.get('batch_delay', 2)
        prioritize_flags = options.get('prioritize_flags', True)
        
        # Calculate cutoff date for upcoming films
        today = date.today()
        time_window_months = options.get('time_window', 6)
        cutoff_date = today + timedelta(days=30 * time_window_months)
        self.stdout.write(f'Using cutoff date: {cutoff_date} for upcoming films')
        
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
            self.stdout.write('Force reset requested - resetting cinema status for all films')
            Film.objects.all().update(is_in_cinema=False, is_upcoming=False)
            self.stdout.write('Reset cinema status for all films')
        
        # Process now playing movies with smarter pagination
        self.stdout.write('Fetching and processing now playing movies...')
        # Set max_pages to 0 to process all pages
        now_playing_films = self._process_movie_batch('now_playing', max_pages, batch_size, batch_delay)
        for film in now_playing_films:
            processed_film_ids.add(film.imdb_id)
        
        # Process upcoming movies with smarter pagination, prioritizing films with closer release dates
        self.stdout.write('Fetching and processing upcoming movies...')
        # First process films releasing in the next month - set max_pages to 0 to process all pages
        upcoming_films_soon = self._process_movie_batch('upcoming', max_pages // 2, batch_size, batch_delay, time_window_months=1)
        for film in upcoming_films_soon:
            processed_film_ids.add(film.imdb_id)
        
        # Then process films releasing in the next 6 months - set max_pages to 0 to process all pages
        upcoming_films_later = self._process_movie_batch('upcoming', max_pages // 2, batch_size, batch_delay, time_window_months=time_window_months)
        for film in upcoming_films_later:
            processed_film_ids.add(film.imdb_id)
        
        # Log the number of films processed
        self.stdout.write(f'Processed {len(processed_film_ids)} films in total')
        
        # Handle films that have left cinemas or are no longer upcoming
        if force and processed_film_ids:
            # Find films that were previously in cinemas but are no longer in the processed list
            films_left_cinemas_count = Film.objects.filter(is_in_cinema=True).exclude(imdb_id__in=processed_film_ids).update(is_in_cinema=False)
            
            # Find films that were previously upcoming but are no longer in the processed list
            films_no_longer_upcoming_count = Film.objects.filter(is_upcoming=True).exclude(imdb_id__in=processed_film_ids).update(is_upcoming=False)
            
            if films_left_cinemas_count > 0:
                self.stdout.write(f'Updated {films_left_cinemas_count} films that have left cinemas')
            
            if films_no_longer_upcoming_count > 0:
                self.stdout.write(f'Updated {films_no_longer_upcoming_count} films that are no longer upcoming')
        
        # Print summary statistics
        now_playing_count = Film.objects.filter(is_in_cinema=True).count()
        upcoming_count = Film.objects.filter(is_upcoming=True).count()
        self.stdout.write(f'Films currently in cinemas: {now_playing_count}')
        self.stdout.write(f'Upcoming films (next {time_window_months} months): {upcoming_count}')
        
        self.stdout.write(self.style.SUCCESS('Cinema database cache update completed'))
    
    def update_film_status(self, film):
        """Update a single film's status by checking TMDB."""
        try:
            self.stdout.write(f'Checking status for {film.title} ({film.imdb_id})')
            
            # Extract TMDB ID if available
            tmdb_id = None
            if film.imdb_id.startswith('tt'):
                # This is an IMDb ID, need to look up TMDB ID
                pass
            elif film.imdb_id.startswith('tmdb-'):
                # This is a TMDB ID
                tmdb_id = film.imdb_id.replace('tmdb-', '')
            
            # Get movie details from TMDB
            movie_details = None
            if tmdb_id:
                movie_details = get_movie_details(tmdb_id)
            
            # Check if film is in now playing
            found_in_now_playing = False
            page = 1
            max_pages = 5  # Check up to 5 pages
            
            while page <= max_pages:
                now_playing, total_pages = get_now_playing_movies(page=page)
                if not now_playing:
                    break
                
                for movie in now_playing:
                    # Check if this is our film
                    if (tmdb_id and str(movie.get('id')) == tmdb_id) or movie.get('imdb_id') == film.imdb_id:
                        self.stdout.write(f'Found {film.title} in now playing (page {page})')
                        film.is_in_cinema = True
                        film.is_upcoming = False
                        film.needs_status_check = False
                        film.save()
                        return True
                
                if page >= total_pages:
                    break
                page += 1
            
            # Check if film is in upcoming
            found_in_upcoming = False
            page = 1
            max_pages = 10  # Check more pages for upcoming
            cutoff_date = date.today() + timedelta(days=180)  # 6 months from now
            
            while page <= max_pages:
                upcoming, total_pages = get_upcoming_movies(page=page)
                if not upcoming:
                    break
                
                for movie in upcoming:
                    # Check if this is our film
                    if (tmdb_id and str(movie.get('id')) == tmdb_id) or movie.get('imdb_id') == film.imdb_id:
                        # Check if release date is within our window
                        release_date = movie.get('release_date')
                        if release_date:
                            release_date = datetime.strptime(release_date, '%Y-%m-%d').date()
                            if release_date <= cutoff_date:
                                self.stdout.write(f'Found {film.title} in upcoming (page {page})')
                                film.is_in_cinema = False
                                film.is_upcoming = True
                                film.needs_status_check = False
                                film.save()
                                return True
                
                if page >= total_pages:
                    break
                page += 1
            
            # If not found in either, mark as not in cinema and not upcoming
            self.stdout.write(f'Film {film.title} not found in now playing or upcoming')
            film.is_in_cinema = False
            film.is_upcoming = False
            film.needs_status_check = False
            film.save()
            return True
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error updating status for {film.title}: {str(e)}'))
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
                        # Check if the release date is beyond our cutoff
                        release_date = movie_data.get('release_date')
                        if release_date:
                            release_date = datetime.strptime(release_date, '%Y-%m-%d').date()
                            if movie_type == 'upcoming' and release_date > cutoff_date:
                                self.stdout.write(f'Skipping {movie_data.get("title")} - release date {release_date} is beyond cutoff {cutoff_date}')
                                continue
                        
                        # Get the IMDb ID or TMDB ID
                        imdb_id = movie_data.get('imdb_id')
                        tmdb_id = movie_data.get('id')
                        
                        # Always fetch complete movie details to ensure we have certification information
                        if tmdb_id:
                            self.stdout.write(f'Fetching complete details for {movie_data.get("title")} (TMDB ID: {tmdb_id})')
                            try:
                                complete_details = get_movie_details(tmdb_id)
                                if complete_details:
                                    # Get IMDb ID from complete details
                                    imdb_id = complete_details.get('imdb_id') or complete_details.get('external_ids', {}).get('imdb_id')
                                    
                                    # Update movie_data with complete details
                                    formatted_data = format_tmdb_data_for_film(complete_details)
                                    
                                    # Log certification information
                                    uk_certification = formatted_data.get('uk_certification')
                                    if uk_certification:
                                        self.stdout.write(f'Found UK certification for {movie_data.get("title")}: {uk_certification}')
                                    else:
                                        self.stdout.write(f'No UK certification found for {movie_data.get("title")}')
                                        
                                        # Debug the release_dates structure to help diagnose certification issues
                                        release_dates = complete_details.get('release_dates')
                                        if release_dates and 'results' in release_dates:
                                            gb_data = None
                                            for country_data in release_dates['results']:
                                                if country_data['iso_3166_1'] == 'GB':
                                                    gb_data = country_data
                                                    break
                                            
                                            if gb_data:
                                                self.stdout.write(f'GB release data found: {gb_data}')
                                            else:
                                                self.stdout.write(f'No GB release data found in {[c["iso_3166_1"] for c in release_dates["results"]]}')
                                        else:
                                            self.stdout.write(f'No release_dates data structure found or invalid format')
                                    
                                    movie_data.update(formatted_data)
                            except Exception as e:
                                self.stdout.write(self.style.WARNING(f'Error fetching complete details: {str(e)}'))
                        
                        # If still no IMDb ID, use TMDB ID with prefix
                        if not imdb_id and tmdb_id:
                            imdb_id = f"tmdb-{tmdb_id}"
                            self.stdout.write(f'Using TMDB ID format: {imdb_id} for {movie_data.get("title")}')
                        
                        if not imdb_id:
                            self.stdout.write(self.style.WARNING(f'Skipping movie with no IMDb ID: {movie_data.get("title")}'))
                            continue
                        
                        # Set the cinema status flags based on movie type
                        movie_data['is_in_cinema'] = is_in_cinema
                        movie_data['is_upcoming'] = is_upcoming
                        
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
                                'is_upcoming': movie_data.get('is_upcoming', False),
                                'uk_certification': movie_data.get('uk_certification'),
                                'popularity': movie_data.get('popularity', 0.0),
                                'vote_count': movie_data.get('vote_count', 0),
                                'vote_average': movie_data.get('vote_average', 0.0),
                                'revenue': movie_data.get('revenue', 0),
                                'needs_status_check': False,  # Reset the flag since we're updating now
                            }
                        )
                        
                        # Update film data if it already existed - only update fields that are present in movie_data
                        if not created:
                            # Create a dictionary of fields to update
                            update_fields = {}
                            
                            # Only include fields that have values in movie_data
                            for field in ['title', 'year', 'poster_url', 'director', 'plot', 'genres', 
                                         'runtime', 'actors', 'is_in_cinema', 'is_upcoming', 'uk_certification', 
                                         'popularity', 'vote_count', 'vote_average', 'revenue']:
                                if field in movie_data and movie_data[field] is not None:
                                    update_fields[field] = movie_data[field]
                            
                            # Always reset the needs_status_check flag
                            update_fields['needs_status_check'] = False
                            
                            # Update the film with the fields that have values
                            for field, value in update_fields.items():
                                setattr(film, field, value)
                        
                        # Update UK release date if present
                        if movie_data.get('uk_release_date'):
                            film.uk_release_date = movie_data['uk_release_date']
                        
                        # Save the film
                        film.save()
                        processed_films.append(film)
                        
                        action = 'Created' if created else 'Updated'
                        cert_info = f" with certification {film.uk_certification}" if film.uk_certification else " (no certification)"
                        self.stdout.write(f'{action} {film.title} ({film.imdb_id}){cert_info} - {"In Cinema" if film.is_in_cinema else "Upcoming" if film.is_upcoming else "Not in Cinema"}')
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'Error processing movie: {str(e)}'))
                
                # Add delay between batches to avoid resource exhaustion
                if i + batch_size < len(movies):
                    self.stdout.write(f'Waiting {batch_delay} seconds before next batch...')
                    time.sleep(batch_delay)
            
            # Update the page tracker
            PageTracker.update_tracker(movie_type, page, total_pages)
            
            # Move to the next page or wrap around to page 1
            page = page + 1 if page < total_pages else 1
            pages_processed += 1
            
            # Add delay between pages to avoid resource exhaustion
            if pages_processed < pages_to_process and page <= total_pages:
                self.stdout.write(f'Waiting {batch_delay} seconds before next page...')
                time.sleep(batch_delay)
        
        self.stdout.write(f'Processed {len(processed_films)} {movie_type} movies across {pages_processed} pages')
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