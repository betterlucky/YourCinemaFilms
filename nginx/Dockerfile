FROM nginx:latest

# Remove the default configuration
RUN rm /etc/nginx/conf.d/default.conf

# Copy your custom configuration
COPY conf.d/app.conf /etc/nginx/conf.d/
