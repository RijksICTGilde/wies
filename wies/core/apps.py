from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "wies.core"

    def ready(self):
        import wies.core.services.filter_order  # noqa: F401, PLC0415
