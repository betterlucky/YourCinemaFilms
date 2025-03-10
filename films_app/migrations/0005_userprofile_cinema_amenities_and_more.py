# Generated by Django 5.1.1 on 2025-03-08 14:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('films_app', '0004_merge_0003_merge_20250307_2026_ensure_tables'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='cinema_amenities',
            field=models.TextField(blank=True, help_text='What cinema amenities are important to you? (e.g., food service, bar, reclining seats)', null=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='cinema_amenities_privacy',
            field=models.CharField(choices=[('public', 'Public - Visible to everyone'), ('users', 'Users - Visible to registered users only'), ('private', 'Private - Visible to only me')], default='private', max_length=10),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='cinema_frequency',
            field=models.CharField(choices=[('weekly', 'Weekly or more'), ('monthly', 'Monthly'), ('quarterly', 'Every few months'), ('yearly', 'A few times a year'), ('rarely', 'Rarely'), ('NS', 'Prefer not to say')], default='NS', help_text='How often do you go to the cinema?', max_length=10),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='cinema_frequency_privacy',
            field=models.CharField(choices=[('public', 'Public - Visible to everyone'), ('users', 'Users - Visible to registered users only'), ('private', 'Private - Visible to only me')], default='private', max_length=10),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='favorite_cinema',
            field=models.CharField(blank=True, help_text='Your preferred cinema or chain', max_length=200, null=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='favorite_cinema_privacy',
            field=models.CharField(choices=[('public', 'Public - Visible to everyone'), ('users', 'Users - Visible to registered users only'), ('private', 'Private - Visible to only me')], default='private', max_length=10),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='film_genres',
            field=models.TextField(blank=True, help_text='What film genres do you prefer to see in theaters?', null=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='film_genres_privacy',
            field=models.CharField(choices=[('public', 'Public - Visible to everyone'), ('users', 'Users - Visible to registered users only'), ('private', 'Private - Visible to only me')], default='private', max_length=10),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='format_preference',
            field=models.CharField(choices=[('standard', 'Standard screening'), ('imax', 'IMAX'), ('3d', '3D'), ('premium', 'Premium (recliner seats, etc.)'), ('varies', 'Depends on the film'), ('NS', 'Prefer not to say')], default='NS', help_text='What format do you prefer to watch films in?', max_length=10),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='format_preference_privacy',
            field=models.CharField(choices=[('public', 'Public - Visible to everyone'), ('users', 'Users - Visible to registered users only'), ('private', 'Private - Visible to only me')], default='private', max_length=10),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='price_sensitivity',
            field=models.CharField(choices=[('full', 'Willing to pay full price'), ('discount', 'Prefer discount days/times'), ('special', 'Only for special films/events'), ('varies', 'It depends on the film'), ('NS', 'Prefer not to say')], default='NS', help_text='How important is ticket price in your decision to see a film?', max_length=10),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='price_sensitivity_privacy',
            field=models.CharField(choices=[('public', 'Public - Visible to everyone'), ('users', 'Users - Visible to registered users only'), ('private', 'Private - Visible to only me')], default='private', max_length=10),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='travel_distance',
            field=models.CharField(blank=True, help_text="How far are you willing to travel for a film? (e.g., '5 miles', '30 minutes')", max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='travel_distance_privacy',
            field=models.CharField(choices=[('public', 'Public - Visible to everyone'), ('users', 'Users - Visible to registered users only'), ('private', 'Private - Visible to only me')], default='private', max_length=10),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='viewing_companions',
            field=models.CharField(choices=[('alone', 'Usually alone'), ('partner', 'With partner/spouse'), ('family', 'With family'), ('friends', 'With friends'), ('varies', 'It varies'), ('NS', 'Prefer not to say')], default='NS', help_text='Who do you usually go to the cinema with?', max_length=10),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='viewing_companions_privacy',
            field=models.CharField(choices=[('public', 'Public - Visible to everyone'), ('users', 'Users - Visible to registered users only'), ('private', 'Private - Visible to only me')], default='private', max_length=10),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='viewing_time',
            field=models.CharField(choices=[('weekday_day', 'Weekday daytime'), ('weekday_evening', 'Weekday evening'), ('weekend_day', 'Weekend daytime'), ('weekend_evening', 'Weekend evening'), ('varies', 'It varies'), ('NS', 'Prefer not to say')], default='NS', help_text='When do you prefer to go to the cinema?', max_length=20),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='viewing_time_privacy',
            field=models.CharField(choices=[('public', 'Public - Visible to everyone'), ('users', 'Users - Visible to registered users only'), ('private', 'Private - Visible to only me')], default='private', max_length=10),
        ),
    ]
