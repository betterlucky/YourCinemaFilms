#!/usr/bin/env python
"""
Script to set up Google OAuth in the database.
This script creates or updates the Google OAuth app configuration.
"""

import os
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'films_project.settings')
django.setup()

from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp

def setup_google_oauth():
    """Set up Google OAuth in the database."""
    # Get required environment variables
    client_id = os.environ.get('GOOGLE_CLIENT_ID')
    client_secret = os.environ.get('GOOGLE_CLIENT_SECRET')
    
    if not client_id or not client_secret:
        print("ERROR: GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables must be set.")
        print("Please set these variables in the Render dashboard.")
        return False
    
    # Get or create the Google social app
    try:
        social_app = SocialApp.objects.get(provider='google')
        print(f"Found existing Google social app: {social_app.name}")
    except SocialApp.DoesNotExist:
        social_app = SocialApp(provider='google', name='Google')
        print("Creating new Google social app")
    
    # Update the client ID and secret
    social_app.client_id = client_id
    social_app.secret = client_secret
    social_app.key = ''  # Not used for Google OAuth
    social_app.save()
    print(f"Updated Google social app with client ID: {client_id[:5]}...{client_id[-5:]}")
    
    # Make sure the social app is associated with the site
    site = Site.objects.get_current()
    if site not in social_app.sites.all():
        social_app.sites.add(site)
        print(f"Associated Google social app with site: {site.domain}")
    
    print("Google OAuth setup completed successfully!")
    return True

if __name__ == "__main__":
    setup_google_oauth() 