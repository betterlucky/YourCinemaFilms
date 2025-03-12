# Start Docker containers
Write-Host "Starting Docker containers..." -ForegroundColor Green
docker-compose up -d

# Wait for services to be ready
Write-Host "Waiting for services to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

# Run migrations
Write-Host "Running migrations..." -ForegroundColor Green
docker-compose exec web python manage.py migrate

# Show running containers
Write-Host "Docker containers running:" -ForegroundColor Cyan
docker-compose ps

Write-Host "Application is running at http://localhost:8080" -ForegroundColor Green 