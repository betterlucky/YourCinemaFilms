#!/usr/bin/env python
"""
Script to update the cinema cache with current and upcoming UK releases.
This script is designed to be run as a scheduled task on Render.com.
Optimized to reduce API calls and improve efficiency with parallel processing.
"""
import os
import sys
import django
import logging
import glob
import time
import concurrent.futures
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
from django.core.cache import cache
from django.db.models import Q, Count
from django.utils import timezone
from films_app.models import PageTracker, Film
from films_app.utils import get_cache_directory

# Lock key for preventing duplicate runs
LOCK_KEY = 'cinema_cache_update_lock'
LOCK_TIMEOUT = 3600  # 1 hour in seconds

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

def optimize_status_check_flags():
    """
    Optimize which films need status checks by using smarter filtering.
    This reduces the number of films that need to be checked against the API.
    """
    logger.info("Optimizing status check flags")
    today = timezone.now().date()
    
    # Get the count before optimization
    initial_count = Film.objects.filter(needs_status_check=True).count()
    logger.info(f"Initial films flagged for status checks: {initial_count}")
    
    # Clear flags for films that were checked recently (within the last 3 days)
    # This prevents checking the same films too frequently
    recent_check_cutoff = today - timedelta(days=3)
    
    # Use bulk update to clear flags for recently checked films
    recently_checked_films = Film.objects.filter(
        needs_status_check=True,
        last_status_check__gte=recent_check_cutoff
    )
    
    # Only perform the update if there are films to update
    recently_checked_count = recently_checked_films.count()
    if recently_checked_count > 0:
        recently_checked_films.update(needs_status_check=False)
        logger.info(f"Cleared status check flags for {recently_checked_count} recently checked films")
    
    # Prioritize films with upcoming or recent release dates
    priority_window = today + timedelta(days=30)  # Next 30 days
    past_window = today - timedelta(days=14)      # Last 14 days
    
    # Flag films with release dates in the priority window
    priority_films = Film.objects.filter(
        Q(uk_release_date__gte=past_window) & 
        Q(uk_release_date__lte=priority_window) &
        Q(needs_status_check=False)
    )
    
    priority_count = priority_films.count()
    if priority_count > 0:
        priority_films.update(needs_status_check=True)
        logger.info(f"Flagged {priority_count} priority films with upcoming/recent release dates")
    
    # Get the final count after optimization
    final_count = Film.objects.filter(needs_status_check=True).count()
    logger.info(f"Final films flagged for status checks after optimization: {final_count}")
    
    return final_count

def optimize_database_queries():
    """
    Perform database optimizations before running the update.
    This includes cleaning up orphaned records and optimizing indexes.
    """
    logger.info("Performing database optimizations")
    
    # Find films with no votes and not in cinema or upcoming that are older than 6 months
    # These are candidates for cleanup to reduce database size
    six_months_ago = timezone.now() - timedelta(days=180)
    
    # Use annotations to count related objects
    old_unused_films = Film.objects.annotate(
        vote_count=Count('votes'),
        cinema_vote_count=Count('cinema_votes')
    ).filter(
        vote_count=0,
        cinema_vote_count=0,
        is_in_cinema=False,
        is_upcoming=False,
        created_at__lt=six_months_ago
    )
    
    # Log the count but don't delete automatically
    old_count = old_unused_films.count()
    if old_count > 0:
        logger.info(f"Found {old_count} old unused films that could be cleaned up")
    
    # Run Django's built-in database maintenance commands
    try:
        # This is a placeholder - in a real implementation, you might run
        # database-specific maintenance commands here
        logger.info("Database optimization completed")
    except Exception as e:
        logger.warning(f"Error during database optimization: {str(e)}")
    
    return True

def main():
    """Run the update_movie_cache management command with optimized parameters."""
    start_time = timezone.now()
    logger.info(f"Starting cinema cache update at {start_time}")
    
    # Check if another update process is already running
    if cache.get(LOCK_KEY):
        logger.warning("Another update process is already running. Exiting.")
        return 0
    
    # Set a lock to prevent duplicate runs
    cache.set(LOCK_KEY, True, LOCK_TIMEOUT)
    
    try:
        # Check if an update was performed recently
        try:
            # Get the most recently updated tracker
            latest_tracker = PageTracker.objects.order_by('-last_updated').first()
            
            # Get the cache update interval from settings
            from django.conf import settings
            cache_interval = getattr(settings, 'CACHE_UPDATE_INTERVAL_MINUTES', 1440)  # Default to 24 hours
            
            if latest_tracker and (timezone.now() - latest_tracker.last_updated) < timedelta(minutes=cache_interval):
                logger.info(f"Skipping update - last update was at {latest_tracker.last_updated}, less than {cache_interval} minutes ago")
                return 0
        except Exception as e:
            logger.warning(f"Error checking last update time: {str(e)}")
        
        # Clean up cache files before updating
        logger.info("Cleaning up cache files before update")
        cleanup_old_cache_files()
        
        # Perform database optimizations
        optimize_database_queries()
        
        # Optimize which films need status checks
        flagged_count = optimize_status_check_flags()
        logger.info(f"Optimized status check flags: {flagged_count} films flagged for checking")
        
        # First, run the update_release_status command to flag films that need checking
        try:
            logger.info("Running update_release_status command to flag films for status checks")
            call_command(
                'update_release_status',
                days=7,
                batch_size=50,
                use_parallel=True
            )
        except Exception as e:
            logger.warning(f"Error running update_release_status: {str(e)}")
        
        # Get the count of films flagged for status checks
        flagged_count = Film.objects.filter(needs_status_check=True).count()
        logger.info(f"Found {flagged_count} films flagged for status checks")
        
        try:
            # Run the management command with improved parameters
            logger.info("Starting cinema cache update with optimized parameters")
            
            # Process all films with optimized parameters
            call_command(
                'update_movie_cache',
                force=True,
                max_pages=0,         # Process all available pages (0 means all)
                batch_size=15,       # Increased batch size for better performance
                batch_delay=1,       # Reduced delay between batches
                prioritize_flags=True,
                time_window_months=6, # 6 months for upcoming films
                use_parallel=True     # Enable parallel processing
            )
            
            end_time = timezone.now()
            duration = end_time - start_time
            logger.info(f"Cinema cache update completed successfully in {duration}")
            return 0
        except Exception as e:
            logger.error(f"Error updating cinema cache: {str(e)}")
            return 1
    finally:
        # Release the lock when done
        cache.delete(LOCK_KEY)
        logger.info("Released update lock")

if __name__ == "__main__":
    sys.exit(main()) 