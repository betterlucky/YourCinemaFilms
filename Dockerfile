FROM python:3.13.1-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Copy entrypoint script and set permissions
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Create db directory with proper permissions
RUN mkdir -p /app/db && chmod 777 /app/db

# Command to run the entrypoint script
CMD ["./entrypoint.sh"] 