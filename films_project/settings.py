"""
Django settings for films_project project.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url
import logging

# Load environment variables from .env file
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-default-key-for-development')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# Add render.com domain to allowed hosts
if not DEBUG:
    ALLOWED_HOSTS.extend(['.onrender.com'])

# Configure logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
        'films_app': {
            'handlers': ['console'],
            'level': os.getenv('FILMS_APP_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
    },
}

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    
    # Third-party apps
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'rest_framework',
    'corsheaders',
    'chartjs',
    
    # Local apps
    'films_app',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'django_htmx.middleware.HtmxMiddleware',
]

ROOT_URLCONF = 'films_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'films_project.wsgi.application'

# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Configure database using DATABASE_URL environment variable if available
DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL:
    # Parse the DATABASE_URL and update the default database configuration
    db_config = dj_database_url.parse(DATABASE_URL)
    
    # Log database connection info (without password)
    db_info = dict(db_config)
    if 'PASSWORD' in db_info:
        db_info['PASSWORD'] = '********'  # Mask the password in logs
    print(f"Database configuration: {db_info}")
    
    DATABASES['default'] = db_config
    
    # Ensure PostgreSQL uses the correct schema
    DATABASES['default']['OPTIONS'] = {
        'options': '-c search_path=public',
        'application_name': 'yourcinemafilms'  # Add application name for better logging
    }
    
    # Set a longer connection timeout for initial connection
    DATABASES['default']['CONN_MAX_AGE'] = 60  # Reduced from 600 to handle free tier spin-down
    DATABASES['default']['CONN_HEALTH_CHECKS'] = True
    
    # Add connection retry logic for free tier spin-down
    DATABASES['default']['OPTIONS']['connect_timeout'] = 10
    DATABASES['default']['OPTIONS']['keepalives'] = 1
    DATABASES['default']['OPTIONS']['keepalives_idle'] = 30
    DATABASES['default']['OPTIONS']['keepalives_interval'] = 10
    DATABASES['default']['OPTIONS']['keepalives_count'] = 5

# Print database engine being used (for debugging)
print(f"Using database engine: {DATABASES['default']['ENGINE']}")

# Ensure migrations are created for all apps
MIGRATION_MODULES = {
    'films_app': 'films_app.migrations',
}

# Set default auto field
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

# Enable WhiteNoise for serving static files in production
if not DEBUG:
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Authentication settings
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

SITE_ID = 1

# AllAuth settings
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = 'optional'  # Changed from 'mandatory' to 'optional' for easier testing
ACCOUNT_AUTHENTICATION_METHOD = 'username_email'
ACCOUNT_LOGOUT_ON_GET = True
ACCOUNT_ADAPTER = 'films_app.adapters.CustomAccountAdapter'

# Social account settings
SOCIALACCOUNT_EMAIL_VERIFICATION = 'none'
SOCIALACCOUNT_EMAIL_REQUIRED = False
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_ADAPTER = 'films_app.adapters.CustomSocialAccountAdapter'

# Important settings for handling different usernames
SOCIALACCOUNT_QUERY_EMAIL = True  # Request email from providers that don't provide it by default
SOCIALACCOUNT_STORE_TOKENS = True  # Store authentication tokens
SOCIALACCOUNT_USERNAME_REQUIRED = False  # Don't require a username for social accounts

# Social account providers
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': [
            'profile',
            'email',
        ],
        'AUTH_PARAMS': {
            'access_type': 'online',
        },
        'FETCH_USERINFO': True,
        'USERINFO_FIELDS': [
            'email',
            'first_name',
            'last_name',
            'picture',
        ],
    }
}

LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# Email Configuration
if DEBUG:
    # Use console backend for development
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    # For production, use a proper email service
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = os.getenv('EMAIL_HOST', '')
    EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
    EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() == 'true'
    EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
    EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
    DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@yourcinemafilms.onrender.com')

# Modify AllAuth settings to handle email verification better
ACCOUNT_EMAIL_VERIFICATION = 'optional'  # Options: 'mandatory', 'optional', 'none'
ACCOUNT_CONFIRM_EMAIL_ON_GET = True
ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS = 3
ACCOUNT_EMAIL_SUBJECT_PREFIX = 'YourCinemaFilms - '

# TMDB API settings
TMDB_API_KEY = os.getenv('TMDB_API_KEY', '')
TMDB_SORT_BY = os.getenv('TMDB_SORT_BY', 'popularity.desc')  # Default sort order for TMDB API requests

# Cinema settings
UPCOMING_FILMS_MONTHS = int(os.getenv('UPCOMING_FILMS_MONTHS', '6'))  # Number of months to look ahead for upcoming films
MAX_CINEMA_FILMS = int(os.getenv('MAX_CINEMA_FILMS', '20'))  # Maximum number of films to display in each section

# CORS settings
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]

# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
} 