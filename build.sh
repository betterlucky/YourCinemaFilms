#!/usr/bin/env bash
# exit on error
set -o errexit

# Print commands for debugging
set -x

echo "Starting build process..."

# Install dependencies
pip install -r requirements.txt

# Print database URL (with masked password)
if [ -n "$DATABASE_URL" ]; then
  # Extract parts of the URL without showing the password
  DB_URL_MASKED=$(echo $DATABASE_URL | sed -E 's/(:\/\/[^:]+:)[^@]+(@)/\1*****\2/')
  echo "Database URL: $DB_URL_MASKED"
else
  echo "WARNING: DATABASE_URL environment variable is not set!"
fi

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --no-input

# Check database connection
echo "Checking database connection..."
python check_db.py || {
  echo "Database check failed. Continuing with migrations anyway..."
}

# Make migrations first to ensure they exist
echo "Creating migrations..."
python manage.py makemigrations --no-input

# Apply database migrations with retries
echo "Applying migrations..."
MAX_RETRIES=3
RETRY_COUNT=0
MIGRATION_SUCCESS=false

while [ $RETRY_COUNT -lt $MAX_RETRIES ] && [ "$MIGRATION_SUCCESS" = false ]; do
  echo "Migration attempt $(($RETRY_COUNT + 1))..."
  
  if python manage.py migrate --no-input; then
    MIGRATION_SUCCESS=true
    echo "Migrations applied successfully!"
  else
    RETRY_COUNT=$(($RETRY_COUNT + 1))
    if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
      echo "Migration failed. Retrying in 5 seconds..."
      sleep 5
    else
      echo "Migration failed after $MAX_RETRIES attempts."
      echo "Will try to apply custom SQL migrations directly..."
      
      # Try to apply the custom SQL directly
      python -c "
import os, django, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'films_project.settings')
django.setup()
from django.db import connection

try:
    with connection.cursor() as cursor:
        # Create films_app_film table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS \"films_app_film\" (
                \"id\" bigserial NOT NULL PRIMARY KEY,
                \"imdb_id\" varchar(20) NOT NULL UNIQUE,
                \"title\" varchar(255) NOT NULL,
                \"year\" varchar(10) NOT NULL,
                \"poster_url\" varchar(500) NULL,
                \"director\" varchar(255) NULL,
                \"plot\" text NULL,
                \"genres\" varchar(255) NULL,
                \"runtime\" varchar(20) NULL,
                \"actors\" text NULL,
                \"created_at\" timestamp with time zone NOT NULL
            );
        ''')
        print('Created films_app_film table')
        
        # Create other tables...
        # (Add more CREATE TABLE statements as needed)
        
    print('Direct SQL migration completed successfully!')
except Exception as e:
    print(f'Error applying direct SQL: {e}')
    sys.exit(1)
"
    fi
  fi
done

# Apply migrations for specific apps to ensure they're created
echo "Applying app-specific migrations..."
python manage.py migrate films_app --no-input || echo "films_app migrations failed, continuing..."
python manage.py migrate admin --no-input || echo "admin migrations failed, continuing..."
python manage.py migrate auth --no-input || echo "auth migrations failed, continuing..."
python manage.py migrate contenttypes --no-input || echo "contenttypes migrations failed, continuing..."
python manage.py migrate sessions --no-input || echo "sessions migrations failed, continuing..."
python manage.py migrate sites --no-input || echo "sites migrations failed, continuing..."
python manage.py migrate allauth --no-input || echo "allauth migrations failed, continuing..."

# Check database again after migrations
echo "Checking database after migrations..."
python check_db.py || {
  echo "Database check after migrations failed. This may indicate a problem with the database setup."
  echo "Continuing anyway, but the application may not work correctly."
}

# Create a superuser if not exists (using environment variables)
if [[ -n "${DJANGO_SUPERUSER_USERNAME}" && -n "${DJANGO_SUPERUSER_EMAIL}" && -n "${DJANGO_SUPERUSER_PASSWORD}" ]]; then
  echo "Creating superuser..."
  python manage.py createsuperuser --noinput || echo "Superuser already exists."
fi

echo "Build process completed successfully!" 