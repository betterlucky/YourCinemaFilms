from django.urls import path
from . import views

app_name = 'films_app'

urlpatterns = [
    path('', views.home, name='home'),
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('profile/image/', views.proxy_profile_image, name='profile_image'),
    path('profile/set-picture/', views.set_profile_picture, name='set_profile_picture'),
    path('profile/google-image/', views.get_google_profile_image, name='google_profile_image'),
    path('profile/upload-image/', views.upload_profile_image, name='upload_profile_image'),
    path('user/<str:username>/image/', views.proxy_user_profile_image, name='user_profile_image'),
    path('search/', views.search_films, name='search_films'),
    path('film/<str:imdb_id>/', views.film_detail, name='film_detail'),
    path('film/<str:imdb_id>/vote/', views.vote_for_film, name='vote_for_film'),
    path('vote/<int:vote_id>/remove/', views.remove_vote, name='remove_vote'),
    path('film/<str:imdb_id>/tag/', views.add_genre_tag, name='add_genre_tag'),
    path('tag/<int:tag_id>/remove/', views.remove_genre_tag, name='remove_genre_tag'),
    path('manage-tags/', views.manage_genre_tags, name='manage_genre_tags'),
    path('charts/', views.charts, name='charts'),
    path('genres/', views.genre_analysis, name='genre_analysis'),
    path('demographics/', views.demographic_analysis, name='demographic_analysis'),
    path('user/<str:username>/', views.user_profile_view, name='user_profile'),
] 