#!/usr/bin/env python
"""
Script to fix BBFC image file names for Linux compatibility.
This script creates lowercase versions of the BBFC image files to ensure they work on case-sensitive file systems.
"""

import os
import shutil
import sys

def fix_bbfc_images():
    """Create lowercase versions of BBFC image files."""
    # Define the directories to check
    static_dirs = ['static/img', 'staticfiles/img']
    
    for static_dir in static_dirs:
        if not os.path.exists(static_dir):
            print(f"Directory {static_dir} does not exist, skipping.")
            continue
        
        print(f"Processing directory: {static_dir}")
        
        # Get all BBFC image files
        bbfc_files = [f for f in os.listdir(static_dir) if f.upper().startswith('BBFC_') and f.endswith('.svg')]
        
        if not bbfc_files:
            print(f"No BBFC image files found in {static_dir}")
            continue
        
        print(f"Found {len(bbfc_files)} BBFC image files")
        
        # Create lowercase versions
        for file_name in bbfc_files:
            source_path = os.path.join(static_dir, file_name)
            lowercase_name = file_name.lower()
            dest_path = os.path.join(static_dir, lowercase_name)
            
            # Skip if source and destination are the same (already lowercase)
            if file_name == lowercase_name:
                print(f"Skipping {file_name} - already lowercase")
                continue
                
            # Skip if the lowercase file already exists and is the same size
            if os.path.exists(dest_path) and os.path.getsize(source_path) == os.path.getsize(dest_path):
                print(f"Skipping {file_name} - lowercase version already exists")
                continue
            
            # Copy the file with a lowercase name
            shutil.copy2(source_path, dest_path)
            print(f"Created lowercase version: {lowercase_name}")

if __name__ == "__main__":
    print("Starting BBFC image fix script...")
    fix_bbfc_images()
    print("Script completed. Lowercase versions of BBFC images have been created.") 