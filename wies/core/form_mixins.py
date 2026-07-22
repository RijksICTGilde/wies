"""Shared form-rendering helpers for design system integration.

Lives in its own module so both ``wies.core.forms`` and
``wies.core.inline_edit.forms`` can import form mixins without
creating a circular dependency.
"""

import logging

from django.forms.renderers import Jinja2
from django.forms.utils import ErrorList
from django.template import engines

logger = logging.getLogger(__name__)


class WiesJinja2Renderer(Jinja2):
    """Custom renderer that uses Django's configured Jinja2 environment with all globals."""

    @property
    def engine(self):
        return engines["jinja2"]


class NlddErrorList(ErrorList):
    """Custom ErrorList with NLDD template"""

    template_name = "nldd/forms/errors/list/default.html"


def wire_field_errors(field) -> list[str]:
    """Point a bound field's widget at its error texts, and return their ids.

    ``nldd-form-field`` only reveals an ``nldd-form-field-error-text`` when the
    slotted input reflects ``invalid`` and names it in ``error-message``.
    Without that wiring the messages render at height 0 and screen readers
    never announce them, so the user sees no reason why a save failed.

    Called from the field template because errors only exist after validation,
    long after the widget was configured.
    """
    error_ids = [f"error-{field.html_name}-{i}" for i, _ in enumerate(field.errors, start=1)]
    if error_ids:
        field.field.widget.attrs.update({"invalid": True, "error-message": " ".join(error_ids)})
    return error_ids


class _BaseFormMixin:
    """Shared form configuration logic for any design system.

    Subclasses set ``_form_template``, ``_field_template``, ``_error_class``,
    and ``widget_templates`` to wire up the correct templates.
    """

    _form_template: str
    _field_template: str
    _error_class: type[ErrorList]

    default_renderer = WiesJinja2Renderer()

    widget_templates: dict[str, str] = {}

    # Invisible widgets need no template; skip the warning for them (#389).
    widgets_without_template = {
        "HiddenInput",
        "MultipleHiddenInput",
    }

    # Per-widget extra configuration applied whenever the widget class is
    # mapped to a template. `DateInput` rendering — HTML5 <input type="date">
    # demands ISO yyyy-mm-dd in its value attribute or the browser silently
    # blanks the field; Django's DateInput defaults to the active
    # locale (Dutch dd-mm-yyyy), so we force ISO here.
    widget_config = {
        "DateInput": {"format": "%Y-%m-%d"},
    }

    @property
    def template_name(self):
        return self._form_template

    @template_name.setter
    def template_name(self, value):
        self._form_template = value

    def _configure_field(self, field_name: str) -> None:
        field = self.fields[field_name]

        # Disable HTML5 client-side required validation
        field.widget.use_required_attribute = lambda _: False
        field.template_name = self._field_template

        # Turn off browser autocomplete for every form field by default
        # — Wies fields are domain-specific (Opdracht naam, Looptijd,
        # Collega) and browsers guessing from generic heuristics
        # (name, email) is more nuisance than help.
        field.widget.attrs.setdefault("autocomplete", "off")

        # nldd-form-field labels only its first child, which for these widgets is
        # a wrapper (nldd-dropdown) or a control with no visible label of its own.
        # Without an explicit name the control is unlabelled for screen readers,
        # so derive one from the field label. The native <select> takes plain
        # aria-label; the NLDD components expose accessible-label instead.
        label_attr = {
            "Select": "aria-label",
            "CheckboxInput": "accessible-label",
            "MultiselectDropdown": "accessible-label",
        }.get(field.widget.__class__.__name__)
        if label_attr and field.label:
            field.widget.attrs.setdefault(label_attr, str(field.label))

        # Auto-assign widget template + any per-widget configuration.
        widget_class_name = field.widget.__class__.__name__
        if widget_class_name in self.widget_templates:
            field.widget.template_name = self.widget_templates[widget_class_name]
            for attr, value in self.widget_config.get(widget_class_name, {}).items():
                setattr(field.widget, attr, value)
        elif widget_class_name in self.widgets_without_template:
            pass
        else:
            logger.warning(
                "Widget '%s' for field '%s' not in widget_templates mapping. Using default Django template.",
                widget_class_name,
                field_name,
            )

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("error_class", self._error_class)
        super().__init__(*args, **kwargs)

        for field_name in self.fields:
            self._configure_field(field_name)


class NlddFormMixin(_BaseFormMixin):
    """Configure forms for NLDD design system rendering.

    Every field renders as a real NLDD component; they are form-associated, so
    HTMX and Django form handling keep working without a bridge layer.
    """

    _form_template = "nldd/forms/form.html"
    _field_template = "nldd/forms/field.html"
    _error_class = NlddErrorList

    widget_templates = {
        "TextInput": "nldd/forms/widgets/text.html",
        "EmailInput": "nldd/forms/widgets/email.html",
        "Select": "nldd/forms/widgets/select.html",
        "CheckboxSelectMultiple": "nldd/forms/widgets/checkbox_select.html",
        "MultiselectDropdown": "nldd/forms/widgets/multiselect.html",
        "RadioSelect": "nldd/forms/widgets/radio.html",
        "DateInput": "nldd/forms/widgets/date.html",
        "Textarea": "nldd/forms/widgets/textarea.html",
        "CheckboxInput": "nldd/forms/widgets/checkbox.html",
        "OrgPickerWidget": "nldd/widgets/org_picker.html",
    }
