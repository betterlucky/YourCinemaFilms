FROM python:3.13.1-slim

WORKDIR /app

# Get the host user's UID (replace with your actual UID)
ARG HOST_UID=1000

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    net-tools \
    curl \
    nginx \
    && rm -rf /var/lib/apt/lists/*

# Create a user with the same UID
RUN adduser --disabled-password --gecos "" --uid "${HOST_UID}" appuser

# Create a custom nginx configuration that doesn't use the user directive
RUN echo 'worker_processes auto;\n\
pid /tmp/nginx.pid;\n\
events {\n\
    worker_connections 1024;\n\
}\n\
http {\n\
    include /etc/nginx/mime.types;\n\
    default_type application/octet-stream;\n\
    access_log /tmp/nginx_access.log;\n\
    error_log /tmp/nginx_error.log;\n\
    client_body_temp_path /tmp/client_body;\n\
    proxy_temp_path /tmp/proxy_temp;\n\
    fastcgi_temp_path /tmp/fastcgi_temp;\n\
    uwsgi_temp_path /tmp/uwsgi_temp;\n\
    scgi_temp_path /tmp/scgi_temp;\n\
    include /etc/nginx/conf.d/*.conf;\n\
}' > /etc/nginx/nginx.conf

# Create temp directories for nginx that are writable by appuser
RUN mkdir -p /tmp/client_body /tmp/proxy_temp /tmp/fastcgi_temp /tmp/uwsgi_temp /tmp/scgi_temp \
    && chown -R appuser:appuser /tmp/client_body /tmp/proxy_temp /tmp/fastcgi_temp /tmp/uwsgi_temp /tmp/scgi_temp \
    && chmod -R 777 /tmp/client_body /tmp/proxy_temp /tmp/fastcgi_temp /tmp/uwsgi_temp /tmp/scgi_temp

# Create necessary directories with proper permissions
RUN mkdir -p /app/db /app/staticfiles /etc/yourcinemafilms \
    && chown -R appuser:appuser /app \
    && chmod 755 /app/staticfiles \
    && chmod 777 /app/db \
    && chown -R appuser:appuser /etc/yourcinemafilms \
    && touch /etc/yourcinemafilms/env.py \
    && chown appuser:appuser /etc/yourcinemafilms/env.py \
    && chmod 600 /etc/yourcinemafilms/env.py

# Install Python dependencies
COPY --chown=appuser:appuser requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files with correct ownership
COPY --chown=appuser:appuser . .

# Copy and set permissions for entrypoint script
COPY --chown=appuser:appuser entrypoint.sh .
RUN chmod +x entrypoint.sh

# Switch to non-root user
USER appuser

# Command to run the entrypoint script
CMD ["./entrypoint.sh"] 
