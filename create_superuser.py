#!/usr/bin/env python
"""
Script to create a Django superuser programmatically.
This can be used on Render where shell access might be limited.
"""

import os
import sys
import django
from django.contrib.auth import get_user_model
from django.db import IntegrityError

def main():
    """Create a Django superuser programmatically."""
    print("Starting superuser creation process...")
    
    # Set up Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'films_project.settings')
    django.setup()
    
    # Get the username, email, and password from environment variables
    username = os.environ.get('DJANGO_SUPERUSER_USERNAME')
    email = os.environ.get('DJANGO_SUPERUSER_EMAIL')
    password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')
    
    # Check if all required environment variables are set
    if not all([username, email, password]):
        print("Error: DJANGO_SUPERUSER_USERNAME, DJANGO_SUPERUSER_EMAIL, and DJANGO_SUPERUSER_PASSWORD must be set.")
        sys.exit(1)
    
    # Get the User model
    User = get_user_model()
    
    try:
        # Check if the user already exists
        if User.objects.filter(username=username).exists():
            print(f"Superuser '{username}' already exists.")
            return
        
        # Create the superuser
        print(f"Creating superuser '{username}'...")
        User.objects.create_superuser(username=username, email=email, password=password)
        print(f"Superuser '{username}' created successfully!")
    except IntegrityError:
        print(f"Superuser '{username}' already exists.")
    except Exception as e:
        print(f"Error creating superuser: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 