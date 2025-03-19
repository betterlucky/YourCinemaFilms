# Setting Up Google OAuth for Your Cinema Films

This guide will help you set up Google OAuth for your Your Cinema Films application.

## Prerequisites

1. A Google account
2. Access to the [Google Cloud Console](https://console.cloud.google.com/)

## Step 1: Create a Google OAuth Client ID and Secret

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Navigate to "APIs & Services" > "Credentials"
4. Click "Create Credentials" > "OAuth client ID"
5. Select "Web application" as the application type
6. Set a name for your OAuth client (e.g., "Your Cinema Films")
7. Add authorized JavaScript origins:
   - For local development: `http://localhost:8000`
   - For production: `https://yourcinemafilms.theworkpc.com`
8. Add authorized redirect URIs:
   - For local development: `http://localhost:8000/accounts/google/login/callback/`
   - For production: `https://yourcinemafilms.theworkpc.com/accounts/google/login/callback/`
9. Click "Create"
10. Note down the Client ID and Client Secret

## Step 2: Add Google OAuth Credentials to .env File

Add your Google OAuth credentials to your `.env` file:

```
GOOGLE_CLIENT_ID=your_client_id_here
GOOGLE_CLIENT_SECRET=your_client_secret_here
```

You can also specify your environment in the `.env` file:

```
# For development (default if not specified)
PRODUCTION=false

# For production
# PRODUCTION=true
```

## Step 3: Run the Setup Script

The setup script will:
1. Automatically detect whether you're in development or production environment
2. Update the Site model with the correct domain based on your environment
3. Create a Google SocialApp with your credentials
4. Associate the SocialApp with the Site

Run the setup script:

```bash
python setup_google_oauth.py
```

## Step 4: Restart the Development Server

Restart your Django development server:

```bash
python manage.py runserver
```

## Step 5: Test Google OAuth

1. Go to the login page: `http://localhost:8000/accounts/login/`
2. Click the "Sign in with Google" button
3. Follow the Google authentication flow
4. You should be redirected back to your application and logged in

## Switching Between Environments

The application now automatically detects your environment:

### For Development:
```
# In your .env file
PRODUCTION=false
```

### For Production:
```
# In your .env file
PRODUCTION=true
```

After changing the environment setting:
1. Run `python setup_google_oauth.py` to update the Site model
2. Restart the Django server

## Environment Detection Logic

The environment is determined using the following logic:
1. If `PRODUCTION=true` in your `.env` file, use production settings
2. If `PRODUCTION=false` in your `.env` file, use development settings
3. If `PRODUCTION` is not set, fall back to using the `DEBUG` setting in Django

## Checking Your Environment

You can check your current environment settings by running:

```bash
python check_environment.py
```

This will show you:
- The current environment (Development or Production)
- The site domain and protocol being used
- The callback URL configuration
- The Site model and SocialApp settings

## Troubleshooting OAuth Issues

If you encounter redirect URI mismatch errors or other OAuth issues, you can run:

```bash
python check_oauth_config.py
```

This script will:
- Display your current OAuth configuration
- Provide instructions for fixing common issues
- Offer to open the Google Cloud Console for you to make necessary changes

## General Troubleshooting

If you encounter any issues:

1. Check that the Site model has the correct domain
2. Verify that the Google SocialApp is created and associated with the Site
3. Ensure the Client ID and Client Secret are correct in your `.env` file
4. Check the Django logs for any error messages
5. Make sure the redirect URIs in the Google Cloud Console match the ones in your application
6. Clear your browser cookies and cache if you continue to have issues 