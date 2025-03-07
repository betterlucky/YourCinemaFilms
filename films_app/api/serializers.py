from rest_framework import serializers
from ..models import Film, Vote, UserProfile, GenreTag


class FilmSerializer(serializers.ModelSerializer):
    """Serializer for Film model."""
    vote_count = serializers.SerializerMethodField()
    genre_list = serializers.ReadOnlyField()
    all_genres = serializers.ReadOnlyField()
    
    class Meta:
        model = Film
        fields = [
            'id', 'imdb_id', 'title', 'year', 'poster_url', 
            'director', 'plot', 'genres', 'genre_list', 'all_genres', 'runtime', 
            'actors', 'vote_count', 'created_at'
        ]
    
    def get_vote_count(self, obj):
        """Get the number of votes for a film."""
        return obj.votes.count()


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for UserProfile model."""
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    gender_display = serializers.SerializerMethodField()
    age_range_display = serializers.SerializerMethodField()
    
    class Meta:
        model = UserProfile
        fields = [
            'id', 'username', 'email', 'bio', 'letterboxd_username', 
            'location', 'gender', 'gender_display', 'age_range', 'age_range_display',
            'location_privacy', 'gender_privacy', 'age_privacy', 'votes_privacy',
            'vote_count'
        ]
    
    def get_gender_display(self, obj):
        """Get the display value for gender."""
        return dict(UserProfile.GENDER_CHOICES).get(obj.gender, 'Unknown')
    
    def get_age_range_display(self, obj):
        """Get the display value for age range."""
        return dict(UserProfile.AGE_RANGE_CHOICES).get(obj.age_range, 'Unknown')


class VoteSerializer(serializers.ModelSerializer):
    """Serializer for Vote model."""
    film_details = FilmSerializer(source='film', read_only=True)
    
    class Meta:
        model = Vote
        fields = ['id', 'film', 'film_details', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class GenreTagSerializer(serializers.ModelSerializer):
    """Serializer for GenreTag model."""
    film_details = FilmSerializer(source='film', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = GenreTag
        fields = ['id', 'film', 'film_details', 'user', 'username', 'tag', 'created_at', 'is_approved', 'approval_date']
        read_only_fields = ['user', 'created_at', 'is_approved', 'approval_date'] 