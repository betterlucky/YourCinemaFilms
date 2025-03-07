import re

# List of common profanity words to filter
# This is a basic list - in a production environment, you would use a more comprehensive list
# or a dedicated profanity filter library
PROFANITY_LIST = [
    'ass', 'asshole', 'bastard', 'bitch', 'bollocks', 'bullshit',
    'cock', 'crap', 'cunt', 'damn', 'dick', 'douche', 'fag', 'faggot',
    'fuck', 'fucking', 'motherfucker', 'nigger', 'piss', 'pussy',
    'shit', 'slut', 'twat', 'wanker', 'whore'
]

def contains_profanity(text):
    """
    Check if the given text contains profanity.
    
    Args:
        text (str): The text to check for profanity
        
    Returns:
        bool: True if profanity is found, False otherwise
    """
    if not text:
        return False
    
    # Convert to lowercase for case-insensitive matching
    text_lower = text.lower()
    
    # Check for exact matches and word boundaries
    for word in PROFANITY_LIST:
        pattern = r'\b' + re.escape(word) + r'\b'
        if re.search(pattern, text_lower):
            return True
    
    return False

def filter_profanity(text):
    """
    Replace profanity in the given text with asterisks.
    
    Args:
        text (str): The text to filter
        
    Returns:
        str: The filtered text with profanity replaced by asterisks
    """
    if not text:
        return text
    
    # Convert to lowercase for case-insensitive matching
    text_lower = text.lower()
    result = text
    
    # Replace profanity with asterisks
    for word in PROFANITY_LIST:
        pattern = r'\b' + re.escape(word) + r'\b'
        matches = re.finditer(pattern, text_lower)
        
        # Process matches in reverse order to avoid index issues
        for match in reversed(list(matches)):
            start, end = match.span()
            replacement = '*' * (end - start)
            result = result[:start] + replacement + result[end:]
    
    return result

def validate_genre_tag(tag):
    """
    Validate a genre tag:
    - No profanity
    - Length between 2 and 50 characters
    - Only alphanumeric characters, spaces, and hyphens
    
    Args:
        tag (str): The genre tag to validate
        
    Returns:
        tuple: (is_valid, error_message)
    """
    # Check for empty tag
    if not tag or not tag.strip():
        return False, "Genre tag cannot be empty"
    
    # Check length
    if len(tag) < 2:
        return False, "Genre tag must be at least 2 characters long"
    
    if len(tag) > 50:
        return False, "Genre tag must be at most 50 characters long"
    
    # Check for valid characters
    if not re.match(r'^[A-Za-z0-9\s\-]+$', tag):
        return False, "Genre tag can only contain letters, numbers, spaces, and hyphens"
    
    # Check for profanity
    if contains_profanity(tag):
        return False, "Genre tag contains inappropriate language"
    
    return True, "" 