#!/bin/bash

# This script sets up a cron job to run the cinema cache update daily

# Define colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "Setting up cron job for YourCinemaFilms cache update..."

# Get the current directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CACHE_SCRIPT="$SCRIPT_DIR/update_cinema_cache.sh"

# Make the update script executable
chmod +x "$CACHE_SCRIPT"

# Check if the script exists
if [ ! -f "$CACHE_SCRIPT" ]; then
    echo -e "${RED}Error: update_cinema_cache.sh not found in $SCRIPT_DIR${NC}"
    exit 1
fi

# Verify Docker is available
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed or not in PATH${NC}"
    exit 1
fi

# Check if the user has Docker permissions
if ! docker ps &> /dev/null; then
    echo -e "${RED}Error: Cannot run Docker commands. Make sure you have the right permissions.${NC}"
    echo "Run the following command and then log out and back in:"
    echo "sudo usermod -aG docker $(whoami)"
    exit 1
fi

# Create a temporary file for the crontab
TEMP_CRON=$(mktemp)

# Export current crontab
crontab -l > "$TEMP_CRON" 2>/dev/null || echo "# YourCinemaFilms cron jobs" > "$TEMP_CRON"

# Check if the cron job already exists
if grep -q "update_cinema_cache.sh" "$TEMP_CRON"; then
    echo -e "${RED}Cron job already exists. Updating...${NC}"
    # Remove the existing cron job
    sed -i '/update_cinema_cache.sh/d' "$TEMP_CRON"
fi

# Add the new cron job to run at 3:00 AM every day
echo "# YourCinemaFilms - Daily cache update at 3:00 AM" >> "$TEMP_CRON"
echo "0 3 * * * $CACHE_SCRIPT" >> "$TEMP_CRON"

# Install the new crontab
if crontab "$TEMP_CRON"; then
    echo -e "${GREEN}Cron job successfully installed!${NC}"
    echo -e "${GREEN}The cache will be updated daily at 3:00 AM.${NC}"
else
    echo -e "${RED}Failed to install cron job.${NC}"
    exit 1
fi

# Clean up
rm "$TEMP_CRON"

echo -e "${GREEN}Setup complete!${NC}"
echo "You can manually run the update script with:"
echo "  $CACHE_SCRIPT"
echo ""
echo "Note: The script is configured to use /app as the base directory in Docker."
echo "Make sure your Docker container is running when the cron job executes."

# Offer to run the script now
read -p "Would you like to run the update script now? (y/n): " RUN_NOW
if [[ $RUN_NOW == "y" || $RUN_NOW == "Y" ]]; then
    echo "Running update script..."
    "$CACHE_SCRIPT"
fi 