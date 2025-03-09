import json
import os
import requests
import logging
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse, HttpResponse, FileResponse, HttpResponseNotAllowed
from django.conf import settings
from django.contrib import messages
from django.db.models import Count, Q, F, Sum, Avg, Case, When, IntegerField, Subquery, OuterRef
from django.db.models.functions import TruncMonth, TruncYear
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
from django.template.loader import render_to_string
from allauth.socialaccount.models import SocialAccount
from django.db import connection
from django.core.management import call_command
from io import StringIO
import sys
import re
import base64
import urllib.parse
from rest_framework.decorators import permission_classes
from rest_framework.permissions import AllowAny

# Try to import PIL, but don't fail if it's not available
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logging.warning("PIL not available. Image processing features will be disabled.")

from .models import Film, Vote, UserProfile, GenreTag, Activity, CinemaVote, PageTracker
from .utils import (
    contains_profanity, validate_and_format_genre_tag, require_http_method,
    count_film_votes, get_date_range_from_period, filter_votes_by_period,
    get_cached_search_results, cache_search_results, fetch_and_update_film_from_tmdb
)
from .tmdb_api import search_movies, sort_and_limit_films, get_movie_details, format_tmdb_data_for_film
# Import forms if they exist in your project
# from .forms import FilmSearchForm, UploadProfileImageForm


def landing(request):
    """Landing page view that introduces the app and offers route options."""
    return render(request, 'films_app/landing.html')


def cinema(request):
    """Cinema page view for current and upcoming releases."""
    from datetime import date
    from .models import Film, CinemaVote
    from django.conf import settings
    
    # Get the maximum number of films to display
    max_films = getattr(settings, 'MAX_CINEMA_FILMS', 20)
    
    # Get films that are in cinema or coming soon
    now_playing_films = Film.objects.filter(is_in_cinema=True).order_by('-popularity')[:max_films]
    
    # Get all upcoming films first
    all_upcoming_films = Film.objects.filter(
        is_in_cinema=False, 
        uk_release_date__isnull=False,
        uk_release_date__gt=date.today()
    ).order_by('-popularity')
    
    # Limit to the most popular ones
    upcoming_films = all_upcoming_films[:max_films]
    
    # Get user's cinema votes if authenticated
    user_cinema_votes = []
    cinema_votes_remaining = 3
    
    if request.user.is_authenticated:
        user_cinema_votes = CinemaVote.objects.filter(user=request.user).select_related('film')
        cinema_votes_remaining = 3 - user_cinema_votes.count()
    
    context = {
        'now_playing_films': now_playing_films,
        'upcoming_films': upcoming_films,
        'user_cinema_votes': user_cinema_votes,
        'cinema_votes_remaining': cinema_votes_remaining,
        'total_now_playing': Film.objects.filter(is_in_cinema=True).count(),
        'total_upcoming': all_upcoming_films.count(),
        'max_films': max_films,
        'upcoming_films_months': getattr(settings, 'UPCOMING_FILMS_MONTHS', 6),
    }
    
    return render(request, 'films_app/cinema.html', context)


def classics(request):
    """Classic films page view."""
    try:
        # Get top films based on votes
        top_films = get_top_films_data(limit=10)
        
        context = {
            'top_films': top_films,
        }
        
        # If user is authenticated, get their votes
        if request.user.is_authenticated:
            user_votes, votes_remaining = get_user_votes_and_remaining(request.user)
            context.update({
                'user_votes': user_votes,
                'votes_remaining': votes_remaining,
            })
        
        return render(request, 'films_app/classics.html', context)
    except Exception as e:
        logging.error(f"Error in classics view: {e}")
        messages.error(request, "An error occurred while loading the classics page. Please try again later.")
        return render(request, 'films_app/error.html', {'error_message': str(e)})


@login_required
def profile(request):
    """User profile view."""
    logger = logging.getLogger(__name__)
    
    # Get user's votes and remaining votes
    user_votes, votes_remaining = get_user_votes_and_remaining(request.user)
    
    # Get user achievements
    from films_app.models import Achievement
    achievements = Achievement.objects.filter(user=request.user)
    
    # Check for Google accounts using raw SQL query
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT COUNT(*) FROM socialaccount_socialaccount WHERE user_id = %s AND LOWER(provider) = 'google'",
            [request.user.id]
        )
        google_account_count = cursor.fetchone()[0]
    
    has_google_account = google_account_count > 0
    logger.info(f"User: {request.user.username}, Has Google account (SQL): {has_google_account}")
    
    # Get all social accounts using raw SQL
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT id, LOWER(provider) as provider FROM socialaccount_socialaccount WHERE user_id = %s",
            [request.user.id]
        )
        social_accounts_raw = cursor.fetchall()
    
    # Convert to a list of dictionaries for the template
    social_accounts = [{'id': row[0], 'provider': row[1]} for row in social_accounts_raw]
    logger.info(f"Social accounts (SQL): {social_accounts}")
    
    context = {
        'profile': request.user.profile,
        'user_votes': user_votes,
        'votes_remaining': votes_remaining,
        'social_accounts': social_accounts,
        'has_google_account': has_google_account,
        'achievements': achievements,
    }
    
    return render(request, 'films_app/profile.html', context)


@login_required
def edit_profile(request):
    """Edit user profile view."""
    if request.method == 'POST':
        # Update profile information
        profile = request.user.profile
        
        # Basic info
        profile.bio = request.POST.get('bio', '')
        profile.letterboxd_username = request.POST.get('letterboxd_username', '')
        
        # Email settings
        profile.contact_email = request.POST.get('contact_email', '')
        profile.use_google_email_for_contact = 'use_google_email_for_contact' in request.POST
        
        # Cinema preferences
        profile.favorite_cinema = request.POST.get('favorite_cinema', '')
        profile.cinema_frequency = request.POST.get('cinema_frequency', 'NS')
        profile.viewing_companions = request.POST.get('viewing_companions', 'NS')
        profile.viewing_time = request.POST.get('viewing_time', 'NS')
        profile.price_sensitivity = request.POST.get('price_sensitivity', 'NS')
        profile.format_preference = request.POST.get('format_preference', 'NS')
        
        # Handle travel_distance as integer
        travel_distance = request.POST.get('travel_distance', '')
        try:
            if travel_distance and travel_distance.strip():
                profile.travel_distance = int(travel_distance)
                # Ensure it's a positive value between 1 and 100
                if profile.travel_distance < 1 or profile.travel_distance > 100:
                    profile.travel_distance = None
            else:
                profile.travel_distance = None
        except (ValueError, TypeError):
            profile.travel_distance = None
        
        profile.cinema_amenities = request.POST.get('cinema_amenities', '')
        profile.film_genres = request.POST.get('film_genres', '')
        
        # Demographic info
        profile.location = request.POST.get('location', '')
        profile.gender = request.POST.get('gender', 'NS')
        profile.age_range = request.POST.get('age_range', 'NS')
        
        # Existing privacy settings
        profile.location_privacy = request.POST.get('location_privacy', 'private')
        profile.gender_privacy = request.POST.get('gender_privacy', 'private')
        profile.age_privacy = request.POST.get('age_privacy', 'private')
        profile.votes_privacy = request.POST.get('votes_privacy', 'public')
        
        # New privacy settings
        profile.favorite_cinema_privacy = request.POST.get('favorite_cinema_privacy', 'private')
        profile.cinema_frequency_privacy = request.POST.get('cinema_frequency_privacy', 'private')
        profile.viewing_companions_privacy = request.POST.get('viewing_companions_privacy', 'private')
        profile.viewing_time_privacy = request.POST.get('viewing_time_privacy', 'private')
        profile.price_sensitivity_privacy = request.POST.get('price_sensitivity_privacy', 'private')
        profile.format_preference_privacy = request.POST.get('format_preference_privacy', 'private')
        profile.travel_distance_privacy = request.POST.get('travel_distance_privacy', 'private')
        profile.cinema_amenities_privacy = request.POST.get('cinema_amenities_privacy', 'private')
        profile.film_genres_privacy = request.POST.get('film_genres_privacy', 'private')
        profile.dashboard_activity_privacy = request.POST.get('dashboard_activity_privacy', 'public')
        
        profile.save()
        
        # Check if profile is complete and award achievement if needed
        if profile.is_profile_complete():
            # Check if user already has this achievement
            from films_app.models import Achievement
            achievement, created = Achievement.objects.get_or_create(
                user=request.user,
                achievement_type='profile_complete'
            )
            
            if created:
                messages.success(
                    request, 
                    mark_safe('Profile updated successfully! <span class="ms-2 badge bg-success">Achievement Unlocked: Profile Completed</span>')
                )
            else:
                messages.success(request, 'Profile updated successfully!')
        else:
            messages.success(request, 'Profile updated successfully!')
            
        return redirect('films_app:profile')
    
    return render(request, 'films_app/edit_profile.html', {'profile': request.user.profile})


