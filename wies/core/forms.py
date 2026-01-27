import logging
from typing import override

from django import forms
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.forms.renderers import Jinja2
from django.forms.utils import ErrorList
from django.template import engines
from django.utils import timezone

from .models import Label, LabelCategory, OrganizationType, OrganizationUnit, User

logger = logging.getLogger(__name__)


class RvoJinja2Renderer(Jinja2):
    """Custom renderer that uses Django's configured Jinja2 environment with all globals."""

    @property
    def engine(self):
        return engines["jinja2"]


class RvoErrorList(ErrorList):
    """Custom ErrorList with RVO template"""

    template_name = "rvo/forms/errors/list/default.html"


class RvoFormMixin:
    """
    Mixin to automatically configure forms for RVO design system rendering.

    Usage:
        class MyForm(RvoFormMixin, forms.ModelForm):
            # Just define fields as normal
            name = forms.CharField()

    All RVO templates, error styling, and widget configuration happens automatically.
    This Mixin also disables client-side required checks on fields.
    """

    template_name = "rvo/forms/form.html"
    default_renderer = RvoJinja2Renderer()

    # Widget type to template mapping (only includes widgets with existing templates)
    widget_templates = {
        "TextInput": "rvo/forms/widgets/text.html",
        "EmailInput": "rvo/forms/widgets/email.html",
        "Select": "rvo/forms/widgets/select.html",
        "CheckboxSelectMultiple": "rvo/forms/widgets/checkbox_select.html",
        "RadioSelect": "rvo/forms/widgets/radio.html",
    }

    # Field types that need a custom field template
    field_templates = {
        "CheckboxInput": "rvo/forms/checkbox_field.html",
    }

    def _configure_field_for_rvo(self, field_name):
        field = self.fields[field_name]

        # Disable HTML5 client-side required validation
        field.widget.use_required_attribute = lambda _: False

        # Check if this widget needs a custom field template
        widget_class_name = field.widget.__class__.__name__
        if widget_class_name in self.field_templates:
            field.template_name = self.field_templates[widget_class_name]
        else:
            field.template_name = "rvo/forms/field.html"

        # Auto-assign widget template based on widget type
        if widget_class_name in self.widget_templates:
            field.widget.template_name = self.widget_templates[widget_class_name]
        elif widget_class_name not in self.field_templates:
            logger.warning(
                "Widget '%s' for field '%s' not in RVO widget_templates mapping. Using default Django template.",
                widget_class_name,
                field_name,
            )

    def __init__(self, *args, **kwargs):
        # Set custom error class before calling super
        kwargs.setdefault("error_class", RvoErrorList)
        super().__init__(*args, **kwargs)

        # Configure all fields and widgets for RVO
        for field_name in self.fields:
            self._configure_field_for_rvo(field_name)


class LabelCategoryForm(RvoFormMixin, forms.ModelForm):
    """Form for creating and updating LabelCategory instances"""

    name = forms.CharField(label="Naam", required=True)
    color = forms.ChoiceField(
        label="Kleur label",
        choices=[
            ("#DCE3EA", "Grijs"),
            ("#B3D7EE", "Blauw"),
            ("#FFE9B8", "Geel"),
            ("#C4DBB7", "Groen"),
            ("#F9DFDD", "Rood"),
        ],
        widget=forms.RadioSelect,
    )

    class Meta:
        model = LabelCategory
        fields = ["name", "color"]


class LabelForm(RvoFormMixin, forms.ModelForm):
    """Form for creating and updating Label instances"""

    name = forms.CharField(label="Naam", required=True)

    class Meta:
        model = Label
        fields = ["name"]

    def __init__(self, *args, **kwargs):
        self.category_id = kwargs.pop("category_id", None)
        super().__init__(*args, **kwargs)

    def clean_name(self):
        new_name = self.cleaned_data["name"]
        creating_new_label = self.instance.id is None

        # when creating new one, we need category for validation initiated on form instance
        # when editing, we already have the instance for this
        if creating_new_label:
            if Label.objects.filter(category=self.category_id, name=new_name).exists():
                msg = "Naam wordt al gebruikt"
                raise ValidationError(msg)
            return new_name
        original_name = self.instance.name
        if new_name == original_name:
            return new_name
        if Label.objects.filter(category=self.instance.category, name=new_name).exists():
            msg = "Naam wordt al gebruikt"
            raise ValidationError(msg)
        return new_name


