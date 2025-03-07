from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('films_app', '0001_initial'),  # Replace with your last migration
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='google_account_id',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ] 