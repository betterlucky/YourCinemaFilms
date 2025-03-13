#!/bin/bash
# Script to fix BBFC image file names for Linux compatibility
# Run this script on your Linux server to create lowercase versions of the BBFC image files

echo "Starting BBFC image fix script..."

# Define directories to check
STATIC_DIRS=("static/img" "staticfiles/img")

for DIR in "${STATIC_DIRS[@]}"; do
    if [ ! -d "$DIR" ]; then
        echo "Directory $DIR does not exist, skipping."
        continue
    fi
    
    echo "Processing directory: $DIR"
    
    # Find all BBFC image files
    BBFC_FILES=$(find "$DIR" -name "BBFC_*.svg")
    
    if [ -z "$BBFC_FILES" ]; then
        echo "No BBFC image files found in $DIR"
        continue
    fi
    
    # Count files
    FILE_COUNT=$(echo "$BBFC_FILES" | wc -l)
    echo "Found $FILE_COUNT BBFC image files"
    
    # Create lowercase versions
    for FILE in $BBFC_FILES; do
        FILENAME=$(basename "$FILE")
        LOWERCASE=$(echo "$FILENAME" | tr '[:upper:]' '[:lower:]')
        DEST="$DIR/$LOWERCASE"
        
        # Skip if source and destination are the same (already lowercase)
        if [ "$FILENAME" = "$LOWERCASE" ]; then
            echo "Skipping $FILENAME - already lowercase"
            continue
        fi
        
        # Skip if the lowercase file already exists and is the same size
        if [ -f "$DEST" ] && [ "$(stat -c%s "$FILE")" = "$(stat -c%s "$DEST")" ]; then
            echo "Skipping $FILENAME - lowercase version already exists"
            continue
        fi
        
        # Copy the file with a lowercase name
        cp "$FILE" "$DEST"
        if [ $? -eq 0 ]; then
            echo "Created lowercase version: $LOWERCASE"
        else
            echo "Error creating lowercase version of $FILENAME"
        fi
    done
done

echo "Script completed. Lowercase versions of BBFC images have been created."
echo ""
echo "IMPORTANT: If you're using Django's collectstatic, run it again to update the staticfiles directory."
echo "Run: python manage.py collectstatic --noinput" 