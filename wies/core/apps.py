from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "wies.core"

    def ready(self):
        # Import the editables package so its REGISTRY dict is built
        # at startup — catches a missing/renamed EditableSet class at
        # boot rather than at first request. Dynamic editables (e.g.
        # one per LabelCategory row) are resolved on-demand via
        # `EditableSet.resolve_dynamic` — no DB access at app start.
        import wies.core.inline_edit.editables  # noqa: PLC0415 — force REGISTRY build at startup
        import wies.core.signals  # noqa: F401, PLC0415 — signal registration must happen inside ready()
