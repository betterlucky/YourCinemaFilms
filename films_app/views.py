import json
import requests
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse, FileResponse
from django.conf import settings
from django.contrib import messages
from django.db.models import Count, Q, F
from django.utils import timezone
from django.contrib.auth.models import User
import logging
from allauth.socialaccount.models import SocialAccount
import os
import time
from django.utils.translation import gettext as _
from django.template.loader import render_to_string
from django.core.cache import cache
from django.db.models.functions import Trim

from .models import Film, Vote, UserProfile, GenreTag
from .utils import (
    validate_genre_tag, 
    fetch_and_update_film_from_omdb, 
    require_http_method, 
    validate_and_format_genre_tag,
    count_film_votes,
    filter_votes_by_period
)


def home(request):
    """Home page view."""
    try:
        # Get top films based on votes
        top_films = get_top_films_data(limit=10)
        
        context = {
            'top_films': top_films,
        }
        
        if request.user.is_authenticated:
            # Get user's votes and remaining votes
            user_votes, votes_remaining = get_user_votes_and_remaining(request.user)
            context['user_votes'] = user_votes
            context['votes_remaining'] = votes_remaining
        
        return render(request, 'films_app/home.html', context)
    except Exception as e:
        # If there's an error (like missing tables), show a simple page
        error_message = str(e)
        return render(request, 'films_app/error.html', {
            'error_message': error_message,
            'is_database_error': 'relation' in error_message and 'does not exist' in error_message
        })


