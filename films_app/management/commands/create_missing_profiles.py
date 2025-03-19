from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from films_app.models import UserProfile

class Command(BaseCommand):
    help = 'Creates UserProfile objects for users that do not have one'

    def handle(self, *args, **options):
        users_without_profile = []
        
        for user in User.objects.all():
            # Check if profile exists using a query instead of attribute access
            if not UserProfile.objects.filter(user=user).exists():
                # Create profile if it doesn't exist
                UserProfile.objects.create(user=user)
                users_without_profile.append(user.username)
        
        if users_without_profile:
            self.stdout.write(self.style.SUCCESS(
                f'Created profiles for {len(users_without_profile)} users: {", ".join(users_without_profile)}'
            ))
        else:
            self.stdout.write(self.style.SUCCESS('All users already have profiles')) 