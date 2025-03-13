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
