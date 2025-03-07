from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('films_app', '0001_initial'),  # Replace with your last migration
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='google_email',
            field=models.EmailField(blank=True, max_length=254, null=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='contact_email',
            field=models.EmailField(blank=True, help_text='Email address for notifications (if different from account email)', max_length=254, null=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='use_google_email_for_contact',
            field=models.BooleanField(default=True, help_text='Use Google email for contact purposes'),
        ),
    ] 