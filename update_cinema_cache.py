#!/usr/bin/env python
"""
Script to update the cinema cache with current and upcoming UK releases.
This script is designed to be run as a scheduled task on Render.com.
"""
import os
import sys
import django
import logging
from datetime import datetime, timedelta

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Set up Django environment
logger.info("Setting up Django environment")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'films_project.settings')
django.setup()

# Now we can import Django-specific modules
from django.core.management import call_command
from films_app.models import PageTracker

def main():
    """Run the update_movie_cache management command with cinema-only flag."""
    start_time = datetime.now()
    logger.info(f"Starting cinema cache update at {start_time}")
    
    # Check if an update was performed recently
    try:
        # Get the most recently updated tracker
        latest_tracker = PageTracker.objects.order_by('-last_updated').first()
        
        if latest_tracker and (datetime.now().replace(tzinfo=latest_tracker.last_updated.tzinfo) - latest_tracker.last_updated) < timedelta(hours=1):
            logger.info(f"Skipping update - last update was at {latest_tracker.last_updated}, less than 1 hour ago")
            return 0
    except Exception as e:
        logger.warning(f"Error checking last update time: {str(e)}")
    
    try:
        # Run the management command with limited pages to avoid timeouts
        logger.info("Starting cinema cache update with max_pages=2")
        call_command('update_movie_cache', type='cinema', max_pages=2)
        
        end_time = datetime.now()
        duration = end_time - start_time
        logger.info(f"Cinema cache update completed successfully in {duration}")
        return 0
    except Exception as e:
        logger.error(f"Error updating cinema cache: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 