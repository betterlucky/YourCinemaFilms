#!/bin/bash

# Log file for output
LOG_DIR="/app/logs"
LOG_FILE="${LOG_DIR}/cache_update_$(date +\%Y\%m\%d).log"

# Create log directory if it doesn't exist - using Docker to ensure proper permissions
echo "Ensuring log directory exists with proper permissions..."
docker-compose exec -T web mkdir -p $LOG_DIR 2>/dev/null || \
docker exec $(docker ps -qf "name=yourcinemafilms_web") mkdir -p $LOG_DIR 2>/dev/null

# Start the log - using Docker to write to the log file
docker-compose exec -T web bash -c "echo '=== Cinema Cache Update Started at $(date) ===' >> $LOG_FILE" 2>/dev/null || \
docker exec $(docker ps -qf "name=yourcinemafilms_web") bash -c "echo '=== Cinema Cache Update Started at $(date) ===' >> $LOG_FILE" 2>/dev/null

# First run the update_release_status command to flag films that need checking
echo "Running update_release_status command via Docker..."
docker-compose exec -T web bash -c "echo 'Running update_release_status command...' >> $LOG_FILE && python manage.py update_release_status --days=7 --batch-size=50 --use-parallel >> $LOG_FILE 2>&1" || \
docker exec $(docker ps -qf "name=yourcinemafilms_web") bash -c "echo 'Running update_release_status command...' >> $LOG_FILE && python manage.py update_release_status --days=7 --batch-size=50 --use-parallel >> $LOG_FILE 2>&1"

# Run the Django management command using Docker with optimized parameters
echo "Running update_movie_cache command via Docker with optimized parameters..."
docker-compose exec -T web bash -c "echo 'Running update_movie_cache command with optimized parameters...' >> $LOG_FILE && python manage.py update_movie_cache --force --max-pages=0 --batch-size=15 --batch-delay=1 --time-window-months=6 --prioritize-flags --use-parallel >> $LOG_FILE 2>&1"

# Check if the command was successful
if [ $? -eq 0 ]; then
    docker-compose exec -T web bash -c "echo 'Cache update completed successfully at $(date)' >> $LOG_FILE" 2>/dev/null || \
    docker exec $(docker ps -qf "name=yourcinemafilms_web") bash -c "echo 'Cache update completed successfully at $(date)' >> $LOG_FILE" 2>/dev/null
else
    docker-compose exec -T web bash -c "echo 'Cache update failed at $(date)' >> $LOG_FILE" 2>/dev/null || \
    docker exec $(docker ps -qf "name=yourcinemafilms_web") bash -c "echo 'Cache update failed at $(date)' >> $LOG_FILE" 2>/dev/null
    
    # Try alternative approach if the first command fails
    echo "Trying alternative Docker command..."
    docker exec $(docker ps -qf "name=yourcinemafilms_web") bash -c "echo 'Trying alternative Docker command...' >> $LOG_FILE && python manage.py update_movie_cache --force --max-pages=0 --batch-size=15 --batch-delay=1 --time-window-months=6 --prioritize-flags --use-parallel >> $LOG_FILE 2>&1"
    
    if [ $? -eq 0 ]; then
        docker exec $(docker ps -qf "name=yourcinemafilms_web") bash -c "echo 'Cache update completed successfully with alternative command at $(date)' >> $LOG_FILE"
    else
        docker exec $(docker ps -qf "name=yourcinemafilms_web") bash -c "echo 'All attempts to update cache failed at $(date)' >> $LOG_FILE"
    fi
fi

# End the log
docker-compose exec -T web bash -c "echo '=== Cinema Cache Update Finished at $(date) ===' >> $LOG_FILE" 2>/dev/null || \
docker exec $(docker ps -qf "name=yourcinemafilms_web") bash -c "echo '=== Cinema Cache Update Finished at $(date) ===' >> $LOG_FILE" 2>/dev/null

# Keep only the last 7 log files - using Docker to ensure proper permissions
docker-compose exec -T web bash -c "find $LOG_DIR -name 'cache_update_*.log' -type f -mtime +7 -delete" 2>/dev/null || \
docker exec $(docker ps -qf "name=yourcinemafilms_web") bash -c "find $LOG_DIR -name 'cache_update_*.log' -type f -mtime +7 -delete" 