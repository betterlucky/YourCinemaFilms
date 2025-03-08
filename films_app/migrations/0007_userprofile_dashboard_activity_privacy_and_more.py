# Generated by Django 5.1.1 on 2025-03-08 15:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('films_app', '0006_alter_userprofile_film_genres_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='dashboard_activity_privacy',
            field=models.CharField(choices=[('public', 'Public - Visible to everyone'), ('users', 'Users - Visible to registered users only'), ('private', 'Private - Visible to only me')], default='public', max_length=10),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='votes_privacy',
            field=models.CharField(choices=[('public', 'Public - Visible to everyone'), ('users', 'Users - Visible to registered users only'), ('private', 'Private - Visible to only me')], default='private', max_length=10),
        ),
    ]
