# Films I Want To See

A web application that allows users to vote for their favorite films and generates charts based on the combined opinions of all users. The app tracks voting trends over time and allows for filtering charts by specific time periods.

## Features

- User authentication (local accounts, Google OAuth, and Letterboxd integration)
- Film search using the OMDB API (IMDb-based)
- Up to 10 individual votes per user that can be changed at any time
- Dynamic search with real-time results
- Time-stamped votes to track trends
- Chart generation with time period filtering
- Responsive design for all devices

## Setup Instructions

### Prerequisites

- Python 3.8+
- PostgreSQL (recommended) or SQLite
- OMDB API key (get one at [omdbapi.com](https://www.omdbapi.com/))

### Installation

1. Clone the repository:
```
git clone https://github.com/yourusername/FilmsIWantToSee.git
cd FilmsIWantToSee
```

2. Create a virtual environment and activate it:
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

3. Install dependencies:
```powershell
pip install -r requirements.txt
```

4. Create a `.env` file in the project root with the following variables:
```
SECRET_KEY=your_django_secret_key
DEBUG=True
OMDB_API_KEY=your_omdb_api_key
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
```

5. Run migrations:
```powershell
python manage.py migrate
```

6. Create a superuser:
```powershell
python manage.py createsuperuser
```

7. Run the development server:
```powershell
python manage.py runserver
```

8. Access the application at http://127.0.0.1:8000/

## Usage

1. Register for an account or log in with Google
2. Search for films using the search bar
3. Vote for up to 10 favorite films
4. View charts showing the most popular films
5. Filter charts by time period to see trends

## License

MIT 