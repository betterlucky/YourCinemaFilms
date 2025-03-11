# Docker Migration Guide for YourCinemaFilms

This guide will help you migrate your YourCinemaFilms application from Render to Docker, which can then be deployed on your Ubuntu server.

## Prerequisites

### For Windows:
- [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop)
- PowerShell 5.0 or later

### For Ubuntu:
- Docker and Docker Compose:
  ```bash
  sudo apt update
  sudo apt install docker.io docker-compose
  sudo systemctl enable --now docker
  sudo usermod -aG docker $USER  # Add your user to the docker group
  ```
  (Log out and back in for the group changes to take effect)

## Migration Steps

### 1. Prepare Your Environment

#### On Windows:
```powershell
# Run the setup script
.\docker-migrate.ps1 setup
```

#### On Ubuntu:
```bash
# Make the script executable
chmod +x docker-migrate.sh

# Run the setup script
./docker-migrate.sh setup
```

### 2. Configure Environment Variables

Edit the `.env` file created by the setup script with your actual values:
- Set your database credentials
- Add your TMDB API key
- Configure Google OAuth credentials
- Set any other required environment variables

### 3. Export Your Current Data (Optional)

If you want to migrate your existing data:

1. Run the export script on your current setup:
   ```
   python export_data.py
   ```

2. This will create JSON fixtures in the `fixtures` directory

### 4. Start Docker Containers

#### On Windows:
```powershell
.\docker-migrate.ps1 start
```

#### On Ubuntu:
```bash
./docker-migrate.sh start
```

### 5. Import Your Data (If Applicable)

If you exported data in step 3:

#### On Windows:
```powershell
.\docker-migrate.ps1 restore
```

#### On Ubuntu:
```bash
./docker-migrate.sh restore
```

### 6. Verify the Application

Open your browser and navigate to:
- http://localhost (if using Nginx)
- http://localhost:8000 (if accessing Django directly)

## Common Tasks

### View Container Logs

#### On Windows:
```powershell
.\docker-migrate.ps1 logs
```

#### On Ubuntu:
```bash
./docker-migrate.sh logs
```

### Stop Containers

#### On Windows:
```powershell
.\docker-migrate.ps1 stop
```

#### On Ubuntu:
```bash
./docker-migrate.sh stop
```

### Backup Data

#### On Windows:
```powershell
.\docker-migrate.ps1 backup
```

#### On Ubuntu:
```bash
./docker-migrate.sh backup
```

## Troubleshooting

### Database Connection Issues
- Check that the database container is running: `docker ps`
- Verify database credentials in the `.env` file
- Check database logs: `docker-compose logs db`

### Static Files Not Loading
- Make sure the static files are collected: `docker-compose exec web python manage.py collectstatic --noinput`
- Check Nginx configuration and volume mappings

### Permission Issues
- On Ubuntu, you might need to adjust permissions: `sudo chown -R $USER:$USER static media profile_images`

## Moving to Production

When moving to your Ubuntu server:

1. Clone your repository with the Docker configuration
2. Follow the Ubuntu setup steps above
3. Update the `.env` file with production values
4. Update the Nginx configuration in `nginx/conf.d/app.conf` with your domain name
5. Consider setting up SSL with Let's Encrypt

## Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Django Deployment Checklist](https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/) 