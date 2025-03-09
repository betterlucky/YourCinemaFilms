#!/usr/bin/env python
"""
Script to completely reset the database by dropping all tables and running fresh migrations.
WARNING: This will delete ALL data in the database!
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
from django.db import connection
from django.core.management import call_command

def drop_all_tables():
    """Drop all tables in the database."""
    logger.info("Dropping all tables in the database")
    
    try:
        with connection.cursor() as cursor:
            # Get the list of all tables
            cursor.execute("""
                SELECT tablename FROM pg_tables
                WHERE schemaname = 'public';
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
            if not tables:
                logger.info("No tables found to drop")
                return True
            
            # Disable foreign key checks
            cursor.execute("SET CONSTRAINTS ALL DEFERRED;")
            
            # Drop all tables
            for table in tables:
                logger.info(f"Dropping table {table}")
                cursor.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE;')
            
            # Re-enable foreign key checks
            cursor.execute("SET CONSTRAINTS ALL IMMEDIATE;")
            
            logger.info(f"Successfully dropped {len(tables)} tables")
            return True
    except Exception as e:
        logger.error(f"Error dropping tables: {str(e)}")
        return False

def run_fresh_migrations():
    """Run fresh migrations to recreate all tables."""
    logger.info("Running fresh migrations")
    
    try:
        # Run makemigrations
        logger.info("Running makemigrations")
        call_command('makemigrations')
        
        # Run migrate
        logger.info("Running migrate")
        call_command('migrate')
        
        logger.info("Migrations completed successfully")
        return True
    except Exception as e:
        logger.error(f"Error running migrations: {str(e)}")
        return False

def load_initial_data():
    """Load initial data from fixtures."""
    logger.info("Loading initial data")
    
    try:
        # Check if fixtures directory exists and has files
        fixtures_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'fixtures')
        if os.path.exists(fixtures_dir):
            fixture_files = [f for f in os.listdir(fixtures_dir) if f.endswith('.json')]
            
            if fixture_files:
                for fixture in fixture_files:
                    fixture_path = os.path.join('fixtures', fixture)
                    logger.info(f"Loading fixture {fixture_path}")
                    call_command('loaddata', fixture_path)
                
                logger.info(f"Successfully loaded {len(fixture_files)} fixtures")
            else:
                logger.info("No fixture files found")
        else:
            logger.info("Fixtures directory not found")
        
        return True
    except Exception as e:
        logger.error(f"Error loading initial data: {str(e)}")
        return False

def main():
    """Reset the database by dropping all tables and running fresh migrations."""
    start_time = datetime.now()
    logger.info(f"Starting database reset at {start_time}")
    
    success = True
    
    # Drop all tables
    if not drop_all_tables():
        success = False
    
    # Run fresh migrations
    if not run_fresh_migrations():
        success = False
    
    # Load initial data
    if not load_initial_data():
        success = False
    
    end_time = datetime.now()
    duration = end_time - start_time
    
    if success:
        logger.info(f"Database reset completed successfully in {duration}")
        return 0
    else:
        logger.error(f"Database reset completed with errors in {duration}")
        return 1

if __name__ == "__main__":
    # Ask for confirmation before proceeding
    if len(sys.argv) > 1 and sys.argv[1] == '--force':
        sys.exit(main())
    else:
        print("WARNING: This will delete ALL data in the database!")
        print("To proceed, run with the --force flag:")
        print("python reset_database.py --force")
        sys.exit(1) 