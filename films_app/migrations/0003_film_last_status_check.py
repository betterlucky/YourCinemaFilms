# Generated by Django 5.1.1 on 2025-03-14 17:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('films_app', '0002_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='film',
            name='last_status_check',
            field=models.DateTimeField(blank=True, help_text='When this film was last checked for status updates', null=True),
        ),
    ]
