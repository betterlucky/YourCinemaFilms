import json
import os
import requests
import logging
import sys
import re
import base64
import time
import urllib.parse
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from io import StringIO
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse, HttpResponse, FileResponse, HttpResponseNotAllowed
from django.conf import settings
from django.contrib import messages
from django.db.models import (
    Count, Q, F, Sum, Avg, Case, When, IntegerField,
    Subquery, OuterRef
)
from django.db.models.functions import TruncMonth, TruncYear
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.contrib.auth.models import User
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
from django.template.loader import render_to_string
from django.core.cache import cache
from django.core.management import call_command
from django.utils.translation import gettext as _
from allauth.socialaccount.models import SocialAccount
from rest_framework.decorators import permission_classes
from rest_framework.permissions import AllowAny
import glob
from django.db import models

# Try to import PIL, but don't fail if it's not available
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logging.warning("PIL not available. Image processing features will be disabled.")

from .models import (
    Film, Vote, UserProfile, GenreTag, Activity,
    CinemaVote, PageTracker, Cinema, CinemaPreference,
    Achievement
)
from .utils import (
    contains_profanity, validate_and_format_genre_tag, require_http_method,
    count_film_votes, get_date_range_from_period, filter_votes_by_period,
    get_cached_search_results, cache_search_results, fetch_and_update_film_from_tmdb,
    get_cache_directory, get_user_votes_and_remaining, user_can_vote, get_top_films_data
)
from .tmdb_api import (
    get_movie_details, format_tmdb_data_for_film,
    search_movies, sort_and_limit_films
)


def landing(request):
    """Landing page view that introduces the app and offers route options."""
    return render(request, 'films_app/landing.html')


