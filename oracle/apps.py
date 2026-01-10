from django.apps import AppConfig


class OracleConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'oracle'
    verbose_name = 'Trading Oracle'

    def ready(self):
        """Import signal handlers and register features"""
        # Import features to register them
        from oracle.features import technical, macro, crypto
