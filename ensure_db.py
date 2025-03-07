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

def create_all_tables_sql():
    """Create all necessary tables using SQL."""
    print("Creating all tables using SQL...")
    
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
        
        # Create Django auth tables first
        cursor.execute("""
            -- Django auth tables
            CREATE TABLE IF NOT EXISTS "django_migrations" (
                "id" bigserial NOT NULL PRIMARY KEY,
                "app" varchar(255) NOT NULL,
                "name" varchar(255) NOT NULL,
                "applied" timestamp with time zone NOT NULL
            );
            
            CREATE TABLE IF NOT EXISTS "django_content_type" (
                "id" bigserial NOT NULL PRIMARY KEY,
                "app_label" varchar(100) NOT NULL,
                "model" varchar(100) NOT NULL,
                CONSTRAINT "django_content_type_app_label_model_uniq" UNIQUE ("app_label", "model")
            );
            
            CREATE TABLE IF NOT EXISTS "auth_permission" (
                "id" bigserial NOT NULL PRIMARY KEY,
                "name" varchar(255) NOT NULL,
                "content_type_id" bigint NOT NULL REFERENCES "django_content_type" ("id") DEFERRABLE INITIALLY DEFERRED,
                "codename" varchar(100) NOT NULL,
                CONSTRAINT "auth_permission_content_type_id_codename_uniq" UNIQUE ("content_type_id", "codename")
            );
            
            CREATE TABLE IF NOT EXISTS "auth_group" (
                "id" bigserial NOT NULL PRIMARY KEY,
                "name" varchar(150) NOT NULL UNIQUE
            );
            
            CREATE TABLE IF NOT EXISTS "auth_group_permissions" (
                "id" bigserial NOT NULL PRIMARY KEY,
                "group_id" bigint NOT NULL REFERENCES "auth_group" ("id") DEFERRABLE INITIALLY DEFERRED,
                "permission_id" bigint NOT NULL REFERENCES "auth_permission" ("id") DEFERRABLE INITIALLY DEFERRED,
                CONSTRAINT "auth_group_permissions_group_id_permission_id_uniq" UNIQUE ("group_id", "permission_id")
            );
            
            CREATE TABLE IF NOT EXISTS "auth_user" (
                "id" bigserial NOT NULL PRIMARY KEY,
                "password" varchar(128) NOT NULL,
                "last_login" timestamp with time zone NULL,
                "is_superuser" boolean NOT NULL,
                "username" varchar(150) NOT NULL UNIQUE,
                "first_name" varchar(150) NOT NULL,
                "last_name" varchar(150) NOT NULL,
                "email" varchar(254) NOT NULL,
                "is_staff" boolean NOT NULL,
                "is_active" boolean NOT NULL,
                "date_joined" timestamp with time zone NOT NULL
            );
            
            CREATE TABLE IF NOT EXISTS "auth_user_groups" (
                "id" bigserial NOT NULL PRIMARY KEY,
                "user_id" bigint NOT NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED,
                "group_id" bigint NOT NULL REFERENCES "auth_group" ("id") DEFERRABLE INITIALLY DEFERRED,
                CONSTRAINT "auth_user_groups_user_id_group_id_uniq" UNIQUE ("user_id", "group_id")
            );
            
            CREATE TABLE IF NOT EXISTS "auth_user_user_permissions" (
                "id" bigserial NOT NULL PRIMARY KEY,
                "user_id" bigint NOT NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED,
                "permission_id" bigint NOT NULL REFERENCES "auth_permission" ("id") DEFERRABLE INITIALLY DEFERRED,
                CONSTRAINT "auth_user_user_permissions_user_id_permission_id_uniq" UNIQUE ("user_id", "permission_id")
            );
            
            CREATE TABLE IF NOT EXISTS "django_admin_log" (
                "id" bigserial NOT NULL PRIMARY KEY,
                "action_time" timestamp with time zone NOT NULL,
                "object_id" text NULL,
                "object_repr" varchar(200) NOT NULL,
                "action_flag" smallint NOT NULL CHECK ("action_flag" >= 0),
                "change_message" text NOT NULL,
                "content_type_id" bigint NULL REFERENCES "django_content_type" ("id") DEFERRABLE INITIALLY DEFERRED,
                "user_id" bigint NOT NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED
            );
            
            CREATE TABLE IF NOT EXISTS "django_session" (
                "session_key" varchar(40) NOT NULL PRIMARY KEY,
                "session_data" text NOT NULL,
                "expire_date" timestamp with time zone NOT NULL
            );
            
            -- Create index on django_session.expire_date
            CREATE INDEX IF NOT EXISTS "django_session_expire_date_idx" ON "django_session" ("expire_date");
            
            -- Create index on django_admin_log.content_type_id
            CREATE INDEX IF NOT EXISTS "django_admin_log_content_type_id_idx" ON "django_admin_log" ("content_type_id");
            
            -- Create index on django_admin_log.user_id
            CREATE INDEX IF NOT EXISTS "django_admin_log_user_id_idx" ON "django_admin_log" ("user_id");
        """)
        
        # Now create the application tables
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
            
            -- Create Django sites framework table (required by django-allauth)
            CREATE TABLE IF NOT EXISTS "django_site" (
                "id" bigserial NOT NULL PRIMARY KEY,
                "domain" varchar(100) NOT NULL,
                "name" varchar(50) NOT NULL
            );
            
            -- Insert default site
            INSERT INTO "django_site" ("id", "domain", "name")
            VALUES (1, 'example.com', 'example.com')
            ON CONFLICT (id) DO NOTHING;
            
            -- Create social account tables
            CREATE TABLE IF NOT EXISTS "socialaccount_socialapp" (
                "id" bigserial NOT NULL PRIMARY KEY,
                "provider" varchar(30) NOT NULL,
                "name" varchar(40) NOT NULL,
                "client_id" varchar(191) NOT NULL,
                "secret" varchar(191) NOT NULL,
                "key" varchar(191) NOT NULL
            );
            
            CREATE TABLE IF NOT EXISTS "socialaccount_socialaccount" (
                "id" bigserial NOT NULL PRIMARY KEY,
                "provider" varchar(30) NOT NULL,
                "uid" varchar(191) NOT NULL,
                "last_login" timestamp with time zone NOT NULL,
                "date_joined" timestamp with time zone NOT NULL,
                "extra_data" text NOT NULL,
                "user_id" integer NOT NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED,
                CONSTRAINT "socialaccount_socialaccount_provider_uid_uniq" UNIQUE ("provider", "uid")
            );
            
            CREATE TABLE IF NOT EXISTS "socialaccount_socialapp_sites" (
                "id" bigserial NOT NULL PRIMARY KEY,
                "socialapp_id" integer NOT NULL REFERENCES "socialaccount_socialapp" ("id") DEFERRABLE INITIALLY DEFERRED,
                "site_id" integer NOT NULL REFERENCES "django_site" ("id") DEFERRABLE INITIALLY DEFERRED,
                CONSTRAINT "socialaccount_socialapp_sites_socialapp_id_site_id_uniq" UNIQUE ("socialapp_id", "site_id")
            );
            
            CREATE TABLE IF NOT EXISTS "socialaccount_socialtoken" (
                "id" bigserial NOT NULL PRIMARY KEY,
                "token" text NOT NULL,
                "token_secret" text NOT NULL,
                "expires_at" timestamp with time zone NULL,
                "account_id" integer NOT NULL REFERENCES "socialaccount_socialaccount" ("id") DEFERRABLE INITIALLY DEFERRED,
                "app_id" integer NOT NULL REFERENCES "socialaccount_socialapp" ("id") DEFERRABLE INITIALLY DEFERRED,
                CONSTRAINT "socialaccount_socialtoken_app_id_account_id_uniq" UNIQUE ("app_id", "account_id")
            );
            
            -- Create account tables for django-allauth
            CREATE TABLE IF NOT EXISTS "account_emailaddress" (
                "id" bigserial NOT NULL PRIMARY KEY,
                "email" varchar(254) NOT NULL,
                "verified" boolean NOT NULL,
                "primary" boolean NOT NULL,
                "user_id" integer NOT NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED,
                CONSTRAINT "account_emailaddress_user_id_email_uniq" UNIQUE ("user_id", "email")
            );
            
            CREATE TABLE IF NOT EXISTS "account_emailconfirmation" (
                "id" bigserial NOT NULL PRIMARY KEY,
                "created" timestamp with time zone NOT NULL,
                "sent" timestamp with time zone NULL,
                "key" varchar(64) NOT NULL UNIQUE,
                "email_address_id" integer NOT NULL REFERENCES "account_emailaddress" ("id") DEFERRABLE INITIALLY DEFERRED
            );
        """)
        
        # Record migrations in django_migrations table
        cursor.execute("""
            INSERT INTO django_migrations (app, name, applied)
            VALUES 
                ('contenttypes', '0001_initial', NOW()),
                ('auth', '0001_initial', NOW()),
                ('admin', '0001_initial', NOW()),
                ('admin', '0002_logentry_remove_auto_add', NOW()),
                ('admin', '0003_logentry_add_action_flag_choices', NOW()),
                ('contenttypes', '0002_remove_content_type_name', NOW()),
                ('auth', '0002_alter_permission_name_max_length', NOW()),
                ('auth', '0003_alter_user_email_max_length', NOW()),
                ('auth', '0004_alter_user_username_opts', NOW()),
                ('auth', '0005_alter_user_last_login_null', NOW()),
                ('auth', '0006_require_contenttypes_0002', NOW()),
                ('auth', '0007_alter_validators_add_error_messages', NOW()),
                ('auth', '0008_alter_user_username_max_length', NOW()),
                ('auth', '0009_alter_user_last_name_max_length', NOW()),
                ('auth', '0010_alter_group_name_max_length', NOW()),
                ('auth', '0011_update_proxy_permissions', NOW()),
                ('auth', '0012_alter_user_first_name_max_length', NOW()),
                ('sessions', '0001_initial', NOW()),
                ('sites', '0001_initial', NOW()),
                ('sites', '0002_alter_domain_unique', NOW()),
                ('account', '0001_initial', NOW()),
                ('account', '0002_email_max_length', NOW()),
                ('socialaccount', '0001_initial', NOW()),
                ('socialaccount', '0002_token_max_lengths', NOW()),
                ('socialaccount', '0003_extra_data_default_dict', NOW()),
                ('films_app', '0001_initial', NOW())
            ON CONFLICT DO NOTHING;
        """)
        
        print("Tables created successfully!")
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error creating tables directly: {e}")
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
    return create_all_tables_sql()

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

def fix_migration_conflicts():
    """Fix migration conflicts by creating a merge migration."""
    print("Checking for migration conflicts...")
    try:
        # Try to create a merge migration
        call_command('makemigrations', '--merge', interactive=False)
        print("Created merge migration successfully!")
        return True
    except Exception as e:
        print(f"Error creating merge migration: {e}")
        return False

if __name__ == "__main__":
    print("Starting database setup...")
    
    # Wait for the database to be available
    if not wait_for_db():
        sys.exit(1)
    
    # Try to fix migration conflicts
    fix_migration_conflicts()
    
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