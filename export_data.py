#!/usr/bin/env python
"""
Script to export data from the local SQLite database to JSON fixtures.
This data can then be loaded into the PostgreSQL database on Render.
"""

import os
import sys
import json
import django
from django.core.serializers import serialize
from django.core.serializers.json import DjangoJSONEncoder

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'films_project.settings')
django.setup()

from django.contrib.auth.models import User
from films_app.models import Film, Vote, UserProfile, GenreTag

def export_model_data(model, filename):
    """Export model data to a JSON file using Django's serializer."""
    print(f"Exporting {model.__name__} data...")
    
    # Get all objects from the model
    objects = model.objects.all()
    count = objects.count()
    print(f"Found {count} {model.__name__} objects")
    
    # Use Django's built-in serializer
    serialized_data = serialize('json', objects)
    
    # Write data to file
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(serialized_data)
    
    print(f"Exported {count} {model.__name__} objects to {filename}")

def main():
    """Main function to export all data."""
    print("Starting data export...")
    
    # Create fixtures directory if it doesn't exist
    os.makedirs('fixtures', exist_ok=True)
    
    # Export data for each model
    export_model_data(User, 'fixtures/users.json')
    export_model_data(Film, 'fixtures/films.json')
    export_model_data(UserProfile, 'fixtures/userprofiles.json')
    export_model_data(Vote, 'fixtures/votes.json')
    export_model_data(GenreTag, 'fixtures/genretags.json')
    
    # Create a combined fixture file
    print("Creating combined fixture file...")
    combined_data = []
    for filename in ['fixtures/users.json', 'fixtures/films.json', 'fixtures/userprofiles.json', 
                    'fixtures/votes.json', 'fixtures/genretags.json']:
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
                combined_data.extend(data)
    
    with open('fixtures/all_data.json', 'w', encoding='utf-8') as f:
        json.dump(combined_data, f, indent=2)
    
    print("Data export completed successfully!")
    print("You can now copy these files to your Render deployment and load them with:")
    print("python manage.py loaddata fixtures/all_data.json")

if __name__ == "__main__":
    main() 