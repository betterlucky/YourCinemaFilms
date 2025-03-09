# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('films_app', '0011_activity'),
    ]

    operations = [
        migrations.AddField(
            model_name='film',
            name='popularity',
            field=models.FloatField(default=0, help_text='Popularity score from TMDB API'),
        ),
    ] 