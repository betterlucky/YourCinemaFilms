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
mkdir -p static

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

# Run the database setup script
echo "Setting up database..."
python ensure_db.py || {
  echo "Database setup failed, but continuing..."
}

# Explicitly run migrations for films_app to ensure Achievement model is created
echo "Running migrations for films_app..."
python manage.py makemigrations films_app --noinput || {
  echo "Making migrations for films_app failed, but continuing..."
}
python manage.py migrate films_app --noinput || {
  echo "Migrating films_app failed, but continuing..."
}

# Run the comprehensive migrations script
echo "Running comprehensive migrations script..."
python run_migrations.py || {
  echo "Comprehensive migrations failed, but continuing..."
}

# Update the site domain
echo "Updating site domain..."
python update_site_domain.py || {
  echo "Site domain update failed, but continuing..."
}

# Set up Google OAuth
echo "Setting up Google OAuth..."
python setup_google_oauth.py || {
  echo "Google OAuth setup failed, but continuing..."
}

echo "Build process completed successfully!" 