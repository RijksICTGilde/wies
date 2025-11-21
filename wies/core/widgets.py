from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import validate_email


class MultiEmailWidget(forms.Widget):
    """Widget that renders multiple email input fields with add/remove buttons."""

    template_name = 'rvo/forms/widgets/multi_email.html'

    def __init__(self, attrs=None):
        default_attrs = {'type': 'email'}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs)

    def value_from_datadict(self, data, files, name):
        """Get list of email values from form data."""
        # Handle multiple values with same name
        if hasattr(data, 'getlist'):
            return [v.strip() for v in data.getlist(name) if v.strip()]
        # Fallback for dict-like data
        value = data.get(name, [])
        if isinstance(value, list):
            return [v.strip() for v in value if v.strip()]
        return [value.strip()] if value and value.strip() else []

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        # Ensure we always have at least one empty field
        if not value:
            value = ['']
        context['widget']['emails'] = value
        return context


class MultiEmailField(forms.Field):
    """Field that handles multiple email values."""

    widget = MultiEmailWidget

    def to_python(self, value):
        """Convert value to list of emails."""
        if not value:
            return []
        return [v.strip() for v in value if v.strip()]

    def validate(self, value):
        """Validate each email in the list."""
        super().validate(value)
        errors = []
        for email in value:
            try:
                validate_email(email)
            except ValidationError:
                errors.append(f'{email} is geen geldig emailadres')
        # Check for duplicates within the list
        seen = set()
        for email in value:
            if email.lower() in seen:
                errors.append(f'{email} komt meerdere keren voor')
            seen.add(email.lower())
        if errors:
            raise ValidationError(errors)
