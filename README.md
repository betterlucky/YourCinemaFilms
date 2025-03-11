# YourCinemaFilms

A web platform designed to identify which films people would actually go to the cinema to watch. Unlike general film rating or recommendation platforms, our specific focus is on theatrical attendance - helping users discover films worth experiencing on the big screen and helping cinemas understand audience demand.

## Features

### User System
- User registration and authentication with Google OAuth
- Extended user profiles with demographic information
- Privacy controls for profile information
- Profile management with customizable profile pictures
- Achievement system for user engagement

### Film Database
- Film information from TMDB API with UK-specific parameters
- UK release dates and certifications when available
- Film details including title, year, director, plot, genres
- Poster images and basic metadata
- Genre tagging system (including user-generated tags)

### Caching System
- Two-tier caching system (JSON files and database)
- Automatic cache updates via management command
- Configurable cache preferences
- Reduced API calls for better performance

### Voting System
- Users can vote for films they want to see in theaters
- Vote tracking and display on user profiles
- Aggregated vote counts to show popularity
- HTMX integration for seamless vote management

### Dashboard and Analytics
- Site activity statistics with customizable time periods (week/month/year/all-time)
- Genre distribution visualization
- Timeline of voting activity
- Top films by vote count
- Active user tracking
- Detailed activity logs

## Technology Stack

- **Backend**: Django 5.1 (Python web framework)
- **Frontend**: Bootstrap 5, jQuery, HTMX
- **Database**: PostgreSQL (production), SQLite (development)
- **Authentication**: django-allauth for social authentication
- **API**: Django REST Framework for API endpoints
- **Visualization**: Chart.js for data visualization
- **Deployment**: Render.com for cloud hosting

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/YourCinemaFilms.git
   cd YourCinemaFilms
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   Create a `.env` file in the project root with the following variables:
   ```
   SECRET_KEY=your_secret_key
   DEBUG=True
   TMDB_API_KEY=your_tmdb_api_key
   GOOGLE_CLIENT_ID=your_google_client_id
   GOOGLE_CLIENT_SECRET=your_google_client_secret
   ```

5. Run migrations:
   ```
   python manage.py migrate
   ```

6. Create a superuser:
   ```
   python manage.py createsuperuser
   ```

7. Run the development server:
   ```
   python manage.py runserver
   ```

8. Access the application at http://localhost:8000

## Setting Up Google OAuth

1. Go to the [Google Developer Console](https://console.developers.google.com/)
2. Create a new project
3. Enable the Google+ API
4. Create OAuth 2.0 credentials
5. Add the redirect URI: `http://localhost:8000/accounts/google/login/callback/`
6. Add your client ID and secret to the `.env` file
7. Configure the social application in the Django admin site:
   - Go to http://localhost:8000/admin/
   - Navigate to "Social applications" under "Social Accounts"
   - Add a new social application with your Google credentials

## Deployment

The application is configured for deployment on Render.com:

1. Fork or clone this repository to your GitHub account
2. Create a new Web Service on Render.com
3. Connect your GitHub repository
4. Set the required environment variables:
   - `SECRET_KEY`
   - `DEBUG` (set to False for production)
   - `TMDB_API_KEY`
   - `GOOGLE_CLIENT_ID`
   - `GOOGLE_CLIENT_SECRET`
   - `DJANGO_SUPERUSER_USERNAME`
   - `DJANGO_SUPERUSER_EMAIL`
   - `DJANGO_SUPERUSER_PASSWORD`
5. Deploy the application

## Project Structure

- `films_project/`: Main project settings
- `films_app/`: Main application code
  - `models.py`: Database models
  - `views.py`: View functions
  - `urls.py`: URL routing
  - `api/`: REST API endpoints
  - `templatetags/`: Custom template tags
  - `utils.py`: Utility functions
- `templates/`: HTML templates
  - `films_app/`: Application templates
  - `account/`: Authentication templates
- `static/`: Static files (CSS, JS, images)
- `profile_images/`: User-uploaded profile images
- `build.sh`: Deployment build script
- `render.yaml`: Render.com configuration

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit your changes: `git commit -m 'Add some feature'`
4. Push to the branch: `git push origin feature-name`
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [TMDB API](https://www.themoviedb.org/) for film data with UK-specific parameters
- [Bootstrap](https://getbootstrap.com/) for the UI framework
- [Django](https://www.djangoproject.com/) for the web framework
- [django-allauth](https://django-allauth.readthedocs.io/) for authentication
- [Chart.js](https://www.chartjs.org/) for data visualization

## Scheduled Tasks

### Daily Cinema Cache Update

The application includes a scheduled task that runs daily at midnight UTC to update the cache of current and upcoming UK cinema releases. This ensures that the Cinema page always displays the latest information without requiring manual updates.

#### How it works

1. The task is configured as a cron job in the `render.yaml` file
2. It runs the `update_cinema_cache.py` script, which:
   - Flags films that need status checks based on their release dates
   - Connects to the TMDB API
   - Fetches current and upcoming UK cinema releases in a single optimized run
   - Updates the database with the latest film information
   - Updates the JSON cache files

#### Optimized Data Retrieval

The system has been optimized to reduce API calls and improve efficiency:

1. **Efficient Data Extraction**: Only extracts the specific data needed from TMDB responses
2. **Reduced API Calls**: Extracts basic information from initial results before making additional API calls
3. **Optimized Database Updates**: Only updates fields that have changed in the database
4. **Smart Batch Processing**: Uses smaller batch sizes with appropriate delays to manage resources effectively

#### Configuration

The Cinema page can be configured using the following settings in `settings.py`:

- `UPCOMING_FILMS_MONTHS`: Number of months to look ahead for upcoming films (default: 6)

This setting can also be configured using the `UPCOMING_FILMS_MONTHS` environment variable.

#### Manual Trigger

Administrators can also trigger the cache update manually from the Cinema page by clicking the "Update Cinema Cache" button at the bottom of the page.

#### Troubleshooting

If the Cinema page shows no films or outdated information:

1. Check if you're logged in as an administrator
2. Scroll to the bottom of the Cinema page
3. Click the "Update Cinema Cache" button
4. Check the output for any errors
5. If errors persist, check the Render logs for the cron job