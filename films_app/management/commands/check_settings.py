from django.core.management.base import BaseCommand
from django.conf import settings
import os
import sys

class Command(BaseCommand):
    help = 'Check critical settings configuration'

    def check_type(self, name, value, expected_type):
        """Helper method to check type of a setting"""
        actual_type = type(value)
        if not isinstance(value, expected_type):
            self.stdout.write(self.style.ERROR(
                f"✗ {name} has wrong type: expected {expected_type.__name__}, got {actual_type.__name__}"
            ))
            return False
        return True

    def handle(self, *args, **options):
        self.stdout.write("Checking critical settings...")
        
        # Check if env.py is in Python path
        env_path = '/etc/yourcinemafilms/env.py'
        if '/etc/yourcinemafilms' not in sys.path:
            self.stdout.write(self.style.WARNING("Adding /etc/yourcinemafilms to Python path"))
            sys.path.append('/etc/yourcinemafilms')
        
        # Try to import env.py directly
        try:
            import env
            self.stdout.write(self.style.SUCCESS("✓ Successfully imported env.py"))
            
            # Check types in env module
            type_checks = {
                'TMDB_API_KEY': str,
                'DJANGO_DEBUG': bool,
                'PRODUCTION': bool,
                'UPCOMING_FILMS_MONTHS': int,
                'MAX_CINEMA_FILMS': int,
                'CACHE_UPDATE_INTERVAL_MINUTES': int,
                'FILMS_PER_PAGE': int
            }
            
            for name, expected_type in type_checks.items():
                if hasattr(env, name):
                    value = getattr(env, name)
                    if self.check_type(f"{name} (in env)", value, expected_type):
                        self.stdout.write(self.style.SUCCESS(f"✓ {name} has correct type: {expected_type.__name__}"))
                else:
                    self.stdout.write(self.style.ERROR(f"✗ {name} not found in env module"))
                    
        except ImportError as e:
            self.stdout.write(self.style.ERROR(f"✗ Could not import env.py: {e}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ Error accessing env module: {e}"))
        
        # Check TMDB API key in Django settings
        tmdb_key = getattr(settings, 'TMDB_API_KEY', None)
        if tmdb_key:
            self.stdout.write(self.style.SUCCESS(f"✓ TMDB_API_KEY is set in Django settings"))
            if self.check_type("TMDB_API_KEY (in settings)", tmdb_key, str):
                self.stdout.write(f"  Key starts with: {tmdb_key[:4]}")
                self.stdout.write(f"  Key ends with: {tmdb_key[-4:]}")
        else:
            self.stdout.write(self.style.ERROR("✗ TMDB_API_KEY is not set in Django settings"))
        
        # Check env.py path and contents
        if os.path.exists(env_path):
            self.stdout.write(self.style.SUCCESS(f"✓ env.py exists at {env_path}"))
            perms = oct(os.stat(env_path).st_mode)[-3:]
            self.stdout.write(f"  File permissions: {perms}")
            
            try:
                with open(env_path, 'r') as f:
                    env_contents = f.read()
                self.stdout.write(self.style.SUCCESS("✓ env.py is readable"))
                if 'TMDB_API_KEY' in env_contents:
                    self.stdout.write(self.style.SUCCESS("✓ TMDB_API_KEY found in env.py contents"))
                else:
                    self.stdout.write(self.style.ERROR("✗ TMDB_API_KEY not found in env.py contents"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"✗ Error reading env.py: {e}"))
        else:
            self.stdout.write(self.style.ERROR(f"✗ env.py not found at {env_path}"))
        
        # Check other critical settings
        self.stdout.write("\nOther critical settings:")
        debug_val = getattr(settings, 'DJANGO_DEBUG', None)
        prod_val = getattr(settings, 'PRODUCTION', None)
        
        if debug_val is not None:
            self.check_type('DJANGO_DEBUG (in settings)', debug_val, bool)
        if prod_val is not None:
            self.check_type('PRODUCTION (in settings)', prod_val, bool)
        
        # Try to verify the API key works
        if tmdb_key:
            import requests
            try:
                response = requests.get(
                    "https://api.themoviedb.org/3/movie/now_playing",
                    params={
                        'api_key': tmdb_key,
                        'region': 'GB'
                    }
                )
                if response.status_code == 200:
                    self.stdout.write(self.style.SUCCESS("✓ Successfully tested TMDB API key"))
                else:
                    self.stdout.write(self.style.ERROR(f"✗ API test failed with status code: {response.status_code}"))
                    self.stdout.write(f"  Response: {response.text[:500]}")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"✗ Error testing API key: {e}"))
