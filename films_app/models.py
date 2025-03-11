from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class Film(models.Model):
    """Model representing a film from TMDB API."""
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
    
    # Cinema-specific fields
    is_in_cinema = models.BooleanField(default=False, help_text="Whether this film is currently in UK cinemas")
    uk_release_date = models.DateField(blank=True, null=True, help_text="UK release date for this film")
    uk_certification = models.CharField(max_length=10, blank=True, null=True, help_text="UK certification (e.g., PG, 12A, 15)")
    popularity = models.FloatField(default=0, help_text="Popularity score from TMDB API")
    vote_count = models.IntegerField(default=0, help_text="Number of votes from TMDB API")
    vote_average = models.FloatField(default=0, help_text="Average vote score from TMDB API (0-10)")
    revenue = models.BigIntegerField(default=0, help_text="Total box office revenue in USD from TMDB API")
    
    # Status tracking fields
    needs_status_check = models.BooleanField(default=False, help_text="Flag indicating this film needs a priority status check")
    
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
    
    @property
    def is_coming_soon(self):
        """Check if film is coming soon (has a future UK release date)."""
        from datetime import date
        if self.uk_release_date and self.uk_release_date > date.today():
            return True
        return False
        
    @property
    def votes_count(self):
        """Return the total number of votes for this film."""
        return self.votes.count()
    
    @property
    def cinema_vote_count(self):
        """Return the total number of cinema votes for this film."""
        return self.cinema_votes.count()
    
    @property
    def commitment_metrics(self):
        """Return metrics about vote commitment levels."""
        votes = self.votes.all()
        total = votes.count()
        if total == 0:
            return {
                'definite': 0,
                'interested': 0,
                'convenient': 0,
                'undecided': 0,
                'definite_percent': 0,
                'interested_percent': 0,
                'convenient_percent': 0,
                'undecided_percent': 0,
                'commitment_score': 0,
                'total': 0
            }
        
        # Count votes by commitment level
        definite = votes.filter(commitment_level='definite').count()
        interested = votes.filter(commitment_level='interested').count()
        convenient = votes.filter(commitment_level='convenient').count()
        undecided = votes.filter(commitment_level='undecided').count()
        
        # Calculate percentages
        definite_percent = (definite / total) * 100 if total > 0 else 0
        interested_percent = (interested / total) * 100 if total > 0 else 0
        convenient_percent = (convenient / total) * 100 if total > 0 else 0
        undecided_percent = (undecided / total) * 100 if total > 0 else 0
        
        # Calculate overall commitment score (weighted average)
        commitment_score = (definite * 3 + interested * 2 + convenient * 1 + undecided * 1) / total if total > 0 else 0
        
        return {
            'definite': definite,
            'interested': interested,
            'convenient': convenient,
            'undecided': undecided,
            'definite_percent': definite_percent,
            'interested_percent': interested_percent,
            'convenient_percent': convenient_percent,
            'undecided_percent': undecided_percent,
            'commitment_score': commitment_score,
            'total': total
        }
    
    @property
    def format_preferences(self):
        """Return metrics about preferred viewing formats."""
        votes = self.votes.all()
        total = votes.count()
        if total == 0:
            return {
                'standard': 0,
                'imax': 0,
                '3d': 0,
                'premium': 0,
                'any': 0,
                'standard_percent': 0,
                'imax_percent': 0,
                '3d_percent': 0,
                'premium_percent': 0,
                'any_percent': 0,
                'total': 0
            }
        
        # Count votes by format preference
        standard = votes.filter(preferred_format='standard').count()
        imax = votes.filter(preferred_format='imax').count()
        three_d = votes.filter(preferred_format='3d').count()
        premium = votes.filter(preferred_format='premium').count()
        any_format = votes.filter(preferred_format='any').count()
        
        # Calculate percentages
        standard_percent = (standard / total) * 100 if total > 0 else 0
        imax_percent = (imax / total) * 100 if total > 0 else 0
        three_d_percent = (three_d / total) * 100 if total > 0 else 0
        premium_percent = (premium / total) * 100 if total > 0 else 0
        any_percent = (any_format / total) * 100 if total > 0 else 0
        
        return {
            'standard': standard,
            'imax': imax,
            '3d': three_d,
            'premium': premium,
            'any': any_format,
            'standard_percent': standard_percent,
            'imax_percent': imax_percent,
            '3d_percent': three_d_percent,
            'premium_percent': premium_percent,
            'any_percent': any_percent,
            'total': total
        }
    
    @property
    def social_preferences(self):
        """Return metrics about social viewing preferences."""
        votes = self.votes.all()
        total = votes.count()
        if total == 0:
            return {
                'solo': 0,
                'partner': 0,
                'friends': 0,
                'family': 0,
                'open': 0,
                'undecided': 0,
                'solo_percent': 0,
                'partner_percent': 0,
                'friends_percent': 0,
                'family_percent': 0,
                'open_percent': 0,
                'undecided_percent': 0,
                'total': 0
            }
        
        # Count votes by social preference
        solo = votes.filter(social_preference='solo').count()
        partner = votes.filter(social_preference='partner').count()
        friends = votes.filter(social_preference='friends').count()
        family = votes.filter(social_preference='family').count()
        open_to_company = votes.filter(social_preference='open').count()
        undecided = votes.filter(social_preference='undecided').count()
        
        # Calculate percentages
        solo_percent = (solo / total) * 100 if total > 0 else 0
        partner_percent = (partner / total) * 100 if total > 0 else 0
        friends_percent = (friends / total) * 100 if total > 0 else 0
        family_percent = (family / total) * 100 if total > 0 else 0
        open_percent = (open_to_company / total) * 100 if total > 0 else 0
        undecided_percent = (undecided / total) * 100 if total > 0 else 0
        
        return {
            'solo': solo,
            'partner': partner,
            'friends': friends,
            'family': family,
            'open': open_to_company,
            'undecided': undecided,
            'solo_percent': solo_percent,
            'partner_percent': partner_percent,
            'friends_percent': friends_percent,
            'family_percent': family_percent,
            'open_percent': open_percent,
            'undecided_percent': undecided_percent,
            'total': total
        }


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
    COMMITMENT_CHOICES = [
        ('definite', 'Definitely attending'),
        ('interested', 'Interested'),
        ('convenient', 'Only if convenient'),
        ('undecided', 'Undecided')
    ]
    
    FORMAT_CHOICES = [
        ('standard', 'Standard screening'),
        ('imax', 'IMAX'),
        ('3d', '3D'),
        ('premium', 'Premium (recliner seats, etc.)'),
        ('any', 'Any format'),
    ]
    
    SOCIAL_CHOICES = [
        ('solo', 'Going solo'),
        ('partner', 'With partner'),
        ('friends', 'With friends'),
        ('family', 'With family'),
        ('open', 'Open to company'),
        ('undecided', 'Undecided')
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='votes')
    film = models.ForeignKey(Film, on_delete=models.CASCADE, related_name='votes')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # New commitment fields
    commitment_level = models.CharField(max_length=20, choices=COMMITMENT_CHOICES, default='interested', 
                                       help_text="How committed are you to seeing this film in theaters?")
    preferred_format = models.CharField(max_length=20, choices=FORMAT_CHOICES, default='any',
                                       help_text="What format would you prefer to see this film in?")
    social_preference = models.CharField(max_length=20, choices=SOCIAL_CHOICES, default='undecided',
                                        help_text="Who would you like to see this film with?")
    
    class Meta:
        unique_together = ('user', 'film')
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.user.username} voted for {self.film.title} ({self.get_commitment_level_display()})"
    
    @property
    def commitment_score(self):
        """Return a numeric score for commitment level (1-3)."""
        scores = {
            'definite': 3,
            'interested': 2,
            'convenient': 1,
            'undecided': 1
        }
        return scores.get(self.commitment_level, 1)


