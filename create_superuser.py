#!/usr/bin/env python
"""
Script to create a Django superuser programmatically.
This can be used on Render where shell access might be limited.
"""

import os
import sys
import django
from django.contrib.auth.models import User
from django.db.utils import IntegrityError

def main():
    """Create a Django superuser programmatically."""
    print("Starting superuser creation process...")
    
    # Set up Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'films_project.settings')
    django.setup()
    
    # Define superuser credentials
    SUPERUSER_USERNAME = 'admin'
    SUPERUSER_PASSWORD = 'pw7443'
    SUPERUSER_EMAIL = 'admin@example.com'  # You can change this if needed
    
    try:
        # Check if the user already exists
        if User.objects.filter(username=SUPERUSER_USERNAME).exists():
            print(f"Superuser '{SUPERUSER_USERNAME}' already exists.")
            # If user already exists, update the password
            superuser = User.objects.get(username=SUPERUSER_USERNAME)
            superuser.set_password(SUPERUSER_PASSWORD)
            superuser.is_superuser = True
            superuser.is_staff = True
            superuser.email = SUPERUSER_EMAIL
            superuser.save()
            print(f"Superuser '{SUPERUSER_USERNAME}' already exists. Password updated.")
        else:
            # Create the superuser
            print(f"Creating superuser '{SUPERUSER_USERNAME}'...")
            superuser = User.objects.create_superuser(
                username=SUPERUSER_USERNAME,
                email=SUPERUSER_EMAIL,
                password=SUPERUSER_PASSWORD
            )
            print(f"Superuser '{SUPERUSER_USERNAME}' created successfully!")
    except IntegrityError:
        print(f"Superuser '{SUPERUSER_USERNAME}' already exists.")
    except Exception as e:
        print(f"Error creating superuser: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 