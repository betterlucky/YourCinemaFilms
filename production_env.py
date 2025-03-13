"""
Production environment variables for YourCinemaFilms project.
This file should be placed at /etc/yourcinemafilms/env.py on the production server.
"""

# Django settings
DJANGO_SECRET_KEY = "your-secure-production-key-here"
DJANGO_DEBUG = "False"
DJANGO_ALLOWED_HOSTS = "yourcinemafilms.theworkpc.com,localhost"
APP_NAME = "YourCinemaFilms"

# Email settings
EMAIL_HOST_PASSWORD = "your-email-password"
CONTACT_EMAIL = "classicsbackonscreen@gmail.com"

# TMDB API settings
TMDB_API_KEY = "your-tmdb-api-key"

# Google OAuth settings
GOOGLE_CLIENT_ID = "your-google-client-id"
GOOGLE_CLIENT_SECRET = "your-google-client-secret"

# Application settings
UPCOMING_FILMS_MONTHS = "6"
TMDB_SORT_BY = "popularity.desc"

# Environment setting
PRODUCTION = "true" 