#!/usr/bin/env python
"""
Script to load data from JSON fixtures into the PostgreSQL database.
This script should be run on Render after the database tables have been created.
"""

import os
import sys
import django
from django.core.management import call_command

def main():
    """Main function to load data from fixtures."""
    print("Starting data import...")
    
    # Set up Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'films_project.settings')
    django.setup()
    
    # Check if the fixtures directory exists
    if not os.path.exists('fixtures'):
        print("Error: fixtures directory not found!")
        print("Make sure you've uploaded the fixtures directory to the server.")
        sys.exit(1)
    
    # Check if the all_data.json file exists
    if not os.path.exists('fixtures/all_data.json'):
        print("Error: fixtures/all_data.json not found!")
        print("Make sure you've uploaded the all_data.json file to the fixtures directory.")
        sys.exit(1)
    
    try:
        # Load data from the fixture file
        print("Loading data from fixtures/all_data.json...")
        call_command('loaddata', 'fixtures/all_data.json')
        print("Data import completed successfully!")
    except Exception as e:
        print(f"Error loading data: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 