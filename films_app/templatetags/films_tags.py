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