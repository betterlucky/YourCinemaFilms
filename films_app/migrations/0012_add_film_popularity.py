# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('films_app', '0010_film_is_in_cinema_film_uk_certification_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='film',
            name='popularity',
            field=models.FloatField(default=0, help_text='Popularity score from TMDB API'),
        ),
    ] 