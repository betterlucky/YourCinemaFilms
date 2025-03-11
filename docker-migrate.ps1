# PowerShell script to help with Docker migration on Windows

# Function to display help
function Show-Help {
    Write-Host "Docker Migration Helper Script (Windows)" -ForegroundColor Cyan
    Write-Host "------------------------------"
    Write-Host "Usage: .\docker-migrate.ps1 [command]"
    Write-Host ""
    Write-Host "Commands:"
    Write-Host "  setup      - Prepare environment for Docker"
    Write-Host "  start      - Start Docker containers"
    Write-Host "  stop       - Stop Docker containers"
    Write-Host "  backup     - Backup database to fixtures"
    Write-Host "  restore    - Restore database from fixtures"
    Write-Host "  logs       - View logs from containers"
    Write-Host "  help       - Show this help message"
    Write-Host ""
}

# Setup environment
function Setup-Environment {
    Write-Host "Setting up environment for Docker..." -ForegroundColor Green
    
    # Copy .env.docker to .env if it doesn't exist
    if (-not (Test-Path .env)) {
        Copy-Item .env.docker .env
        Write-Host "Created .env file from template. Please edit it with your actual values." -ForegroundColor Yellow
    } else {
        Write-Host ".env file already exists. Make sure it contains the necessary Docker variables." -ForegroundColor Yellow
    }
    
    # Create necessary directories
    if (-not (Test-Path static)) { New-Item -ItemType Directory -Path static | Out-Null }
    if (-not (Test-Path media)) { New-Item -ItemType Directory -Path media | Out-Null }
    if (-not (Test-Path profile_images)) { New-Item -ItemType Directory -Path profile_images | Out-Null }
    Write-Host "Created necessary directories." -ForegroundColor Green
    
    Write-Host "Setup complete. Edit your .env file with actual values before starting containers." -ForegroundColor Green
}

# Start containers
function Start-Containers {
    Write-Host "Starting Docker containers..." -ForegroundColor Green
    docker-compose up -d
    Write-Host "Containers started. You can view logs with '.\docker-migrate.ps1 logs'" -ForegroundColor Green
}

# Stop containers
function Stop-Containers {
    Write-Host "Stopping Docker containers..." -ForegroundColor Green
    docker-compose down
    Write-Host "Containers stopped." -ForegroundColor Green
}

# Backup database
function Backup-Database {
    Write-Host "Backing up database to fixtures..." -ForegroundColor Green
    docker-compose exec web python export_data.py
    Write-Host "Backup complete. Check the fixtures directory." -ForegroundColor Green
}

# Restore database
function Restore-Database {
    Write-Host "Restoring database from fixtures..." -ForegroundColor Green
    docker-compose exec web python load_data.py
    Write-Host "Restore complete." -ForegroundColor Green
}

# View logs
function Show-Logs {
    Write-Host "Viewing container logs (press Ctrl+C to exit)..." -ForegroundColor Green
    docker-compose logs -f
}

# Main script logic
$command = $args[0]
switch ($command) {
    "setup" { Setup-Environment }
    "start" { Start-Containers }
    "stop" { Stop-Containers }
    "backup" { Backup-Database }
    "restore" { Restore-Database }
    "logs" { Show-Logs }
    default { Show-Help }
} 