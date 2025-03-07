#!/usr/bin/env python
"""
Script to ensure database tables exist and data is loaded.
This script is designed to be run during the build process on Render.
"""

import os
import sys
import django
import time
import psycopg2
from psycopg2 import sql
from urllib.parse import urlparse

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'films_project.settings')
django.setup()

from django.core.management import call_command
from django.db import connection, OperationalError, ProgrammingError
from django.contrib.auth.models import User
from films_app.models import Film, Vote, UserProfile, GenreTag

def wait_for_db(max_retries=5, retry_interval=5):
    """Wait for the database to be available."""
    print("Checking database connection...")
    retries = 0
    while retries < max_retries:
        try:
            connection.ensure_connection()
            print("Database connection successful!")
            return True
        except OperationalError as e:
            retries += 1
            print(f"Database connection failed (attempt {retries}/{max_retries}): {e}")
            if retries < max_retries:
                print(f"Retrying in {retry_interval} seconds...")
                time.sleep(retry_interval)
    
    print("Failed to connect to the database after multiple attempts.")
    return False

def ensure_tables_exist():
    """Ensure all required tables exist in the database."""
    print("Ensuring tables exist...")
    
    # First try using Django migrations
    try:
        print("Running makemigrations...")
        call_command('makemigrations', interactive=False)
        print("Running migrate...")
        call_command('migrate', interactive=False)
        print("Migrations completed successfully!")
        return True
    except Exception as e:
        print(f"Error during migrations: {e}")
        print("Attempting to create tables directly...")
    
    # If migrations fail, try creating tables directly using SQL
    try:
        # Get the database URL from environment
        db_url = os.environ.get('DATABASE_URL')
        if not db_url:
            print("DATABASE_URL environment variable not set!")
            return False
        
        # Parse the database URL
        parsed_url = urlparse(db_url)
        db_name = parsed_url.path[1:]  # Remove leading slash
        db_user = parsed_url.username
        db_password = parsed_url.password
        db_host = parsed_url.hostname
        db_port = parsed_url.port or 5432
        
        # Connect to the database
        conn = psycopg2.connect(
            dbname=db_name,
            user=db_user,
            password=db_password,
            host=db_host,
            port=db_port
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Create tables if they don't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS "films_app_film" (
                "id" bigserial NOT NULL PRIMARY KEY,
                "imdb_id" varchar(20) NOT NULL UNIQUE,
                "title" varchar(255) NOT NULL,
                "year" varchar(10) NOT NULL,
                "poster_url" varchar(500) NULL,
                "director" varchar(255) NULL,
                "plot" text NULL,
                "genres" varchar(255) NULL,
                "runtime" varchar(20) NULL,
                "actors" text NULL,
                "created_at" timestamp with time zone NOT NULL
            );
            
            CREATE TABLE IF NOT EXISTS "films_app_vote" (
                "id" bigserial NOT NULL PRIMARY KEY,
                "created_at" timestamp with time zone NOT NULL,
                "updated_at" timestamp with time zone NOT NULL,
                "film_id" bigint NOT NULL REFERENCES "films_app_film" ("id") DEFERRABLE INITIALLY DEFERRED,
                "user_id" integer NOT NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED,
                CONSTRAINT "films_app_vote_user_id_film_id_uniq" UNIQUE ("user_id", "film_id")
            );
            
            CREATE TABLE IF NOT EXISTS "films_app_userprofile" (
                "id" bigserial NOT NULL PRIMARY KEY,
                "bio" text NULL,
                "profile_picture_url" varchar(500) NULL,
                "letterboxd_username" varchar(100) NULL,
                "google_account_id" varchar(100) NULL,
                "google_email" varchar(254) NULL,
                "contact_email" varchar(254) NULL,
                "use_google_email_for_contact" boolean NOT NULL,
                "location" varchar(100) NULL,
                "gender" varchar(2) NOT NULL,
                "age_range" varchar(5) NOT NULL,
                "location_privacy" varchar(10) NOT NULL,
                "gender_privacy" varchar(10) NOT NULL,
                "age_privacy" varchar(10) NOT NULL,
                "votes_privacy" varchar(10) NOT NULL,
                "user_id" integer NOT NULL UNIQUE REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED
            );
            
            CREATE TABLE IF NOT EXISTS "films_app_genretag" (
                "id" bigserial NOT NULL PRIMARY KEY,
                "tag" varchar(50) NOT NULL,
                "created_at" timestamp with time zone NOT NULL,
                "is_approved" boolean NOT NULL,
                "approval_date" timestamp with time zone NULL,
                "film_id" bigint NOT NULL REFERENCES "films_app_film" ("id") DEFERRABLE INITIALLY DEFERRED,
                "user_id" integer NOT NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED,
                CONSTRAINT "films_app_genretag_film_id_user_id_tag_uniq" UNIQUE ("film_id", "user_id", "tag")
            );
        """)
        
        print("Tables created successfully!")
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error creating tables directly: {e}")
        return False

def load_fixture_data():
    """Load data from fixtures."""
    print("Loading data from fixtures...")
    try:
        # Check if fixtures directory exists
        if not os.path.isdir('fixtures'):
            print("Fixtures directory not found!")
            return False
        
        # Check if all_data.json exists
        if os.path.isfile('fixtures/all_data.json'):
            print("Loading all_data.json...")
            call_command('loaddata', 'fixtures/all_data.json')
            print("Data loaded successfully!")
            return True
        
        # If all_data.json doesn't exist, try loading individual fixtures
        fixtures = [
            'fixtures/users.json',
            'fixtures/films.json',
            'fixtures/userprofiles.json',
            'fixtures/votes.json',
            'fixtures/genretags.json'
        ]
        
        for fixture in fixtures:
            if os.path.isfile(fixture):
                print(f"Loading {fixture}...")
                call_command('loaddata', fixture)
        
        print("Data loaded successfully!")
        return True
    except Exception as e:
        print(f"Error loading data: {e}")
        return False

def create_superuser():
    """Create a superuser if environment variables are set."""
    print("Checking if superuser needs to be created...")
    username = os.environ.get('DJANGO_SUPERUSER_USERNAME')
    email = os.environ.get('DJANGO_SUPERUSER_EMAIL')
    password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')
    
    if not all([username, email, password]):
        print("Superuser environment variables not set, skipping superuser creation.")
        return False
    
    try:
        if not User.objects.filter(username=username).exists():
            print(f"Creating superuser {username}...")
            User.objects.create_superuser(username, email, password)
            print("Superuser created successfully!")
        else:
            print(f"Superuser {username} already exists.")
        return True
    except Exception as e:
        print(f"Error creating superuser: {e}")
        return False

def verify_tables():
    """Verify that tables exist and contain data."""
    print("Verifying tables...")
    try:
        # Check if tables exist and have data
        film_count = Film.objects.count()
        user_count = User.objects.count()
        vote_count = Vote.objects.count()
        profile_count = UserProfile.objects.count()
        tag_count = GenreTag.objects.count()
        
        print(f"Found {film_count} films, {user_count} users, {vote_count} votes, "
              f"{profile_count} profiles, and {tag_count} genre tags.")
        
        return film_count > 0
    except Exception as e:
        print(f"Error verifying tables: {e}")
        return False

if __name__ == "__main__":
    print("Starting database setup...")
    
    # Wait for the database to be available
    if not wait_for_db():
        sys.exit(1)
    
    # Ensure tables exist
    if not ensure_tables_exist():
        print("Failed to ensure tables exist!")
        sys.exit(1)
    
    # Load fixture data
    load_fixture_data()
    
    # Create superuser
    create_superuser()
    
    # Verify tables
    if verify_tables():
        print("Database setup completed successfully!")
        sys.exit(0)
    else:
        print("Database setup completed, but verification failed.")
        # Don't exit with error to allow the build to continue
        sys.exit(0) 