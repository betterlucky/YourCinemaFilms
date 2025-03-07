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

# Apply database migrations
echo "Applying migrations..."
python manage.py migrate --no-input

# Apply migrations for specific apps to ensure they're created
echo "Applying app-specific migrations..."
python manage.py migrate films_app --no-input
python manage.py migrate admin --no-input
python manage.py migrate auth --no-input
python manage.py migrate contenttypes --no-input
python manage.py migrate sessions --no-input
python manage.py migrate sites --no-input
python manage.py migrate allauth --no-input

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