# YourCinemaFilms Cache Update Cron Job Setup for Docker

This guide explains how to set up a daily cron job to update the cinema cache for YourCinemaFilms running in Docker on your Ubuntu server.

## Files

- `update_cinema_cache.sh`: The main script that updates the cinema cache using Docker
- `setup_cron.sh`: A helper script to set up the cron job
- `CRON_SETUP_README.md`: This README file

## Setup Instructions

### 1. Prepare the Scripts

1. Upload these files to your Ubuntu server
2. The script is already configured to use `/app` as the base directory, which is the standard mount point in Docker:
   ```bash
   # In Docker, the application is mounted at /app/
   cd /app
   ```

3. If your Docker container name is different from `yourcinemafilms_web`, update it in the script:
   ```bash
   docker exec $(docker ps -qf "name=yourcinemafilms_web") python manage.py update_movie_cache --force
   ```

4. Make both scripts executable:
   ```bash
   chmod +x update_cinema_cache.sh setup_cron.sh
   ```

### 2. Set Up the Cron Job

Run the setup script:
```bash
./setup_cron.sh
```

This will:
- Make the update script executable
- Add a cron job to run the update script daily at 3:00 AM
- Offer to run the update script immediately

### 3. Verify the Cron Job

Check that the cron job was added correctly:
```bash
crontab -l
```

You should see a line like:
```
0 3 * * * /path/to/update_cinema_cache.sh
```

### 4. Check the Logs

After the script runs (either manually or via cron), you can check the logs:
```bash
cat /app/logs/cache_update_YYYYMMDD.log
```

Replace `YYYYMMDD` with the current date.

## Docker-Specific Notes

The script uses `docker-compose exec` to run the management command inside your running Docker container. This requires:

1. The Docker container must be running when the cron job executes
2. The user running the cron job must have permission to execute Docker commands

If the first approach fails, the script will try an alternative method using `docker exec` with the container ID.

### Docker Permissions

To ensure the cron job can run Docker commands:

1. Add the user to the docker group:
   ```bash
   sudo usermod -aG docker $(whoami)
   ```

2. Log out and log back in for the changes to take effect

3. Test that you can run Docker commands without sudo:
   ```bash
   docker ps
   ```

## Troubleshooting

### Script Not Running

1. Check if the cron service is running:
   ```bash
   systemctl status cron
   ```

2. Check the cron logs:
   ```bash
   grep CRON /var/log/syslog
   ```

3. Ensure the script has execute permissions:
   ```bash
   chmod +x update_cinema_cache.sh
   ```

4. Check for syntax errors in the script:
   ```bash
   bash -n update_cinema_cache.sh
   ```

### Docker Issues

1. Check if the Docker container is running:
   ```bash
   docker ps | grep web
   ```

2. Test the Docker command manually:
   ```bash
   docker-compose exec web python manage.py update_movie_cache --force
   ```

3. Check Docker permissions:
   ```bash
   groups | grep docker
   ```

### Permission Issues

If you see permission errors in the logs:

1. Ensure the log directory exists and is writable:
   ```bash
   mkdir -p /app/logs
   chmod 755 /app/logs
   ```

2. Check if the script can access the Docker socket:
   ```bash
   ls -la /var/run/docker.sock
   ```

## Customization

### Change the Update Time

To change when the script runs, edit the cron job:
```bash
crontab -e
```

The format is:
```
minute hour day-of-month month day-of-week command
```

For example, to run at 5:30 AM:
```
30 5 * * * /path/to/update_cinema_cache.sh
```

### Add Email Notifications

To receive email notifications when the script runs, add a MAILTO line to your crontab:
```bash
crontab -e
```

Add this line at the top:
```
MAILTO=your-email@example.com
```

## Manual Update

To manually update the cache at any time:
```bash
./update_cinema_cache.sh
```

# Docker Permission Considerations

The script has been designed to handle permission issues by:

1. Using Docker commands to create the log directory inside the container
2. Writing all logs through Docker commands to ensure proper file ownership
3. Cleaning up old log files through Docker commands

This approach ensures that all file operations are performed by the same user that runs your application inside the container, avoiding permission conflicts between the host system and the container.

### Checking Logs

To view the logs, you'll need to use Docker:

```bash
docker-compose exec web cat /app/logs/cache_update_YYYYMMDD.log
```

Or:

```bash
docker exec $(docker ps -qf "name=yourcinemafilms_web") cat /app/logs/cache_update_YYYYMMDD.log
```

This approach is much more robust because:

1. All file operations (creating directories, writing logs, cleaning up) are performed inside the container
2. The operations use the same user that runs your application inside the container
3. We don't rely on the host system's permissions to write to container-mounted volumes
4. Both docker-compose and direct docker exec commands are tried for better compatibility

Would this approach address your permission concerns? If you've encountered specific permission errors, I can further tailor the solution to your exact setup.

## How This Works

This setup uses a cron job that runs on your host Ubuntu server (not inside the Docker container). The cron job:

1. Executes at the scheduled time (3:00 AM by default)
2. Runs the `update_cinema_cache.sh` script on the host system
3. The script uses `docker-compose exec` or `docker exec` commands to run operations inside your Docker container
4. This approach ensures that all file operations happen with the correct permissions inside the container

### Important Requirements

For this to work properly:

1. Docker and docker-compose must be installed on the host system
2. The Docker container must be running when the cron job executes
3. The user running the cron job must have permission to execute Docker commands
4. The container name must match what's in the script (`yourcinemafilms_web` by default) 