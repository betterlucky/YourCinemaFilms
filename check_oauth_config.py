import os
import django
import webbrowser
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'films_project.settings')
django.setup()

# Import settings
from django.conf import settings

def print_header(text):
    print("\n" + "=" * 80)
    print(f" {text} ".center(80, "="))
    print("=" * 80)

# Check environment and OAuth settings
print_header("CURRENT ENVIRONMENT SETTINGS")
print(f"DEBUG mode: {settings.DEBUG}")
print(f"PRODUCTION environment variable: {os.environ.get('PRODUCTION', 'Not set')}")
print(f"Detected environment: {'Production' if settings.PRODUCTION else 'Development'}")
print(f"Site domain: {settings.SITE_DOMAIN}")
print(f"Site protocol: {settings.SITE_PROTOCOL}")
print(f"SOCIALACCOUNT_CALLBACK_URL: {settings.SOCIALACCOUNT_CALLBACK_URL}")

# Check Google OAuth credentials
print_header("GOOGLE OAUTH CREDENTIALS")
client_id = os.environ.get('GOOGLE_CLIENT_ID', 'Not set')
client_secret = os.environ.get('GOOGLE_CLIENT_SECRET', 'Not set')
print(f"GOOGLE_CLIENT_ID: {client_id[:10]}...{client_id[-10:] if len(client_id) > 20 else client_id}")
print(f"GOOGLE_CLIENT_SECRET: {'*' * 10}...{'*' * 5 if client_secret != 'Not set' else client_secret}")

# Check Site model
from django.contrib.sites.models import Site
sites = Site.objects.all()
print_header("SITE MODEL CONFIGURATION")
print(f"Number of sites: {sites.count()}")

for site in sites:
    print(f"Site ID: {site.id}")
    print(f"Domain: {site.domain}")
    print(f"Name: {site.name}")
    print("-" * 40)

# Check social apps
from allauth.socialaccount.models import SocialApp
social_apps = SocialApp.objects.all()
print_header("SOCIAL APP CONFIGURATION")
print(f"Number of social apps: {social_apps.count()}")

for app in social_apps:
    print(f"Provider: {app.provider}")
    print(f"Name: {app.name}")
    print(f"Client ID: {app.client_id[:10]}...{app.client_id[-10:] if len(app.client_id) > 20 else app.client_id}")
    print(f"Secret: {'*' * 10}...{'*' * 5 if app.secret else 'Not set'}")
    
    # Get the sites this app is associated with
    sites = app.sites.all()
    print(f"Associated sites: {', '.join([site.domain for site in sites])}")
    print("-" * 40)

# Provide instructions for fixing the redirect URI mismatch
print_header("FIXING REDIRECT URI MISMATCH")
print("The error 'Error 400: redirect_uri_mismatch' indicates that the redirect URI")
print("used by your application doesn't match what's registered in Google Cloud Console.")
print("\nCurrent callback URL in your application:")
print(f"  {settings.SOCIALACCOUNT_CALLBACK_URL}")
print("\nTo fix this issue, you need to:")
print("\n1. Go to the Google Cloud Console:")
print("   https://console.cloud.google.com/apis/credentials")
print("\n2. Find and edit your OAuth 2.0 Client ID")
print("\n3. Add the following Authorized Redirect URI:")
print(f"   {settings.SOCIALACCOUNT_CALLBACK_URL}")
print("\n4. Make sure the following Authorized JavaScript Origins are added:")
print(f"   {settings.SITE_PROTOCOL}://{settings.SITE_DOMAIN}")
print("\n5. Click 'Save' and wait a few minutes for changes to propagate")

# Ask if user wants to open Google Cloud Console
print_header("OPEN GOOGLE CLOUD CONSOLE")
open_browser = input("Would you like to open the Google Cloud Console now? (y/n): ")
if open_browser.lower() == 'y':
    webbrowser.open("https://console.cloud.google.com/apis/credentials")
    print("Browser opened to Google Cloud Console.")
    print("Please find and edit your OAuth 2.0 Client ID to add the redirect URI.")
else:
    print("You can manually open the Google Cloud Console at:")
    print("https://console.cloud.google.com/apis/credentials")

print_header("ADDITIONAL TROUBLESHOOTING")
print("If you continue to have issues after updating the redirect URI:")
print("1. Clear your browser cookies and cache")
print("2. Restart your Django server")
print("3. Try signing in again")
print("\nIf you're using a custom port other than 8000, make sure to update")
print("both your application settings and Google Cloud Console accordingly.") 