import logging
from datetime import date, timedelta
from django.core.management.base import BaseCommand
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

    def handle(self, *args, **options):
        """Handle the command."""
        days_back = options['days']
        today = date.today()
        
        # Find films with release dates that have recently passed
        recently_released = Film.objects.filter(
            is_in_cinema=False,
            uk_release_date__lt=today,
            uk_release_date__gte=today - timedelta(days=days_back)
        )
        
        # Flag these films for status checks
        transition_count = recently_released.update(needs_status_check=True)
        
        # Also flag films that are in cinemas but have old release dates
        old_releases = Film.objects.filter(
            is_in_cinema=True,
            uk_release_date__lt=today - timedelta(days=90)  # Films released more than 90 days ago
        )
        
        old_count = old_releases.update(needs_status_check=True)
        
        # Log the results
        self.stdout.write(f'Flagged {transition_count} recently released films for status checks')
        self.stdout.write(f'Flagged {old_count} older cinema releases for status checks')
        
        # Return a string message instead of an integer
        return f"Flagged {transition_count + old_count} films for status checks" 