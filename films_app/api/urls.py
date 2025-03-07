from django.urls import path
from . import views

app_name = 'films_api'

urlpatterns = [
    path('films/', views.FilmListAPIView.as_view(), name='film_list'),
    path('films/<str:imdb_id>/', views.FilmDetailAPIView.as_view(), name='film_detail'),
    path('votes/', views.VoteListCreateAPIView.as_view(), name='vote_list'),
    path('votes/<int:pk>/', views.VoteDetailAPIView.as_view(), name='vote_detail'),
    path('tags/', views.GenreTagListCreateAPIView.as_view(), name='tag_list'),
    path('tags/<int:pk>/', views.GenreTagDetailAPIView.as_view(), name='tag_detail'),
    path('search/', views.search_films, name='search_films'),
    path('charts/data/', views.charts_data, name='charts_data'),
    path('genres/data/', views.genre_data, name='genre_data'),
    path('demographics/data/', views.demographic_data, name='demographic_data'),
    path('profile/', views.UserProfileAPIView.as_view(), name='user_profile'),
    path('recommendations/', views.film_recommendations, name='recommendations'),
] 