class CinemaVote(models.Model):
    """Model representing a user's vote for a cinema film (current or upcoming)."""
    COMMITMENT_CHOICES = [
        ('definite', 'Definitely attending'),
        ('interested', 'Interested'),
        ('convenient', 'Only if convenient'),
        ('undecided', 'Undecided')
    ]
    
    FORMAT_CHOICES = [
        ('standard', 'Standard screening'),
        ('imax', 'IMAX'),
        ('3d', '3D'),
        ('premium', 'Premium (recliner seats, etc.)'),
        ('any', 'Any format'),
    ]
    
    SOCIAL_CHOICES = [
        ('solo', 'Going solo'),
        ('partner', 'With partner'),
        ('friends', 'With friends'),
        ('family', 'With family'),
        ('open', 'Open to company'),
        ('undecided', 'Undecided')
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cinema_votes')
    film = models.ForeignKey(Film, on_delete=models.CASCADE, related_name='cinema_votes')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # New commitment fields
    commitment_level = models.CharField(max_length=20, choices=COMMITMENT_CHOICES, default='interested', 
                                       help_text="How committed are you to seeing this film in theaters?")
    preferred_format = models.CharField(max_length=20, choices=FORMAT_CHOICES, default='any',
                                       help_text="What format would you prefer to see this film in?")
    social_preference = models.CharField(max_length=20, choices=SOCIAL_CHOICES, default='undecided',
                                        help_text="Who would you like to see this film with?")
    
    class Meta:
        unique_together = ('user', 'film')
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.user.username} voted for cinema film {self.film.title} ({self.get_commitment_level_display()})"
    
    @property
    def commitment_score(self):
        """Return a numeric score for commitment level (1-3)."""
        scores = {
            'definite': 3,
            'interested': 2,
            'convenient': 1,
            'undecided': 1
        }
        return scores.get(self.commitment_level, 1)


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
    
    # Viewing frequency choices
    VIEWING_FREQUENCY_CHOICES = [
        ('weekly', 'Weekly or more'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Every few months'),
        ('yearly', 'A few times a year'),
        ('rarely', 'Rarely'),
        ('NS', 'Prefer not to say')
    ]
    
    # Viewing companion choices
    VIEWING_COMPANION_CHOICES = [
        ('alone', 'Usually alone'),
        ('partner', 'With partner/spouse'),
        ('family', 'With family'),
        ('friends', 'With friends'),
        ('varies', 'It varies'),
        ('NS', 'Prefer not to say')
    ]
    
    # Viewing time preferences
    VIEWING_TIME_CHOICES = [
        ('weekday_day', 'Weekday daytime'),
        ('weekday_evening', 'Weekday evening'),
        ('weekend_day', 'Weekend daytime'),
        ('weekend_evening', 'Weekend evening'),
        ('varies', 'It varies'),
        ('NS', 'Prefer not to say')
    ]
    
    # Price sensitivity
    PRICE_SENSITIVITY_CHOICES = [
        ('full', 'Willing to pay full price'),
        ('discount', 'Prefer discount days/times'),
        ('special', 'Only for special films/events'),
        ('varies', 'It depends on the film'),
        ('NS', 'Prefer not to say')
    ]
    
    # Format preferences
    FORMAT_PREFERENCE_CHOICES = [
        ('standard', 'Standard screening'),
        ('imax', 'IMAX'),
        ('3d', '3D'),
        ('premium', 'Premium (recliner seats, etc.)'),
        ('varies', 'Depends on the film'),
        ('NS', 'Prefer not to say')
    ]
    
    # Fields with privacy settings
    PRIVACY_FIELDS = [
        'location', 'gender', 'age', 'votes', 'cinema_frequency', 
        'viewing_companions', 'viewing_time', 
        'price_sensitivity', 'format_preference', 'travel_distance',
        'cinema_amenities', 'film_genres', 'dashboard_activity'
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(blank=True, null=True)
    profile_picture_url = models.URLField(blank=True, null=True)
    letterboxd_username = models.CharField(max_length=100, blank=True, null=True)
    
    # Social account identifiers and information
    google_account_id = models.CharField(max_length=100, blank=True, null=True)
    google_email = models.EmailField(blank=True, null=True)
    contact_email = models.EmailField(blank=True, null=True, help_text="Email address for notifications (if different from account email)")
    use_google_email_for_contact = models.BooleanField(default=True, help_text="Use Google email for contact purposes")
    
    # Existing demographic information
    location = models.CharField(max_length=100, blank=True, null=True, help_text="Your city, town or region in the UK")
    gender = models.CharField(max_length=2, choices=GENDER_CHOICES, default='NS')
    age_range = models.CharField(max_length=5, choices=AGE_RANGE_CHOICES, default='NS')
    
    # New cinema-specific demographic information
    cinema_frequency = models.CharField(max_length=10, choices=VIEWING_FREQUENCY_CHOICES, default='NS', help_text="How often do you go to the cinema?")
    viewing_companions = models.CharField(max_length=10, choices=VIEWING_COMPANION_CHOICES, default='NS', help_text="Who do you usually go to the cinema with?")
    viewing_time = models.CharField(max_length=20, choices=VIEWING_TIME_CHOICES, default='NS', help_text="When do you prefer to go to the cinema?")
    price_sensitivity = models.CharField(max_length=10, choices=PRICE_SENSITIVITY_CHOICES, default='NS', help_text="How important is ticket price in your decision to see a film?")
    format_preference = models.CharField(max_length=10, choices=FORMAT_PREFERENCE_CHOICES, default='NS', help_text="What format do you prefer to watch films in?")
    travel_distance = models.PositiveIntegerField(default=10, help_text="How far are you willing to travel to a cinema (in miles)?")
    cinema_amenities = models.TextField(blank=True, null=True, help_text="What cinema amenities are important to you? (e.g., food service, bar, reclining seats)")
    film_genres = models.TextField(blank=True, null=True, help_text="What film genres do you prefer to see in the cinema?")
    
    # Existing privacy settings
    location_privacy = models.CharField(max_length=10, choices=PRIVACY_CHOICES, default='private')
    gender_privacy = models.CharField(max_length=10, choices=PRIVACY_CHOICES, default='private')
    age_privacy = models.CharField(max_length=10, choices=PRIVACY_CHOICES, default='private')
    votes_privacy = models.CharField(max_length=10, choices=PRIVACY_CHOICES, default='private')
    
    # New privacy settings
    cinema_frequency_privacy = models.CharField(max_length=10, choices=PRIVACY_CHOICES, default='private')
    viewing_companions_privacy = models.CharField(max_length=10, choices=PRIVACY_CHOICES, default='private')
    viewing_time_privacy = models.CharField(max_length=10, choices=PRIVACY_CHOICES, default='private')
    price_sensitivity_privacy = models.CharField(max_length=10, choices=PRIVACY_CHOICES, default='private')
    format_preference_privacy = models.CharField(max_length=10, choices=PRIVACY_CHOICES, default='private')
    travel_distance_privacy = models.CharField(max_length=10, choices=PRIVACY_CHOICES, default='private')
    cinema_amenities_privacy = models.CharField(max_length=10, choices=PRIVACY_CHOICES, default='private')
    film_genres_privacy = models.CharField(max_length=10, choices=PRIVACY_CHOICES, default='private')
    dashboard_activity_privacy = models.CharField(max_length=10, choices=PRIVACY_CHOICES, default='public')
    
    def __str__(self):
        return f"Profile for {self.user.username}"
    
    @property
    def vote_count(self):
        """Get the number of votes cast by the user."""
        return self.user.votes.count()
    
    @property
    def can_vote(self):
        """Check if the user can vote for more films."""
        return self.vote_count < 10
    
    @property
    def cinema_vote_count(self):
        """Get the number of cinema votes cast by the user."""
        return self.user.cinema_votes.count()
    
    @property
    def can_cinema_vote(self):
        """Check if the user can vote for more cinema films."""
        return self.cinema_vote_count < 3
    
    @property
    def primary_email(self):
        """Return the primary email address for the user."""
        if self.use_google_email_for_contact and self.google_email:
            return self.google_email
        elif self.contact_email:
            return self.contact_email
        return self.user.email
    
    def get_gender_display(self):
        """Return the display value for gender."""
        return dict(self.GENDER_CHOICES).get(self.gender, 'Not specified')
    
    def get_age_range_display(self):
        """Return the display value for age range."""
        return dict(self.AGE_RANGE_CHOICES).get(self.age_range, 'Not specified')
    
    def get_cinema_frequency_display(self):
        """Return the display value for cinema frequency."""
        return dict(self.VIEWING_FREQUENCY_CHOICES).get(self.cinema_frequency, 'Not specified')
    
    def get_viewing_companions_display(self):
        """Return the display value for viewing companions."""
        return dict(self.VIEWING_COMPANION_CHOICES).get(self.viewing_companions, 'Not specified')
    
    def get_viewing_time_display(self):
        """Return the display value for viewing time."""
        return dict(self.VIEWING_TIME_CHOICES).get(self.viewing_time, 'Not specified')
    
    def get_price_sensitivity_display(self):
        """Return the display value for price sensitivity."""
        return dict(self.PRICE_SENSITIVITY_CHOICES).get(self.price_sensitivity, 'Not specified')
    
    def get_format_preference_display(self):
        """Return the display value for format preference."""
        return dict(self.FORMAT_PREFERENCE_CHOICES).get(self.format_preference, 'Not specified')
    
    def get_location_privacy_display(self):
        """Return the display value for location privacy."""
        return dict(self.PRIVACY_CHOICES).get(self.location_privacy, 'Private')
    
    def get_gender_privacy_display(self):
        """Return the display value for gender privacy."""
        return dict(self.PRIVACY_CHOICES).get(self.gender_privacy, 'Private')
    
    def get_age_privacy_display(self):
        """Return the display value for age privacy."""
        return dict(self.PRIVACY_CHOICES).get(self.age_privacy, 'Private')
    
    def get_votes_privacy_display(self):
        """Return the display value for votes privacy."""
        return dict(self.PRIVACY_CHOICES).get(self.votes_privacy, 'Private')
    
    def get_cinema_frequency_privacy_display(self):
        """Return the display value for cinema frequency privacy."""
        return dict(self.PRIVACY_CHOICES).get(self.cinema_frequency_privacy, 'Private')
    
    def get_viewing_companions_privacy_display(self):
        """Return the display value for viewing companions privacy."""
        return dict(self.PRIVACY_CHOICES).get(self.viewing_companions_privacy, 'Private')
    
    def get_viewing_time_privacy_display(self):
        """Return the display value for viewing time privacy."""
        return dict(self.PRIVACY_CHOICES).get(self.viewing_time_privacy, 'Private')
    
    def get_price_sensitivity_privacy_display(self):
        """Return the display value for price sensitivity privacy."""
        return dict(self.PRIVACY_CHOICES).get(self.price_sensitivity_privacy, 'Private')
    
    def get_format_preference_privacy_display(self):
        """Return the display value for format preference privacy."""
        return dict(self.PRIVACY_CHOICES).get(self.format_preference_privacy, 'Private')
    
    def get_travel_distance_privacy_display(self):
        """Return the display value for travel distance privacy."""
        return dict(self.PRIVACY_CHOICES).get(self.travel_distance_privacy, 'Private')
    
    def get_cinema_amenities_privacy_display(self):
        """Return the display value for cinema amenities privacy."""
        return dict(self.PRIVACY_CHOICES).get(self.cinema_amenities_privacy, 'Private')
    
    def get_film_genres_privacy_display(self):
        """Return the display value for film genres privacy."""
        return dict(self.PRIVACY_CHOICES).get(self.film_genres_privacy, 'Private')
    
    def get_dashboard_activity_privacy_display(self):
        """Return the display value for dashboard activity privacy."""
        return dict(self.PRIVACY_CHOICES).get(self.dashboard_activity_privacy, 'Public')
    
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
    
    def is_profile_complete(self):
        """Check if the user profile is complete with meaningful information."""
        # Check if all required fields have been filled out
        required_fields = [
            self.bio,
            self.location,
            self.cinema_frequency != 'NS',
            self.viewing_companions != 'NS',
            self.viewing_time != 'NS',
            self.price_sensitivity != 'NS',
            self.format_preference != 'NS',
            self.travel_distance,
            self.cinema_amenities,
            self.film_genres,
            self.gender != 'NS',
            self.age_range != 'NS'
        ]
        
        # Profile is complete if at least 80% of fields are filled
        return sum(bool(field) for field in required_fields) >= 10
    
    def profile_completion_percentage(self):
        """Calculate the percentage of profile completion."""
        required_fields = [
            self.bio,
            self.location,
            self.cinema_frequency != 'NS',
            self.viewing_companions != 'NS',
            self.viewing_time != 'NS',
            self.price_sensitivity != 'NS',
            self.format_preference != 'NS',
            self.travel_distance,
            self.cinema_amenities,
            self.film_genres,
            self.gender != 'NS',
            self.age_range != 'NS'
        ]
        
        completed = sum(bool(field) for field in required_fields)
        total = len(required_fields)
        
        return int((completed / total) * 100)


class Achievement(models.Model):
    """Model for tracking user achievements."""
    ACHIEVEMENT_TYPES = [
        ('profile_complete', 'Profile Completed'),
        ('first_vote', 'First Vote'),
        ('ten_votes', '10 Votes'),
        ('fifty_votes', '50 Votes'),
        ('first_tag', 'First Genre Tag'),
        ('tag_approved', 'Genre Tag Approved'),
        ('cinema_expert', 'Cinema Expert'),
    ]
    
    ACHIEVEMENT_DESCRIPTIONS = {
        'profile_complete': 'Completed your profile with detailed cinema preferences',
        'first_vote': 'Cast your first vote for a film',
        'ten_votes': 'Voted for 10 different films',
        'fifty_votes': 'Voted for 50 different films',
        'first_tag': 'Added your first genre tag to a film',
        'tag_approved': 'Had a genre tag approved by moderators',
        'cinema_expert': 'Contributed significantly to the community',
    }
    
    ACHIEVEMENT_ICONS = {
        'profile_complete': 'fa-user-check',
        'first_vote': 'fa-thumbs-up',
        'ten_votes': 'fa-award',
        'fifty_votes': 'fa-trophy',
        'first_tag': 'fa-tag',
        'tag_approved': 'fa-check-circle',
        'cinema_expert': 'fa-film',
    }
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='achievements')
    achievement_type = models.CharField(max_length=50, choices=ACHIEVEMENT_TYPES)
    date_achieved = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'achievement_type')
        ordering = ['achievement_type']
    
    def __str__(self):
        return f"{self.user.username} - {self.get_achievement_type_display()}"
    
    @property
    def description(self):
        """Get the description for this achievement."""
        return self.ACHIEVEMENT_DESCRIPTIONS.get(self.achievement_type, '')
    
    @property
    def icon(self):
        """Get the Font Awesome icon for this achievement."""
        return self.ACHIEVEMENT_ICONS.get(self.achievement_type, 'fa-award')


