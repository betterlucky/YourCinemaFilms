#!/usr/bin/env bash
# exit on error
set -o errexit

# Print commands for debugging
set -x

# Install dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --no-input

# Make migrations first to ensure they exist
python manage.py makemigrations

# Apply database migrations
python manage.py migrate

# Apply migrations for specific apps to ensure they're created
python manage.py migrate films_app
python manage.py migrate admin
python manage.py migrate auth
python manage.py migrate contenttypes
python manage.py migrate sessions
python manage.py migrate sites
python manage.py migrate allauth

# Create a superuser if not exists (using environment variables)
if [[ -n "${DJANGO_SUPERUSER_USERNAME}" && -n "${DJANGO_SUPERUSER_EMAIL}" && -n "${DJANGO_SUPERUSER_PASSWORD}" ]]; then
  python manage.py createsuperuser --noinput || echo "Superuser already exists."
fi 