class UserForm(RvoFormMixin, forms.ModelForm):
    """Form for creating and updating User instances"""

    first_name = forms.CharField(label="Voornaam", required=True)
    last_name = forms.CharField(label="Achternaam", required=True)
    email = forms.EmailField(label="Email (ODI)", required=True)
    groups = forms.ModelMultipleChoiceField(
        label="Rollen",
        queryset=Group.objects.filter(),
        required=False,
        widget=forms.CheckboxSelectMultiple(),
    )

    # Init will create category_* fields for the different label categories

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "groups"]
        # label attribute is manually constructed and serialized below

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Map labels stored on model to separate fields per category, which are dynamically generated
        instance = kwargs.get("instance")
        self._category_field_names = set()
        for category in LabelCategory.objects.all():
            field_name = f"category_{category.name}"

            initial = None
            if instance and instance.labels.filter(category=category).exists():
                initial = instance.labels.filter(
                    category=category
                ).first()  # this maps potential multiple in DB to single!

            self.fields[field_name] = forms.ModelChoiceField(
                label=category.name,
                queryset=Label.objects.filter(category=category),
                required=False,
                initial=initial,
            )

            # used in clean
            self._category_field_names.add(field_name)

            # necessary because RVOForm init already ran and otherwise wrong templates are referenced
            self._configure_field_for_rvo(field_name)

    def clean(self):
        cleaned_data = super().clean()

        # combine selected labels into single label attribute
        cleaned_data["labels"] = []
        for category_field_name in self._category_field_names:
            selected_label = cleaned_data.pop(category_field_name)
            if selected_label is not None:
                cleaned_data["labels"].append(selected_label)

        return cleaned_data


class OrganizationUnitForm(RvoFormMixin, forms.ModelForm):
    """Form for creating and updating OrganizationUnit instances."""

    name = forms.CharField(label="Naam", required=True)
    abbreviations_input = forms.CharField(
        label="Afkortingen",
        required=False,
        help_text="Komma-gescheiden (bijv. 'BZK, MinBZK')",
    )
    organization_type = forms.ChoiceField(
        label="Type organisatie",
        choices=OrganizationType.choices,
    )
    parent = forms.ModelChoiceField(
        label="Bovenliggende organisatie",
        queryset=OrganizationUnit.objects.active(),
        required=False,
    )
    is_active = forms.BooleanField(label="Actief", required=False, initial=True)

    class Meta:
        model = OrganizationUnit
        fields = ["name", "organization_type", "parent", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Pre-fill abbreviations_input from model's JSONField
        if self.instance and self.instance.pk and self.instance.abbreviations:
            self.fields["abbreviations_input"].initial = ", ".join(self.instance.abbreviations)

        # Make fields readonly for organizations from external sources
        if self.instance and self.instance.pk and self.instance.is_from_external_source:
            readonly_fields = ["name", "abbreviations_input", "organization_type", "parent", "is_active"]
            for field_name in readonly_fields:
                if field_name in self.fields:
                    self.fields[field_name].disabled = True
                    self.fields[field_name].widget.attrs["disabled"] = True

    def clean(self):
        cleaned_data = super().clean()
        # Run model validation on a temp instance with form data
        temp = OrganizationUnit(
            pk=self.instance.pk if self.instance else None,
            name=cleaned_data.get("name", ""),
            organization_type=cleaned_data.get("organization_type", ""),
            parent=cleaned_data.get("parent"),
        )
        try:
            temp.clean()
        except ValidationError as e:
            # Add error to parent field since hierarchy errors relate to parent selection
            self.add_error("parent", e.message)
        return cleaned_data

    @override
    def save(self, commit=True):
        instance = super().save(commit=False)

        # Track name changes in previous_names history
        if instance.pk:
            old_name = OrganizationUnit.objects.filter(pk=instance.pk).values_list("name", flat=True).first()
            new_name = self.cleaned_data.get("name")
            if old_name and new_name and old_name != new_name:
                history_entry = {"name": old_name, "until": timezone.now().date().isoformat()}
                instance.previous_names.append(history_entry)

        # Convert comma-separated string to list
        abbrev_input = self.cleaned_data.get("abbreviations_input", "")
        if abbrev_input:
            instance.abbreviations = [a.strip() for a in abbrev_input.split(",") if a.strip()]
        else:
            instance.abbreviations = []
        if commit:
            instance.save()
        return instance
