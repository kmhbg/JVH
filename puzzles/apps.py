from django.apps import AppConfig

class PuzzlesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'puzzles'

    def ready(self):
        import puzzles.signals  # noqa 