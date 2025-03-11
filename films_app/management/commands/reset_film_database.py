from django.core.management.base import BaseCommand
from films_app.models import Film, Vote, CinemaVote, GenreTag, Activity, PageTracker
from django.db.models import Q

class Command(BaseCommand):
    help = 'Reset the film database by deleting all films and related data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm that you want to delete all films and related data',
        )
        parser.add_argument(
            '--keep-votes',
            action='store_true',
            help='Keep user votes (not recommended)',
        )

    def handle(self, *args, **options):
        confirm = options.get('confirm', False)
        keep_votes = options.get('keep_votes', False)
        
        if not confirm:
            self.stdout.write(self.style.WARNING('This command will delete all films and related data.'))
            self.stdout.write(self.style.WARNING('Run with --confirm to proceed.'))
            return
        
        # Count items before deletion
        film_count = Film.objects.count()
        vote_count = Vote.objects.count()
        cinema_vote_count = CinemaVote.objects.count()
        tag_count = GenreTag.objects.count()
        activity_count = Activity.objects.filter(
            Q(activity_type='vote') | Q(activity_type='tag')
        ).count()
        
        self.stdout.write(f'Found {film_count} films, {vote_count} votes, {cinema_vote_count} cinema votes, {tag_count} genre tags')
        
        # Delete page trackers
        PageTracker.objects.all().delete()
        self.stdout.write('Deleted all page trackers')
        
        # Delete activities related to films
        if not keep_votes:
            Activity.objects.filter(
                Q(activity_type='vote') | Q(activity_type='tag')
            ).delete()
            self.stdout.write(f'Deleted {activity_count} film-related activities')
        
        # Delete genre tags
        GenreTag.objects.all().delete()
        self.stdout.write(f'Deleted {tag_count} genre tags')
        
        # Delete votes
        if not keep_votes:
            Vote.objects.all().delete()
            self.stdout.write(f'Deleted {vote_count} votes')
            
            CinemaVote.objects.all().delete()
            self.stdout.write(f'Deleted {cinema_vote_count} cinema votes')
        
        # Delete films
        Film.objects.all().delete()
        self.stdout.write(f'Deleted {film_count} films')
        
        self.stdout.write(self.style.SUCCESS('Film database has been reset successfully.'))
        self.stdout.write(self.style.SUCCESS('Run "python manage.py update_movie_cache --force" to repopulate the database.')) 