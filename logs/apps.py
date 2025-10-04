from django.apps import AppConfig


class LogsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'logs'

    def ready(self):
        """
        Este método é executado quando o Django inicia.
        É o local perfeito para importar e conectar os signals.
        """
        import logs.signals