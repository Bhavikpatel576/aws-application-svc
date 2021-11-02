from django.apps import AppConfig    # pragma: no cover


class ApplicationConfig(AppConfig):  # pragma: no cover
    name = 'application'

    def ready(self):
        import application.signals  # noqa: F401
