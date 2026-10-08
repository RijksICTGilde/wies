"""Editables for Service. The ``assignment`` FK is not editable — a service
cannot be reparented.

Permissions live in ``wies/core/permissions.py``.
"""

from django import forms
from django.core.validators import MaxValueValidator, MinValueValidator

from wies.core.inline_edit import Editable, EditableSet
from wies.core.models import HOURS_PER_WEEK_CHOICES, MAX_HOURS_PER_WEEK, REQUEST_DURATION_CHOICES, Service


class ServiceEditables(EditableSet):
    class Meta:
        model = Service

    description = Editable(
        label="Taken",
        widget=forms.Textarea(attrs={"rows": 2}),
    )
    request_description = Editable(
        label="Omschrijving",
        widget=forms.Textarea(attrs={"rows": 8}),
        display="forms/displays/textarea.html",
    )
    location = Editable(label="Standplaats")
    duration_months = Editable(
        label="Duur",
        widget=forms.Select(choices=[("", " "), *REQUEST_DURATION_CHOICES]),
        display=lambda s: s.get_duration_months_display() if s.duration_months else "",
    )
    skill = Editable(label="Rol")
    hours_per_week = Editable(
        label="Uren per week",
        widget=forms.Select(choices=HOURS_PER_WEEK_CHOICES),
        # The model's range does not travel to a plain form; repeated here so a
        # posted value outside the select is refused, not stored.
        validators=[MinValueValidator(1), MaxValueValidator(MAX_HOURS_PER_WEEK)],
        display=lambda s: f"{s.hours_per_week} uur" if s.hours_per_week else "",
    )
    period_source = Editable(label="Periode")
    specific_start_date = Editable(label="Specifieke startdatum")
    specific_end_date = Editable(label="Specifieke einddatum")
    status = Editable(label="Status", display=lambda s: s.get_status_display())


def request_period_text(service: Service) -> str:
    """The period of an aanvraag in words: dates where known, otherwise "Per
    direct" for the start and the duration for the end. Empty without either."""
    # Deferred: config.jinja2 imports the editables, so a top-level import is circular.
    from config.jinja2 import datum_nl  # noqa: PLC0415 (import not at top level) — see above

    start = "Per direct" if service.starts_immediately else datum_nl(service.start_date) if service.start_date else ""
    if service.end_date:
        end = f"t/m {datum_nl(service.end_date)}"
        return f"{start} {end}" if start else end
    if service.duration_months:
        duration = service.get_duration_months_display()
        if not start:
            return f"Voor {duration}"
        return f"{start}, voor {duration}" if service.starts_immediately else f"Vanaf {start}, voor {duration}"
    if service.starts_immediately:
        return start
    return f"Vanaf {start}" if start else ""
