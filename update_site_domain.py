#!/usr/bin/env python
"""
Script to update the site domain in the database.
This is necessary for Google OAuth to work correctly.
"""

import os
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'films_project.settings')
django.setup()

from django.contrib.sites.models import Site

def update_site_domain():
    """Update the site domain to match the Render domain."""
    # Get the domain from environment variable or use default
    domain = os.environ.get('RENDER_EXTERNAL_URL', 'yourcinemafilms.onrender.com')
    
    # Remove protocol if present
    if domain.startswith('http://'):
        domain = domain[7:]
    elif domain.startswith('https://'):
        domain = domain[8:]
    
    # Remove trailing slash if present
    if domain.endswith('/'):
        domain = domain[:-1]
    
    # Try to get the current site, create one if it doesn't exist
    try:
        site = Site.objects.get(id=1)
        print(f"Current site domain: {site.domain}")
    except Site.DoesNotExist:
        site = Site(id=1, domain=domain, name='YourCinemaFilms')
        print(f"Creating new site with domain: {domain}")
    
    # Update the site domain and name
    site.domain = domain
    site.name = 'YourCinemaFilms'
    site.save()
    
    print(f"Site domain updated successfully to: {site.domain}")
    
    # Verify site exists in database
    sites_count = Site.objects.count()
    print(f"Total sites in database: {sites_count}")
    
    return True

if __name__ == "__main__":
    update_site_domain() 