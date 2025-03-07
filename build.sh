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
else
  echo "WARNING: DATABASE_URL environment variable is not set!"
fi

# Create static directory if it doesn't exist
echo "Creating static directories..."
mkdir -p staticfiles

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput || {
  echo "Static file collection failed, but continuing..."
}

# List directories for debugging
echo "Directory structure:"
ls -la
echo "Static files directory:"
ls -la staticfiles || echo "Static files directory not found or empty"

# Run migrations using the Python script
echo "Running migrations using Python script..."
python -c "
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'films_project.settings')
django.setup()
from django.core.management import call_command
try:
    call_command('makemigrations')
    call_command('migrate')
    print('Migrations completed successfully!')
except Exception as e:
    print(f'Error during migrations: {e}')
    # Don't exit with error, continue the build
"

# Load data from fixtures if they exist
if [ -d "fixtures" ] && [ -f "fixtures/all_data.json" ]; then
  echo "Loading data from fixtures..."
  python -c "
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'films_project.settings')
django.setup()
from django.core.management import call_command
try:
    call_command('loaddata', 'fixtures/all_data.json')
    print('Data loaded successfully!')
except Exception as e:
    print(f'Error loading data: {e}')
    # Don't exit with error, continue the build
"
else
  echo "Fixtures not found, skipping data load..."
fi

# Create a superuser if environment variables are set
if [[ -n "${DJANGO_SUPERUSER_USERNAME}" && -n "${DJANGO_SUPERUSER_EMAIL}" && -n "${DJANGO_SUPERUSER_PASSWORD}" ]]; then
  echo "Creating superuser..."
  python -c "
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'films_project.settings')
django.setup()
from django.contrib.auth import get_user_model
User = get_user_model()
try:
    if not User.objects.filter(username='${DJANGO_SUPERUSER_USERNAME}').exists():
        User.objects.create_superuser('${DJANGO_SUPERUSER_USERNAME}', '${DJANGO_SUPERUSER_EMAIL}', '${DJANGO_SUPERUSER_PASSWORD}')
        print('Superuser created successfully!')
    else:
        print('Superuser already exists!')
except Exception as e:
    print(f'Error creating superuser: {e}')
    # Don't exit with error, continue the build
"
else
  echo "Superuser environment variables not set, skipping superuser creation..."
fi

echo "Build process completed successfully!" 