class Activity(models.Model):
    """Model for tracking user activity."""
    ACTIVITY_TYPES = [
        ('vote', 'Vote'),
        ('tag', 'Genre Tag'),
        ('profile', 'Profile Update'),
        ('login', 'Login'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    film = models.ForeignKey(Film, on_delete=models.SET_NULL, null=True, blank=True, related_name='activities')
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = 'Activities'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.activity_type} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class PageTracker(models.Model):
    """Model to track the last processed page for each movie type."""
    
    MOVIE_TYPE_CHOICES = [
        ('now_playing', 'Now Playing'),
        ('upcoming', 'Upcoming'),
    ]
    
    movie_type = models.CharField(max_length=20, choices=MOVIE_TYPE_CHOICES, unique=True)
    last_page = models.IntegerField(default=0)
    total_pages = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.get_movie_type_display()} - Page {self.last_page} of {self.total_pages}"
    
    @classmethod
    def get_next_page(cls, movie_type):
        """Get the next page to process for the given movie type."""
        tracker, created = cls.objects.get_or_create(movie_type=movie_type)
        
        # If this is a new tracker or we've processed all pages, start from page 1
        if created or tracker.last_page >= tracker.total_pages:
            return 1
        
        # Otherwise, return the next page
        return tracker.last_page + 1
    
    @classmethod
    def update_tracker(cls, movie_type, current_page, total_pages):
        """Update the tracker with the current page and total pages."""
        tracker, _ = cls.objects.get_or_create(movie_type=movie_type)
        tracker.last_page = current_page
        tracker.total_pages = total_pages
        tracker.save()


