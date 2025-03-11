from django import template
from django.utils.safestring import mark_safe
import re
import json

register = template.Library()

@register.simple_tag
def display_period(period):
    """
    Display a human-readable time period.
    
    Args:
        period (str): The time period code ('all', 'year', 'month', 'week')
        
    Returns:
        str: Human-readable time period
    """
    period_map = {
        'all': 'All Time',
        'year': 'Past Year',
        'month': 'Past Month',
        'week': 'Past Week'
    }
    
    return period_map.get(period, 'Unknown Period')

@register.filter
def has_user_voted(cinema_votes, user_id):
    """
    Check if a user has voted for a film.
    
    Args:
        cinema_votes: The cinema_votes queryset for a film
        user_id: The user ID to check
        
    Returns:
        bool: True if the user has voted for the film, False otherwise
    """
    return cinema_votes.filter(user_id=user_id).exists()

@register.filter
def get_vote_by_imdb_id(votes, imdb_id):
    """Get a vote by imdb_id from a list of votes."""
    for vote in votes:
        if vote.film.imdb_id == imdb_id:
            return vote
    return None

@register.filter
def pprint(value):
    """Pretty print a Python object as JSON."""
    try:
        # Convert to a formatted JSON string
        formatted_json = json.dumps(value, indent=2, sort_keys=True, default=str)
        # Make it safe for HTML display
        return mark_safe(formatted_json)
    except Exception as e:
        return f"Error formatting data: {str(e)}"

@register.filter
def get_page_range(num_pages, current_page):
    """
    Generate a range of page numbers for pagination.
    Shows current page, 2 pages before and after, and first/last pages.
    """
    current_page = int(current_page)
    num_pages = int(num_pages)
    
    if num_pages <= 7:
        # If there are 7 or fewer pages, show all
        return range(1, num_pages + 1)
    
    # Always include first and last page
    pages = [1, num_pages]
    
    # Add the current page and 2 pages before and after
    for i in range(max(2, current_page - 2), min(current_page + 3, num_pages)):
        pages.append(i)
    
    # Sort the pages
    pages = sorted(list(set(pages)))
    
    # Add ellipses where needed
    result = []
    prev = 0
    for page in pages:
        if prev + 1 < page:
            result.append('...')
        result.append(page)
        prev = page
    
    return result

@register.filter
def get_mobile_page_range(num_pages, current_page):
    """
    Generate a mobile-friendly range of page numbers for pagination.
    Shows only current page, previous/next, and first/last pages.
    """
    current_page = int(current_page)
    num_pages = int(num_pages)
    
    if num_pages <= 3:
        # If there are 3 or fewer pages, show all
        return range(1, num_pages + 1)
    
    # Always include first, current, and last page
    pages = [1]
    
    # Add previous and next page if they exist
    if current_page > 1:
        pages.append(current_page - 1)
    
    pages.append(current_page)
    
    if current_page < num_pages:
        pages.append(current_page + 1)
    
    if num_pages > 1:
        pages.append(num_pages)
    
    # Sort the pages and remove duplicates
    pages = sorted(list(set(pages)))
    
    # Add ellipses where needed
    result = []
    prev = 0
    for page in pages:
        if prev + 1 < page:
            result.append('...')
        result.append(page)
        prev = page
    
    return result 