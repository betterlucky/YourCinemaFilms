#!/usr/bin/env python
"""
Script to update the release status of films.
This script is designed to be run as a daily scheduled task on Render.com.
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
    """Run the update_release_status management command."""
    start_time = datetime.now()
    logger.info(f"Starting release status update at {start_time}")
    
    try:
        # Run the management command to flag films that need status checks
        logger.info("Running update_release_status command")
        result = call_command('update_release_status')
        
        end_time = datetime.now()
        duration = end_time - start_time
        logger.info(f"Release status update completed successfully in {duration}")
        logger.info(result)  # Log the result message
        return 0
    except Exception as e:
        logger.error(f"Error updating release status: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 