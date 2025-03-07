from django.apps import AppConfig


class FilmsAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'films_app'
    
    def ready(self):
        """
        Import signals when the app is ready.
        This ensures that the signal handlers are registered.
        """
        import films_app.signals 