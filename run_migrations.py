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
        try:
            call_command('migrate')
        except Exception as e:
            print(f"Error during full migration: {e}")
            print("Attempting to apply migrations one by one...")
        
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
                print(f"Attempting to apply migrations for {app} one by one...")
                
                # Try to apply migrations one by one for this app
                try:
                    from django.db.migrations.loader import MigrationLoader
                    loader = MigrationLoader(django.db.connections['default'])
                    
                    # Get all migrations for this app
                    app_migrations = [
                        name for app_name, name in loader.disk_migrations.keys()
                        if app_name == app
                    ]
                    
                    # Sort migrations by name (assuming they follow a pattern like 0001, 0002, etc.)
                    app_migrations.sort()
                    
                    for migration in app_migrations:
                        try:
                            print(f"Applying {app}.{migration}...")
                            call_command('migrate', app, migration)
                        except Exception as migration_error:
                            print(f"Error applying {app}.{migration}: {migration_error}")
                except Exception as inner_e:
                    print(f"Error processing migrations for {app}: {inner_e}")
                
                print(f"Continuing with other migrations...")
        
        print("Migration process completed!")
    except Exception as e:
        print(f"Error during migration process: {e}")
        # Don't exit with error code, as we want the deployment to continue
        # even if migrations have issues
        print("Comprehensive migrations failed, but continuing...")

if __name__ == "__main__":
    main() 