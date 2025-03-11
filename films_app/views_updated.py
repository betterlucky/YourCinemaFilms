def filter_cinema_films(request):
    """Filter cinema films by title."""
    from django.db.models import Q
    
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
    
    # Apply pagination to show a reasonable number of results (10 per page)
    now_playing_paginator = Paginator(now_playing_films, 10)
    upcoming_paginator = Paginator(upcoming_films, 10)
    
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
    }
    
    return render(request, 'films_app/partials/cinema_films.html', context) 