@login_required
def profile(request):
    """User profile view."""
    logger = logging.getLogger(__name__)
    
    # Get the user's profile
    profile = request.user.profile
    
    # Get user's votes and remaining votes
    user_votes, votes_remaining = get_user_votes_and_remaining(request.user)
    
    # Check if the user has a Google account (case-insensitive)
    google_accounts = SocialAccount.objects.filter(user=request.user)
    has_google_account = False
    
    # Debug logging for all social accounts
    logger.info(f"User {request.user.username} has {google_accounts.count()} social accounts")
    for account in google_accounts:
        logger.info(f"Social account provider: {account.provider}")
        # Case-insensitive check for 'google'
        if account.provider.lower() == 'google':
            has_google_account = True
            logger.info(f"Found Google account with provider: {account.provider}")
            logger.info(f"Google account UID: {account.uid}")
            if hasattr(account, 'extra_data'):
                logger.info(f"Google account extra_data: {account.extra_data}")
    
    logger.info(f"Final has_google_account value: {has_google_account}")
    
    context = {
        'profile': profile,
        'user_votes': user_votes,
        'votes_remaining': votes_remaining,
        'social_accounts': google_accounts,
        'has_google_account': has_google_account,
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
        
        # Demographic info
        profile.location = request.POST.get('location', '')
        profile.gender = request.POST.get('gender', 'NS')
        profile.age_range = request.POST.get('age_range', 'NS')
        
        # Privacy settings
        profile.location_privacy = request.POST.get('location_privacy', 'private')
        profile.gender_privacy = request.POST.get('gender_privacy', 'private')
        profile.age_privacy = request.POST.get('age_privacy', 'private')
        profile.votes_privacy = request.POST.get('votes_privacy', 'public')
        
        profile.save()
        messages.success(request, 'Profile updated successfully!')
        return redirect('films_app:profile')
    
    return render(request, 'films_app/edit_profile.html', {'profile': request.user.profile})


def search_films(request):
    """Search films using OMDB API."""
    query = request.GET.get('query', '')
    
    if not query or len(query) < 3:
        if request.htmx:
            # Check which target is being used
            if request.htmx.target == 'search-results':
                return render(request, 'films_app/partials/modal_search_results.html', {'results': []})
            return render(request, 'films_app/partials/search_results.html', {'results': []})
        return JsonResponse({'results': []})
    
    api_key = settings.OMDB_API_KEY
    url = f"http://www.omdbapi.com/?apikey={api_key}&s={query}&type=movie"
    
    try:
        response = requests.get(url)
        data = response.json()
        
        if data.get('Response') == 'True':
            results = data.get('Search', [])
            
            if request.htmx:
                # Check which target is being used
                if request.htmx.target == 'search-results':
                    return render(request, 'films_app/partials/modal_search_results.html', {'results': results})
                # Check for navbar or main search targets
                if request.htmx.target == 'navbar-search-results':
                    return render(request, 'films_app/partials/search_results.html', {'results': results})
                if request.htmx.target == 'main-search-results':
                    return render(request, 'films_app/partials/search_results.html', {'results': results})
                return render(request, 'films_app/partials/search_results.html', {'results': results})
            return JsonResponse({'results': results})
        else:
            if request.htmx:
                # Check which target is being used
                if request.htmx.target == 'search-results':
                    return render(request, 'films_app/partials/modal_search_results.html', {'results': []})
                return render(request, 'films_app/partials/search_results.html', {'results': []})
            return JsonResponse({'results': []})
    except Exception as e:
        if request.htmx:
            # Check which target is being used
            if request.htmx.target == 'search-results':
                return render(request, 'films_app/partials/modal_search_results.html', {'results': []})
            return render(request, 'films_app/partials/search_results.html', {'results': []})
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def film_detail(request, imdb_id):
    """Get detailed information about a film."""
    try:
        # Fetch or update film from OMDB
        film, created = fetch_and_update_film_from_omdb(imdb_id)
        
        # Check if user has voted for this film and can vote
        has_voted = False
        user_vote = None
        can_vote = False
        
        if request.user.is_authenticated:
            can_vote, _ = user_can_vote(request.user, film)
            user_vote = Vote.objects.filter(user=request.user, film=film).first()
            has_voted = user_vote is not None
        
        # Get vote count
        vote_count = count_film_votes(film)
        
        # Get user tags for this film
        user_tags = GenreTag.objects.filter(film=film, user=request.user)
        
        # Get all approved tags for this film
        approved_tags = GenreTag.objects.filter(film=film, is_approved=True).exclude(user=request.user)
        
        context = {
            'film': film,
            'has_voted': has_voted,
            'can_vote': can_vote,
            'vote_count': vote_count,
            'user_tags': user_tags,
            'approved_tags': approved_tags,
            'genres': film.genre_list,
            'all_genres': film.all_genres,
        }
        
        return render(request, 'films_app/film_detail.html', context)
    except ValueError as e:
        messages.error(request, str(e))
        return redirect('films_app:home')


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
    # Check if method is POST
    method_error = require_http_method(request)
    if method_error:
        return method_error
    
    vote = get_object_or_404(Vote, id=vote_id, user=request.user)
    film = vote.film
    vote.delete()
    
    # Get updated data for the response
    user_votes, votes_remaining = get_user_votes_and_remaining(request.user)
    top_films = get_top_films_data()
    
    # Return the updated card with empty content to remove it
    response_html = f"""
    <div hx-swap-oob="true" id="user-vote-status">
        {render_to_string('films_app/partials/user_vote_status.html', {'user_votes': user_votes, 'votes_remaining': votes_remaining}, request=request)}
    </div>
    <div hx-swap-oob="true" id="top-films-container">
        {render_to_string('films_app/partials/top_films.html', {'top_films': top_films}, request=request)}
    </div>
    """
    
    return HttpResponse(response_html)


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
        # Yearly activity for all time
        earliest_vote = Vote.objects.order_by('created_at').first()
        if earliest_vote:
            earliest_year = earliest_vote.created_at.year
            current_year = timezone.now().year
            for year in range(earliest_year, current_year + 1):
                activity_dates.append(str(year))
                year_start = timezone.make_aware(datetime(year, 1, 1))
                year_end = timezone.make_aware(datetime(year, 12, 31, 23, 59, 59))
                activity_counts.append(Vote.objects.filter(created_at__range=(year_start, year_end)).count())
    
    # Get active users
    active_users = User.objects.filter(votes__in=period_votes_query).annotate(
        vote_count=Count('votes')
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
    recent_votes = Vote.objects.select_related('user', 'film').order_by('-created_at')[:10]
    
    for vote in recent_votes:
        recent_activity.append({
            'user': vote.user,
            'action': 'voted for',
            'description': f"{vote.film.title} ({vote.film.year})",
            'timestamp': vote.created_at
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
        return redirect('films_app:home')
    
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


def debug_profile(request):
    """Debug view to check profile data."""
    if not request.user.is_authenticated:
        return redirect('account_login')
    
    from django.http import JsonResponse
    from allauth.socialaccount.models import SocialAccount
    import json
    
    logger = logging.getLogger(__name__)
    
    # Get the user's profile
    profile = request.user.profile
    
    # PRIORITY 1: Try to find Google account by stored ID
    google_account = None
    if profile.google_account_id:
        try:
            google_account = SocialAccount.objects.get(
                provider='google',
                uid=profile.google_account_id
            )
            logger.info(f"Found Google account by stored ID: {profile.google_account_id}")
        except SocialAccount.DoesNotExist:
            logger.warning(f"No Google account found with stored ID: {profile.google_account_id}")
    
    # PRIORITY 2 (FALLBACK): Only if no account found by ID, try user's social accounts
    if not google_account:
        social_accounts = request.user.socialaccount_set.filter(provider='google')
        if social_accounts.exists():
            google_account = social_accounts.first()
            logger.info(f"Found Google account through user relationship")
            
            # Store the Google account ID for future use if not already set
            if not profile.google_account_id:
                profile.google_account_id = google_account.uid
                if 'email' in google_account.extra_data:
                    profile.google_email = google_account.extra_data['email']
                profile.save()
                logger.info(f"Stored Google account ID: {profile.google_account_id}")
    
    # ALWAYS update the profile picture if we have a Google account with a picture
    if google_account and 'picture' in google_account.extra_data:
        picture_url = google_account.extra_data['picture']
        logger.info(f"Found picture URL in Google account: {picture_url}")
        
        # Update the profile picture
        profile.profile_picture_url = picture_url
        profile.save()
        
        logger.info(f"Updated profile picture URL to: {picture_url}")
        messages.success(request, f"Updated profile picture URL to: {picture_url}")
    
    # Check if we need to manually update the Google account ID and email
    if request.GET.get('update_google_id') and google_account:
        profile.google_account_id = google_account.uid
        if 'email' in google_account.extra_data:
            profile.google_email = google_account.extra_data['email']
        profile.save()
        messages.success(request, f"Updated Google account ID to: {profile.google_account_id}")
        logger.info(f"Manually updated Google account ID to: {profile.google_account_id}")
        if profile.google_email:
            logger.info(f"Manually updated Google email to: {profile.google_email}")
    
    # Check if we need to find all Google accounts
    all_google_accounts = []
    if request.GET.get('find_accounts'):
        # Find all Google accounts in the system
        all_accounts = SocialAccount.objects.filter(provider='google')
        for account in all_accounts:
            account_data = {
                'id': account.id,
                'user': account.user.username,
                'uid': account.uid,
                'email': account.extra_data.get('email', 'Unknown'),
                'has_picture': 'picture' in account.extra_data,
                'picture_url': account.extra_data.get('picture', None)
            }
            all_google_accounts.append(account_data)
            logger.info(f"Found Google account: {account.user.username}, UID: {account.uid}, Email: {account.extra_data.get('email', 'Unknown')}")
    
    # Check if we need to link a specific account
    if request.GET.get('link_account'):
        account_id = request.GET.get('link_account')
        try:
            account = SocialAccount.objects.get(id=account_id)
            # Update the user reference
            account.user = request.user
            account.save()
            
            # Also update the Google account ID and email in the profile
            profile.google_account_id = account.uid
            if 'email' in account.extra_data:
                profile.google_email = account.extra_data['email']
            profile.save()
            
            messages.success(request, f"Successfully linked Google account {account.uid} to your user!")
            logger.info(f"Linked Google account {account.uid} to user {request.user.username}")
            
            # Also update the profile picture
            if 'picture' in account.extra_data:
                profile.profile_picture_url = account.extra_data['picture']
                profile.save()
        except SocialAccount.DoesNotExist:
            messages.error(request, f"Account with ID {account_id} not found")
    
    # Get all social accounts for the response
    social_accounts = request.user.socialaccount_set.all()
    
    data = {
        'user': {
            'username': request.user.username,
            'email': request.user.email,
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
        },
        'profile': {
            'profile_picture_url': profile.profile_picture_url,
            'google_account_id': profile.google_account_id,
            'google_email': profile.google_email,
            'contact_email': profile.contact_email,
            'use_google_email_for_contact': profile.use_google_email_for_contact,
            'primary_email': profile.primary_email,
        },
        'social_accounts': [],
        'all_google_accounts': all_google_accounts
    }
    
    for account in social_accounts:
        account_data = {
            'provider': account.provider,
            'uid': account.uid,
        }
        
        # Add extra_data but ensure it's JSON serializable
        try:
            account_data['extra_data'] = account.extra_data
        except:
            account_data['extra_data'] = json.dumps(str(account.extra_data))
            
        data['social_accounts'].append(account_data)
    
    return JsonResponse(data)


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
    
    # Try to find a Google account for the user (case-insensitive)
    social_accounts = SocialAccount.objects.filter(user=request.user)
    google_account = None
    
    for account in social_accounts:
        if account.provider.lower() == 'google':
            google_account = account
            break
    
    if google_account and 'picture' in google_account.extra_data:
        picture_url = google_account.extra_data['picture']
        logger.info(f"Found Google profile picture URL: {picture_url}")
        
        # Update the profile with the Google profile picture URL
        profile = request.user.profile
        profile.profile_picture_url = picture_url
        profile.google_account_id = google_account.uid
        profile.save()
        
        messages.success(request, _("Google profile picture set successfully."))
        return redirect('films_app:profile')
    
    # If no Google account found or no picture in the account
    logger.warning(f"No Google account found for {request.user.username}")
    messages.warning(request, _("No Google account connected. Please connect a Google account to use this feature."))
    
    return redirect('films_app:profile')


@login_required
def update_film_from_omdb(request, imdb_id):
    """Update film information from OMDB API."""
    try:
        # Fetch or update film from OMDB with force_update=True
        from .utils import fetch_and_update_film_from_omdb
        film, _ = fetch_and_update_film_from_omdb(imdb_id, force_update=True)
        
        messages.success(request, f"Successfully updated '{film.title}' with the latest information from OMDB, including genres: {film.genres}")
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