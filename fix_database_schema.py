#!/usr/bin/env python
"""
Script to fix database schema issues by directly creating missing tables
and fixing migration state.
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
from django.db import connection, transaction
from django.db.migrations.recorder import MigrationRecorder

def check_table_exists(table_name):
    """Check if a table exists in the database."""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public'
                AND table_name = %s
            );
        """, [table_name])
        return cursor.fetchone()[0]

def create_cinemavote_table():
    """Create the CinemaVote table if it doesn't exist."""
    if check_table_exists('films_app_cinemavote'):
        logger.info("Table films_app_cinemavote already exists, skipping creation")
        return True
    
    logger.info("Creating films_app_cinemavote table")
    try:
        with connection.cursor() as cursor:
            # Create the table
            cursor.execute("""
                CREATE TABLE "films_app_cinemavote" (
                    "id" bigserial NOT NULL PRIMARY KEY,
                    "created_at" timestamp with time zone NOT NULL,
                    "updated_at" timestamp with time zone NOT NULL,
                    "film_id" bigint NOT NULL,
                    "user_id" integer NOT NULL,
                    CONSTRAINT "films_app_cinemavote_user_id_film_id_5a9e3e4c_uniq" UNIQUE ("user_id", "film_id"),
                    CONSTRAINT "films_app_cinemavote_film_id_fkey" FOREIGN KEY ("film_id") REFERENCES "films_app_film" ("id") DEFERRABLE INITIALLY DEFERRED,
                    CONSTRAINT "films_app_cinemavote_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED
                );
            """)
            
            # Create indexes
            cursor.execute('CREATE INDEX "films_app_cinemavote_film_id_idx" ON "films_app_cinemavote" ("film_id");')
            cursor.execute('CREATE INDEX "films_app_cinemavote_user_id_idx" ON "films_app_cinemavote" ("user_id");')
            cursor.execute('CREATE INDEX "films_app_cinemavote_updated_at_idx" ON "films_app_cinemavote" ("updated_at" DESC);')
            
            logger.info("Table films_app_cinemavote created successfully")
            return True
    except Exception as e:
        logger.error(f"Error creating films_app_cinemavote table: {str(e)}")
        return False

def fix_migration_state():
    """Fix the migration state in the django_migrations table."""
    logger.info("Fixing migration state")
    
    # List of migrations that should be marked as applied
    migrations_to_mark = [
        ('films_app', '0010_film_is_in_cinema_film_uk_certification_and_more'),
    ]
    
    try:
        with transaction.atomic():
            for app, name in migrations_to_mark:
                # Check if the migration is already recorded
                recorder = MigrationRecorder.Migration.objects.filter(app=app, name=name).first()
                
                if recorder:
                    logger.info(f"Migration {app}.{name} is already recorded")
                else:
                    # Record the migration as applied
                    MigrationRecorder.Migration.objects.create(app=app, name=name)
                    logger.info(f"Marked migration {app}.{name} as applied")
        
        logger.info("Migration state fixed successfully")
        return True
    except Exception as e:
        logger.error(f"Error fixing migration state: {str(e)}")
        return False

def main():
    """Fix database schema issues."""
    start_time = datetime.now()
    logger.info(f"Starting database schema fix at {start_time}")
    
    success = True
    
    # Create the CinemaVote table
    if not create_cinemavote_table():
        success = False
    
    # Fix migration state
    if not fix_migration_state():
        success = False
    
    end_time = datetime.now()
    duration = end_time - start_time
    
    if success:
        logger.info(f"Database schema fix completed successfully in {duration}")
        return 0
    else:
        logger.error(f"Database schema fix completed with errors in {duration}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 