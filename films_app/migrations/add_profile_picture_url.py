from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('films_app', '0001_initial'),  # Replace with your last migration
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='profile_picture_url',
            field=models.URLField(blank=True, null=True),
        ),
    ] 