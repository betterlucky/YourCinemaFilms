#!/usr/bin/env python
"""
Script to run Django migrations programmatically.
This can be used on Render where shell access might be limited.
"""

import os
import sys
import django
from django.core.management import call_command

def main():
    """Run Django migrations programmatically."""
    print("Starting migration process...")
    
    # Set up Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'films_project.settings')
    django.setup()
    
    try:
        # Make migrations
        print("Creating migrations...")
        call_command('makemigrations')
        
        # Apply migrations for all apps
        print("Applying migrations for all apps...")
        call_command('migrate')
        
        # Apply migrations for specific apps to ensure they're created
        print("Applying app-specific migrations...")
        app_list = [
            'films_app',
            'admin',
            'auth',
            'contenttypes',
            'sessions',
            'sites',
            'allauth',
        ]
        
        for app in app_list:
            try:
                print(f"Migrating {app}...")
                call_command('migrate', app)
            except Exception as e:
                print(f"Error migrating {app}: {e}")
                print(f"Continuing with other migrations...")
        
        print("Migration process completed successfully!")
    except Exception as e:
        print(f"Error during migration process: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 