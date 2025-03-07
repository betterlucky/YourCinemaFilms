#!/usr/bin/env python
"""
Script to export migrations from the local database.
Run this script before deploying to ensure all migrations are properly created.
"""

import os
import sys
import subprocess

def main():
    print("Exporting migrations from local database...")
    
    # Make sure we're in the project directory
    project_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_dir)
    
    # Make migrations for all apps
    subprocess.run([sys.executable, "manage.py", "makemigrations"], check=True)
    
    # Make migrations specifically for the films_app
    subprocess.run([sys.executable, "manage.py", "makemigrations", "films_app"], check=True)
    
    print("Migrations exported successfully.")
    print("Please commit these migrations to your repository before deploying.")

if __name__ == "__main__":
    main() 