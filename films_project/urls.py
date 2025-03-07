"""
URL configuration for films_project project.
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from films_app import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('api/', include('films_app.api.urls')),
    path('', include('films_app.urls')),
    path('debug-profile/', views.debug_profile, name='debug_profile'),
] 