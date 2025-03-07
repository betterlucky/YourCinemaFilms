# YourCinemaFilms

A web application for discovering, tracking, and voting for films you want to see.

## Features

- User authentication with Google OAuth
- Profile management with customizable profile pictures
- Film discovery and voting system
- Film details with genre tagging
- Charts and analytics for film preferences
- Responsive design with Bootstrap 5

## Technology Stack

- **Backend**: Django 5.1
- **Frontend**: Bootstrap 5, jQuery
- **Database**: SQLite (development)
- **Authentication**: django-allauth
- **API Integration**: OMDB API for film data

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
   OMDB_API_KEY=your_omdb_api_key
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
6. Add your client ID and secret to the Django admin site under "Social applications"

## Project Structure

- `films_project/`: Main project settings
- `films_app/`: Main application code
  - `models.py`: Database models
  - `views.py`: View functions
  - `urls.py`: URL routing
  - `templates/`: HTML templates
- `static/`: Static files (CSS, JS, images)
- `media/`: User-uploaded content

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [OMDB API](http://www.omdbapi.com/) for film data
- [Bootstrap](https://getbootstrap.com/) for the UI framework
- [Django](https://www.djangoproject.com/) for the web framework
- [django-allauth](https://django-allauth.readthedocs.io/) for authentication