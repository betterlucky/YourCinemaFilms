from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.account.adapter import DefaultAccountAdapter
from django.contrib.auth.models import User
from django.db import transaction
from django.contrib import messages
from django.conf import settings
from .models import UserProfile
import logging
import socket
import smtplib

# Get a logger
logger = logging.getLogger(__name__)

class CustomAccountAdapter(DefaultAccountAdapter):
    """
    Custom adapter for django-allauth to handle email verification failures gracefully.
    """
    def send_mail(self, template_prefix, email, context):
        """
        Override the send_mail method to handle email sending failures gracefully.
        """
        try:
            # Try to send the email using the parent method
            return super().send_mail(template_prefix, email, context)
        except (socket.error, smtplib.SMTPException) as e:
            # Log the error
            logger.error(f"Failed to send email to {email}: {str(e)}")
            
            # If we're in development, just log the email content
            if settings.DEBUG:
                logger.info(f"Would have sent email to {email} with template {template_prefix}")
                logger.info(f"Context: {context}")
            
            # If this is a verification email, mark the email as verified anyway
            if template_prefix == 'account/email/email_confirmation_signup':
                user = context.get('user')
                if user:
                    email_address = user.emailaddress_set.filter(email=email).first()
                    if email_address and not email_address.verified:
                        logger.info(f"Auto-verifying email {email} for user {user.username} due to email sending failure")
                        email_address.verified = True
                        email_address.save()
            
            # Return True to prevent the exception from propagating
            return True

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def populate_user(self, request, sociallogin, data):
        """
        Populates user instance with data from social account.
        """
        user = super().populate_user(request, sociallogin, data)
        
        # Get profile information from Google
        if sociallogin.account.provider == 'google':
            # Debug log the data we're receiving
            logger.info(f"Google data: {data}")
            
            user.first_name = data.get('given_name', '')
            user.last_name = data.get('family_name', '')
            
            # If email is not set but available in data, set it
            if not user.email and 'email' in data:
                user.email = data['email']
        
        return user
    
    def pre_social_login(self, request, sociallogin):
        """
        Invoked just after a user successfully authenticates via a social provider,
        but before the login is actually processed.
        
        This is where we can match the social account to an existing user.
        """
        # Check if the social account is already connected to a user
        if sociallogin.is_existing:
            logger.info(f"Social account already connected to user: {sociallogin.user.username}")
            return
        
        # For Google accounts, try to match by Google account ID
        if sociallogin.account.provider == 'google':
            google_id = sociallogin.account.uid
            logger.info(f"Looking for user with Google account ID: {google_id}")
            
            # Try to find a user profile with this Google account ID
            try:
                profile = UserProfile.objects.get(google_account_id=google_id)
                logger.info(f"Found user profile with Google account ID: {profile.user.username}")
                
                # Connect the social account to this user
                sociallogin.connect(request, profile.user)
                logger.info(f"Connected social account to user: {profile.user.username}")
                return
            except UserProfile.DoesNotExist:
                logger.info(f"No user profile found with Google account ID: {google_id}")
        
        # If no match by Google ID, fall back to email matching
        email = sociallogin.account.extra_data.get('email')
        if email:
            try:
                # Try to find an existing user with this email
                user = User.objects.get(email=email)
                logger.info(f"Found existing user with email {email}: {user.username}")
                
                # Connect the social account to this user
                sociallogin.connect(request, user)
                logger.info(f"Connected social account to user: {user.username}")
                
                # Also store the Google account ID and email in the user's profile
                if sociallogin.account.provider == 'google':
                    user.profile.google_account_id = sociallogin.account.uid
                    user.profile.google_email = email
                    user.profile.save()
                    logger.info(f"Stored Google account ID and email in user profile: {sociallogin.account.uid}, {email}")
            except User.DoesNotExist:
                logger.info(f"No existing user found with email: {email}")
            except User.MultipleObjectsReturned:
                logger.warning(f"Multiple users found with email: {email}")
    
    def save_user(self, request, sociallogin, form=None):
        """
        Saves the newly created user and creates a profile for them.
        """
        with transaction.atomic():
            # First save the user using the parent method
            user = super().save_user(request, sociallogin, form)
            logger.info(f"Saved user: {user.username}")
            
            # Create a profile for the user if it doesn't exist
            try:
                profile = UserProfile.objects.get(user=user)
                logger.info(f"Found existing profile for user: {user.username}")
            except UserProfile.DoesNotExist:
                profile = UserProfile(user=user)
                logger.info(f"Created new profile for user: {user.username}")
            
            # Store basic Google account information
            if sociallogin.account.provider == 'google':
                extra_data = sociallogin.account.extra_data
                logger.info(f"Google extra_data: {extra_data}")
                
                # Store the Google account ID and email
                profile.google_account_id = sociallogin.account.uid
                if 'email' in extra_data:
                    profile.google_email = extra_data['email']
                    # If this is a new user, set the contact email to the Google email by default
                    if not profile.contact_email:
                        profile.contact_email = extra_data['email']
                
                logger.info(f"Stored Google account ID: {profile.google_account_id}")
                logger.info(f"Stored Google email: {profile.google_email}")
                
                # Save the profile
                profile.save()
                logger.info(f"Saved profile with Google account ID and email")
            else:
                profile.save()
            
            return user 