def search_films(request):
    """Search films using TMDB API."""
    query = request.GET.get('query', '')
    
    # Debug information
    print(f"Search query: {query}")
    print(f"Is HTMX request: {hasattr(request, 'htmx')}")
    if hasattr(request, 'htmx'):
        print(f"HTMX target: {request.htmx.target}")
    
    if not query or len(query) < 3:
        if hasattr(request, 'htmx'):
            # Check which target is being used
            target_id = request.htmx.target
            print(f"Empty results for target: {target_id}")
            
            if target_id == 'search-results':
                return render(request, 'films_app/partials/modal_search_results.html', {'results': []})
            else:
                # Use the same template for all other search targets
                return render(request, 'films_app/partials/search_results.html', {'results': []})
        return JsonResponse({'results': []})
    
    # Try to get cached results first
    cached_results = get_cached_search_results(query)
    if cached_results:
        results = cached_results
        print(f"Using cached results: {len(results)} items")
    else:
        # Fetch from TMDB API
        try:
            print(f"Fetching results from TMDB API for: {query}")
            tmdb_data = search_movies(query)
            
            if tmdb_data.get('results'):
                print(f"TMDB returned {len(tmdb_data['results'])} results")
                # Format results to match the expected structure in templates
                results = []
                for movie in tmdb_data['results']:
                    # Get the IMDb ID for the movie
                    imdb_id = None
                    try:
                        # Try to get the movie details which include external IDs
                        movie_details = get_movie_details(movie.get('id'))
                        if movie_details and 'external_ids' in movie_details:
                            imdb_id = movie_details['external_ids'].get('imdb_id')
                    except Exception as e:
                        logging.warning(f"Error getting IMDb ID for movie {movie.get('id')}: {str(e)}")
                    
                    # If we couldn't get an IMDb ID, use the TMDB ID as a fallback
                    if not imdb_id:
                        imdb_id = f"tmdb-{movie.get('id')}"
                    
                    # Format each movie to match the structure expected by the template
                    formatted_movie = {
                        'imdbID': imdb_id,  # Use the actual IMDb ID or TMDB ID with prefix
                        'Title': movie.get('title', ''),
                        'Year': movie.get('release_date', '')[:4] if movie.get('release_date') else '',
                        'Poster': f"https://image.tmdb.org/t/p/w500{movie.get('poster_path')}" if movie.get('poster_path') else '',
                        'tmdb_id': movie.get('id'),  # Store TMDB ID for later use
                    }
                    results.append(formatted_movie)
                
                # Cache the results
                cache_search_results(query, results)
            else:
                print("TMDB returned no results")
                results = []
        except Exception as e:
            logging.error(f"Error searching TMDB: {str(e)}")
            print(f"Error searching TMDB: {str(e)}")
            results = []
    
    if hasattr(request, 'htmx'):
        # Check which target is being used
        target_id = request.htmx.target
        print(f"Returning results for HTMX target: {target_id}")
        
        if target_id == 'search-results':
            return render(request, 'films_app/partials/modal_search_results.html', {'results': results})
        else:
            # Use the same template for all other search targets
            print(f"Using search_results.html template for target: {target_id}")
            return render(request, 'films_app/partials/search_results.html', {'results': results})
    
    return JsonResponse({'results': results})


@permission_classes([AllowAny])
def film_detail(request, imdb_id):
    """Get detailed information about a film."""
    try:
        # Initialize skip_fetch variable
        skip_fetch = False
        
        # Check if this is a numeric ID (likely a TMDB ID without the prefix)
        if imdb_id.isdigit():
            # Convert to tmdb-prefixed format
            imdb_id = f"tmdb-{imdb_id}"
        
        # Check if this is a TMDB ID (prefixed with 'tmdb-')
        if imdb_id.startswith('tmdb-'):
            # Extract the TMDB ID
            tmdb_id = imdb_id.replace('tmdb-', '')
            
            # Get movie details from TMDB
            try:
                movie_details = get_movie_details(tmdb_id)
                if movie_details and 'external_ids' in movie_details and movie_details['external_ids'].get('imdb_id'):
                    # Use the IMDb ID from the movie details
                    imdb_id = movie_details['external_ids'].get('imdb_id')
                else:
                    # If we can't get an IMDb ID, create a film with the TMDB ID
                    formatted_data = format_tmdb_data_for_film(movie_details)
                    film, created = Film.objects.get_or_create(
                        imdb_id=imdb_id,  # Use the original tmdb-prefixed ID
                        defaults=formatted_data
                    )
                    # Skip the fetch_and_update_film_from_tmdb call
                    skip_fetch = True
            except Exception as e:
                logging.error(f"Error getting movie details for TMDB ID {tmdb_id}: {str(e)}")
                return render(request, 'films_app/error.html', {'error': 'Film not found'})
        else:
            # This is a regular IMDb ID
            skip_fetch = False
        
        # Fetch or update film from TMDB if not skipped
        if not skip_fetch:
            film, created = fetch_and_update_film_from_tmdb(imdb_id)
        
        # Check if user has voted for this film and can vote
        has_voted = False
        user_vote = None
        can_vote = False
        user_tags = []
        
        if request.user.is_authenticated:
            can_vote, _ = user_can_vote(request.user, film)
            user_vote = Vote.objects.filter(user=request.user, film=film).first()
            has_voted = user_vote is not None
            # Get user tags for this film
            user_tags = GenreTag.objects.filter(film=film, user=request.user)
        
        # Get vote count
        vote_count = count_film_votes(film)
        
        # Get all approved tags for this film
        approved_tags = GenreTag.objects.filter(film=film, is_approved=True)
        
        # If user is authenticated, exclude their tags from approved tags
        if request.user.is_authenticated:
            approved_tags = approved_tags.exclude(user=request.user)
        
        context = {
            'film': film,
            'has_voted': has_voted,
            'can_vote': can_vote,
            'vote_count': vote_count,
            'user_tags': user_tags,
            'approved_tags': approved_tags,
            'genres': film.genre_list,
            'all_genres': film.all_genres,
            'is_authenticated': request.user.is_authenticated,
        }
        
        return render(request, 'films_app/film_detail.html', context)
    except ValueError as e:
        messages.error(request, str(e))
        return redirect('films_app:classics')


