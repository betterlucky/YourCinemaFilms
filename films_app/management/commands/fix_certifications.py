import os
import json
import time
from django.core.management.base import BaseCommand
from django.conf import settings
from films_app.models import Film
from films_app.tmdb_api import get_movie_details, get_movie_by_imdb_id, get_uk_certification

class Command(BaseCommand):
    help = 'Fix missing UK certifications for films by checking the TMDB API'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )
        parser.add_argument(
            '--film-id',
            type=str,
            help='Fix a specific film by IMDb ID (e.g., tt13186482)',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Check all films, not just those with missing certifications',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        specific_film_id = options.get('film_id')
        check_all = options.get('all', False)
        
        if specific_film_id:
            # Fix a specific film
            try:
                film = Film.objects.get(imdb_id=specific_film_id)
                self.fix_film_certification(film, dry_run)
            except Film.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Film with ID {specific_film_id} not found"))
            return
        
        # Get films with missing certifications or all films if check_all is True
        if check_all:
            films = Film.objects.all()
            self.stdout.write(f"Checking all {films.count()} films for certification updates")
        else:
            films = Film.objects.filter(uk_certification__isnull=True)
            self.stdout.write(f"Found {films.count()} films with missing UK certifications")
        
        updated_count = 0
        for film in films:
            if self.fix_film_certification(film, dry_run):
                updated_count += 1
            
            # Add a small delay to avoid rate limiting
            time.sleep(0.5)
        
        if dry_run:
            self.stdout.write(self.style.SUCCESS(f"Dry run completed. {updated_count} films would be updated."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Updated certifications for {updated_count} films."))

    def fix_film_certification(self, film, dry_run=False):
        """Fix the certification for a single film"""
        self.stdout.write(f"Checking {film.title} ({film.imdb_id})")
        
        # Check if the film has a TMDB ID format or IMDb ID format
        tmdb_id = None
        if film.imdb_id.startswith('tmdb-'):
            # Extract TMDB ID from the format "tmdb-123456"
            tmdb_id = film.imdb_id.replace('tmdb-', '')
            self.stdout.write(f"  Using TMDB ID: {tmdb_id}")
            movie_details = get_movie_details(tmdb_id)
        else:
            # This is an IMDb ID, use it directly
            self.stdout.write(f"  Using IMDb ID: {film.imdb_id}")
            movie_details = get_movie_by_imdb_id(film.imdb_id)
            if movie_details:
                tmdb_id = movie_details.get('id')
        
        if not movie_details:
            self.stdout.write(self.style.WARNING(f"  Could not fetch details for {film.title}"))
            return False
        
        # Extract UK certification
        release_dates = movie_details.get('release_dates', {})
        uk_certification = get_uk_certification(release_dates)
        
        if not uk_certification:
            self.stdout.write(self.style.WARNING(f"  No UK certification found for {film.title}"))
            return False
        
        # Check if certification needs updating
        if film.uk_certification == uk_certification:
            self.stdout.write(f"  Certification already up to date: {uk_certification}")
            return False
        
        # Update the certification
        old_cert = film.uk_certification or 'None'
        self.stdout.write(self.style.SUCCESS(f"  Updating certification from {old_cert} to {uk_certification}"))
        
        if not dry_run:
            film.uk_certification = uk_certification
            film.save(update_fields=['uk_certification'])
        
        return True 