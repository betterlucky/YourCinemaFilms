from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class Film(models.Model):
    """Model representing a film from OMDB API."""
    imdb_id = models.CharField(max_length=20, unique=True)
    title = models.CharField(max_length=255)
    year = models.CharField(max_length=10)
    poster_url = models.URLField(max_length=500, blank=True, null=True)
    director = models.CharField(max_length=255, blank=True, null=True)
    plot = models.TextField(blank=True, null=True)
    genres = models.CharField(max_length=255, blank=True, null=True)
    runtime = models.CharField(max_length=20, blank=True, null=True)
    actors = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.title} ({self.year})"
    
    class Meta:
        ordering = ['title']
    
    @property
    def genre_list(self):
        """Return genres as a list."""
        if not self.genres:
            return []
        return [genre.strip() for genre in self.genres.split(',')]
    
    @property
    def all_genres(self):
        """Return all genres including user tags."""
        # Get official genres
        genres = set(self.genre_list)
        
        # Add approved user tags
        user_tags = GenreTag.objects.filter(film=self, is_approved=True)
        for tag in user_tags:
            genres.add(tag.tag)
        
        return sorted(list(genres))


class GenreTag(models.Model):
    """Model representing a user-generated genre tag."""
    film = models.ForeignKey(Film, on_delete=models.CASCADE, related_name='tags')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='genre_tags')
    tag = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    is_approved = models.BooleanField(default=False)
    approval_date = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ('film', 'user', 'tag')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.tag} - {self.film.title} (by {self.user.username})"


class Vote(models.Model):
    """Model representing a user's vote for a film."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='votes')
    film = models.ForeignKey(Film, on_delete=models.CASCADE, related_name='votes')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('user', 'film')
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.user.username} voted for {self.film.title}"


class UserProfile(models.Model):
    """Extended user profile model with demographic information."""
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('NB', 'Non-binary'),
        ('O', 'Other'),
        ('NS', 'Prefer not to say')
    ]
    
    AGE_RANGE_CHOICES = [
        ('U18', 'Under 18'),
        ('18-24', '18-24'),
        ('25-34', '25-34'),
        ('35-44', '35-44'),
        ('45-54', '45-54'),
        ('55-64', '55-64'),
        ('65+', '65 and over'),
        ('NS', 'Prefer not to say')
    ]
    
    PRIVACY_CHOICES = [
        ('public', 'Public - Visible to everyone'),
        ('users', 'Users - Visible to registered users only'),
        ('private', 'Private - Visible to only me')
    ]
    
    # Fields with privacy settings
    PRIVACY_FIELDS = ['location', 'gender', 'age', 'votes']
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(blank=True, null=True)
    profile_picture_url = models.URLField(blank=True, null=True)
    letterboxd_username = models.CharField(max_length=100, blank=True, null=True)
    
    # Social account identifiers and information
    google_account_id = models.CharField(max_length=100, blank=True, null=True)
    google_email = models.EmailField(blank=True, null=True)
    contact_email = models.EmailField(blank=True, null=True, help_text="Email address for notifications (if different from account email)")
    use_google_email_for_contact = models.BooleanField(default=True, help_text="Use Google email for contact purposes")
    
    # Demographic information
    location = models.CharField(max_length=100, blank=True, null=True)
    gender = models.CharField(max_length=2, choices=GENDER_CHOICES, default='NS')
    age_range = models.CharField(max_length=5, choices=AGE_RANGE_CHOICES, default='NS')
    
    # Privacy settings
    location_privacy = models.CharField(max_length=10, choices=PRIVACY_CHOICES, default='private')
    gender_privacy = models.CharField(max_length=10, choices=PRIVACY_CHOICES, default='private')
    age_privacy = models.CharField(max_length=10, choices=PRIVACY_CHOICES, default='private')
    votes_privacy = models.CharField(max_length=10, choices=PRIVACY_CHOICES, default='public')
    
    def __str__(self):
        return f"Profile for {self.user.username}"
    
    @property
    def vote_count(self):
        return self.user.votes.count()
    
    @property
    def can_vote(self):
        return self.vote_count < 10
    
    @property
    def primary_email(self):
        """Return the primary email address for this user."""
        if self.use_google_email_for_contact and self.google_email:
            return self.google_email
        elif self.contact_email:
            return self.contact_email
        return self.user.email
    
    def is_visible_to(self, field_name, viewer=None):
        """Check if a field is visible to the viewer based on privacy settings."""
        privacy_setting = getattr(self, f"{field_name}_privacy", "private")
        
        if privacy_setting == 'public':
            return True
        elif privacy_setting == 'users' and viewer and viewer.is_authenticated:
            return True
        elif viewer and (viewer == self.user or viewer.is_staff):
            return True
        return False
    
    def get_privacy_settings(self):
        """Get all privacy settings as a dictionary."""
        return {field: getattr(self, f"{field}_privacy") for field in self.PRIVACY_FIELDS}
    
    def set_privacy_setting(self, field, value):
        """Set a privacy setting for a field."""
        if field in self.PRIVACY_FIELDS and value in dict(self.PRIVACY_CHOICES):
            setattr(self, f"{field}_privacy", value)
            return True
        return False 