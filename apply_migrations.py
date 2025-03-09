#!/usr/bin/env python
"""
Script to apply all migrations on the production server.
This script is designed to be run as a one-time task on Render.com.
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
    """Apply all migrations."""
    start_time = datetime.now()
    logger.info(f"Starting migration application at {start_time}")
    
    try:
        # Apply all migrations
        logger.info("Applying all migrations")
        call_command('migrate')
        
        end_time = datetime.now()
        duration = end_time - start_time
        logger.info(f"Migration application completed successfully in {duration}")
        return 0
    except Exception as e:
        logger.error(f"Error applying migrations: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 