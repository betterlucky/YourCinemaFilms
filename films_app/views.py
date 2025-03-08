import json
import requests
from datetime import datetime, timedelta
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

from .models import Film, Vote, UserProfile, GenreTag
from .utils import validate_genre_tag, fetch_and_update_film_from_omdb


def home(request):
    """Home page view."""
    try:
        # Get top 10 films based on votes
        top_films = Film.objects.annotate(vote_count=Count('votes')).order_by('-vote_count')[:10]
        
        context = {
            'top_films': top_films,
        }
        
        if request.user.is_authenticated:
            # Get user's votes
            user_votes = Vote.objects.filter(user=request.user).select_related('film')
            context['user_votes'] = user_votes
            context['votes_remaining'] = 10 - user_votes.count()
        
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
    
    # Get user's votes
    user_votes = Vote.objects.filter(user=request.user).select_related('film')
    
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
        'votes_remaining': 10 - user_votes.count(),
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
        
        # Check if user has voted for this film
        has_voted = False
        user_vote = None
        
        if request.user.is_authenticated:
            user_vote = Vote.objects.filter(user=request.user, film=film).first()
            has_voted = user_vote is not None
        
        # Get vote count
        vote_count = Vote.objects.filter(film=film).count()
        
        # Get user tags for this film
        user_tags = GenreTag.objects.filter(film=film, user=request.user)
        
        # Get all approved tags for this film
        approved_tags = GenreTag.objects.filter(film=film, is_approved=True).exclude(user=request.user)
        
        context = {
            'film': film,
            'has_voted': has_voted,
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
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    # Get or create film
    film = get_object_or_404(Film, imdb_id=imdb_id)
    
    # Check if user has already voted for this film
    existing_vote = Vote.objects.filter(user=request.user, film=film).first()
    if existing_vote:
        return JsonResponse({'message': 'You have already voted for this film'})
    
    # Check if user has reached the maximum number of votes
    user_votes_count = Vote.objects.filter(user=request.user).count()
    if user_votes_count >= 10:
        return JsonResponse({'error': 'You have reached the maximum number of votes (10)'}, status=400)
    
    # Create vote
    vote = Vote(user=request.user, film=film)
    vote.save()
    
    return JsonResponse({'message': 'Vote recorded successfully'})


@login_required
def remove_vote(request, vote_id):
    """Remove a vote."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    vote = get_object_or_404(Vote, id=vote_id, user=request.user)
    vote.delete()
    
    return JsonResponse({'message': 'Vote removed successfully'})


@login_required
def add_genre_tag(request, imdb_id):
    """Add a genre tag to a film."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    # Get film
    film = get_object_or_404(Film, imdb_id=imdb_id)
    
    # Get tag from request
    tag = request.POST.get('tag', '').strip()
    
    # Validate tag
    is_valid, error_message = validate_genre_tag(tag)
    if not is_valid:
        return JsonResponse({'error': error_message}, status=400)
    
    # Capitalize the first letter of each word for consistency
    tag = ' '.join(word.capitalize() for word in tag.split())
    
    # Check if tag already exists for this film and user
    existing_tag = GenreTag.objects.filter(film=film, user=request.user, tag=tag).first()
    if existing_tag:
        return JsonResponse({'error': 'You have already added this genre tag'}, status=400)
    
    # Check if tag is already an official genre
    if tag in film.genre_list:
        return JsonResponse({'error': 'This genre is already listed for this film'}, status=400)
    
    # Create tag (not approved by default)
    genre_tag = GenreTag(film=film, user=request.user, tag=tag)
    genre_tag.save()
    
    return JsonResponse({
        'message': 'Genre tag added successfully. It will be visible after approval.',
        'tag_id': genre_tag.id
    })


@login_required
def remove_genre_tag(request, tag_id):
    """Remove a genre tag."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    # Get tag and check ownership
    tag = get_object_or_404(GenreTag, id=tag_id, user=request.user)
    
    # Delete tag
    tag.delete()
    
    return JsonResponse({'message': 'Genre tag removed successfully'})


@login_required
def manage_genre_tags(request):
    """View for managing user's genre tags."""
    # Get user's tags
    user_tags = GenreTag.objects.filter(user=request.user).select_related('film')
    
    context = {
        'user_tags': user_tags,
    }
    
    return render(request, 'films_app/manage_tags.html', context)


def charts(request):
    """View for displaying charts."""
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
    if start_date:
        votes_query = votes_query.filter(created_at__gte=start_date)
    
    # Get top films
    top_films = Film.objects.filter(votes__in=votes_query).annotate(
        vote_count=Count('votes')
    ).order_by('-vote_count')[:10]
    
    # Prepare data for charts
    labels = [film.title for film in top_films]
    data = [film.vote_count for film in top_films]
    
    # Get genre distribution
    genre_data = get_genre_distribution(votes_query)
    
    context = {
        'period': period,
        'labels': json.dumps(labels),
        'data': json.dumps(data),
        'top_films': top_films,
        'genre_labels': json.dumps(list(genre_data.keys())),
        'genre_data': json.dumps(list(genre_data.values())),
    }
    
    return render(request, 'films_app/charts.html', context)


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


def genre_analysis(request):
    """View for genre analysis."""
    # Get all genres (including approved user tags)
    all_genres = set()
    
    # Get official genres from films
    for film in Film.objects.all():
        all_genres.update(film.genre_list)
    
    # Get approved user tags
    approved_tags = GenreTag.objects.filter(is_approved=True).values_list('tag', flat=True).distinct()
    all_genres.update(approved_tags)
    
    # Sort genres alphabetically
    genres = sorted(list(all_genres))
    
    # Get selected genre
    selected_genre = request.GET.get('genre', '')
    
    # Get films in the selected genre
    films = []
    if selected_genre:
        # Get films with official genre
        official_genre_films = Film.objects.filter(genres__icontains=selected_genre)
        
        # Get films with user tag
        user_tag_films = Film.objects.filter(tags__tag=selected_genre, tags__is_approved=True)
        
        # Combine and remove duplicates
        films = (official_genre_films | user_tag_films).distinct().annotate(
            vote_count=Count('votes')
        ).order_by('-vote_count')
    
    context = {
        'genres': genres,
        'selected_genre': selected_genre,
        'films': films,
    }
    
    return render(request, 'films_app/genre_analysis.html', context)


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