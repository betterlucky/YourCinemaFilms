"""
Django settings for films_project project.
"""

import os
from pathlib import Path
import dj_database_url
import logging
from .env_loader import load_environment_variables

# Load environment variables from secure location
load_environment_variables()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DJANGO_DEBUG', '0') == 'True'

# Determine if we're in production mode
production_env = os.environ.get('PRODUCTION', '').lower()
if production_env == 'true':
    PRODUCTION = True
elif production_env == 'false':
    PRODUCTION = False
else:
    # If PRODUCTION is not explicitly set, fall back to DEBUG setting
    PRODUCTION = not DEBUG

# Site and domain settings
ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
SITE_DOMAIN = 'yourcinemafilms.theworkpc.com' if PRODUCTION else f"localhost:{os.environ.get('PORT', '8000')}"
SITE_PROTOCOL = 'https' if PRODUCTION else 'http'
SITE_ID = 1  # for django.contrib.sites

# Security settings
if DEBUG:
    # For local development, disable secure SSL settings
    SECURE_PROXY_SSL_HEADER = None
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
else:
    # For production, enable secure SSL settings
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    # Additional security settings for production
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    X_FRAME_OPTIONS = 'DENY'

# CSRF Trusted Origins - needed for Docker and OAuth
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:8080',
    'http://127.0.0.1:8080',
    'http://localhost',
    'http://127.0.0.1',
    'https://yourcinemafilms.theworkpc.com'
]

# Configure logging - more concise configuration
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
            'level': os.environ.get('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
        'films_app': {
            'handlers': ['console'],
            'level': os.environ.get('FILMS_APP_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
    },
}

# Application definition - grouped by purpose
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
]

THIRD_PARTY_APPS = [
    # Authentication
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    
    # API and cross-origin
    'rest_framework',
    'corsheaders',
    
    # UI and charts
    'chartjs',
]

LOCAL_APPS = [
    'films_app',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# Middleware - ordered for optimal performance
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Static files
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',  # CORS headers
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
                'films_app.context_processors.site_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'films_project.wsgi.application'

# Database configuration
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.environ.get('DJANGO_DB_PATH', os.path.join(BASE_DIR, 'db.sqlite3')),
    }
}

# Configure database using DATABASE_URL environment variable if available
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    # Parse the DATABASE_URL and update the default database configuration
    db_config = dj_database_url.parse(DATABASE_URL)
    
    # Log database connection info (without password)
    if DEBUG:
        db_info = dict(db_config)
        if 'PASSWORD' in db_info:
            db_info['PASSWORD'] = '********'  # Mask the password in logs
        print(f"Database configuration: {db_info}")
    
    DATABASES['default'] = db_config
    
    # PostgreSQL specific settings
    if DATABASES['default']['ENGINE'] == 'django.db.backends.postgresql':
        # Ensure PostgreSQL uses the correct schema
        DATABASES['default']['OPTIONS'] = {
            'options': '-c search_path=public',
            'application_name': 'yourcinemafilms',  # Add application name for better logging
            'connect_timeout': 10,
            'keepalives': 1,
            'keepalives_idle': 30,
            'keepalives_interval': 10,
            'keepalives_count': 5,
        }
        
        # Connection pooling settings
        DATABASES['default']['CONN_MAX_AGE'] = 60  # 60 seconds
        DATABASES['default']['CONN_HEALTH_CHECKS'] = True

# Only print database engine in debug mode
if DEBUG:
    print(f"Using database engine: {DATABASES['default']['ENGINE']}")

# Ensure migrations are created for all apps
MIGRATION_MODULES = {
    'films_app': 'films_app.migrations',
}

# Set default auto field
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Password validation
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
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files configuration
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

# AllAuth settings - consolidated
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = 'optional'
ACCOUNT_AUTHENTICATION_METHOD = 'username_email'
ACCOUNT_LOGOUT_ON_GET = True
ACCOUNT_ADAPTER = 'films_app.adapters.CustomAccountAdapter'
ACCOUNT_CONFIRM_EMAIL_ON_GET = True
ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS = 3
ACCOUNT_EMAIL_SUBJECT_PREFIX = 'YourCinemaFilms - '
ACCOUNT_DEFAULT_HTTP_PROTOCOL = SITE_PROTOCOL

# Social account settings - consolidated
SOCIALACCOUNT_EMAIL_VERIFICATION = 'none'
SOCIALACCOUNT_EMAIL_REQUIRED = False
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_ADAPTER = 'films_app.adapters.CustomSocialAccountAdapter'
SOCIALACCOUNT_QUERY_EMAIL = True
SOCIALACCOUNT_STORE_TOKENS = True
SOCIALACCOUNT_USERNAME_REQUIRED = False
SOCIALACCOUNT_CALLBACK_URL = f"{SITE_PROTOCOL}://{SITE_DOMAIN}/accounts/google/login/callback/"

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

# Login/logout URLs
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# Email Configuration - consolidated
if DEBUG:
    # Use console backend for development
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    # For production, use a proper email service
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = os.environ.get('EMAIL_HOST', '')
    EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
    EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True').lower() == 'true'
    EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
    EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
    DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'dwgharris@gmail.com')

# TMDB API settings
TMDB_API_KEY = os.environ.get('TMDB_API_KEY', '')
TMDB_SORT_BY = os.environ.get('TMDB_SORT_BY', 'revenue.desc,vote_count.desc,popularity.desc')

# Cinema settings - consolidated
UPCOMING_FILMS_MONTHS = int(os.environ.get('UPCOMING_FILMS_MONTHS', '6'))
MAX_CINEMA_FILMS = int(os.environ.get('MAX_CINEMA_FILMS', '20'))
CACHE_UPDATE_INTERVAL_MINUTES = int(os.environ.get('CACHE_UPDATE_INTERVAL_MINUTES', '15'))
FILMS_PER_PAGE = int(os.environ.get('FILMS_PER_PAGE', '8'))
CONTACT_EMAIL = os.environ.get('CONTACT_EMAIL', 'classicsbackonscreen@gmail.com')

# CORS settings
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    'http://localhost:8000',
    'http://127.0.0.1:8000',
    'http://localhost:8080',
    'http://127.0.0.1:8080',
]
if PRODUCTION:
    CORS_ALLOWED_ORIGINS.append(f'{SITE_PROTOCOL}://{SITE_DOMAIN}')

# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/day',
        'user': '1000/day'
    }
}

# Cache settings
CACHE_TYPE = os.environ.get('CACHE_TYPE', 'local')
CACHE_TIMEOUT = int(os.environ.get('CACHE_TIMEOUT', 3600))

# Configure caching based on environment
if PRODUCTION:
    # Use memory cache for production if no specific cache is configured
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'unique-snowflake',
            'TIMEOUT': CACHE_TIMEOUT,
        }
    }
else:
    # Use dummy cache for development
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        }
    } 