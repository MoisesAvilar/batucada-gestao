from django.apps import AppConfig


class LogsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "logs"

    def ready(self):
        print("DEBUG [LogsConfig] App 'logs' iniciando e importando signals...")
        import logs.signals
