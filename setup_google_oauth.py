import os
import django
import sys
import socket
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'films_project.settings')
django.setup()

# Import the necessary models
from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp
from django.conf import settings

def get_current_domain():
    """
    Determine the current domain based on environment variables or settings.
    """
    # Check if we're in a production environment
    # Explicitly check for PRODUCTION=true/false first
    production_env = os.environ.get('PRODUCTION', '').lower()
    if production_env == 'true':
        return 'yourcinemafilms.theworkpc.com'
    elif production_env == 'false':
        # For development, use localhost with the appropriate port
        port = os.environ.get('PORT', '8000')
        return f'localhost:{port}'
    
    # If PRODUCTION is not explicitly set, fall back to DEBUG setting
    if not settings.DEBUG:
        return 'yourcinemafilms.theworkpc.com'
    else:
        port = os.environ.get('PORT', '8000')
        return f'localhost:{port}'

def setup_google_oauth():
    """
    Set up Google OAuth by:
    1. Updating the Site model with the correct domain
    2. Creating a Google SocialApp if it doesn't exist
    """
    # Get the Google client ID and secret from .env file
    client_id = os.environ.get('GOOGLE_CLIENT_ID')
    client_secret = os.environ.get('GOOGLE_CLIENT_SECRET')
    
    if not client_id or not client_secret:
        print("Error: GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET not found in .env file.")
        print("Please add these variables to your .env file and try again.")
        print("Example:")
        print("GOOGLE_CLIENT_ID=your_client_id")
        print("GOOGLE_CLIENT_SECRET=your_client_secret")
        sys.exit(1)
    
    # Determine the current domain
    current_domain = get_current_domain()
    is_production = current_domain == 'yourcinemafilms.theworkpc.com'
    
    print(f"Detected environment: {'Production' if is_production else 'Development'}")
    print(f"Using domain: {current_domain}")
    
    # Update the Site model
    try:
        site = Site.objects.get(id=1)
        print(f"Found existing site: {site.domain}")
        
        # Update the site domain and name
        site.domain = current_domain
        site.name = 'Your Cinema Films'
        site.save()
        print(f"Updated site domain to {site.domain} and name to {site.name}")
    except Site.DoesNotExist:
        # Create a new site if it doesn't exist
        site = Site.objects.create(
            id=1,
            domain=current_domain,
            name='Your Cinema Films'
        )
        print(f"Created new site with domain {site.domain} and name {site.name}")
    
    # Check if a Google SocialApp already exists
    google_app = SocialApp.objects.filter(provider='google').first()
    
    if google_app:
        print(f"Found existing Google SocialApp: {google_app.name}")
        
        # Update the app with the new credentials
        google_app.client_id = client_id
        google_app.secret = client_secret
        google_app.save()
        
        # Make sure the app is associated with the site
        if site not in google_app.sites.all():
            google_app.sites.add(site)
            print(f"Associated Google SocialApp with site {site.domain}")
        
        print(f"Updated Google SocialApp with new credentials")
    else:
        # Create a new Google SocialApp
        google_app = SocialApp.objects.create(
            provider='google',
            name='Google',
            client_id=client_id,
            secret=client_secret
        )
        
        # Associate the app with the site
        google_app.sites.add(site)
        
        print(f"Created new Google SocialApp and associated it with site {site.domain}")
    
    # Update the callback URL in settings if needed
    callback_url = f"{'https' if is_production else 'http'}://{current_domain}/accounts/google/login/callback/"
    print(f"Callback URL should be set to: {callback_url}")
    print("You may need to update SOCIALACCOUNT_CALLBACK_URL in settings.py if it doesn't match.")
    
    print("\nGoogle OAuth setup complete!")
    
    if not is_production:
        print("\nWhen deploying to production:")
        print("1. Set the PRODUCTION environment variable to 'true' in your .env file")
        print("2. Run this script again to update the site domain")
        print("3. Make sure your Google OAuth credentials in the Google Cloud Console include the production domain")

if __name__ == "__main__":
    setup_google_oauth() 