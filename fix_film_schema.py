#!/usr/bin/env python
"""
Script to fix the Film table schema by directly adding missing columns.
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

def check_column_exists(table, column):
    """Check if a column exists in a table."""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_name = %s
                AND column_name = %s
            );
        """, [table, column])
        return cursor.fetchone()[0]

def add_missing_columns():
    """Add missing columns to the Film table."""
    logger.info("Checking and adding missing columns to the Film table")
    
    # Define the columns that should exist in the Film table
    required_columns = [
        {
            'name': 'is_in_cinema',
            'definition': 'boolean NOT NULL DEFAULT false',
            'description': 'Whether this film is currently in UK cinemas'
        },
        {
            'name': 'uk_certification',
            'definition': 'varchar(10) NULL',
            'description': 'UK certification (e.g., PG, 12A, 15)'
        },
        {
            'name': 'uk_release_date',
            'definition': 'date NULL',
            'description': 'UK release date for this film'
        },
        {
            'name': 'popularity',
            'definition': 'double precision NOT NULL DEFAULT 0',
            'description': 'Popularity score from TMDB API'
        }
    ]
    
    # Check and add each column
    for column in required_columns:
        if not check_column_exists('films_app_film', column['name']):
            logger.info(f"Adding missing column '{column['name']}' to films_app_film table")
            
            try:
                with connection.cursor() as cursor:
                    # Add the column
                    cursor.execute(f"""
                        ALTER TABLE films_app_film 
                        ADD COLUMN {column['name']} {column['definition']};
                    """)
                    
                    # Add a comment to the column
                    cursor.execute(f"""
                        COMMENT ON COLUMN films_app_film.{column['name']} IS %s;
                    """, [column['description']])
                    
                logger.info(f"Successfully added column '{column['name']}' to films_app_film table")
            except Exception as e:
                logger.error(f"Error adding column '{column['name']}': {str(e)}")
        else:
            logger.info(f"Column '{column['name']}' already exists in films_app_film table")

def create_cinemavote_table():
    """Create the CinemaVote table if it doesn't exist."""
    if check_column_exists('films_app_cinemavote', 'id'):
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
        ('films_app', '0011_film_popularity'),
        ('films_app', '0012_add_film_popularity'),
        ('films_app', '0013_merge_0011_film_popularity_0012_add_film_popularity'),
        ('films_app', '0014_pagetracker')
    ]
    
    try:
        with connection.cursor() as cursor:
            for app, name in migrations_to_mark:
                # Check if the migration is already recorded
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM django_migrations 
                        WHERE app = %s AND name = %s
                    );
                """, [app, name])
                
                if cursor.fetchone()[0]:
                    logger.info(f"Migration {app}.{name} is already recorded")
                else:
                    # Record the migration as applied
                    cursor.execute("""
                        INSERT INTO django_migrations (app, name, applied) 
                        VALUES (%s, %s, NOW());
                    """, [app, name])
                    logger.info(f"Marked migration {app}.{name} as applied")
        
        logger.info("Migration state fixed successfully")
        return True
    except Exception as e:
        logger.error(f"Error fixing migration state: {str(e)}")
        return False

def main():
    """Fix the Film table schema and ensure CinemaVote table exists."""
    start_time = datetime.now()
    logger.info(f"Starting schema fix at {start_time}")
    
    success = True
    
    # Add missing columns to the Film table
    add_missing_columns()
    
    # Create the CinemaVote table
    if not create_cinemavote_table():
        success = False
    
    # Fix migration state
    if not fix_migration_state():
        success = False
    
    end_time = datetime.now()
    duration = end_time - start_time
    
    if success:
        logger.info(f"Schema fix completed successfully in {duration}")
        return 0
    else:
        logger.error(f"Schema fix completed with errors in {duration}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 