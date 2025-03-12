from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db.utils import IntegrityError

class Command(BaseCommand):
    help = 'Creates a superuser with predefined credentials'

    def handle(self, *args, **options):
        username = 'admin'
        email = 'admin@example.com'
        password = 'pw7443'

        try:
            superuser = User.objects.create_superuser(
                username=username,
                email=email,
                password=password
            )
            self.stdout.write(self.style.SUCCESS(f"Superuser '{username}' created successfully!"))
        except IntegrityError:
            # If user already exists, update the password
            superuser = User.objects.get(username=username)
            superuser.set_password(password)
            superuser.is_superuser = True
            superuser.is_staff = True
            superuser.email = email
            superuser.save()
            self.stdout.write(self.style.SUCCESS(f"Superuser '{username}' already exists. Password updated."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error creating superuser: {str(e)}")) 