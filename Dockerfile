FROM python:3.13.1-slim

# Set Python to run in unbuffered mode
ENV PYTHONUNBUFFERED=1
# Prevent Python from writing pyc files
ENV PYTHONDONTWRITEBYTECODE=1
# Set timezone
ENV TZ=UTC

WORKDIR /app

# Get the host user's UID (replace with your actual UID)
ARG HOST_UID=1000

# Install system dependencies and security updates
RUN apt-get update && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends \
    gcc \
    net-tools \
    curl \
    nginx \
    ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* /var/tmp/* \
    && mkdir -p /var/lib/nginx/body \
    && chown -R www-data:www-data /var/lib/nginx

# Create a user with the same UID
RUN adduser --disabled-password --gecos "" --uid "${HOST_UID}" appuser \
    && usermod -aG www-data appuser

# Create necessary directories with proper permissions
RUN mkdir -p /app/db /app/staticfiles /etc/yourcinemafilms \
    && chown -R appuser:www-data /app \
    && chmod 755 /app/staticfiles \
    && chmod 770 /app/db \
    && chown -R appuser:appuser /etc/yourcinemafilms \
    && touch /etc/yourcinemafilms/env.py \
    && chown appuser:appuser /etc/yourcinemafilms/env.py \
    && chmod 600 /etc/yourcinemafilms/env.py

# Install Python dependencies
COPY --chown=appuser:www-data requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && rm -rf ~/.cache/pip/*

# Copy project files with correct ownership
COPY --chown=appuser:www-data . .

# Remove unnecessary files
RUN find . -type f -name '*.pyc' -delete && \
    find . -type d -name '__pycache__' -delete

# Copy and set permissions for entrypoint script
COPY --chown=appuser:www-data entrypoint.sh .
RUN chmod +x entrypoint.sh

# Switch to non-root user
USER appuser

# Set secure umask
RUN echo "umask 027" >> ~/.bashrc

# Command to run the entrypoint script
CMD ["./entrypoint.sh"] 
