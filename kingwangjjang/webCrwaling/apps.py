from django.apps import AppConfig
from .tasks import scheduler


class WebcrwalingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'webCrwaling'

    def ready(self):
        scheduler.start()
  