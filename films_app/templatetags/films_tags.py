from django import template

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