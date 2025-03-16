FROM nginx:latest

# Install Python for reading env.py
RUN apt-get update && \
    apt-get install -y python3 && \
    rm -rf /var/lib/apt/lists/*

# Remove the default configuration
RUN rm /etc/nginx/conf.d/default.conf

# Copy both configurations
COPY conf.d/dev.conf /etc/nginx/conf.d/
COPY conf.d/prod.conf /etc/nginx/conf.d/

# Copy and set up entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