@login_required
def vote_for_film(request, imdb_id):
    """Vote for a film."""
    # Check if method is POST
    method_error = require_http_method(request)
    if method_error:
        return method_error
    
    # Get or create film
    film = get_object_or_404(Film, imdb_id=imdb_id)
    
    # Check if user can vote
    can_vote, reason = user_can_vote(request.user, film)
    
    if not can_vote:
        if reason == "already_voted":
            # Return the "already voted" button
            return render(request, 'films_app/partials/voted_button.html', {'film': film})
        elif reason == "max_votes_reached":
            # Return the "max votes reached" button
            return render(request, 'films_app/partials/max_votes_button.html')
    
    # Create vote
    vote = Vote(user=request.user, film=film)
    vote.save()
    
    # Get updated vote count for the film
    vote_count = count_film_votes(film)
    
    # Return the success button with updated vote count
    response_html = f"""
    {render_to_string('films_app/partials/voted_button.html', {'film': film}, request=request)}
    <div hx-swap-oob="true" id="film-vote-count">
        {render_to_string('films_app/partials/vote_count_badge.html', {'vote_count': vote_count}, request=request)}
    </div>
    """
    
    return HttpResponse(response_html)


@login_required
def remove_vote(request, vote_id):
    """Remove a vote."""
    # Check if method is POST or DELETE (for HTMX)
    if request.method not in ['POST', 'DELETE']:
        return HttpResponseNotAllowed(['POST', 'DELETE'])
    
    vote = get_object_or_404(Vote, id=vote_id, user=request.user)
    film = vote.film
    vote.delete()
    
    # Get updated data for the response
    user_votes, votes_remaining = get_user_votes_and_remaining(request.user)
    top_films = get_top_films_data()
    
    # Check if this is an HTMX request
    if request.headers.get('HX-Request'):
        # If the request is from the profile page
        if 'profile' in request.headers.get('HX-Current-URL', ''):
            # Set the HX-Trigger header to trigger client-side events
            response = HttpResponse("")
            response.headers['HX-Trigger'] = json.dumps({
                'voteRemoved': {
                    'voteCount': len(user_votes),
                    'votesRemaining': votes_remaining
                }
            })
            return response
        else:
            # Return the updated card with empty content to remove it (for film detail page)
            response_html = f"""
            <div hx-swap-oob="true" id="user-vote-status">
                {render_to_string('films_app/partials/user_vote_status.html', {'user_votes': user_votes, 'votes_remaining': votes_remaining}, request=request)}
            </div>
            <div hx-swap-oob="true" id="top-films-container">
                {render_to_string('films_app/partials/top_films.html', {'top_films': top_films}, request=request)}
            </div>
            """
            return HttpResponse(response_html)
    
    # For non-HTMX requests, redirect back to the referring page
    return redirect(request.META.get('HTTP_REFERER', 'films_app:classics'))


@login_required
def add_genre_tag(request, imdb_id):
    """Add a genre tag to a film."""
    # Check if method is POST
    method_error = require_http_method(request)
    if method_error:
        return method_error
    
    # Get film
    film = get_object_or_404(Film, imdb_id=imdb_id)
    
    # Get tag from request
    tag = request.POST.get('tag', '').strip()
    
    # Validate and format tag
    is_valid, result = validate_and_format_genre_tag(tag, request.user, film)
    if not is_valid:
        # Return the form with an error message
        return render(request, 'films_app/partials/genre_tag_form.html', {
            'film': film,
            'error_message': result
        })
    
    # Create tag (not approved by default)
    genre_tag = GenreTag(film=film, user=request.user, tag=result)
    genre_tag.save()
    
    # Get all user tags for this film to render the updated list
    user_tags = GenreTag.objects.filter(film=film, user=request.user)
    
    # Return the form with a success message
    return render(request, 'films_app/partials/genre_tag_form.html', {
        'film': film,
        'user_tags': user_tags,
        'success_message': 'Genre tag added successfully. It will be visible after approval.'
    })


@login_required
def remove_genre_tag(request, tag_id):
    """Remove a genre tag."""
    # Check if method is POST
    method_error = require_http_method(request)
    if method_error:
        return method_error
    
    # Get tag and check ownership
    tag = get_object_or_404(GenreTag, id=tag_id, user=request.user)
    film = tag.film
    
    # Delete tag
    tag.delete()
    
    # Return empty response to remove the tag from the UI
    return HttpResponse('')


@login_required
def manage_genre_tags(request):
    """View for managing user's genre tags."""
    # Get user's tags
    user_tags = GenreTag.objects.filter(user=request.user).select_related('film')
    
    context = {
        'user_tags': user_tags,
    }
    
    return render(request, 'films_app/manage_tags.html', context)


