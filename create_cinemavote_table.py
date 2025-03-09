#!/usr/bin/env python
"""
Script to directly create the CinemaVote table in the database.
This is a workaround for when migrations fail to create the table.
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

def main():
    """Create the CinemaVote table directly using SQL."""
    start_time = datetime.now()
    logger.info(f"Starting table creation at {start_time}")
    
    try:
        with connection.cursor() as cursor:
            # Check if the table already exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public'
                    AND table_name = 'films_app_cinemavote'
                );
            """)
            table_exists = cursor.fetchone()[0]
            
            if table_exists:
                logger.info("Table films_app_cinemavote already exists, skipping creation")
                return 0
            
            # Create the table
            logger.info("Creating films_app_cinemavote table")
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
            logger.info("Creating indexes for films_app_cinemavote table")
            cursor.execute('CREATE INDEX "films_app_cinemavote_film_id_idx" ON "films_app_cinemavote" ("film_id");')
            cursor.execute('CREATE INDEX "films_app_cinemavote_user_id_idx" ON "films_app_cinemavote" ("user_id");')
            cursor.execute('CREATE INDEX "films_app_cinemavote_updated_at_idx" ON "films_app_cinemavote" ("updated_at" DESC);')
            
            # Mark the migration as applied in django_migrations
            logger.info("Marking migration as applied")
            cursor.execute("""
                INSERT INTO django_migrations (app, name, applied)
                VALUES ('films_app', '0010_film_is_in_cinema_film_uk_certification_and_more', NOW())
                ON CONFLICT DO NOTHING;
            """)
            
            logger.info("Table creation completed successfully")
        
        end_time = datetime.now()
        duration = end_time - start_time
        logger.info(f"Table creation completed in {duration}")
        return 0
    except Exception as e:
        logger.error(f"Error creating table: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 