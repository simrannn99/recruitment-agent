from django.apps import AppConfig


class RecruitmentConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'recruitment'
    
    def ready(self):
        """Import signals when the app is ready."""
        import recruitment.signals  # noqa
