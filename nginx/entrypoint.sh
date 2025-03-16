#!/bin/bash

# Wait for env.py to be available (mounted from host)
while [ ! -f /etc/yourcinemafilms/env.py ]; do
    echo "Waiting for env.py to be mounted..."
    sleep 1
done

# Extract production value from env.py using Python
ENVIRONMENT=$(python3 -c '
import sys
sys.path.append("/etc/yourcinemafilms")
from env import production
print("prod" if production else "dev")
')

echo "Environment detected from env.py: $ENVIRONMENT"

# Select the appropriate configuration
if [ "$ENVIRONMENT" = "prod" ]; then
    echo "Using production nginx configuration"
    cp /etc/nginx/conf.d/prod.conf /etc/nginx/conf.d/default.conf
else
    echo "Using development nginx configuration"
    cp /etc/nginx/conf.d/dev.conf /etc/nginx/conf.d/default.conf
fi

# Start nginx
exec nginx -g "daemon off;" 