def dashboard(request):
    """View for displaying the dashboard with site statistics and activity."""
    # Get time period from request
    period = request.GET.get('period', 'week')
    
    # Calculate date range based on period
    end_date = timezone.now()
    start_date = None
    
    if period == 'week':
        start_date = end_date - timedelta(days=7)
    elif period == 'month':
        start_date = end_date - timedelta(days=30)
    elif period == 'year':
        start_date = end_date - timedelta(days=365)
    
    # Query votes based on date range
    votes_query = Vote.objects.all()
    period_votes_query = votes_query
    if start_date:
        period_votes_query = votes_query.filter(created_at__gte=start_date)
    
    # Get top films
    top_films = Film.objects.filter(votes__in=period_votes_query).annotate(
        vote_count=Count('votes')
    ).order_by('-vote_count')[:10]
    
    # Get genre distribution
    genre_data = get_genre_distribution(period_votes_query)
    
    # Get activity timeline data
    activity_dates = []
    activity_counts = []
    
    if period == 'week':
        # Daily activity for the past week
        for i in range(7, -1, -1):
            date = end_date - timedelta(days=i)
            activity_dates.append(date.strftime('%a'))
            day_start = timezone.make_aware(datetime.combine(date, datetime.min.time()))
            day_end = timezone.make_aware(datetime.combine(date, datetime.max.time()))
            activity_counts.append(Vote.objects.filter(created_at__range=(day_start, day_end)).count())
    elif period == 'month':
        # Weekly activity for the past month
        for i in range(4, -1, -1):
            week_end = end_date - timedelta(days=i*7)
            week_start = week_end - timedelta(days=6)
            activity_dates.append(f"{week_start.strftime('%d %b')}-{week_end.strftime('%d %b')}")
            activity_counts.append(Vote.objects.filter(created_at__range=(week_start, week_end)).count())
    elif period == 'year':
        # Monthly activity for the past year
        for i in range(12, -1, -1):
            month_date = end_date - relativedelta(months=i)
            activity_dates.append(month_date.strftime('%b'))
            month_start = timezone.make_aware(datetime(month_date.year, month_date.month, 1))
            if month_date.month == 12:
                month_end = timezone.make_aware(datetime(month_date.year + 1, 1, 1)) - timedelta(seconds=1)
            else:
                month_end = timezone.make_aware(datetime(month_date.year, month_date.month + 1, 1)) - timedelta(seconds=1)
            activity_counts.append(Vote.objects.filter(created_at__range=(month_start, month_end)).count())
    else:
        # Activity for all time - improved visualization
        earliest_vote = Vote.objects.order_by('created_at').first()
        if earliest_vote:
            earliest_year = earliest_vote.created_at.year
            current_year = timezone.now().year
            years_span = current_year - earliest_year + 1
            
            # If we have a short history (less than 3 years), show quarterly data
            if years_span <= 3:
                # Quarterly activity
                for year in range(earliest_year, current_year + 1):
                    for quarter in range(1, 5):
                        if year == current_year and quarter > ((end_date.month - 1) // 3) + 1:
                            # Skip future quarters in current year
                            continue
                            
                        quarter_start_month = (quarter - 1) * 3 + 1
                        quarter_end_month = quarter * 3
                        
                        quarter_start = timezone.make_aware(datetime(year, quarter_start_month, 1))
                        if quarter_end_month == 12:
                            quarter_end = timezone.make_aware(datetime(year + 1, 1, 1)) - timedelta(seconds=1)
                        else:
                            quarter_end = timezone.make_aware(datetime(year, quarter_end_month + 1, 1)) - timedelta(seconds=1)
                        
                        # Skip quarters before the earliest vote
                        if quarter_end < earliest_vote.created_at:
                            continue
                            
                        quarter_label = f"Q{quarter} {year}"
                        activity_dates.append(quarter_label)
                        activity_counts.append(Vote.objects.filter(created_at__range=(quarter_start, quarter_end)).count())
            # If we have 4-10 years of data, show semi-annual data
            elif years_span <= 10:
                # Semi-annual activity
                for year in range(earliest_year, current_year + 1):
                    for half in range(1, 3):
                        if year == current_year and half > ((end_date.month - 1) // 6) + 1:
                            # Skip future half-years in current year
                            continue
                            
                        half_start_month = (half - 1) * 6 + 1
                        half_end_month = half * 6
                        
                        half_start = timezone.make_aware(datetime(year, half_start_month, 1))
                        if half_end_month == 12:
                            half_end = timezone.make_aware(datetime(year + 1, 1, 1)) - timedelta(seconds=1)
                        else:
                            half_end = timezone.make_aware(datetime(year, half_end_month + 1, 1)) - timedelta(seconds=1)
                        
                        # Skip half-years before the earliest vote
                        if half_end < earliest_vote.created_at:
                            continue
                            
                        half_label = f"H{half} {year}"
                        activity_dates.append(half_label)
                        activity_counts.append(Vote.objects.filter(created_at__range=(half_start, half_end)).count())
            else:
                # For longer periods, show yearly data
                for year in range(earliest_year, current_year + 1):
                    activity_dates.append(str(year))
                    year_start = timezone.make_aware(datetime(year, 1, 1))
                    year_end = timezone.make_aware(datetime(year, 12, 31, 23, 59, 59))
                    activity_counts.append(Vote.objects.filter(created_at__range=(year_start, year_end)).count())
    
    # Get active users
    active_users = User.objects.filter(votes__in=period_votes_query).annotate(
        vote_count=Count('votes')
    ).filter(
        vote_count__gt=0,
        profile__dashboard_activity_privacy='public'  # Only include users who have set their dashboard activity to public
    ).order_by('-vote_count')[:5]
    
    active_users_data = []
    for i, user in enumerate(active_users):
        active_users_data.append({
            'user': user,
            'vote_count': user.vote_count,
            'rank': i + 1
        })
    
    # Get recent activity
    recent_activity = []
    recent_votes = Vote.objects.select_related('user', 'film').filter(
        user__profile__dashboard_activity_privacy='public'  # Only include users who have set their dashboard activity to public
    ).order_by('-created_at')[:10]
    
    for vote in recent_votes:
        recent_activity.append({
            'user': vote.user,
            'action': 'voted for',
            'description': f"{vote.film.title} ({vote.film.year})",
            'timestamp': vote.created_at,
            'film': vote.film
        })
    
    # Get stats
    total_films = Film.objects.count()
    total_votes = Vote.objects.count()
    period_votes = period_votes_query.count()
    total_users = User.objects.count()
    new_users = User.objects.filter(date_joined__gte=start_date).count() if start_date else total_users
    
    # Get genre stats
    all_genres = set()
    for film in Film.objects.all():
        all_genres.update(film.genres.split(', ') if film.genres else [])
    
    user_tags = GenreTag.objects.filter(is_approved=True).count()
    total_genres = len(all_genres)
    
    context = {
        'period': period,
        'genre_labels': json.dumps(list(genre_data.keys())),
        'genre_data': json.dumps(list(genre_data.values())),
        'activity_dates': json.dumps(activity_dates),
        'activity_counts': json.dumps(activity_counts),
        'top_films': top_films,
        'active_users': active_users_data,
        'recent_activity': recent_activity,
        'total_films': total_films,
        'total_votes': total_votes,
        'period_votes': period_votes,
        'total_users': total_users,
        'new_users': new_users,
        'total_genres': total_genres,
        'user_genres': user_tags
    }
    
    return render(request, 'films_app/dashboard.html', context)


def all_activity(request):
    """View for displaying all site activity."""
    # Get time period from request
    period = request.GET.get('period', 'all')
    
    # Calculate date range based on period
    end_date = timezone.now()
    start_date = None
    
    if period == 'week':
        start_date = end_date - timedelta(days=7)
    elif period == 'month':
        start_date = end_date - timedelta(days=30)
    elif period == 'year':
        start_date = end_date - timedelta(days=365)
    
    # Get paginated activity
    page = request.GET.get('page', 1)
    
    # Get all votes with public profiles
    votes_query = Vote.objects.select_related('user', 'film').filter(
        user__profile__dashboard_activity_privacy='public'
    ).order_by('-created_at')
    
    # Apply time period filter if needed
    if start_date:
        votes_query = votes_query.filter(created_at__gte=start_date)
    
    # Format activity data
    all_activity = []
    for vote in votes_query:
        all_activity.append({
            'user': vote.user,
            'action': 'voted for',
            'description': f"{vote.film.title} ({vote.film.year})",
            'timestamp': vote.created_at,
            'film': vote.film
        })
    
    # Paginate results
    paginator = Paginator(all_activity, 25)  # Show 25 activities per page
    
    try:
        activities = paginator.page(page)
    except PageNotAnInteger:
        activities = paginator.page(1)
    except EmptyPage:
        activities = paginator.page(paginator.num_pages)
    
    context = {
        'period': period,
        'activities': activities,
        'periods': [
            {'value': 'all', 'label': 'All Time'},
            {'value': 'year', 'label': 'Past Year'},
            {'value': 'month', 'label': 'Past Month'},
            {'value': 'week', 'label': 'Past Week'}
        ]
    }
    
    return render(request, 'films_app/all_activity.html', context)


def all_top_films(request):
    """View for displaying all top films."""
    # Get time period from request
    period = request.GET.get('period', 'all')
    
    # Calculate date range based on period
    end_date = timezone.now()
    start_date = None
    
    if period == 'week':
        start_date = end_date - timedelta(days=7)
    elif period == 'month':
        start_date = end_date - timedelta(days=30)
    elif period == 'year':
        start_date = end_date - timedelta(days=365)
    
    # Get paginated films
    page = request.GET.get('page', 1)
    
    # Get all films with votes
    films_query = Film.objects.annotate(vote_count=Count('votes')).filter(vote_count__gt=0)
    
    # Apply time period filter if needed
    if start_date:
        films_query = films_query.filter(votes__created_at__gte=start_date).annotate(
            period_vote_count=Count('votes', filter=Q(votes__created_at__gte=start_date))
        ).filter(period_vote_count__gt=0).order_by('-period_vote_count')
    else:
        films_query = films_query.order_by('-vote_count')
    
    # Paginate results
    paginator = Paginator(films_query, 20)  # Show 20 films per page
    
    try:
        films = paginator.page(page)
    except PageNotAnInteger:
        films = paginator.page(1)
    except EmptyPage:
        films = paginator.page(paginator.num_pages)
    
    context = {
        'period': period,
        'films': films,
        'periods': [
            {'value': 'all', 'label': 'All Time'},
            {'value': 'year', 'label': 'Past Year'},
            {'value': 'month', 'label': 'Past Month'},
            {'value': 'week', 'label': 'Past Week'}
        ]
    }
    
    return render(request, 'films_app/all_top_films.html', context)


def all_users(request):
    """View for displaying all active users."""
    # Get time period from request
    period = request.GET.get('period', 'all')
    
    # Calculate date range based on period
    end_date = timezone.now()
    start_date = None
    
    if period == 'week':
        start_date = end_date - timedelta(days=7)
    elif period == 'month':
        start_date = end_date - timedelta(days=30)
    elif period == 'year':
        start_date = end_date - timedelta(days=365)
    
    # Get paginated users
    page = request.GET.get('page', 1)
    
    # Get all users with votes and respect privacy settings
    users_query = User.objects.filter(
        profile__dashboard_activity_privacy='public'  # Only include users who have set their dashboard activity to public
    )
    
    # Apply time period filter if needed
    if start_date:
        # Get users who have voted in the period
        users_with_votes = Vote.objects.filter(created_at__gte=start_date).values_list('user_id', flat=True).distinct()
        users_query = users_query.filter(id__in=users_with_votes)
    
    # Annotate with vote count
    users_query = users_query.annotate(vote_count=Count('votes'))
    
    # Filter to only include users with votes
    users_query = users_query.filter(vote_count__gt=0)
    
    # Order by vote count
    users_query = users_query.order_by('-vote_count')
    
    # Paginate results
    paginator = Paginator(users_query, 20)  # Show 20 users per page
    
    try:
        users = paginator.page(page)
    except PageNotAnInteger:
        users = paginator.page(1)
    except EmptyPage:
        users = paginator.page(paginator.num_pages)
    
    # Format user data with ranks
    users_data = []
    start_rank = (users.number - 1) * paginator.per_page + 1
    
    for i, user in enumerate(users):
        users_data.append({
            'user': user,
            'vote_count': user.vote_count,
            'rank': start_rank + i
        })
    
    context = {
        'period': period,
        'users': users,
        'users_data': users_data,
        'periods': [
            {'value': 'all', 'label': 'All Time'},
            {'value': 'year', 'label': 'Past Year'},
            {'value': 'month', 'label': 'Past Month'},
            {'value': 'week', 'label': 'Past Week'}
        ]
    }
    
    return render(request, 'films_app/all_users.html', context)


def get_genre_distribution(votes_queryset):
    """Get genre distribution from votes."""
    genre_counts = {}
    
    # Get all films from votes
    films = Film.objects.filter(votes__in=votes_queryset).distinct()
    
    # Count genres (including approved user tags)
    for film in films:
        for genre in film.all_genres:
            if genre in genre_counts:
                genre_counts[genre] += 1
            else:
                genre_counts[genre] = 1
    
    # Sort by count (descending)
    sorted_genres = dict(sorted(genre_counts.items(), key=lambda item: item[1], reverse=True))
    
    # Return top 10 genres
    return dict(list(sorted_genres.items())[:10])


def user_profile_view(request, username):
    """Public user profile view."""
    user = get_object_or_404(User, username=username)
    
    # If viewing your own profile, redirect to the profile page
    if request.user.is_authenticated and request.user.username == username:
        return redirect('films_app:profile')
    
    profile = user.profile
    
    # Check if the viewer is the profile owner or staff
    is_owner = request.user.is_authenticated and request.user == user
    
    # Get user's votes if they're visible to the viewer
    user_votes = None
    if is_owner or profile.votes_privacy == 'public' or (profile.votes_privacy == 'users' and request.user.is_authenticated):
        user_votes = Vote.objects.filter(user=user).select_related('film')
    
    context = {
        'profile_user': user,
        'profile': profile,
        'user_votes': user_votes,
        'is_owner': is_owner,
    }
    
    return render(request, 'films_app/user_profile.html', context)


def get_all_genres():
    """Get all genres from films and approved tags, sorted alphabetically."""
    # Try to get genres from cache
    cached_genres = cache.get('all_genres')
    if cached_genres:
        return cached_genres
    
    # If not in cache, query the database
    all_genres = set()
    
    # Get official genres more efficiently
    film_genres = Film.objects.exclude(genres__isnull=True).exclude(genres='')
    
    # Use values_list to get only the genres field and avoid loading entire objects
    for genres_str in film_genres.values_list('genres', flat=True):
        if genres_str:
            all_genres.update([genre.strip() for genre in genres_str.split(',')])
    
    # Get approved user tags more efficiently
    approved_tags = GenreTag.objects.filter(is_approved=True).values_list('tag', flat=True).distinct()
    all_genres.update(approved_tags)
    
    # Sort genres alphabetically
    sorted_genres = sorted(list(all_genres))
    
    # Cache the result for 1 hour (3600 seconds)
    cache.set('all_genres', sorted_genres, 3600)
    
    return sorted_genres

def get_films_by_genre(genre, period=None):
    """Get films in a specific genre, optionally filtered by period."""
    # Get films with official genre
    official_genre_films = Film.objects.filter(genres__icontains=genre)
    
    # Get films with user tag
    user_tag_films = Film.objects.filter(tags__tag=genre, tags__is_approved=True)
    
    # Combine and remove duplicates
    films = (official_genre_films | user_tag_films).distinct()
    
    # Filter by period if specified
    if period and period != 'all':
        votes = filter_votes_by_period(period)
        films = films.filter(votes__in=votes).distinct()
    
    # Annotate with vote count and order by votes
    return films.annotate(vote_count=Count('votes')).order_by('-vote_count')

def genre_analysis(request):
    """View for genre analysis."""
    # Get all genres
    genres = get_all_genres()
    
    # Get selected genre and period
    selected_genre = request.GET.get('genre', '')
    period = request.GET.get('period', 'all')
    
    # If no genre is selected, default to the first genre with films
    if not selected_genre and genres:
        # Try to find a genre with films
        for genre in genres:
            test_films = get_films_by_genre(genre, period)
            if test_films.exists():
                selected_genre = genre
                break
        
        # If still no genre found with films, just use the first genre
        if not selected_genre and genres:
            selected_genre = genres[0]
    
    # Get films in the selected genre
    films = []
    if selected_genre:
        films = get_films_by_genre(selected_genre, period)
    
    context = {
        'genres': genres,
        'selected_genre': selected_genre,
        'period': period,
        'films': films,
        'periods': [
            {'value': 'all', 'label': 'All Time'},
            {'value': 'year', 'label': 'Past Year'},
            {'value': 'month', 'label': 'Past Month'},
            {'value': 'week', 'label': 'Past Week'}
        ]
    }
    
    # Check if this is an HTMX request
    if request.headers.get('HX-Request'):
        return render(request, 'films_app/partials/genre_content.html', context)
    
    return render(request, 'films_app/genre_analysis.html', context)


def genre_comparison(request):
    """View for genre comparison."""
    # Get all genres
    genres = get_all_genres()
    
    # Get selected period
    period = request.GET.get('period', 'all')
    
    context = {
        'genres': genres,
        'period': period,
        'periods': [
            {'value': 'all', 'label': 'All Time'},
            {'value': 'year', 'label': 'Past Year'},
            {'value': 'month', 'label': 'Past Month'},
            {'value': 'week', 'label': 'Past Week'}
        ]
    }
    
    return render(request, 'films_app/genre_comparison.html', context)


def demographic_analysis(request):
    """View for demographic analysis."""
    # Only staff can access this view
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('films_app:classics')
    
    # Get demographic data
    gender_data = UserProfile.objects.exclude(gender='NS').values('gender').annotate(
        count=Count('gender')
    ).order_by('gender')
    
    age_data = UserProfile.objects.exclude(age_range='NS').values('age_range').annotate(
        count=Count('age_range')
    ).order_by('age_range')
    
    # Prepare data for charts
    gender_labels = [dict(UserProfile.GENDER_CHOICES)[g['gender']] for g in gender_data]
    gender_counts = [g['count'] for g in gender_data]
    
    age_labels = [dict(UserProfile.AGE_RANGE_CHOICES)[a['age_range']] for a in age_data]
    age_counts = [a['count'] for a in age_data]
    
    context = {
        'gender_labels': json.dumps(gender_labels),
        'gender_data': json.dumps(gender_counts),
        'age_labels': json.dumps(age_labels),
        'age_data': json.dumps(age_counts),
    }
    
    return render(request, 'films_app/demographic_analysis.html', context)


def debug_profile(request, username):
    """Debug view for profile information."""
    if not request.user.is_authenticated or not request.user.is_superuser:
        return redirect('films_app:classics')
    
    # Get the user by username
    target_user = get_object_or_404(User, username=username)
    profile = target_user.profile
    
    # Get all privacy settings
    privacy_settings = {
        'location_privacy': profile.location_privacy,
        'gender_privacy': profile.gender_privacy,
        'age_privacy': profile.age_privacy,
        'votes_privacy': profile.votes_privacy,
        'favorite_cinema_privacy': profile.favorite_cinema_privacy,
        'cinema_frequency_privacy': profile.cinema_frequency_privacy,
        'viewing_companions_privacy': profile.viewing_companions_privacy,
        'viewing_time_privacy': profile.viewing_time_privacy,
        'price_sensitivity_privacy': profile.price_sensitivity_privacy,
        'format_preference_privacy': profile.format_preference_privacy,
        'travel_distance_privacy': profile.travel_distance_privacy,
        'cinema_amenities_privacy': profile.cinema_amenities_privacy,
        'film_genres_privacy': profile.film_genres_privacy,
        'dashboard_activity_privacy': profile.dashboard_activity_privacy,
    }
    
    # Get all profile fields
    profile_fields = {
        'location': profile.location,
        'gender': profile.gender,
        'age_range': profile.age_range,
        'favorite_cinema': profile.favorite_cinema,
        'cinema_frequency': profile.cinema_frequency,
        'viewing_companions': profile.viewing_companions,
        'viewing_time': profile.viewing_time,
        'price_sensitivity': profile.price_sensitivity,
        'format_preference': profile.format_preference,
        'travel_distance': profile.travel_distance,
        'cinema_amenities': profile.cinema_amenities,
        'film_genres': profile.film_genres,
    }
    
    context = {
        'privacy_settings': privacy_settings,
        'profile_fields': profile_fields,
        'target_user': target_user,
    }
    
    return render(request, 'films_app/debug_profile.html', context)


def proxy_profile_image(request):
    """
    Proxy for profile images to avoid CORS issues and handle local files.
    """
    if not request.user.is_authenticated:
        return redirect('account_login')
    
    import requests
    from django.http import HttpResponse, FileResponse
    from allauth.socialaccount.models import SocialAccount
    import json
    import os
    
    logger = logging.getLogger(__name__)
    
    # Get the user's profile
    profile = request.user.profile
    
    # DIRECT APPROACH: If we have a profile picture URL, use it immediately
    if profile.profile_picture_url:
        logger.info(f"Using existing profile picture URL: {profile.profile_picture_url}")
        
        # Check if it's a local file path (doesn't start with http:// or https://)
        if not profile.profile_picture_url.startswith(('http://', 'https://')):
            # It's a local file path, serve it directly
            try:
                # For media files
                if 'profile_images' in profile.profile_picture_url:
                    # Extract the filename from the URL
                    filename = os.path.basename(profile.profile_picture_url)
                    file_path = os.path.join(settings.MEDIA_ROOT, 'profile_images', filename)
                    
                    if os.path.exists(file_path):
                        return FileResponse(open(file_path, 'rb'), content_type='image/jpeg')
                    else:
                        logger.warning(f"Local file not found: {file_path}")
                        # Continue to try other methods
                else:
                    logger.warning(f"Unrecognized local file path format: {profile.profile_picture_url}")
            except Exception as e:
                logger.warning(f"Error serving local file: {e}")
                # Continue to try other methods
        else:
            # It's a remote URL, fetch it
            try:
                response = requests.get(profile.profile_picture_url, stream=True)
                if response.status_code == 200:
                    return HttpResponse(
                        response.content,
                        content_type=response.headers.get('Content-Type', 'image/jpeg')
                    )
                else:
                    logger.warning(f"Failed to fetch existing profile image, status code: {response.status_code}")
                    # Continue to try other methods
            except Exception as e:
                logger.warning(f"Error fetching existing profile image: {e}")
                # Continue to try other methods
    
    # APPROACH 1: Try to find by Google account ID
    if profile.google_account_id:
        try:
            # Direct database query for the social account
            google_account = SocialAccount.objects.get(provider='google', uid=profile.google_account_id)
            
            if 'picture' in google_account.extra_data:
                picture_url = google_account.extra_data['picture']
                logger.info(f"Found picture URL via Google ID: {picture_url}")
                
                # Update the profile
                profile.profile_picture_url = picture_url
                profile.save()
                
                # Fetch and return the image
                try:
                    response = requests.get(picture_url, stream=True)
                    if response.status_code == 200:
                        return HttpResponse(
                            response.content,
                            content_type=response.headers.get('Content-Type', 'image/jpeg')
                        )
                except Exception as e:
                    logger.warning(f"Error fetching image by Google ID: {e}")
        except SocialAccount.DoesNotExist:
            logger.info(f"No social account found with Google ID: {profile.google_account_id}")
    
    # APPROACH 2: Try to find by user's social accounts
    social_accounts = SocialAccount.objects.filter(user=request.user, provider='google')
    if social_accounts.exists():
        google_account = social_accounts.first()
        
        # Debug the extra_data
        logger.info(f"Social account extra_data: {json.dumps(google_account.extra_data)}")
        
        if 'picture' in google_account.extra_data:
            picture_url = google_account.extra_data['picture']
            logger.info(f"Found picture URL via user's social account: {picture_url}")
            
            # Update the profile
            profile.profile_picture_url = picture_url
            profile.google_account_id = google_account.uid
            profile.save()
            
            # Fetch and return the image
            try:
                response = requests.get(picture_url, stream=True)
                if response.status_code == 200:
                    return HttpResponse(
                        response.content,
                        content_type=response.headers.get('Content-Type', 'image/jpeg')
                    )
            except Exception as e:
                logger.warning(f"Error fetching image by social account: {e}")
    
    # APPROACH 3: Try to find by email
    if profile.google_email or request.user.email:
        email_to_try = profile.google_email or request.user.email
        try:
            google_accounts = SocialAccount.objects.filter(
                provider='google',
                extra_data__email=email_to_try
            )
            
            if google_accounts.exists():
                google_account = google_accounts.first()
                
                if 'picture' in google_account.extra_data:
                    picture_url = google_account.extra_data['picture']
                    logger.info(f"Found picture URL via email match: {picture_url}")
                    
                    # Update the profile
                    profile.profile_picture_url = picture_url
                    profile.google_account_id = google_account.uid
                    profile.save()
                    
                    # Fetch and return the image
                    try:
                        response = requests.get(picture_url, stream=True)
                        if response.status_code == 200:
                            return HttpResponse(
                                response.content,
                                content_type=response.headers.get('Content-Type', 'image/jpeg')
                            )
                    except Exception as e:
                        logger.warning(f"Error fetching image by email: {e}")
        except Exception as e:
            logger.warning(f"Error finding account by email: {e}")
    
    # If all else fails, return a default image
    logger.warning(f"All approaches failed to find a profile picture for user {request.user.username}")
    return redirect('https://via.placeholder.com/150')


def proxy_user_profile_image(request, username):
    """
    Proxy for other users' Google profile images to avoid CORS issues.
    """
    import requests
    from django.http import HttpResponse
    from allauth.socialaccount.models import SocialAccount
    
    logger = logging.getLogger(__name__)
    
    # Get the user
    user = get_object_or_404(User, username=username)
    profile = user.profile
    
    # If profile doesn't have a picture URL, try to find one from Google
    if not profile.profile_picture_url:
        logger.info(f"No profile picture URL for user {username}, trying to find one")
        
        # FIRST PRIORITY: Use the stored Google account ID from the profile
        if profile.google_account_id:
            logger.info(f"Looking for Google account with ID: {profile.google_account_id}")
            try:
                # Find the social account using the stored Google ID
                google_account = SocialAccount.objects.get(
                    provider='google', 
                    uid=profile.google_account_id
                )
                
                logger.info(f"Found Google account by stored ID: {profile.google_account_id}")
                
                if 'picture' in google_account.extra_data:
                    profile.profile_picture_url = google_account.extra_data['picture']
                    profile.save()
                    logger.info(f"Found and saved profile picture URL by Google ID: {profile.profile_picture_url}")
            except SocialAccount.DoesNotExist:
                logger.info(f"No Google account found with ID: {profile.google_account_id}")
        
        # SECOND PRIORITY: If still no picture, try to find by Google email
        if not profile.profile_picture_url and profile.google_email:
            logger.info(f"Looking for Google account with email: {profile.google_email}")
            try:
                google_accounts = SocialAccount.objects.filter(
                    provider='google',
                    extra_data__email=profile.google_email
                )
                
                if google_accounts.exists():
                    google_account = google_accounts.first()
                    logger.info(f"Found Google account by email: {profile.google_email}")
                    
                    if 'picture' in google_account.extra_data:
                        profile.profile_picture_url = google_account.extra_data['picture']
                        profile.save()
                        logger.info(f"Found and saved profile picture URL by Google email: {profile.profile_picture_url}")
            except Exception as e:
                logger.info(f"Error finding Google account by email: {e}")
    
    if not profile.profile_picture_url:
        # If still no profile picture URL, return a default image
        logger.info(f"No profile picture URL found for user {username}")
        return redirect('https://via.placeholder.com/150')
    
    try:
        # Fetch the image from Google
        response = requests.get(profile.profile_picture_url, stream=True)
        
        if response.status_code == 200:
            # Return the image with appropriate content type
            return HttpResponse(
                response.content,
                content_type=response.headers.get('Content-Type', 'image/jpeg')
            )
        else:
            # If failed to fetch, return a default image
            logger.info(f"Failed to fetch profile image, status code: {response.status_code}")
            return redirect('https://via.placeholder.com/150')
    except Exception as e:
        logger.error(f"Error proxying user profile image: {e}")
        return redirect('https://via.placeholder.com/150')


@login_required
def set_profile_picture(request):
    """
    Directly set a profile picture URL for the user.
    This bypasses the Google account lookup process.
    """
    logger = logging.getLogger(__name__)
    
    # Get the user's profile
    profile = request.user.profile
    
    # Default Google profile picture URL (this is a standard Google profile picture URL)
    default_picture_url = "https://lh3.googleusercontent.com/a/default-user=s96-c"
    
    # If a URL is provided in the request, use that
    picture_url = request.GET.get('url', default_picture_url)
    
    # Update the profile
    profile.profile_picture_url = picture_url
    profile.save()
    
    logger.info(f"Manually set profile picture URL to: {picture_url}")
    
    messages.success(request, _("Profile picture updated successfully."))
    return redirect('films_app:profile')


@login_required
def upload_profile_image(request):
    """
    Handle file uploads for profile pictures.
    """
    logger = logging.getLogger(__name__)
    
    if request.method == 'POST' and request.FILES.get('image'):
        image_file = request.FILES['image']
        
        # Validate file size (5MB max)
        if image_file.size > 5 * 1024 * 1024:  # 5MB in bytes
            messages.error(request, _("Image file is too large. Maximum size is 5MB."))
            return redirect('films_app:profile')
        
        # Validate file type
        valid_extensions = ['.jpg', '.jpeg', '.png', '.gif']
        ext = os.path.splitext(image_file.name)[1].lower()
        if ext not in valid_extensions:
            messages.error(request, _("Invalid file type. Supported formats: JPG, PNG, GIF."))
            return redirect('films_app:profile')
        
        # Create a unique filename
        filename = f"profile_{request.user.id}_{int(time.time())}{ext}"
        filepath = os.path.join(settings.MEDIA_ROOT, 'profile_images', filename)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Save the file
        with open(filepath, 'wb+') as destination:
            for chunk in image_file.chunks():
                destination.write(chunk)
        
        # Update the profile with the URL to the saved file
        profile = request.user.profile
        
        # Store just the relative path to the file
        profile.profile_picture_url = f"{settings.MEDIA_URL}profile_images/{filename}"
        profile.save()
        
        logger.info(f"Uploaded profile picture: {filename}")
        messages.success(request, _("Profile picture uploaded successfully."))
    else:
        messages.error(request, _("No image file provided."))
    
    return redirect('films_app:profile')


@login_required
def get_google_profile_image(request):
    """
    Get the Google profile image URL for the current user.
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Attempting to get Google profile image for user: {request.user.username}")
    
    # Try to find a Google account using raw SQL
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT id, uid, extra_data FROM socialaccount_socialaccount WHERE user_id = %s AND LOWER(provider) = 'google'",
            [request.user.id]
        )
        google_account_raw = cursor.fetchone()
    
    if google_account_raw:
        account_id, account_uid, extra_data_json = google_account_raw
        logger.info(f"Found Google account: {account_id}")
        
        import json
        try:
            extra_data = json.loads(extra_data_json)
            logger.info(f"Extra data: {extra_data}")
            
            if 'picture' in extra_data:
                picture_url = extra_data['picture']
                logger.info(f"Found Google profile picture URL: {picture_url}")
                
                # Update the profile with the Google profile picture URL
                profile = request.user.profile
                profile.profile_picture_url = picture_url
                profile.google_account_id = account_uid
                profile.save()
                
                messages.success(request, _("Google profile picture set successfully."))
                return redirect('films_app:profile')
            else:
                logger.warning(f"No picture found in Google account extra data")
                messages.warning(request, _("No profile picture found in your Google account."))
        except json.JSONDecodeError:
            logger.error(f"Failed to parse extra_data JSON: {extra_data_json}")
            messages.error(request, _("Failed to retrieve profile picture from Google account."))
    else:
        logger.warning(f"No Google account found for {request.user.username}")
        messages.warning(request, _("No Google account connected. Please connect a Google account to use this feature."))
    
    return redirect('films_app:profile')


@login_required
def update_film_from_tmdb(request, imdb_id):
    """Update film information from TMDB API."""
    try:
        # Check if this is a numeric ID (likely a TMDB ID without the prefix)
        if imdb_id.isdigit():
            # Convert to tmdb-prefixed format
            imdb_id = f"tmdb-{imdb_id}"
            
        # Fetch or update film from TMDB with force_update=True
        film, _ = fetch_and_update_film_from_tmdb(imdb_id, force_update=True)
        
        messages.success(request, f"Successfully updated '{film.title}' with the latest information from TMDB, including genres: {film.genres}")
        return redirect('films_app:film_detail', imdb_id=imdb_id)
    except ValueError as e:
        messages.error(request, str(e))
        return redirect('films_app:film_detail', imdb_id=imdb_id)


def get_film_vote_count(request, imdb_id):
    """Get the vote count for a film."""
    film = get_object_or_404(Film, imdb_id=imdb_id)
    vote_count = count_film_votes(film)
    return render(request, 'films_app/partials/vote_count_badge.html', {'vote_count': vote_count})


@login_required
def get_user_vote_status(request):
    """Get the user's voting status."""
    user_votes, votes_remaining = get_user_votes_and_remaining(request.user)
    return render(request, 'films_app/partials/user_vote_status.html', {
        'user_votes': user_votes,
        'votes_remaining': votes_remaining
    })


def get_top_films_partial(request):
    """Get the top films partial HTML."""
    top_films = get_top_films_data()
    return render(request, 'films_app/partials/top_films.html', {'top_films': top_films})


# Utility functions to reduce duplication
def get_user_votes_and_remaining(user):
    """Get user votes and remaining votes count."""
    user_votes = Vote.objects.filter(user=user).select_related('film')
    votes_remaining = 10 - user_votes.count()
    return user_votes, votes_remaining

def get_top_films_data(limit=8):
    """Get top films by vote count."""
    return Film.objects.annotate(vote_count=Count('votes')).filter(vote_count__gt=0).order_by('-vote_count')[:limit]

def user_can_vote(user, film=None):
    """Check if a user can vote for a film."""
    # Check if user has already voted for this film
    if film:
        existing_vote = Vote.objects.filter(user=user, film=film).first()
        if existing_vote:
            return False, "already_voted"
    
    # Check if user has reached the maximum number of votes
    user_votes_count = Vote.objects.filter(user=user).count()
    if user_votes_count >= 10:
        return False, "max_votes_reached"
    
    return True, None

@login_required
def vote_for_cinema_film(request, imdb_id):
    """Vote for a cinema film."""
    # Check if method is POST
    method_error = require_http_method(request)
    if method_error:
        return method_error
    
    # Get or create film
    film = get_object_or_404(Film, imdb_id=imdb_id)
    
    # Check if film is in cinema or coming soon
    if not film.is_in_cinema and not film.is_coming_soon:
        return HttpResponseBadRequest("This film is not currently in cinemas or coming soon.")
    
    # Check if user already voted for this film
    if CinemaVote.objects.filter(user=request.user, film=film).exists():
        # Return the "already voted" button
        return render(request, 'films_app/partials/cinema_voted_button.html', {'film': film})
    
    # Check if user has reached the maximum number of votes
    if CinemaVote.objects.filter(user=request.user).count() >= 3:
        # Return the "max votes reached" button
        return render(request, 'films_app/partials/cinema_max_votes_button.html')
    
    # Create vote
    vote = CinemaVote(user=request.user, film=film)
    vote.save()
    
    # Get updated vote count for the film
    vote_count = CinemaVote.objects.filter(film=film).count()
    
    # Return the success button with updated vote count
    response_html = f"""
    {render_to_string('films_app/partials/cinema_voted_button.html', {'film': film}, request=request)}
    <div hx-swap-oob="true" id="cinema-film-vote-count-{film.imdb_id}">
        {render_to_string('films_app/partials/vote_count_badge.html', {'vote_count': vote_count}, request=request)}
    </div>
    """
    
    # Also update the user's vote status
    response_html += f"""
    <div hx-swap-oob="true" id="user-cinema-vote-status">
        {render_to_string('films_app/partials/user_cinema_vote_status.html', 
                         {'user_cinema_votes': CinemaVote.objects.filter(user=request.user),
                          'cinema_votes_remaining': 3 - CinemaVote.objects.filter(user=request.user).count()}, 
                         request=request)}
    </div>
    """
    
    # Log activity
    Activity.objects.create(
        user=request.user,
        activity_type='vote',
        film=film,
        description=f"Voted for cinema film: {film.title}"
    )
    
    return HttpResponse(response_html)


@login_required
def remove_cinema_vote(request, vote_id):
    """Remove a cinema vote."""
    # Check if method is POST or DELETE (for HTMX)
    if request.method not in ['POST', 'DELETE']:
        return HttpResponseNotAllowed(['POST', 'DELETE'])
    
    # Get vote
    vote = get_object_or_404(CinemaVote, id=vote_id, user=request.user)
    film = vote.film
    
    # Delete vote
    vote.delete()
    
    # Log activity
    Activity.objects.create(
        user=request.user,
        activity_type='vote',
        film=film,
        description=f"Removed vote for cinema film: {film.title}"
    )
    
    # Return success message
    return render(request, 'films_app/partials/cinema_vote_removed.html', {
        'film': film,
        'user_cinema_votes': CinemaVote.objects.filter(user=request.user),
        'cinema_votes_remaining': 3 - CinemaVote.objects.filter(user=request.user).count()
    })






@login_required
def get_cinema_vote_status(request):
    """Get the user's cinema vote status."""
    user_cinema_votes = CinemaVote.objects.filter(user=request.user).select_related('film')
    cinema_votes_remaining = 3 - user_cinema_votes.count()
    
    return render(request, 'films_app/partials/user_cinema_vote_status.html', {
        'user_cinema_votes': user_cinema_votes,
        'cinema_votes_remaining': cinema_votes_remaining
    })







@staff_member_required
def update_cinema_cache(request):
    """Update the cinema cache with current and upcoming UK releases."""
    from django.core.management import call_command
    from io import StringIO
    import sys
    import logging
    from datetime import datetime, timedelta
    from films_app.models import PageTracker
    
    logger = logging.getLogger(__name__)
    
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    
    # Check if an update was performed recently
    try:
        # Get the most recently updated tracker
        latest_tracker = PageTracker.objects.order_by('-last_updated').first()
        
        if latest_tracker and (datetime.now().replace(tzinfo=latest_tracker.last_updated.tzinfo) - latest_tracker.last_updated) < timedelta(hours=1):
            message = f"Skipping update - last update was at {latest_tracker.last_updated.strftime('%Y-%m-%d %H:%M:%S')}, less than 1 hour ago"
            logger.info(message)
            return render(request, 'films_app/partials/cache_update_result.html', {
                'status': 'info',
                'result': message
            })
    except Exception as e:
        logger.warning(f"Error checking last update time: {str(e)}")
    
    # Capture command output
    output = StringIO()
    sys.stdout = output
    
    try:
        # Run the management command with limited pages to avoid timeouts
        logger.info("Starting cinema cache update with max_pages=2")
        call_command('update_movie_cache', type='cinema', force=True, max_pages=2)
        result = output.getvalue()
        status = 'success'
        logger.info("Cinema cache update completed successfully")
    except Exception as e:
        result = f"Error: {str(e)}"
        status = 'error'
        logger.error(f"Cinema cache update failed: {str(e)}")
    finally:
        # Reset stdout
        sys.stdout = sys.__stdout__
    
    # Format the output for display
    formatted_output = result.replace('\n', '<br>')
    
    # Return the result
    if status == 'success':
        return render(request, 'films_app/partials/cache_update_success.html', {
            'output': formatted_output
        })
    else:
        return render(request, 'films_app/partials/cache_update_error.html', {
            'output': formatted_output
        })

def filter_cinema_films(request):
    """Filter cinema films based on a search query."""
    from datetime import date
    from .models import Film, CinemaVote
    from django.conf import settings
    from django.db.models import Q
    
    logger = logging.getLogger(__name__)
    
    # Get the search query
    query = request.GET.get('query', '').strip()
    logger.info(f"Filtering cinema films with query: '{query}'")
    
    # Get the maximum number of films to display
    max_films = getattr(settings, 'MAX_CINEMA_FILMS', 20)
    
    # Base queryset for now playing films
    now_playing_base = Film.objects.filter(is_in_cinema=True)
    
    # Base queryset for upcoming films
    upcoming_base = Film.objects.filter(
        is_in_cinema=False, 
        uk_release_date__isnull=False,
        uk_release_date__gt=date.today()
    )
    
    # Apply search filter if query is provided
    if query:
        now_playing_filtered = now_playing_base.filter(title__icontains=query).order_by('-popularity')
        upcoming_filtered = upcoming_base.filter(title__icontains=query).order_by('-popularity')
    else:
        now_playing_filtered = now_playing_base.order_by('-popularity')
        upcoming_filtered = upcoming_base.order_by('-popularity')
    
    # Limit to the most popular ones
    now_playing_films = now_playing_filtered[:max_films]
    upcoming_films = upcoming_filtered[:max_films]
    
    # Get user's cinema votes if authenticated
    user_cinema_votes = []
    if request.user.is_authenticated:
        user_cinema_votes = CinemaVote.objects.filter(user=request.user).select_related('film')
    
    context = {
        'now_playing_films': now_playing_films,
        'upcoming_films': upcoming_films,
        'total_now_playing': now_playing_filtered.count(),
        'total_upcoming': upcoming_filtered.count(),
        'max_films': max_films,
        'query': query,
    }
    
    return render(request, 'films_app/partials/cinema_films.html', context) 