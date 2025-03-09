#!/usr/bin/env python
"""
Script to set up Google OAuth in the database.
This script creates or updates the Google OAuth app configuration.
"""

import os
import django
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'films_project.settings')
django.setup()

from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp
from django.db import connection, DatabaseError

def check_socialapp_schema():
    """Check the schema of the SocialApp table to determine the provider column name."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'socialaccount_socialapp' 
                AND column_name LIKE '%provider%';
            """)
            columns = [row[0] for row in cursor.fetchall()]
            
            if 'provider' in columns:
                return 'provider'
            elif 'provider_id' in columns:
                return 'provider_id'
            else:
                logger.warning("Could not find provider column in socialaccount_socialapp table")
                return None
    except DatabaseError as e:
        logger.error(f"Error checking SocialApp schema: {e}")
        return None

def create_socialapp_manually():
    """Create the SocialApp record using direct SQL to bypass ORM issues."""
    try:
        client_id = os.environ.get('GOOGLE_CLIENT_ID')
        client_secret = os.environ.get('GOOGLE_CLIENT_SECRET')
        
        if not client_id or not client_secret:
            logger.error("GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables must be set.")
            return False
        
        with connection.cursor() as cursor:
            # Check if the app already exists
            cursor.execute("""
                SELECT id FROM socialaccount_socialapp 
                WHERE provider = 'google';
            """)
            existing = cursor.fetchone()
            
            if existing:
                app_id = existing[0]
                logger.info(f"Updating existing Google social app (ID: {app_id})")
                cursor.execute("""
                    UPDATE socialaccount_socialapp 
                    SET client_id = %s, secret = %s 
                    WHERE id = %s;
                """, [client_id, client_secret, app_id])
            else:
                logger.info("Creating new Google social app")
                cursor.execute("""
                    INSERT INTO socialaccount_socialapp 
                    (provider, name, client_id, secret, key) 
                    VALUES ('google', 'Google', %s, %s, '');
                """, [client_id, client_secret])
                
                # Get the ID of the newly created app
                cursor.execute("SELECT lastval();")
                app_id = cursor.fetchone()[0]
            
            # Get the current site ID
            cursor.execute("SELECT id FROM django_site WHERE id = 1;")
            site_id = cursor.fetchone()[0]
            
            # Check if the site association exists
            cursor.execute("""
                SELECT * FROM socialaccount_socialapp_sites 
                WHERE socialapp_id = %s AND site_id = %s;
            """, [app_id, site_id])
            
            if not cursor.fetchone():
                logger.info(f"Associating Google social app with site ID: {site_id}")
                cursor.execute("""
                    INSERT INTO socialaccount_socialapp_sites 
                    (socialapp_id, site_id) 
                    VALUES (%s, %s);
                """, [app_id, site_id])
            
            logger.info("Google OAuth setup completed successfully!")
            return True
    except Exception as e:
        logger.error(f"Error creating SocialApp manually: {e}")
        return False

def setup_google_oauth():
    """Set up Google OAuth in the database."""
    # Get required environment variables
    client_id = os.environ.get('GOOGLE_CLIENT_ID')
    client_secret = os.environ.get('GOOGLE_CLIENT_SECRET')
    
    if not client_id or not client_secret:
        logger.error("GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables must be set.")
        logger.error("Please set these variables in the Render dashboard.")
        return False
    
    try:
        # Try using the ORM approach first
        try:
            social_app = SocialApp.objects.get(provider='google')
            logger.info(f"Found existing Google social app: {social_app.name}")
        except SocialApp.DoesNotExist:
            social_app = SocialApp(provider='google', name='Google')
            logger.info("Creating new Google social app")
        except Exception as e:
            logger.warning(f"Error using ORM to get/create SocialApp: {e}")
            logger.info("Falling back to manual SQL approach")
            return create_socialapp_manually()
        
        # Update the client ID and secret
        social_app.client_id = client_id
        social_app.secret = client_secret
        social_app.key = ''  # Not used for Google OAuth
        social_app.save()
        logger.info(f"Updated Google social app with client ID: {client_id[:5]}...{client_id[-5:]}")
        
        # Make sure the social app is associated with the site
        site = Site.objects.get_current()
        if site not in social_app.sites.all():
            social_app.sites.add(site)
            logger.info(f"Associated Google social app with site: {site.domain}")
        
        logger.info("Google OAuth setup completed successfully!")
        return True
    except Exception as e:
        logger.error(f"Error in setup_google_oauth: {e}")
        logger.info("Falling back to manual SQL approach")
        return create_socialapp_manually()

if __name__ == "__main__":
    setup_google_oauth() 