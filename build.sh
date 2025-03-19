#!/usr/bin/env bash
# exit on error
set -o errexit

echo "Starting build process..."

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Print Python and pip versions for debugging
echo "Python version:"
python --version
echo "Pip version:"
pip --version

# Print database URL (with masked password)
if [ -n "$DATABASE_URL" ]; then
  # Extract parts of the URL without showing the password
  DB_URL_MASKED=$(echo $DATABASE_URL | sed -E 's/(:\/\/[^:]+:)[^@]+(@)/\1*****\2/')
  echo "Database URL: $DB_URL_MASKED"
  
  # Wait for database to be available (only for PostgreSQL)
  echo "Waiting for database to be available..."
  python -c "
  import os
  import sys
  import time
  import django
  from django.db import connection
  from django.db.utils import OperationalError

  os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'films_project.settings')
  django.setup()

  retries = 0
  max_retries = 5
  retry_interval = 5

  while retries < max_retries:
      try:
          connection.ensure_connection()
          print('Database connection successful!')
          sys.exit(0)
      except OperationalError as e:
          retries += 1
          print(f'Database connection failed (attempt {retries}/{max_retries}): {e}')
          if retries < max_retries:
              print(f'Retrying in {retry_interval} seconds...')
              time.sleep(retry_interval)

  print('Failed to connect to the database after multiple attempts.')
  sys.exit(1)
  "
else
  echo "Using SQLite database"
fi

# Create static directory if it doesn't exist
echo "Creating static directories..."
mkdir -p staticfiles
mkdir -p static

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Run migrations
echo "Running migrations..."
# First, make migrations to ensure all model changes are captured
python manage.py makemigrations --noinput

# Apply migrations
python manage.py migrate --noinput

# Update site domain for OAuth
echo "Updating site domain..."
python update_site_domain.py

# Set up Google OAuth
echo "Setting up Google OAuth..."
python setup_google_oauth.py

# Note: We've removed the cinema cache update from the build process
# to prevent duplicate TMDB API calls. The cron job will handle this.

echo "Build process completed successfully!" 