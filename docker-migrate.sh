#!/bin/bash
# Script to help with Docker migration

# Make script executable
chmod +x docker-migrate.sh

# Function to display help
show_help() {
    echo "Docker Migration Helper Script"
    echo "------------------------------"
    echo "Usage: ./docker-migrate.sh [command]"
    echo ""
    echo "Commands:"
    echo "  setup      - Prepare environment for Docker"
    echo "  start      - Start Docker containers"
    echo "  stop       - Stop Docker containers"
    echo "  backup     - Backup database to fixtures"
    echo "  restore    - Restore database from fixtures"
    echo "  logs       - View logs from containers"
    echo "  help       - Show this help message"
    echo ""
}

# Setup environment
setup() {
    echo "Setting up environment for Docker..."
    
    # Copy .env.docker to .env if it doesn't exist
    if [ ! -f .env ]; then
        cp .env.docker .env
        echo "Created .env file from template. Please edit it with your actual values."
    else
        echo ".env file already exists. Make sure it contains the necessary Docker variables."
    fi
    
    # Create necessary directories
    mkdir -p static media profile_images
    echo "Created necessary directories."
    
    echo "Setup complete. Edit your .env file with actual values before starting containers."
}

# Start containers
start() {
    echo "Starting Docker containers..."
    docker-compose up -d
    echo "Containers started. You can view logs with './docker-migrate.sh logs'"
}

# Stop containers
stop() {
    echo "Stopping Docker containers..."
    docker-compose down
    echo "Containers stopped."
}

# Backup database
backup() {
    echo "Backing up database to fixtures..."
    docker-compose exec web python export_data.py
    echo "Backup complete. Check the fixtures directory."
}

# Restore database
restore() {
    echo "Restoring database from fixtures..."
    docker-compose exec web python load_data.py
    echo "Restore complete."
}

# View logs
logs() {
    echo "Viewing container logs (press Ctrl+C to exit)..."
    docker-compose logs -f
}

# Main script logic
case "$1" in
    setup)
        setup
        ;;
    start)
        start
        ;;
    stop)
        stop
        ;;
    backup)
        backup
        ;;
    restore)
        restore
        ;;
    logs)
        logs
        ;;
    help|*)
        show_help
        ;;
esac 