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