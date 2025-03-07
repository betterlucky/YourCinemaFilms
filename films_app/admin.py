from django.contrib import admin
from django.utils import timezone
from .models import Film, Vote, UserProfile, GenreTag


@admin.register(Film)
class FilmAdmin(admin.ModelAdmin):
    """Admin interface for Film model."""
    list_display = ('title', 'year', 'imdb_id', 'vote_count', 'created_at')
    search_fields = ('title', 'imdb_id', 'director')
    list_filter = ('year',)
    readonly_fields = ('created_at',)
    
    def vote_count(self, obj):
        """Get the number of votes for a film."""
        return obj.votes.count()
    
    vote_count.short_description = 'Votes'


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    """Admin interface for Vote model."""
    list_display = ('user', 'film', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('user__username', 'film__title')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """Admin interface for UserProfile model."""
    list_display = ('user', 'letterboxd_username', 'vote_count')
    search_fields = ('user__username', 'user__email', 'letterboxd_username')
    
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