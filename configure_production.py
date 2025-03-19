import os
import django
import sys

# Set environment variables directly in the script
os.environ['PRODUCTION'] = 'true'

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'films_project.settings')
django.setup()

# Import the necessary models
from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp
from django.conf import settings

def configure_production():
    """
    Configure the application for production by:
    1. Setting the Site model domain to the production domain
    2. Ensuring the Google SocialApp is associated with the production site
    """
    # Production domain
    production_domain = 'yourcinemafilms.theworkpc.com'
    
    print(f"Configuring for production with domain: {production_domain}")
    
    # Update the Site model
    try:
        site = Site.objects.get(id=1)
        print(f"Found existing site: {site.domain}")
        
        # Update the site domain and name
        site.domain = production_domain
        site.name = 'Your Cinema Films'
        site.save()
        print(f"Updated site domain to {site.domain} and name to {site.name}")
    except Site.DoesNotExist:
        # Create a new site if it doesn't exist
        site = Site.objects.create(
            id=1,
            domain=production_domain,
            name='Your Cinema Films'
        )
        print(f"Created new site with domain {site.domain} and name {site.name}")
    
    # Check if a Google SocialApp already exists
    google_app = SocialApp.objects.filter(provider='google').first()
    
    if google_app:
        print(f"Found existing Google SocialApp: {google_app.name}")
        
        # Make sure the app is associated with the site
        if site not in google_app.sites.all():
            google_app.sites.add(site)
            print(f"Associated Google SocialApp with site {site.domain}")
        
        print(f"Google SocialApp is configured for production")
    else:
        print("No Google SocialApp found. Please run setup_google_oauth.py first.")
        sys.exit(1)
    
    # Print the production callback URL
    callback_url = f"https://{production_domain}/accounts/google/login/callback/"
    print(f"\nProduction callback URL: {callback_url}")
    print("\nMake sure this URL is registered in your Google Cloud Console as an Authorized Redirect URI.")
    print("Also ensure that the following is registered as an Authorized JavaScript Origin:")
    print(f"https://{production_domain}")
    
    print("\nProduction configuration complete!")

if __name__ == "__main__":
    configure_production() 