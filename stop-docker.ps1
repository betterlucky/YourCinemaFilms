# Stop Docker containers
Write-Host "Stopping Docker containers..." -ForegroundColor Yellow
docker-compose down

Write-Host "Docker containers stopped" -ForegroundColor Green 