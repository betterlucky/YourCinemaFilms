#!/usr/bin/env python
"""
Script to check database connection and verify tables.
"""

import os
import sys
import django
from django.db import connections, connection, OperationalError, ProgrammingError

def main():
    print("Checking database connection...")
    
    # Set up Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'films_project.settings')
    django.setup()
    
    # Check if DATABASE_URL is set
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        print("WARNING: DATABASE_URL environment variable is not set!")
    
    # Try to connect to the database
    try:
        connections['default'].ensure_connection()
        print("Database connection successful!")
    except OperationalError as e:
        print(f"Database connection error: {e}")
        print("Please check your DATABASE_URL environment variable.")
        sys.exit(1)
    
    # List all tables in the database
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            tables = cursor.fetchall()
            
            if not tables:
                print("No tables found in the database!")
                sys.exit(1)
            
            print("Database tables:")
            for table in tables:
                print(f"- {table[0]}")
                
            # Check for specific tables
            table_names = [table[0] for table in tables]
            required_tables = [
                'films_app_film',
                'films_app_vote',
                'films_app_userprofile',
                'films_app_genretag',
                'auth_user'
            ]
            
            missing_tables = [table for table in required_tables if table not in table_names]
            if missing_tables:
                print(f"WARNING: Missing required tables: {', '.join(missing_tables)}")
                sys.exit(1)
            else:
                print("All required tables are present!")
                
    except ProgrammingError as e:
        print(f"Error querying database tables: {e}")
        sys.exit(1)
    
    print("Database check completed successfully!")

if __name__ == "__main__":
    main() 