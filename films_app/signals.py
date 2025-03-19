from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.contrib.auth.signals import user_logged_in
from allauth.socialaccount.models import SocialAccount
from films_app.models import UserProfile
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Create a UserProfile instance for all newly created User instances.
    """
    if created:
        UserProfile.objects.create(user=instance)
        logger.info(f"Created profile for new user: {instance.username}")

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """
    Save the UserProfile instance whenever the User instance is saved.
    """
    # Check if profile exists using a query
    profile, created = UserProfile.objects.get_or_create(user=instance)
    if not created:
        profile.save()

@receiver(user_logged_in)
def update_profile_on_login(sender, request, user, **kwargs):
    """
    Update basic user information when they log in.
    """
    logger.info(f"User {user.username} logged in")
    
    # Store Google account ID and email if available
    social_accounts = user.socialaccount_set.filter(provider='google')
    if social_accounts.exists():
        google_account = social_accounts.first()
        profile = user.profile
        
        # Track if changes were made
        changes_made = False
        
        # Store the Google account ID if not already set
        if not profile.google_account_id:
            profile.google_account_id = google_account.uid
            logger.info(f"Stored Google account ID: {google_account.uid}")
            changes_made = True
        
        # Store Google email if available and not already set
        if 'email' in google_account.extra_data and not profile.google_email:
            profile.google_email = google_account.extra_data['email']
            logger.info(f"Stored Google email: {profile.google_email}")
            changes_made = True
            
        # Save the profile if changes were made
        if changes_made:
            profile.save()
            logger.info(f"Saved profile for user {user.username} after login") 