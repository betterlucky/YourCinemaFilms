#!/usr/bin/env python
"""
Script to update the cinema cache with current and upcoming UK releases.
This script is designed to be run as a scheduled task on Render.com.
Optimized to reduce API calls and improve efficiency without staged pulls.
"""
import os
import sys
import django
import logging
import glob
import time
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
from films_app.models import PageTracker, Film
from films_app.utils import get_cache_directory

def cleanup_old_cache_files():
    """Clean up all JSON cache files daily to ensure fresh data."""
    logger.info("Cleaning up cache files")
    
    # Get cache directory
    cache_dir = get_cache_directory()
    
    # Find all JSON files in the cache directory
    json_files = glob.glob(os.path.join(cache_dir, "*.json"))
    
    # Keep track of how many files were deleted
    deleted_count = 0
    
    # Delete all JSON files except for cache_info.json and cinema_cache_info.json
    for file_path in json_files:
        file_name = os.path.basename(file_path)
        
        # Skip cache info files
        if file_name in ['cache_info.json', 'cinema_cache_info.json']:
            continue
        
        try:
            os.remove(file_path)
            deleted_count += 1
            logger.info(f"Deleted cache file: {file_name}")
        except Exception as e:
            logger.warning(f"Error deleting cache file {file_name}: {str(e)}")
    
    logger.info(f"Cleaned up {deleted_count} cache files")

def main():
    """Run the update_movie_cache management command with optimized parameters."""
    start_time = datetime.now()
    logger.info(f"Starting cinema cache update at {start_time}")
    
    # Check if an update was performed recently
    try:
        # Get the most recently updated tracker
        latest_tracker = PageTracker.objects.order_by('-last_updated').first()
        
        # Get the cache update interval from settings
        from django.conf import settings
        cache_interval = getattr(settings, 'CACHE_UPDATE_INTERVAL_MINUTES', 15)
        
        if latest_tracker and (datetime.now().replace(tzinfo=latest_tracker.last_updated.tzinfo) - latest_tracker.last_updated) < timedelta(minutes=cache_interval):
            logger.info(f"Skipping update - last update was at {latest_tracker.last_updated}, less than {cache_interval} minutes ago")
            return 0
    except Exception as e:
        logger.warning(f"Error checking last update time: {str(e)}")
    
    # First, run the update_release_status command to flag films that need checking
    try:
        logger.info("Running update_release_status command to flag films for status checks")
        call_command('update_release_status')
    except Exception as e:
        logger.warning(f"Error running update_release_status: {str(e)}")
    
    # Get the count of films flagged for status checks
    flagged_count = Film.objects.filter(needs_status_check=True).count()
    logger.info(f"Found {flagged_count} films flagged for status checks")
    
    try:
        # Clean up cache files before updating
        logger.info("Cleaning up cache files before update")
        cleanup_old_cache_files()
        
        # Run the management command with improved parameters
        logger.info("Starting cinema cache update with --all-pages option")
        
        # Process all films with optimized parameters
        call_command(
            'update_movie_cache',
            force=True,
            all_pages=True,  # Process all available pages
            batch_size=5,    # Balanced batch size for performance
            batch_delay=2,   # Reasonable delay between batches
            prioritize_flags=True,
            time_window=6    # 6 months for upcoming films
        )
        
        end_time = datetime.now()
        duration = end_time - start_time
        logger.info(f"Cinema cache update completed successfully in {duration}")
        return 0
    except Exception as e:
        logger.error(f"Error updating cinema cache: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 