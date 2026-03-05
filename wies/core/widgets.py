from django.forms import SelectMultiple


class MultiselectDropdown(SelectMultiple):
    """Custom dropdown multiselect widget using the multiselect component."""

    template_name = "rvo/forms/widgets/multiselect.html"

    def id_for_label(self, id_, index=None):
        # Return None so the <label> in field.html gets no "for" attribute.
        # The widget uses aria-labelledby instead.
        return None