class Cinema(models.Model):
    """Model representing a cinema site."""
    name = models.CharField(max_length=255, help_text="Name of the cinema")
    chain = models.CharField(max_length=255, blank=True, null=True, help_text="Cinema chain (e.g., Odeon, Vue, Cineworld)")
    location = models.CharField(max_length=255, help_text="Location of the cinema (city/town)")
    postcode = models.CharField(max_length=10, blank=True, null=True, help_text="Postcode of the cinema")
    latitude = models.FloatField(blank=True, null=True, help_text="Latitude coordinate for mapping")
    longitude = models.FloatField(blank=True, null=True, help_text="Longitude coordinate for mapping")
    website = models.URLField(blank=True, null=True, help_text="Website URL for the cinema")
    
    # Amenities as boolean fields
    has_imax = models.BooleanField(default=False, help_text="Whether this cinema has IMAX screens")
    has_3d = models.BooleanField(default=False, help_text="Whether this cinema has 3D capability")
    has_premium_seating = models.BooleanField(default=False, help_text="Whether this cinema has premium seating (recliners, etc.)")
    has_food_service = models.BooleanField(default=False, help_text="Whether this cinema has in-screen food service")
    has_bar = models.BooleanField(default=False, help_text="Whether this cinema has a bar")
    has_disabled_access = models.BooleanField(default=True, help_text="Whether this cinema has disabled access")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name', 'location']
        unique_together = ('name', 'location', 'postcode')
    
    def __str__(self):
        if self.chain:
            return f"{self.name} ({self.chain}) - {self.location}"
        return f"{self.name} - {self.location}"
    
    @property
    def amenities_list(self):
        """Return a list of available amenities."""
        amenities = []
        if self.has_imax:
            amenities.append("IMAX")
        if self.has_3d:
            amenities.append("3D")
        if self.has_premium_seating:
            amenities.append("Premium Seating")
        if self.has_food_service:
            amenities.append("Food Service")
        if self.has_bar:
            amenities.append("Bar")
        if self.has_disabled_access:
            amenities.append("Disabled Access")
        return amenities


class CinemaPreference(models.Model):
    """Model representing a user's cinema site preference."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cinema_preferences')
    cinema = models.ForeignKey(Cinema, on_delete=models.CASCADE, related_name='user_preferences')
    is_favorite = models.BooleanField(default=False, help_text="Whether this is a favorite cinema")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('user', 'cinema')
        ordering = ['-is_favorite', '-updated_at']
    
    def __str__(self):
        favorite_status = "favorite" if self.is_favorite else "preferred"
        return f"{self.user.username}'s {favorite_status} cinema: {self.cinema.name}" 