def cinema(request):
    """View for cinema films."""
    today = timezone.now().date()
    
    # Get current films - those marked as in cinema and with release date today or earlier
    now_playing_films = Film.objects.filter(
        is_in_cinema=True, 
        uk_release_date__lte=today
    ).extra(
        select={'combined_score': '(revenue / 10000000) * 0.5 + popularity * 0.3 + (vote_count / 100) * 0.2'}
    ).order_by('-combined_score')[:20]
    
    # Get upcoming films - those marked with is_upcoming=True
    upcoming_films = Film.objects.filter(
        is_upcoming=True
    ).extra(
        select={'combined_score': '(revenue / 10000000) * 0.5 + popularity * 0.3 + (vote_count / 100) * 0.2'}
    ).order_by('uk_release_date')[:20]
    
    # Get total counts
    total_now_playing = Film.objects.filter(
        is_in_cinema=True, 
        uk_release_date__lte=today
    ).count()
    
    total_upcoming = Film.objects.filter(
        is_upcoming=True
    ).count()
    
    # Get user's cinema votes if authenticated
    user_cinema_votes = []
    user_voted_films = []
    if request.user.is_authenticated:
        user_cinema_votes = CinemaVote.objects.filter(user=request.user).select_related('film')
        user_voted_films = [vote.film.imdb_id for vote in user_cinema_votes]
    
    # Get the time window for upcoming films from settings
    from django.conf import settings
    upcoming_films_months = getattr(settings, 'UPCOMING_FILMS_MONTHS', 6)
    
    # Get the last update timestamp from PageTracker
    last_update = None
    try:
        latest_tracker = PageTracker.objects.order_by('-last_updated').first()
        if latest_tracker:
            last_update = latest_tracker.last_updated
    except Exception as e:
        logging.error(f"Error getting last update timestamp: {str(e)}")
    
    context = {
        'now_playing_films': now_playing_films,
        'upcoming_films': upcoming_films,
        'total_now_playing': total_now_playing,
        'total_upcoming': total_upcoming,
        'upcoming_films_months': upcoming_films_months,
        'user_cinema_votes': user_cinema_votes,
        'user_voted_films': user_voted_films,
        'last_update': last_update,
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
            user_voted_films = [vote.film.imdb_id for vote in user_votes]
            can_vote = votes_remaining > 0
            context.update({
                'user_votes': user_votes,
                'votes_remaining': votes_remaining,
                'user_voted_films': user_voted_films,
                'can_vote': can_vote,
            })
        
        return render(request, 'films_app/classics.html', context)
    except Exception as e:
        logging.error(f"Error in classics view: {e}")
        messages.error(request, "An error occurred while loading the classics page. Please try again later.")
        return render(request, 'films_app/error.html', {'error_message': str(e)})


def filter_classics_films(request):
    """Filter classic films for pagination."""
    query = request.GET.get('query', '').strip()
    page_num = request.GET.get('page', 1)
    
    # Get classic films (films with votes)
    from django.db.models import Count
    from django.conf import settings
    
    # Base query for classic films - films with at least one vote
    # Using 'total_votes' instead of 'vote_count' to avoid conflict with existing field
    classic_films = Film.objects.annotate(total_votes=Count('votes'))
    
    # If we want to show all films, not just those with votes, remove the filter
    # classic_films = classic_films.filter(total_votes__gt=0)
    
    # Add title filter if query is provided
    if query:
        classic_films = classic_films.filter(title__icontains=query)
    
    # Order by vote count (descending)
    classic_films = classic_films.order_by('-total_votes')
    
    # Get pagination settings
    # If user is authenticated and has a custom pagination setting, use that
    films_per_page = 8  # Default value
    if request.user.is_authenticated:
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            if user_profile.films_per_page:
                films_per_page = user_profile.films_per_page
        except UserProfile.DoesNotExist:
            # Use the default from settings
            films_per_page = getattr(settings, 'FILMS_PER_PAGE', 8)
    else:
        # Use the default from settings
        films_per_page = getattr(settings, 'FILMS_PER_PAGE', 8)
    
    # Apply pagination
    paginator = Paginator(classic_films, films_per_page)
    
    try:
        page = paginator.page(page_num)
    except PageNotAnInteger:
        page = paginator.page(1)
    except EmptyPage:
        page = paginator.page(paginator.num_pages)
    
    # Get total count
    total_films = classic_films.count()
    
    # Get user votes if authenticated
    user_voted_films = []
    user_votes = []
    can_vote = False
    
    if request.user.is_authenticated:
        user_votes, votes_remaining = get_user_votes_and_remaining(request.user)
        user_voted_films = [vote.film.imdb_id for vote in user_votes]
        can_vote = votes_remaining > 0
    
    # Prepare context
    context = {
        'classic_films': page.object_list,
        'total_films': total_films,
        'page': page.number,
        'num_pages': max(paginator.num_pages, 1),  # Ensure at least 1 page
        'has_previous': page.has_previous(),
        'has_next': page.has_next(),
        'previous_page': page.previous_page_number() if page.has_previous() else None,
        'next_page': page.next_page_number() if page.has_next() else None,
        'query': query,
        'user_voted_films': user_voted_films,
        'user_votes': user_votes,
        'can_vote': can_vote,
        'films_per_page': films_per_page,  # Add this to the context
    }
    
    return render(request, 'films_app/partials/classics_films.html', context)


@login_required
def profile(request):
    """User profile view."""
    logger = logging.getLogger(__name__)
    
    # Get user's votes and remaining votes
    user_votes = Vote.objects.filter(user=request.user).select_related('film')
    user_cinema_votes = CinemaVote.objects.filter(user=request.user).select_related('film')
    votes_remaining = max(0, 10 - user_votes.count())
    
    # Get user achievements
    achievements = Achievement.objects.filter(user=request.user)
    
    # Get Google accounts using Django ORM
    has_google_account = SocialAccount.objects.filter(
        user=request.user,
        provider__iexact='google'
    ).exists()
    
    logger.info(
        "User: %s, Has Google account: %s",
        request.user.username,
        has_google_account
    )
    
    # Get all social accounts using Django ORM
    social_accounts = SocialAccount.objects.filter(
        user=request.user
    ).values('id', 'provider')
    
    logger.info("Social accounts: %s", list(social_accounts))
    
    context = {
        'profile': request.user.profile,
        'user_votes': user_votes,
        'user_cinema_votes': user_cinema_votes,
        'votes_remaining': votes_remaining,
        'social_accounts': social_accounts,
        'has_google_account': has_google_account,
        'achievements': achievements,
        'total_achievements': len(Achievement.ACHIEVEMENT_TYPES),
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
        
        # Display preferences
        try:
            films_per_page = int(request.POST.get('films_per_page', '8'))
            # Ensure it's one of the valid choices
            valid_choices = [choice[0] for choice in UserProfile.PAGINATION_CHOICES]
            if films_per_page in valid_choices:
                profile.films_per_page = films_per_page
            else:
                profile.films_per_page = 8  # Default to 8 if invalid
        except (ValueError, TypeError):
            profile.films_per_page = 8  # Default to 8 if there's an error
        
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
    
    if not query or len(query) < 3:
        if hasattr(request, 'htmx'):
            target_id = request.htmx.target
            if target_id == 'search-results':
                return render(request, 'films_app/partials/modal_search_results.html', {'results': []})
            else:
                return render(request, 'films_app/partials/search_results.html', {'results': []})
        return JsonResponse({'results': []})
    
    # Try to get cached results first
    cached_results = get_cached_search_results(query)
    if cached_results:
        results = cached_results
    else:
        # Fetch from TMDB API
        try:
            tmdb_data = search_movies(query)
            
            if tmdb_data.get('results'):
                # Format results to match the expected structure in templates
                results = []
                
                # Get all potential TMDB IDs to check in a single database query
                tmdb_ids = [f"tmdb-{movie.get('id')}" for movie in tmdb_data['results'] if movie.get('id')]
                
                # Fetch all matching films in a single query
                existing_films = {film.imdb_id: film for film in Film.objects.filter(imdb_id__in=tmdb_ids)}
                
                for movie in tmdb_data['results']:
                    # Get the TMDB ID
                    tmdb_id = movie.get('id')
                    if not tmdb_id:
                        continue
                        
                    # Use TMDB ID with prefix as the ID format
                    imdb_id = f"tmdb-{tmdb_id}"
                    
                    # Check if this film exists in our database
                    is_in_cinema = False
                    is_upcoming = False
                    uk_certification = None
                    
                    # Check if film exists in our pre-fetched results
                    existing_film = existing_films.get(imdb_id)
                    
                    if existing_film:
                        is_in_cinema = existing_film.is_in_cinema
                        is_upcoming = existing_film.is_upcoming
                        uk_certification = existing_film.uk_certification
                    
                    # Format each movie to match the structure expected by the template
                    formatted_movie = {
                        'imdbID': imdb_id,
                        'Title': movie.get('title', ''),
                        'Year': movie.get('release_date', '')[:4] if movie.get('release_date') else '',
                        'Poster': f"https://image.tmdb.org/t/p/w500{movie.get('poster_path')}" if movie.get('poster_path') else '',
                        'tmdb_id': tmdb_id,
                        'is_in_cinema': is_in_cinema,
                        'is_upcoming': is_upcoming,
                        'uk_certification': uk_certification
                    }
                    results.append(formatted_movie)
                
                # Cache the results
                cache_search_results(query, results)
            else:
                results = []
        except Exception as e:
            logging.error(f"Error searching TMDB: {str(e)}")
            results = []
    
    if hasattr(request, 'htmx'):
        target_id = request.htmx.target
        
        if target_id == 'search-results':
            return render(request, 'films_app/partials/modal_search_results.html', {'results': results})
        else:
            return render(request, 'films_app/partials/search_results.html', {'results': results})
    
    return JsonResponse({'results': results})


@permission_classes([AllowAny])
def film_detail(request, imdb_id):
    """Film detail view."""
    logger = logging.getLogger(__name__)
    
    try:
        film = Film.objects.get(imdb_id=imdb_id)
    except Film.DoesNotExist:
        # If the film doesn't exist in our database, try to fetch it from TMDB
        if imdb_id.startswith('tmdb-'):
            tmdb_id = imdb_id.replace('tmdb-', '')
            try:
                logger.info(f"Attempting to fetch film with TMDB ID {tmdb_id} from TMDB API")
                
                # Fetch the movie details from TMDB
                movie_data = get_movie_details(tmdb_id)
                
                if movie_data:
                    # Format the data for our Film model
                    film_data = format_tmdb_data_for_film(movie_data)
                    
                    # Create the film in our database
                    film = Film.objects.create(
                        imdb_id=imdb_id,
                        title=film_data.get('title', ''),
                        year=film_data.get('year', ''),
                        director=film_data.get('director', ''),
                        poster_url=film_data.get('poster_url', ''),
                        plot=film_data.get('plot', ''),
                        genres=film_data.get('genres', ''),
                        runtime=film_data.get('runtime', 0),
                        popularity=film_data.get('popularity', 0.0),
                        vote_count=film_data.get('vote_count', 0),
                        vote_average=film_data.get('vote_average', 0.0),
                        uk_certification=film_data.get('uk_certification', ''),
                        uk_release_date=film_data.get('uk_release_date'),
                        revenue=film_data.get('revenue', 0),
                        actors=film_data.get('actors', ''),
                    )
                    
                    logger.info(f"Successfully created film {film.title} with ID {film.imdb_id}")
                else:
                    logger.error(f"Failed to fetch film with TMDB ID {tmdb_id} from TMDB API")
                    messages.error(request, _('Film not found in TMDB.'))
                    return redirect('films_app:classics')
            except Exception as e:
                logger.error(f"Error fetching film from TMDB: {str(e)}")
                messages.error(request, _('Error fetching film details.'))
                return redirect('films_app:classics')
        else:
            messages.error(request, _('Film not found.'))
            return redirect('films_app:classics')
    
    # Get similar films
    similar_films = (
        Film.objects.filter(director=film.director)
        .exclude(imdb_id=film.imdb_id)
        .order_by('-popularity')[:6]
    )
    
    # Get all approved tags for this film
    approved_tags = GenreTag.objects.filter(film=film, is_approved=True)
    
    # Initialize vote-related variables
    has_voted = False
    can_vote = False
    votes_remaining = 0
    
    # If user is authenticated, check if they've voted for this film and how many votes they have left
    if request.user.is_authenticated:
        # Exclude user's tags from approved tags
        approved_tags = approved_tags.exclude(user=request.user)
        # Get user tags for this film
        user_tags = GenreTag.objects.filter(film=film, user=request.user)
        
        # Check if user has voted for this film
        has_voted = Vote.objects.filter(user=request.user, film=film).exists()
        
        # Get user's votes and remaining votes
        user_votes, votes_remaining = get_user_votes_and_remaining(request.user)
        
        # User can vote if they haven't already voted for this film and have votes remaining
        can_vote = not has_voted and votes_remaining > 0
    else:
        user_tags = []
    
    context = {
        'film': film,
        'user_tags': user_tags,
        'approved_tags': approved_tags,
        'genres': film.genre_list,
        'all_genres': film.all_genres,
        'is_authenticated': request.user.is_authenticated,
        'from_classics': False,
        'similar_films': similar_films,
        'has_voted': has_voted,
        'can_vote': can_vote,
        'votes_remaining': votes_remaining,
        'vote_count': film.votes_count,
    }
    
    return render(request, 'films_app/film_detail.html', context)


@login_required
def vote(request, imdb_id):
    """Vote for a film with commitment level and preferences."""
    # Check if method is POST
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    
    user = request.user
    
    # Check if user can vote
    try:
        film = Film.objects.get(imdb_id=imdb_id)
        can_vote, reason = user_can_vote(user, film)
        
        if not can_vote:
            if reason == "already_voted":
                messages.error(request, _('You have already voted for this film.'))
                return redirect('films_app:film_detail', imdb_id=imdb_id)
            elif reason == "max_votes_reached":
                messages.error(request, _('You have reached the maximum number of votes.'))
                return redirect('films_app:film_detail', imdb_id=imdb_id)
        
        # Create vote with default preferences
        vote, created = Vote.objects.get_or_create(
            user=user,
            film=film,
            defaults={
                'commitment_level': 'interested',
                'preferred_format': 'any',
                'social_preference': 'undecided'
            }
        )
        
        # Create activity record
        Activity.objects.create(
            user=user,
            activity_type='vote',
            film=film,
            description=f"Voted for {film.title}"
        )
        
        # Check for achievements
        check_vote_achievements(user)
        
        # Get updated vote count for the film
        vote_count = film.votes.count()
        
        # If this is an HTMX request
        if request.headers.get('HX-Request'):
            # If the request is from the film detail page
            if request.headers.get('HX-Target') == 'vote-container':
                context = {
                    'film': film,
                    'has_voted': True,
                    'vote': vote,
                }
                return render(request, 'films_app/partials/vote_success.html', context)
            # If the request is for updating the vote button container
            elif 'vote-button-container' in request.headers.get('HX-Target', ''):
                # Return the remove vote button
                context = {
                    'vote': vote,
                    'film': film,  # Add film to context to ensure it's available
                }
                response = render(request, 'films_app/partials/remove_vote_button.html', context)
                # Also trigger an update to the vote count
                response.headers['HX-Trigger'] = json.dumps({
                    'filmVoteCountChanged': {
                        'imdb_id': film.imdb_id,
                        'vote_count': vote_count
                    },
                    'updateVoteStatus': True
                })
                return response
            # If the request is for updating the vote count
            elif 'film-vote-count' in request.headers.get('HX-Target', ''):
                return HttpResponse(f'<div id="film-vote-count-{film.imdb_id}" class="vote-badge">{vote_count} vote{"s" if vote_count != 1 else ""}</div>')
        
        messages.success(request, _('Your vote has been recorded.'))
        return redirect('films_app:film_detail', imdb_id=imdb_id)
        
    except Film.DoesNotExist:
        messages.error(request, _('Film not found.'))
        return redirect('films_app:classics')


@login_required
def remove_vote(request, imdb_id):
    """Remove a vote for a film."""
    # Check if method is POST or DELETE (for HTMX)
    if request.method not in ['POST', 'DELETE']:
        return HttpResponseNotAllowed(['POST', 'DELETE'])
    
    try:
        # Get the vote
        vote = Vote.objects.get(user=request.user, film__imdb_id=imdb_id)
        film = vote.film
        vote.delete()
        
        # Create activity record
        Activity.objects.create(
            user=request.user,
            activity_type='vote',
            film=film,
            description=f"Removed vote for film: {film.title}"
        )
        
        # Get updated vote count for the film
        vote_count = film.votes.count()
        
        # If this is an HTMX request
        if request.headers.get('HX-Request'):
            # Check the target to determine the response
            target = request.headers.get('HX-Target', '')
            
            # If the request is from the film detail page
            if target == 'vote-container':
                context = {
                    'film': film,
                    'has_voted': False,
                    'can_vote': True,
                }
                return render(request, 'films_app/partials/vote_removed_response.html', context)
            # If the request is for updating the vote button container
            elif 'vote-button-container' in target:
                # Get user's remaining votes
                _, votes_remaining = get_user_votes_and_remaining(request.user)
                
                # Return the vote button if the user can still vote
                context = {
                    'film': film,
                    'can_vote': votes_remaining > 0,
                }
                response = render(request, 'films_app/partials/vote_button.html', context)
                # Also trigger an update to the vote count
                response.headers['HX-Trigger'] = json.dumps({
                    'filmVoteCountChanged': {
                        'imdb_id': film.imdb_id,
                        'vote_count': vote_count
                    },
                    'updateVoteStatus': True
                })
                return response
            # If the request is for updating the vote count
            elif 'film-vote-count' in target:
                # Trigger an event to update the user's vote status
                response = HttpResponse(f'<div id="film-vote-count-{film.imdb_id}" class="vote-badge">{vote_count} vote{"s" if vote_count != 1 else ""}</div>')
                response.headers['HX-Trigger'] = json.dumps({
                    'filmVoteStatusChanged': {
                        'imdb_id': film.imdb_id,
                        'has_voted': False
                    },
                    'updateVoteStatus': True
                })
                return response
        
        messages.success(request, _('Your vote has been removed.'))
        # Fix the redirect by using reverse() properly
        referer = request.META.get('HTTP_REFERER')
        if referer:
            return redirect(referer)
        else:
            return redirect('films_app:film_detail', imdb_id=imdb_id)
        
    except Vote.DoesNotExist:
        messages.error(request, _('Vote not found.'))
        return redirect('films_app:film_detail', imdb_id=imdb_id)


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
        total_votes=Count('votes')
    ).order_by('-total_votes')[:10]
    
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
        total_votes=Count('votes')
    ).filter(
        total_votes__gt=0,
        profile__dashboard_activity_privacy='public'  # Only include users who have set their dashboard activity to public
    ).order_by('-total_votes')[:5]
    
    active_users_data = []
    for i, user in enumerate(active_users):
        active_users_data.append({
            'user': user,
            'vote_count': user.total_votes,
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
    films_query = Film.objects.annotate(total_votes=Count('votes')).filter(total_votes__gt=0)
    
    # Apply time period filter if needed
    if start_date:
        films_query = films_query.filter(votes__created_at__gte=start_date).annotate(
            period_vote_count=Count('votes', filter=Q(votes__created_at__gte=start_date))
        ).filter(period_vote_count__gt=0).order_by('-period_vote_count')
    else:
        films_query = films_query.order_by('-total_votes')
    
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
    users_query = users_query.annotate(total_votes=Count('votes'))
    
    # Filter to only include users with votes
    users_query = users_query.filter(total_votes__gt=0)
    
    # Order by vote count
    users_query = users_query.order_by('-total_votes')
    
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
            'total_votes': user.total_votes,
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
    
    # Get all films from votes and count genres
    films = (Film.objects.filter(votes__in=votes_queryset)
            .distinct()
            .values_list('genres', flat=True))
    
    # Count genres (including approved user tags)
    for genres in films:
        if genres:
            for genre in genres.split(', '):
                genre_counts[genre] = genre_counts.get(genre, 0) + 1
    
    # Sort by count (descending) and return top 10
    sorted_genres = dict(sorted(
        genre_counts.items(),
        key=lambda item: item[1],
        reverse=True
    )[:10])
    
    return sorted_genres


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
    return films.annotate(total_votes=Count('votes')).order_by('-total_votes')

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
@staff_member_required
def update_film_from_tmdb(request, imdb_id):
    """Update film information from TMDB API. Admin only."""
    try:
        # Check if this is a numeric ID (likely a TMDB ID without the prefix)
        if imdb_id.isdigit():
            # Convert to tmdb-prefixed format
            imdb_id = f"tmdb-{imdb_id}"
        
        # Get the original film data before update
        try:
            original_film = Film.objects.get(imdb_id=imdb_id)
            original_data = {
                'title': original_film.title,
                'year': original_film.year,
                'director': original_film.director,
                'plot': original_film.plot,
                'genres': original_film.genres,
                'runtime': original_film.runtime,
                'actors': original_film.actors,
                'uk_certification': original_film.uk_certification,
                'uk_release_date': original_film.uk_release_date,
                'poster_url': original_film.poster_url,
                'popularity': original_film.popularity
            }
        except Film.DoesNotExist:
            original_data = {}
        
        # Get the raw TMDB data first
        from .tmdb_api import get_movie_by_imdb_id
        raw_tmdb_data = get_movie_by_imdb_id(imdb_id, include_raw=True)
            
        # Fetch or update film from TMDB with force_update=True
        film, _ = fetch_and_update_film_from_tmdb(imdb_id, force_update=True)
        
        # Get the updated film data
        updated_data = {
            'title': film.title,
            'year': film.year,
            'director': film.director,
            'plot': film.plot,
            'genres': film.genres,
            'runtime': film.runtime,
            'actors': film.actors,
            'uk_certification': film.uk_certification,
            'uk_release_date': film.uk_release_date,
            'poster_url': film.poster_url,
            'popularity': film.popularity
        }
        
        # Determine what fields were updated
        changes = {}
        for key, new_value in updated_data.items():
            old_value = original_data.get(key)
            if old_value != new_value:
                changes[key] = {'old': old_value, 'new': new_value}
        
        # Render the update results template
        context = {
            'film': film,
            'changes': changes,
            'original_data': original_data,
            'updated_data': updated_data,
            'raw_tmdb_data': raw_tmdb_data
        }
        
        if request.headers.get('HX-Request'):
            # If it's an HTMX request, return just the update results partial
            html = render_to_string('films_app/partials/film_update_results.html', context, request=request)
            return HttpResponse(html)
        else:
            # Otherwise, show a success message and redirect to the film detail page
            messages.success(request, f"Successfully updated '{film.title}' with the latest information from TMDB. {len(changes)} fields were updated.")
            return render(request, 'films_app/film_update_results.html', context)
            
    except ValueError as e:
        messages.error(request, str(e))
        return redirect('films_app:film_detail', imdb_id=imdb_id)


@login_required
def get_user_cinema_votes(request):
    """Get the user's cinema votes for AJAX updates."""
    user_cinema_votes = CinemaVote.objects.filter(user=request.user).select_related('film')
    
    return render(request, 'films_app/partials/user_cinema_votes.html', {
        'user_cinema_votes': user_cinema_votes
    })

def get_film_vote_count(request, imdb_id):
    """Get the vote count for a film in JSON format."""
    try:
        film = Film.objects.get(imdb_id=imdb_id)
        vote_count = film.cinema_votes.count()
        has_voted = False
        
        if request.user.is_authenticated:
            has_voted = film.cinema_votes.filter(user=request.user).exists()
        
        data = {
            'count': vote_count,
            'has_voted': has_voted
        }
        
        return JsonResponse(data)
    except Film.DoesNotExist:
        return JsonResponse({'error': 'Film not found'}, status=404)

def get_film_vote_status(request, imdb_id):
    """Get the vote status for a film in JSON format."""
    try:
        film = Film.objects.get(imdb_id=imdb_id)
        vote_count = film.cinema_votes.count()
        has_voted = False
        
        if request.user.is_authenticated:
            has_voted = film.cinema_votes.filter(user=request.user).exists()
        
        data = {
            'count': vote_count,
            'has_voted': has_voted
        }
        
        return JsonResponse(data)
    except Film.DoesNotExist:
        return JsonResponse({'error': 'Film not found'}, status=404)

@login_required
def get_user_vote_status(request):
    """Get the user's vote status for the vote counter in the navbar."""
    user_votes, votes_remaining = get_user_votes_and_remaining(request.user)
    context = {
        'user_votes': user_votes,
        'votes_remaining': votes_remaining,
    }
    return render(request, 'films_app/partials/user_vote_status.html', context)

@login_required
def check_vote_exists(request, imdb_id):
    """Check if a vote exists for a given film IMDb ID."""
    vote_exists = Vote.objects.filter(user=request.user, film__imdb_id=imdb_id).exists()
    return JsonResponse({'exists': vote_exists})

@login_required
def get_vote_button(request, imdb_id):
    """Get the vote button for a film."""
    try:
        film = Film.objects.get(imdb_id=imdb_id)
        
        # Check if the user has already voted for this film
        vote = Vote.objects.filter(
            user=request.user,
            film=film
        ).first()
        
        if vote:
            return render(
                request,
                'films_app/partials/remove_vote_button.html',
                {'vote': vote, 'film': film}
            )
        
        # Check if the user can vote
        _, votes_remaining = get_user_votes_and_remaining(request.user)
        return render(
            request,
            'films_app/partials/vote_button.html',
            {'film': film, 'can_vote': votes_remaining > 0}
        )
    except Film.DoesNotExist:
        return HttpResponse("Film not found", status=404)

def get_top_films_partial(request):
    """Get the top films partial HTML."""
    return render(
        request,
        'films_app/partials/top_films.html',
        {'top_films': get_top_films_data()}
    )


@login_required
def get_cinema_vote_status(request):
    """Get the user's cinema vote status."""
    user_cinema_votes = (CinemaVote.objects
                        .filter(user=request.user)
                        .select_related('film'))
    cinema_votes_remaining = 3 - user_cinema_votes.count()
    
    return render(
        request,
        'films_app/partials/user_cinema_vote_status.html',
        {
            'user_cinema_votes': user_cinema_votes,
            'cinema_votes_remaining': cinema_votes_remaining
        }
    )


@staff_member_required
def update_cinema_cache(request):
    """Update the cinema cache with current and upcoming UK releases."""
    logger = logging.getLogger(__name__)
    
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    
    # Capture command output
    output = StringIO()
    sys.stdout = output
    
    try:
        # Clean up cache files before updating
        logger.info("Cleaning up cache files before update")
        cleanup_output = cleanup_cache_files()
        
        # First run the update_release_status command to flag films that need checking
        logger.info("Running update_release_status command to flag films for status checks")
        call_command(
            'update_release_status',
            days=7,
            batch_size=50,
            use_parallel=True
        )
        
        # Run the management command with optimized parameters
        logger.info("Starting cinema cache update with optimized parameters")
        call_command(
            'update_movie_cache',
            force=True,
            max_pages=2,         # Limited to 2 pages for web UI to avoid timeouts
            batch_size=15,       # Increased batch size for better performance
            batch_delay=1,       # Reduced delay between batches
            prioritize_flags=True,
            time_window_months=6, # 6 months for upcoming films
            use_parallel=True     # Enable parallel processing
        )
        
        result = f"{cleanup_output}\n\n{output.getvalue()}"
        status = 'success'
        logger.info("Cinema cache update completed successfully")
    except Exception as e:
        result = f"Error: {str(e)}"
        status = 'error'
        logger.error(f"Cinema cache update failed: {str(e)}")
    finally:
        sys.stdout = sys.__stdout__
    
    # Get the last update timestamp
    last_update = None
    try:
        latest_tracker = PageTracker.objects.order_by('-last_updated').first()
        if latest_tracker:
            last_update = latest_tracker.last_updated
    except Exception as e:
        logger.error(f"Error getting last update timestamp: {str(e)}")
    
    template = (
        'films_app/partials/cache_update_success.html'
        if status == 'success'
        else 'films_app/partials/cache_update_error.html'
    )
    
    return render(request, template, {
        'output': result.replace('\n', '<br>'),
        'last_update': last_update
    })

def cleanup_cache_files():
    """Clean up all JSON cache files to ensure fresh data."""
    import logging
    import glob
    import os
    from films_app.utils import get_cache_directory
    
    logger = logging.getLogger(__name__)
    output = "Cleaning up cache files...\n"
    
    # Get cache directory
    cache_dir = get_cache_directory()
    
    # Find all JSON files in the cache directory
    json_files = glob.glob(os.path.join(cache_dir, "*.json"))
    
    # Keep track of how many files were deleted
    deleted_count = 0
    
    # Delete all JSON files except for cache_info.json and cinema_cache_info.json
    for file_path in json_files:
        file_name = os.path.basename(file_path)
        
        # Skip cache info files
        if file_name in ['cache_info.json', 'cinema_cache_info.json']:
            continue
        
        try:
            os.remove(file_path)
            deleted_count += 1
            output += f"Deleted cache file: {file_name}\n"
        except Exception as e:
            output += f"Error deleting cache file {file_name}: {str(e)}\n"
    
    output += f"Cleaned up {deleted_count} cache files\n"
    return output

def filter_cinema_films(request):
    """Filter cinema films by title."""
    from django.db.models import Q
    from django.conf import settings
    
    query = request.GET.get('query', '').strip()
    today = timezone.now().date()
    
    # Get pagination parameters
    now_playing_page = request.GET.get('now_playing_page', 1)
    upcoming_page = request.GET.get('upcoming_page', 1)
    section = request.GET.get('section', 'both')  # 'now_playing', 'upcoming', or 'both'
    
    # Base filters for now playing and upcoming
    now_playing_filter = Q(
        is_in_cinema=True, 
        uk_release_date__lte=today
    )
    
    # For upcoming films, use the is_upcoming flag
    upcoming_filter = Q(
        is_upcoming=True
    )
    
    # Add title filter if query is provided
    if query:
        now_playing_filter &= Q(title__icontains=query)
        upcoming_filter &= Q(title__icontains=query)
    
    # Get filtered films
    now_playing_films = Film.objects.filter(now_playing_filter).order_by('-popularity')
    upcoming_films = Film.objects.filter(upcoming_filter).order_by('uk_release_date')
    
    # Get pagination settings
    # If user is authenticated and has a custom pagination setting, use that
    films_per_page = 8  # Default value
    if request.user.is_authenticated:
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            if user_profile.films_per_page:
                films_per_page = user_profile.films_per_page
        except UserProfile.DoesNotExist:
            # Use the default from settings
            films_per_page = getattr(settings, 'FILMS_PER_PAGE', 8)
    else:
        # Use the default from settings
        films_per_page = getattr(settings, 'FILMS_PER_PAGE', 8)
    
    # Apply pagination
    now_playing_paginator = Paginator(now_playing_films, films_per_page)
    upcoming_paginator = Paginator(upcoming_films, films_per_page)
    
    # Get the appropriate page for each section
    if section == 'now_playing' or section == 'both':
        try:
            now_playing_page_obj = now_playing_paginator.page(now_playing_page)
        except PageNotAnInteger:
            now_playing_page_obj = now_playing_paginator.page(1)
        except EmptyPage:
            now_playing_page_obj = now_playing_paginator.page(now_playing_paginator.num_pages)
    else:
        now_playing_page_obj = []
    
    if section == 'upcoming' or section == 'both':
        try:
            upcoming_page_obj = upcoming_paginator.page(upcoming_page)
        except PageNotAnInteger:
            upcoming_page_obj = upcoming_paginator.page(1)
        except EmptyPage:
            upcoming_page_obj = upcoming_paginator.page(upcoming_paginator.num_pages)
    else:
        upcoming_page_obj = []
    
    # Get total counts
    total_now_playing = now_playing_paginator.count
    total_upcoming = upcoming_paginator.count
    
    # Get user's cinema votes if authenticated
    user_cinema_votes = []
    user_voted_films = []
    if request.user.is_authenticated:
        user_cinema_votes = CinemaVote.objects.filter(user=request.user).select_related('film')
        user_voted_films = [vote.film.imdb_id for vote in user_cinema_votes]
    
    # Get the time window for upcoming films from settings
    from django.conf import settings
    upcoming_films_months = getattr(settings, 'UPCOMING_FILMS_MONTHS', 6)
    
    context = {
        'now_playing_films': now_playing_page_obj,
        'upcoming_films': upcoming_page_obj,
        'total_now_playing': total_now_playing,
        'total_upcoming': total_upcoming,
        'upcoming_films_months': upcoming_films_months,
        'user_cinema_votes': user_cinema_votes,
        'user_voted_films': user_voted_films,
        'query': query,
        'section': section,
        'now_playing_page': int(now_playing_page) if str(now_playing_page).isdigit() else 1,
        'upcoming_page': int(upcoming_page) if str(upcoming_page).isdigit() else 1,
        'now_playing_has_previous': now_playing_page_obj.has_previous() if hasattr(now_playing_page_obj, 'has_previous') else False,
        'now_playing_has_next': now_playing_page_obj.has_next() if hasattr(now_playing_page_obj, 'has_next') else False,
        'now_playing_previous_page': now_playing_page_obj.previous_page_number() if hasattr(now_playing_page_obj, 'has_previous') and now_playing_page_obj.has_previous() else None,
        'now_playing_next_page': now_playing_page_obj.next_page_number() if hasattr(now_playing_page_obj, 'has_next') and now_playing_page_obj.has_next() else None,
        'now_playing_num_pages': now_playing_paginator.num_pages,
        'upcoming_has_previous': upcoming_page_obj.has_previous() if hasattr(upcoming_page_obj, 'has_previous') else False,
        'upcoming_has_next': upcoming_page_obj.has_next() if hasattr(upcoming_page_obj, 'has_next') else False,
        'upcoming_previous_page': upcoming_page_obj.previous_page_number() if hasattr(upcoming_page_obj, 'has_previous') and upcoming_page_obj.has_previous() else None,
        'upcoming_next_page': upcoming_page_obj.next_page_number() if hasattr(upcoming_page_obj, 'has_next') and upcoming_page_obj.has_next() else None,
        'upcoming_num_pages': upcoming_paginator.num_pages,
        'films_per_page': films_per_page,  # Add this to the context
    }
    
    return render(request, 'films_app/partials/cinema_films.html', context)

def get_top_genres(votes_queryset, limit=10):
    """Get the top genres from a queryset of votes."""
    # Get all films from the votes
    film_ids = votes_queryset.values_list('film_id', flat=True)
    films = Film.objects.filter(id__in=film_ids)
    
    # Count genres
    genre_counts = {}
    for film in films:
        for genre in film.genre_list:
            if genre in genre_counts:
                genre_counts[genre] += 1
            else:
                genre_counts[genre] = 1
    
    # Sort by count (descending)
    sorted_genres = dict(sorted(genre_counts.items(), key=lambda item: item[1], reverse=True))
    
    # Return top 10 genres
    return dict(list(sorted_genres.items())[:limit])

@login_required
def commitment_filter(request):
    """View for filtering films by commitment level."""
    # Get filter parameters
    min_score = request.GET.get('min_score', 1)
    min_votes = request.GET.get('min_votes', 1)
    
    # Format preferences
    format_standard = request.GET.get('format_standard') == 'on'
    format_imax = request.GET.get('format_imax') == 'on'
    format_3d = request.GET.get('format_3d') == 'on'
    format_premium = request.GET.get('format_premium') == 'on'
    
    # Social preferences
    social_solo = request.GET.get('social_solo') == 'on'
    social_partner = request.GET.get('social_partner') == 'on'
    social_friends = request.GET.get('social_friends') == 'on'
    social_family = request.GET.get('social_family') == 'on'
    social_open = request.GET.get('social_open') == 'on'
    
    # Convert to float/int
    try:
        min_score = float(min_score)
        min_votes = int(min_votes)
    except (ValueError, TypeError):
        min_score = 1.0
        min_votes = 1
    
    # Get all films with votes
    films_with_votes = Film.objects.annotate(total_votes=Count('votes')).filter(total_votes__gte=min_votes)
    
    # Filter by commitment score
    filtered_films = []
    for film in films_with_votes:
        metrics = film.commitment_metrics
        
        # Skip if not enough votes or commitment score is too low
        if metrics['total'] < min_votes or metrics['commitment_score'] < min_score:
            continue
        
        # Check format preferences if any are selected
        if any([format_standard, format_imax, format_3d, format_premium]):
            format_prefs = film.format_preferences
            format_match = False
            
            if format_standard and format_prefs['standard'] > 0:
                format_match = True
            elif format_imax and format_prefs['imax'] > 0:
                format_match = True
            elif format_3d and format_prefs['3d'] > 0:
                format_match = True
            elif format_premium and format_prefs['premium'] > 0:
                format_match = True
            
            if not format_match:
                continue
        
        # Check social preferences if any are selected
        if any([social_solo, social_partner, social_friends, social_family, social_open]):
            social_prefs = film.social_preferences
            social_match = False
            
            if social_solo and social_prefs['solo'] > 0:
                social_match = True
            elif social_partner and social_prefs['partner'] > 0:
                social_match = True
            elif social_friends and social_prefs['friends'] > 0:
                social_match = True
            elif social_family and social_prefs['family'] > 0:
                social_match = True
            elif social_open and social_prefs['open'] > 0:
                social_match = True
            
            if not social_match:
                continue
        
        # If we got here, the film matches all criteria
        filtered_films.append(film)
    
    # Sort by commitment score (highest first)
    filtered_films.sort(key=lambda x: x.commitment_metrics['commitment_score'], reverse=True)
    
    context = {
        'films': filtered_films,
        'min_score': min_score,
        'min_votes': min_votes,
        'format_standard': format_standard,
        'format_imax': format_imax,
        'format_3d': format_3d,
        'format_premium': format_premium,
        'social_solo': social_solo,
        'social_partner': social_partner,
        'social_friends': social_friends,
        'social_family': social_family,
        'social_open': social_open,
    }
    
    return render(request, 'films_app/commitment_filter.html', context)

@login_required
def cinema_preferences(request):
    """View for managing cinema preferences."""
    user = request.user
    user_cinemas = CinemaPreference.objects.filter(user=user).select_related('cinema')
    
    # Search parameters
    search_query = request.GET.get('search', '')
    has_imax = request.GET.get('has_imax') == 'on'
    has_3d = request.GET.get('has_3d') == 'on'
    has_premium_seating = request.GET.get('has_premium_seating') == 'on'
    has_food_service = request.GET.get('has_food_service') == 'on'
    has_bar = request.GET.get('has_bar') == 'on'
    
    # Search for cinemas
    search_results = None
    if search_query or has_imax or has_3d or has_premium_seating or has_food_service or has_bar:
        search_results = Cinema.objects.all()
        
        if search_query:
            search_results = search_results.filter(
                Q(name__icontains=search_query) | 
                Q(chain__icontains=search_query) | 
                Q(location__icontains=search_query) |
                Q(postcode__icontains=search_query)
            )
        
        # Apply amenity filters
        if has_imax:
            search_results = search_results.filter(has_imax=True)
        if has_3d:
            search_results = search_results.filter(has_3d=True)
        if has_premium_seating:
            search_results = search_results.filter(has_premium_seating=True)
        if has_food_service:
            search_results = search_results.filter(has_food_service=True)
        if has_bar:
            search_results = search_results.filter(has_bar=True)
        
        # Exclude cinemas the user already has preferences for
        user_cinema_ids = user_cinemas.values_list('cinema_id', flat=True)
        search_results = search_results.exclude(id__in=user_cinema_ids)
        
        # Paginate results
        paginator = Paginator(search_results, 10)
        page = request.GET.get('page')
        search_results = paginator.get_page(page)
    
    context = {
        'user_cinemas': user_cinemas,
        'search_results': search_results,
        'search_query': search_query,
        'has_imax': has_imax,
        'has_3d': has_3d,
        'has_premium_seating': has_premium_seating,
        'has_food_service': has_food_service,
        'has_bar': has_bar,
    }
    
    return render(request, 'films_app/cinema_preferences.html', context)

@login_required
def add_cinema_preference(request, cinema_id):
    """Add a cinema to user's preferences."""
    if request.method == 'POST':
        user = request.user
        try:
            cinema = Cinema.objects.get(id=cinema_id)
            
            # Check if preference already exists
            preference, created = CinemaPreference.objects.get_or_create(
                user=user,
                cinema=cinema,
                defaults={'is_favorite': False}
            )
            
            if created:
                messages.success(request, _('Cinema added to your preferences.'))
            else:
                messages.info(request, _('This cinema is already in your preferences.'))
                
        except Cinema.DoesNotExist:
            messages.error(request, _('Cinema not found.'))
    
    return redirect('films_app:cinema_preferences')

@login_required
def remove_cinema_preference(request, cinema_id):
    """Remove a cinema from user's preferences."""
    if request.method == 'POST':
        user = request.user
        try:
            preference = CinemaPreference.objects.get(user=user, cinema_id=cinema_id)
            preference.delete()
            messages.success(request, _('Cinema removed from your preferences.'))
        except CinemaPreference.DoesNotExist:
            messages.error(request, _('Cinema preference not found.'))
    
    return redirect('films_app:cinema_preferences')

@login_required
def toggle_favorite_cinema(request, cinema_id):
    """Toggle favorite status for a cinema."""
    if request.method == 'POST':
        user = request.user
        try:
            preference = CinemaPreference.objects.get(user=user, cinema_id=cinema_id)
            preference.is_favorite = not preference.is_favorite
            preference.save()
            
            if preference.is_favorite:
                messages.success(request, _('Cinema added to favorites.'))
            else:
                messages.success(request, _('Cinema removed from favorites.'))
                
        except CinemaPreference.DoesNotExist:
            messages.error(request, _('Cinema preference not found.'))
    
    return redirect('films_app:cinema_preferences')

@login_required
def add_new_cinema(request):
    """Add a new cinema to the database and user's preferences."""
    if request.method == 'POST':
        user = request.user
        
        # Get form data
        name = request.POST.get('name')
        chain = request.POST.get('chain')
        location = request.POST.get('location')
        postcode = request.POST.get('postcode')
        website = request.POST.get('website')
        
        # Get amenities
        has_imax = request.POST.get('has_imax') == 'on'
        has_3d = request.POST.get('has_3d') == 'on'
        has_premium_seating = request.POST.get('has_premium_seating') == 'on'
        has_food_service = request.POST.get('has_food_service') == 'on'
        has_bar = request.POST.get('has_bar') == 'on'
        has_disabled_access = request.POST.get('has_disabled_access') == 'on'
        
        # Get favorite status
        is_favorite = request.POST.get('is_favorite') == 'on'
        
        # Validate required fields
        if not name or not location:
            messages.error(request, _('Cinema name and location are required.'))
            return redirect('films_app:cinema_preferences')
        
        # Create or get the cinema
        cinema, created = Cinema.objects.get_or_create(
            name=name,
            location=location,
            postcode=postcode,
            defaults={
                'chain': chain,
                'website': website,
                'has_imax': has_imax,
                'has_3d': has_3d,
                'has_premium_seating': has_premium_seating,
                'has_food_service': has_food_service,
                'has_bar': has_bar,
                'has_disabled_access': has_disabled_access,
            }
        )
        
        if not created:
            # Update existing cinema
            cinema.chain = chain
            cinema.website = website
            cinema.has_imax = has_imax
            cinema.has_3d = has_3d
            cinema.has_premium_seating = has_premium_seating
            cinema.has_food_service = has_food_service
            cinema.has_bar = has_bar
            cinema.has_disabled_access = has_disabled_access
            cinema.save()
        
        # Create or update preference
        preference, pref_created = CinemaPreference.objects.get_or_create(
            user=user,
            cinema=cinema,
            defaults={'is_favorite': is_favorite}
        )
        
        if not pref_created:
            preference.is_favorite = is_favorite
            preference.save()
        
        if created:
            messages.success(request, _('New cinema added to your preferences.'))
        else:
            messages.success(request, _('Existing cinema added to your preferences.'))
    
    return redirect('films_app:cinema_preferences')

@login_required
def update_travel_distance(request):
    """Update user's travel distance preference."""
    if request.method == 'POST':
        user = request.user
        travel_distance = request.POST.get('travel_distance')
        
        try:
            travel_distance = int(travel_distance)
            if travel_distance < 1:
                travel_distance = 1
            elif travel_distance > 50:
                travel_distance = 50
                
            user.profile.travel_distance = travel_distance
            user.profile.save()
            
            messages.success(request, _('Travel distance updated.'))
            
        except (ValueError, TypeError):
            messages.error(request, _('Invalid travel distance.'))
    
    return redirect('films_app:cinema_preferences')

# Helper function for vote achievements
def check_vote_achievements(user):
    """Check and award vote-related achievements."""
    vote_count = Vote.objects.filter(user=user).count()
    
    # Check for first vote achievement
    if vote_count == 1:
        Achievement.objects.get_or_create(
            user=user,
            achievement_type='first_vote'
        )
    
    # Check for 10 votes achievement
    if vote_count >= 10:
        Achievement.objects.get_or_create(
            user=user,
            achievement_type='ten_votes'
        )
    
    # Check for 50 votes achievement
    if vote_count >= 50:
        Achievement.objects.get_or_create(
            user=user,
            achievement_type='fifty_votes'
        )

@login_required
def cinema_vote(request, imdb_id):
    """Add a cinema vote for a film."""
    if request.method != 'POST':
        return HttpResponse(
            "Method not allowed. Expected POST.",
            status=405
        )
    
    try:
        film = Film.objects.get(imdb_id=imdb_id)
        
        # Check if user has already voted for this film
        existing_vote = (CinemaVote.objects
                        .filter(user=request.user, film=film)
                        .exists())
        if existing_vote:
            return HttpResponse(
                "You have already voted for this film.",
                status=400
            )
        
        # Check if user has reached the maximum number of votes
        user_cinema_votes_count = (CinemaVote.objects
                                 .filter(user=request.user)
                                 .count())
        if user_cinema_votes_count >= 3:
            return HttpResponse(
                "You have reached the maximum number of cinema votes (3).",
                status=400
            )
        
        # Create the vote
        vote = CinemaVote.objects.create(
            user=request.user,
            film=film,
            commitment_level='interested',
            preferred_format='any',
            social_preference='undecided'
        )
        
        # Get updated vote count and user's cinema votes
        vote_count = film.cinema_votes.count()
        user_cinema_votes = (CinemaVote.objects
                           .filter(user=request.user)
                           .select_related('film'))
        
        # Create activity record
        Activity.objects.create(
            user=request.user,
            activity_type='vote',
            film=film,
            description=f"Voted for cinema film: {film.title}"
        )
        
        context = {
            'film': film,
            'vote': vote,
            'vote_count': vote_count,
            'user_cinema_votes': user_cinema_votes,
        }
        
        return render(
            request,
            'films_app/partials/cinema_vote_success.html',
            context
        )
    
    except Film.DoesNotExist:
        return HttpResponse("Film not found.", status=404)
    except Exception as e:
        return HttpResponse(f"An error occurred: {str(e)}", status=500)


@login_required
def remove_cinema_vote(request, imdb_id):
    """Remove a cinema vote for a film."""
    if request.method != 'POST':
        return HttpResponse(
            "Method not allowed. Expected POST.",
            status=405
        )
    
    if not request.user.is_authenticated:
        return HttpResponse(
            "You must be logged in to remove a vote.",
            status=401
        )
    
    try:
        film = Film.objects.get(imdb_id=imdb_id)
        
        # Check if user has voted for this film
        vote = (CinemaVote.objects
               .filter(user=request.user, film=film)
               .first())
        if not vote:
            return HttpResponse(
                "You have not voted for this film.",
                status=400
            )
        
        # Remove the vote
        vote.delete()
        
        # Get updated vote count and user's cinema votes
        vote_count = film.cinema_votes.count()
        user_cinema_votes = (CinemaVote.objects
                           .filter(user=request.user)
                           .select_related('film'))
        cinema_votes_remaining = 3 - user_cinema_votes.count()
        
        # Create activity record
        Activity.objects.create(
            user=request.user,
            activity_type='vote',
            film=film,
            description=f"Removed vote for cinema film: {film.title}"
        )
        
        context = {
            'film': film,
            'vote_count': vote_count,
            'user_cinema_votes': user_cinema_votes,
            'cinema_votes_remaining': cinema_votes_remaining,
        }
        
        return render(
            request,
            'films_app/partials/cinema_vote_removed_response.html',
            context
        )
    
    except Film.DoesNotExist:
        return HttpResponse("Film not found.", status=404)
    except Exception as e:
        return HttpResponse(f"An error occurred: {str(e)}", status=500)