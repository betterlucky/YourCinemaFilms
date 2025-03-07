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
python manage.py collectstatic --noinput

# Run migrations using the Python script
echo "Running migrations using Python script..."
python run_migrations.py || {
  echo "Migration script failed. Continuing anyway..."
}

# Load data from fixtures if they exist
if [ -d "fixtures" ] && [ -f "fixtures/all_data.json" ]; then
  echo "Loading data from fixtures..."
  python load_data.py || echo "Data loading failed, continuing..."
fi

# Create a superuser using the Python script
echo "Creating superuser using Python script..."
python create_superuser.py || {
  echo "Superuser creation script failed. Continuing anyway..."
}

echo "Build process completed successfully!" 