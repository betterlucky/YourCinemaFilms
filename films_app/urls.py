from django.urls import path
from . import views
from django.views.generic.base import RedirectView

app_name = 'films_app'

urlpatterns = [
    # Root URL is now handled at the project level
    path('landing-page/', views.landing, name='landing'),
    path('classic-films/', views.classics, name='classics'),
    path('cinema/', views.cinema, name='cinema'),
    path('filter-cinema-films/', views.filter_cinema_films, name='filter_cinema_films'),
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('profile/image/', views.proxy_profile_image, name='profile_image'),
    path('profile/set-picture/', views.set_profile_picture, name='set_profile_picture'),
    path('profile/google-image/', views.get_google_profile_image, name='google_profile_image'),
    path('profile/upload-image/', views.upload_profile_image, name='upload_profile_image'),
    path('user/<str:username>/image/', views.proxy_user_profile_image, name='user_profile_image'),
    path('search/', views.search_films, name='search_films'),
    path('film/<str:imdb_id>/', views.film_detail, name='film_detail'),
    path('film/<str:imdb_id>/update/', views.update_film_from_tmdb, name='update_film_from_tmdb'),
    path('film/<str:imdb_id>/vote/', views.vote, name='vote'),
    path('film/<str:imdb_id>/vote-count/', views.get_film_vote_count, name='get_film_vote_count'),
    path('film/<str:imdb_id>/remove-vote/', views.remove_vote, name='remove_vote'),
    path('film/<str:imdb_id>/cinema-vote/', views.cinema_vote, name='cinema_vote'),
    path('film/<str:imdb_id>/remove-cinema-vote/', views.remove_cinema_vote, name='remove_cinema_vote'),
    path('film/<str:imdb_id>/tag/', views.add_genre_tag, name='add_genre_tag'),
    path('tag/<int:tag_id>/remove/', views.remove_genre_tag, name='remove_genre_tag'),
    path('manage-tags/', views.manage_genre_tags, name='manage_genre_tags'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('activity/', views.all_activity, name='all_activity'),
    path('top-films/', views.get_top_films_partial, name='get_top_films'),
    path('top-films/all/', views.all_top_films, name='all_top_films'),
    path('users/all/', views.all_users, name='all_users'),
    path('charts/', RedirectView.as_view(pattern_name='films_app:dashboard', permanent=True)),
    path('genres/', views.genre_analysis, name='genre_analysis'),
    path('genres/compare/', views.genre_comparison, name='genre_comparison'),
    path('demographics/', views.demographic_analysis, name='demographic_analysis'),
    path('user/<str:username>/', views.user_profile_view, name='user_profile'),
    path('user-vote-status/', views.get_user_vote_status, name='get_user_vote_status'),
    path('update-cinema-cache/', views.update_cinema_cache, name='update_cinema_cache'),
    
    # Cinema preferences URLs
    path('cinema_preferences/', views.cinema_preferences, name='cinema_preferences'),
    path('add_cinema_preference/<int:cinema_id>/', views.add_cinema_preference, name='add_cinema_preference'),
    path('remove_cinema_preference/<int:cinema_id>/', views.remove_cinema_preference, name='remove_cinema_preference'),
    path('toggle_favorite_cinema/<int:cinema_id>/', views.toggle_favorite_cinema, name='toggle_favorite_cinema'),
    path('add_new_cinema/', views.add_new_cinema, name='add_new_cinema'),
    path('update_travel_distance/', views.update_travel_distance, name='update_travel_distance'),
    
    # Commitment filter URL
    path('commitment_filter/', views.commitment_filter, name='commitment_filter'),
] 