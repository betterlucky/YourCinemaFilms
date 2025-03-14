import logging
import concurrent.futures
from datetime import date, timedelta, datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from films_app.models import Film

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Update films whose release dates have passed and flag them for status checks'

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days to look back for recently released films'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=50,
            help='Number of films to process in each batch'
        )
        parser.add_argument(
            '--use_parallel',
            action='store_true',
            default=False,
            help='Use parallel processing for database operations'
        )

    def handle(self, *args, **options):
        """Handle the command."""
        days_back = options['days']
        batch_size = options['batch_size']
        use_parallel = options['use_parallel']
        today = date.today()
        
        self.stdout.write(f'Starting update_release_status with days={days_back}, batch_size={batch_size}, use_parallel={use_parallel}')
        
        # Find films with release dates that have recently passed
        recently_released = Film.objects.filter(
            is_in_cinema=False,
            uk_release_date__lt=today,
            uk_release_date__gte=today - timedelta(days=days_back)
        )
        
        recently_released_count = recently_released.count()
        self.stdout.write(f'Found {recently_released_count} recently released films')
        
        # Also find films that are in cinemas but have old release dates
        old_releases = Film.objects.filter(
            is_in_cinema=True,
            uk_release_date__lt=today - timedelta(days=90)  # Films released more than 90 days ago
        )
        
        old_releases_count = old_releases.count()
        self.stdout.write(f'Found {old_releases_count} older cinema releases')
        
        # Process films in batches if using parallel processing
        if use_parallel and (recently_released_count > 0 or old_releases_count > 0):
            self.stdout.write('Using parallel processing for updating films')
            
            # Process recently released films
            if recently_released_count > 0:
                self.stdout.write(f'Processing {recently_released_count} recently released films in parallel')
                self._process_films_in_parallel(recently_released, batch_size)
            
            # Process old releases
            if old_releases_count > 0:
                self.stdout.write(f'Processing {old_releases_count} older cinema releases in parallel')
                self._process_films_in_parallel(old_releases, batch_size)
                
            transition_count = recently_released_count
            old_count = old_releases_count
        else:
            # Flag these films for status checks using bulk update
            transition_count = recently_released.update(needs_status_check=True, last_status_check=timezone.now())
            
            # Flag old releases using bulk update
            old_count = old_releases.update(needs_status_check=True, last_status_check=timezone.now())
        
        # Log the results
        self.stdout.write(f'Flagged {transition_count} recently released films for status checks')
        self.stdout.write(f'Flagged {old_count} older cinema releases for status checks')
        
        # Return a string message instead of an integer
        return f"Flagged {transition_count + old_count} films for status checks"
    
    def _process_films_in_parallel(self, queryset, batch_size):
        """Process films in parallel using ThreadPoolExecutor.
        
        Args:
            queryset: Django queryset of films to process
            batch_size: Number of films to process in each batch
        """
        total_count = queryset.count()
        processed_count = 0
        
        # Process in batches to avoid memory issues
        for i in range(0, total_count, batch_size):
            batch = list(queryset[i:i+batch_size])
            self.stdout.write(f'Processing batch {i//batch_size + 1} of {(total_count-1)//batch_size + 1} ({len(batch)} films)')
            
            # Define a function to process a single film
            def process_film(film):
                try:
                    film.needs_status_check = True
                    film.last_status_check = timezone.now()
                    film.save(update_fields=['needs_status_check', 'last_status_check'])
                    return True
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Error processing film {film.title}: {str(e)}'))
                    return False
            
            # Use ThreadPoolExecutor for parallel processing
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(10, len(batch))) as executor:
                # Submit all films for processing
                future_to_film = {executor.submit(process_film, film): film for film in batch}
                
                # Process results as they complete
                for future in concurrent.futures.as_completed(future_to_film):
                    film = future_to_film[future]
                    try:
                        success = future.result()
                        processed_count += 1
                        if processed_count % 50 == 0:
                            self.stdout.write(f'Processed {processed_count}/{total_count} films')
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'Error processing film {film.title}: {str(e)}'))
        
        self.stdout.write(f'Processed {processed_count}/{total_count} films in parallel') 