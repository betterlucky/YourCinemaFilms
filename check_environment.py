import os
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'films_project.settings')
django.setup()

# Import settings
from django.conf import settings

# Check environment
print(f"Database engine: {settings.DATABASES['default']['ENGINE']}")
print(f"DEBUG mode: {settings.DEBUG}")
print(f"PRODUCTION environment variable: {os.environ.get('PRODUCTION', 'Not set')}")
print(f"Detected environment: {'Production' if settings.PRODUCTION else 'Development'}")
print(f"Site domain: {settings.SITE_DOMAIN}")
print(f"Site protocol: {settings.SITE_PROTOCOL}")
print(f"SOCIALACCOUNT_CALLBACK_URL: {settings.SOCIALACCOUNT_CALLBACK_URL}")

# Check Site model
from django.contrib.sites.models import Site
sites = Site.objects.all()
print(f"\nNumber of sites: {sites.count()}")

# Print each site
for site in sites:
    print(f"Site ID: {site.id}")
    print(f"Domain: {site.domain}")
    print(f"Name: {site.name}")
    print("-" * 30)

# Check social apps
from allauth.socialaccount.models import SocialApp
social_apps = SocialApp.objects.all()
print(f"\nNumber of social apps: {social_apps.count()}")

# Print each social app
for app in social_apps:
    print(f"Provider: {app.provider}")
    print(f"Name: {app.name}")
    print(f"Client ID: {app.client_id}")
    print(f"Secret: {'*' * len(app.secret) if app.secret else 'Not set'}")
    
    # Get the sites this app is associated with
    sites = app.sites.all()
    print(f"Associated sites: {', '.join([site.domain for site in sites])}")
    print("-" * 30)

print("\nTo switch environments:")
print("1. For development: Remove PRODUCTION from .env or set PRODUCTION=false")
print("2. For production: Set PRODUCTION=true in .env")
print("3. Run 'python setup_google_oauth.py' to update the Site model")
print("4. Restart the Django server") 