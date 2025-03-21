# Generated by Django 5.1.1 on 2025-03-12 03:29

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('films_app', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Film',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('imdb_id', models.CharField(max_length=20, unique=True)),
                ('title', models.CharField(max_length=255)),
                ('year', models.CharField(max_length=10)),
                ('poster_url', models.URLField(blank=True, max_length=500, null=True)),
                ('director', models.CharField(blank=True, max_length=255, null=True)),
                ('plot', models.TextField(blank=True, null=True)),
                ('genres', models.CharField(blank=True, max_length=255, null=True)),
                ('runtime', models.CharField(blank=True, max_length=20, null=True)),
                ('actors', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('is_in_cinema', models.BooleanField(default=False, help_text='Whether this film is currently in UK cinemas')),
                ('is_upcoming', models.BooleanField(default=False, help_text='Whether this film is scheduled for future UK release')),
                ('uk_release_date', models.DateField(blank=True, help_text='UK release date for this film', null=True)),
                ('uk_certification', models.CharField(blank=True, help_text='UK certification (e.g., PG, 12A, 15)', max_length=10, null=True)),
                ('popularity', models.FloatField(default=0, help_text='Popularity score from TMDB API')),
                ('vote_count', models.IntegerField(default=0, help_text='Number of votes from TMDB API')),
                ('vote_average', models.FloatField(default=0, help_text='Average vote score from TMDB API (0-10)')),
                ('revenue', models.BigIntegerField(default=0, help_text='Total box office revenue in USD from TMDB API')),
                ('needs_status_check', models.BooleanField(default=False, help_text='Flag indicating this film needs a priority status check')),
            ],
            options={
                'ordering': ['title'],
            },
        ),
        migrations.CreateModel(
            name='PageTracker',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('movie_type', models.CharField(choices=[('now_playing', 'Now Playing'), ('upcoming', 'Upcoming')], max_length=20, unique=True)),
                ('last_page', models.IntegerField(default=0)),
                ('total_pages', models.IntegerField(default=0)),
                ('last_updated', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='Cinema',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Name of the cinema', max_length=255)),
                ('chain', models.CharField(blank=True, help_text='Cinema chain (e.g., Odeon, Vue, Cineworld)', max_length=255, null=True)),
                ('location', models.CharField(help_text='Location of the cinema (city/town)', max_length=255)),
                ('postcode', models.CharField(blank=True, help_text='Postcode of the cinema', max_length=10, null=True)),
                ('latitude', models.FloatField(blank=True, help_text='Latitude coordinate for mapping', null=True)),
                ('longitude', models.FloatField(blank=True, help_text='Longitude coordinate for mapping', null=True)),
                ('website', models.URLField(blank=True, help_text='Website URL for the cinema', null=True)),
                ('has_imax', models.BooleanField(default=False, help_text='Whether this cinema has IMAX screens')),
                ('has_3d', models.BooleanField(default=False, help_text='Whether this cinema has 3D capability')),
                ('has_premium_seating', models.BooleanField(default=False, help_text='Whether this cinema has premium seating (recliners, etc.)')),
                ('has_food_service', models.BooleanField(default=False, help_text='Whether this cinema has in-screen food service')),
                ('has_bar', models.BooleanField(default=False, help_text='Whether this cinema has a bar')),
                ('has_disabled_access', models.BooleanField(default=True, help_text='Whether this cinema has disabled access')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['name', 'location'],
                'unique_together': {('name', 'location', 'postcode')},
            },
        ),
        migrations.CreateModel(
            name='Activity',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('activity_type', models.CharField(choices=[('vote', 'Vote'), ('tag', 'Genre Tag'), ('profile', 'Profile Update'), ('login', 'Login')], max_length=20)),
                ('description', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='activities', to=settings.AUTH_USER_MODEL)),
                ('film', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='activities', to='films_app.film')),
            ],
            options={
                'verbose_name_plural': 'Activities',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('bio', models.TextField(blank=True, null=True)),
                ('profile_picture_url', models.URLField(blank=True, null=True)),
                ('letterboxd_username', models.CharField(blank=True, max_length=100, null=True)),
                ('films_per_page', models.PositiveIntegerField(choices=[(4, '4 films per page'), (8, '8 films per page'), (12, '12 films per page'), (16, '16 films per page'), (20, '20 films per page')], default=8, help_text='Number of films to display per page')),
                ('google_account_id', models.CharField(blank=True, max_length=100, null=True)),
                ('google_email', models.EmailField(blank=True, max_length=254, null=True)),
                ('contact_email', models.EmailField(blank=True, help_text='Email address for notifications (if different from account email)', max_length=254, null=True)),
                ('use_google_email_for_contact', models.BooleanField(default=True, help_text='Use Google email for contact purposes')),
                ('location', models.CharField(blank=True, help_text='Your city, town or region in the UK', max_length=100, null=True)),
                ('gender', models.CharField(choices=[('M', 'Male'), ('F', 'Female'), ('NB', 'Non-binary'), ('O', 'Other'), ('NS', 'Prefer not to say')], default='NS', max_length=2)),
                ('age_range', models.CharField(choices=[('U18', 'Under 18'), ('18-24', '18-24'), ('25-34', '25-34'), ('35-44', '35-44'), ('45-54', '45-54'), ('55-64', '55-64'), ('65+', '65 and over'), ('NS', 'Prefer not to say')], default='NS', max_length=5)),
                ('cinema_frequency', models.CharField(choices=[('weekly', 'Weekly or more'), ('monthly', 'Monthly'), ('quarterly', 'Every few months'), ('yearly', 'A few times a year'), ('rarely', 'Rarely'), ('NS', 'Prefer not to say')], default='NS', help_text='How often do you go to the cinema?', max_length=10)),
                ('viewing_companions', models.CharField(choices=[('alone', 'Usually alone'), ('partner', 'With partner/spouse'), ('family', 'With family'), ('friends', 'With friends'), ('varies', 'It varies'), ('NS', 'Prefer not to say')], default='NS', help_text='Who do you usually go to the cinema with?', max_length=10)),
                ('viewing_time', models.CharField(choices=[('weekday_day', 'Weekday daytime'), ('weekday_evening', 'Weekday evening'), ('weekend_day', 'Weekend daytime'), ('weekend_evening', 'Weekend evening'), ('varies', 'It varies'), ('NS', 'Prefer not to say')], default='NS', help_text='When do you prefer to go to the cinema?', max_length=20)),
                ('price_sensitivity', models.CharField(choices=[('full', 'Willing to pay full price'), ('discount', 'Prefer discount days/times'), ('special', 'Only for special films/events'), ('varies', 'It depends on the film'), ('NS', 'Prefer not to say')], default='NS', help_text='How important is ticket price in your decision to see a film?', max_length=10)),
                ('format_preference', models.CharField(choices=[('standard', 'Standard screening'), ('imax', 'IMAX'), ('3d', '3D'), ('premium', 'Premium (recliner seats, etc.)'), ('varies', 'Depends on the film'), ('NS', 'Prefer not to say')], default='NS', help_text='What format do you prefer to watch films in?', max_length=10)),
                ('travel_distance', models.PositiveIntegerField(default=10, help_text='How far are you willing to travel to a cinema (in miles)?')),
                ('cinema_amenities', models.TextField(blank=True, help_text='What cinema amenities are important to you? (e.g., food service, bar, reclining seats)', null=True)),
                ('film_genres', models.TextField(blank=True, help_text='What film genres do you prefer to see in the cinema?', null=True)),
                ('favorite_cinema', models.CharField(blank=True, help_text='Your preferred cinema or chain', max_length=200, null=True)),
                ('location_privacy', models.CharField(choices=[('public', 'Public - Visible to everyone'), ('users', 'Users - Visible to registered users only'), ('private', 'Private - Visible to only me')], default='private', max_length=10)),
                ('gender_privacy', models.CharField(choices=[('public', 'Public - Visible to everyone'), ('users', 'Users - Visible to registered users only'), ('private', 'Private - Visible to only me')], default='private', max_length=10)),
                ('age_privacy', models.CharField(choices=[('public', 'Public - Visible to everyone'), ('users', 'Users - Visible to registered users only'), ('private', 'Private - Visible to only me')], default='private', max_length=10)),
                ('votes_privacy', models.CharField(choices=[('public', 'Public - Visible to everyone'), ('users', 'Users - Visible to registered users only'), ('private', 'Private - Visible to only me')], default='private', max_length=10)),
                ('favorite_cinema_privacy', models.CharField(choices=[('public', 'Public - Visible to everyone'), ('users', 'Users - Visible to registered users only'), ('private', 'Private - Visible to only me')], default='private', max_length=10)),
                ('cinema_frequency_privacy', models.CharField(choices=[('public', 'Public - Visible to everyone'), ('users', 'Users - Visible to registered users only'), ('private', 'Private - Visible to only me')], default='private', max_length=10)),
                ('viewing_companions_privacy', models.CharField(choices=[('public', 'Public - Visible to everyone'), ('users', 'Users - Visible to registered users only'), ('private', 'Private - Visible to only me')], default='private', max_length=10)),
                ('viewing_time_privacy', models.CharField(choices=[('public', 'Public - Visible to everyone'), ('users', 'Users - Visible to registered users only'), ('private', 'Private - Visible to only me')], default='private', max_length=10)),
                ('price_sensitivity_privacy', models.CharField(choices=[('public', 'Public - Visible to everyone'), ('users', 'Users - Visible to registered users only'), ('private', 'Private - Visible to only me')], default='private', max_length=10)),
                ('format_preference_privacy', models.CharField(choices=[('public', 'Public - Visible to everyone'), ('users', 'Users - Visible to registered users only'), ('private', 'Private - Visible to only me')], default='private', max_length=10)),
                ('travel_distance_privacy', models.CharField(choices=[('public', 'Public - Visible to everyone'), ('users', 'Users - Visible to registered users only'), ('private', 'Private - Visible to only me')], default='private', max_length=10)),
                ('cinema_amenities_privacy', models.CharField(choices=[('public', 'Public - Visible to everyone'), ('users', 'Users - Visible to registered users only'), ('private', 'Private - Visible to only me')], default='private', max_length=10)),
                ('film_genres_privacy', models.CharField(choices=[('public', 'Public - Visible to everyone'), ('users', 'Users - Visible to registered users only'), ('private', 'Private - Visible to only me')], default='private', max_length=10)),
                ('dashboard_activity_privacy', models.CharField(choices=[('public', 'Public - Visible to everyone'), ('users', 'Users - Visible to registered users only'), ('private', 'Private - Visible to only me')], default='public', max_length=10)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='profile', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Achievement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('achievement_type', models.CharField(choices=[('profile_complete', 'Profile Completed'), ('first_vote', 'First Vote'), ('ten_votes', '10 Votes'), ('fifty_votes', '50 Votes'), ('first_tag', 'First Genre Tag'), ('tag_approved', 'Genre Tag Approved'), ('cinema_expert', 'Cinema Expert')], max_length=50)),
                ('date_achieved', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='achievements', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['achievement_type'],
                'unique_together': {('user', 'achievement_type')},
            },
        ),
        migrations.CreateModel(
            name='CinemaPreference',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_favorite', models.BooleanField(default=False, help_text='Whether this is a favorite cinema')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('cinema', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_preferences', to='films_app.cinema')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cinema_preferences', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-is_favorite', '-updated_at'],
                'unique_together': {('user', 'cinema')},
            },
        ),
        migrations.CreateModel(
            name='CinemaVote',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('commitment_level', models.CharField(choices=[('definite', 'Definitely attending'), ('interested', 'Interested'), ('convenient', 'Only if convenient'), ('undecided', 'Undecided')], default='interested', help_text='How committed are you to seeing this film in theaters?', max_length=20)),
                ('preferred_format', models.CharField(choices=[('standard', 'Standard screening'), ('imax', 'IMAX'), ('3d', '3D'), ('premium', 'Premium (recliner seats, etc.)'), ('any', 'Any format')], default='any', help_text='What format would you prefer to see this film in?', max_length=20)),
                ('social_preference', models.CharField(choices=[('solo', 'Going solo'), ('partner', 'With partner'), ('friends', 'With friends'), ('family', 'With family'), ('open', 'Open to company'), ('undecided', 'Undecided')], default='undecided', help_text='Who would you like to see this film with?', max_length=20)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cinema_votes', to=settings.AUTH_USER_MODEL)),
                ('film', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cinema_votes', to='films_app.film')),
            ],
            options={
                'ordering': ['-updated_at'],
                'unique_together': {('user', 'film')},
            },
        ),
        migrations.CreateModel(
            name='GenreTag',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tag', models.CharField(max_length=50)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('is_approved', models.BooleanField(default=False)),
                ('approval_date', models.DateTimeField(blank=True, null=True)),
                ('film', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tags', to='films_app.film')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='genre_tags', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
                'unique_together': {('film', 'user', 'tag')},
            },
        ),
        migrations.CreateModel(
            name='Vote',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('commitment_level', models.CharField(choices=[('definite', 'Definitely attending'), ('interested', 'Interested'), ('convenient', 'Only if convenient'), ('undecided', 'Undecided')], default='interested', help_text='How committed are you to seeing this film in theaters?', max_length=20)),
                ('preferred_format', models.CharField(choices=[('standard', 'Standard screening'), ('imax', 'IMAX'), ('3d', '3D'), ('premium', 'Premium (recliner seats, etc.)'), ('any', 'Any format')], default='any', help_text='What format would you prefer to see this film in?', max_length=20)),
                ('social_preference', models.CharField(choices=[('solo', 'Going solo'), ('partner', 'With partner'), ('friends', 'With friends'), ('family', 'With family'), ('open', 'Open to company'), ('undecided', 'Undecided')], default='undecided', help_text='Who would you like to see this film with?', max_length=20)),
                ('film', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='votes', to='films_app.film')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='votes', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-updated_at'],
                'unique_together': {('user', 'film')},
            },
        ),
    ]
