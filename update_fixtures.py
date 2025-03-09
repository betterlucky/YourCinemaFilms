#!/usr/bin/env python
"""
Script to update fixtures to include the popularity field.
"""

import os
import sys
import json
import django

def main():
    """Update fixtures to include the popularity field."""
    print("Starting fixture update process...")
    
    # Set up Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'films_project.settings')
    django.setup()
    
    try:
        # Path to the fixtures file
        fixtures_path = os.path.join('fixtures', 'all_data.json')
        
        if not os.path.exists(fixtures_path):
            print(f"Fixtures file not found at {fixtures_path}")
            return
        
        # Load the fixtures
        with open(fixtures_path, 'r', encoding='utf-8') as f:
            fixtures = json.load(f)
        
        # Update Film model fixtures to include popularity field
        updated_count = 0
        for item in fixtures:
            if item.get('model') == 'films_app.film':
                if 'popularity' not in item.get('fields', {}):
                    item['fields']['popularity'] = 0.0
                    updated_count += 1
        
        print(f"Updated {updated_count} Film model fixtures to include popularity field")
        
        # Save the updated fixtures
        with open(fixtures_path, 'w', encoding='utf-8') as f:
            json.dump(fixtures, f, indent=4, ensure_ascii=False)
        
        print(f"Saved updated fixtures to {fixtures_path}")
        
    except Exception as e:
        print(f"Error updating fixtures: {e}")
        return

if __name__ == "__main__":
    main() 