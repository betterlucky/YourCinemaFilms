#!/usr/bin/env python
"""
Script to update the cinema cache with current and upcoming UK releases.
This script is designed to be run as a scheduled task on Render.com.
"""
import os
import sys
import django
import logging
from datetime import datetime

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

def main():
    """Run the update_movie_cache management command with cinema-only flag."""
    start_time = datetime.now()
    logger.info(f"Starting cinema cache update at {start_time}")
    
    try:
        # Run the management command with cinema-only flag
        call_command('update_movie_cache', cinema_only=True)
        
        end_time = datetime.now()
        duration = end_time - start_time
        logger.info(f"Cinema cache update completed successfully in {duration}")
        return 0
    except Exception as e:
        logger.error(f"Error updating cinema cache: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 