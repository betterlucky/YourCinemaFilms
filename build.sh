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

echo "Build process completed successfully!" 