from django.contrib import admin
from django.utils import timezone
from .models import Film, Vote, UserProfile, GenreTag, Cinema, CinemaPreference, CinemaVote


@admin.register(Film)
class FilmAdmin(admin.ModelAdmin):
    """Admin interface for Film model."""
    list_display = ('title', 'year', 'imdb_id', 'vote_count', 'commitment_score', 'created_at')
    search_fields = ('title', 'imdb_id', 'director')
    list_filter = ('year', 'is_in_cinema')
    readonly_fields = ('created_at',)
    
    def vote_count(self, obj):
        """Get the number of votes for a film."""
        return obj.votes.count()
    
    def commitment_score(self, obj):
        """Get the commitment score for a film."""
        metrics = obj.commitment_metrics
        return f"{metrics['commitment_score']:.2f} ({metrics['total']} votes)"
    
    vote_count.short_description = 'Votes'
    commitment_score.short_description = 'Commitment Score'


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    """Admin interface for Vote model."""
    list_display = ('user', 'film', 'commitment_level', 'preferred_format', 'social_preference', 'created_at')
    list_filter = ('created_at', 'updated_at', 'commitment_level', 'preferred_format', 'social_preference')
    search_fields = ('user__username', 'film__title')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(CinemaVote)
class CinemaVoteAdmin(admin.ModelAdmin):
    """Admin interface for CinemaVote model."""
    list_display = ('user', 'film', 'commitment_level', 'preferred_format', 'social_preference', 'created_at')
    list_filter = ('created_at', 'updated_at', 'commitment_level', 'preferred_format', 'social_preference')
    search_fields = ('user__username', 'film__title')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """Admin interface for UserProfile model."""
    list_display = ('user', 'letterboxd_username', 'vote_count', 'travel_distance')
    search_fields = ('user__username', 'user__email', 'letterboxd_username')
    list_filter = ('cinema_frequency', 'format_preference')
    
    def vote_count(self, obj):
        """Get the number of votes for a user."""
        return obj.user.votes.count()
    
    vote_count.short_description = 'Votes'


@admin.register(GenreTag)
class GenreTagAdmin(admin.ModelAdmin):
    """Admin interface for GenreTag model."""
    list_display = ('tag', 'film', 'user', 'created_at', 'is_approved')
    list_filter = ('is_approved', 'created_at')
    search_fields = ('tag', 'film__title', 'user__username')
    actions = ['approve_tags', 'reject_tags']
    
    def approve_tags(self, request, queryset):
        """Approve selected genre tags."""
        queryset.update(is_approved=True, approval_date=timezone.now())
        self.message_user(request, f"{queryset.count()} genre tags were approved.")
    
    approve_tags.short_description = "Approve selected genre tags"
    
    def reject_tags(self, request, queryset):
        """Reject selected genre tags."""
        queryset.update(is_approved=False, approval_date=None)
        self.message_user(request, f"{queryset.count()} genre tags were rejected.")
    
    reject_tags.short_description = "Reject selected genre tags"


@admin.register(Cinema)
class CinemaAdmin(admin.ModelAdmin):
    """Admin interface for Cinema model."""
    list_display = ('name', 'chain', 'location', 'postcode', 'amenities_display')
    list_filter = ('chain', 'has_imax', 'has_3d', 'has_premium_seating', 'has_food_service', 'has_bar')
    search_fields = ('name', 'chain', 'location', 'postcode')
    
    def amenities_display(self, obj):
        """Display amenities as a comma-separated list."""
        return ", ".join(obj.amenities_list)
    
    amenities_display.short_description = 'Amenities'


@admin.register(CinemaPreference)
class CinemaPreferenceAdmin(admin.ModelAdmin):
    """Admin interface for CinemaPreference model."""
    list_display = ('user', 'cinema', 'is_favorite', 'created_at')
    list_filter = ('is_favorite', 'created_at')
    search_fields = ('user__username', 'cinema__name', 'cinema__location')
    readonly_fields = ('created_at', 'updated_at') 