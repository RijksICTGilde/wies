import logging

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.forms.renderers import Jinja2
from django.forms.utils import ErrorList
from django.template import engines

from .models import Colleague, Label, LabelCategory, OrganizationUnit, Skill
from .services.users import validate_email_domain
from .widgets import MultiselectDropdown

logger = logging.getLogger(__name__)

User = get_user_model()


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
        "MultiselectDropdown": "rvo/forms/widgets/multiselect.html",
        "RadioSelect": "rvo/forms/widgets/radio.html",
        "DateInput": "rvo/forms/widgets/date.html",
        "Textarea": "rvo/forms/widgets/textarea.html",
        "CheckboxInput": "rvo/forms/widgets/checkbox.html",
    }

    def _configure_field_for_rvo(self, field_name):
        field = self.fields[field_name]

        # Disable HTML5 client-side required validation
        field.widget.use_required_attribute = lambda _: False
        field.template_name = "rvo/forms/field.html"

        # Auto-assign widget template based on widget type
        widget_class_name = field.widget.__class__.__name__
        if widget_class_name in self.widget_templates:
            field.widget.template_name = self.widget_templates[widget_class_name]
        else:
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


class ProfileLabelsForm(RvoFormMixin, forms.Form):
    """Form for editing a colleague's labels within a single category."""

    def __init__(self, *args, category, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["labels"] = forms.ModelMultipleChoiceField(
            label="",
            queryset=Label.objects.filter(category=category).order_by("name"),
            required=False,
            widget=MultiselectDropdown(),
        )
        self._configure_field_for_rvo("labels")


class UserForm(RvoFormMixin, forms.ModelForm):
    """Form for creating and updating User instances"""

    first_name = forms.CharField(label="Voornaam", required=True)
    last_name = forms.CharField(label="Achternaam", required=True)
    email = forms.EmailField(label="E-mail (ODI)", required=True)
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

    def clean_email(self):
        email = self.cleaned_data.get("email", "").lower()
        validate_email_domain(email, user_facing=True)
        return email

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Map labels stored on model to separate fields per category, which are dynamically generated
        instance = kwargs.get("instance")
        self._category_field_names = set()
        for category in LabelCategory.objects.all():
            field_name = f"category_{category.name}"

            initial = []
            if instance and hasattr(instance, "colleague") and instance.colleague is not None:
                initial = list(instance.colleague.labels.filter(category=category).values_list("pk", flat=True))

            self.fields[field_name] = forms.ModelMultipleChoiceField(
                label=category.name,
                queryset=Label.objects.filter(category=category),
                required=False,
                initial=initial,
                widget=MultiselectDropdown(),
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
            selected_labels = cleaned_data.pop(category_field_name, None)
            if selected_labels:
                cleaned_data["labels"].extend(selected_labels)

        return cleaned_data


class AssignmentCreateForm(RvoFormMixin, forms.Form):
    """Form for creating a new Assignment with services and optional placements."""

    name = forms.CharField(label="Naam opdracht", max_length=200, error_messages={"required": "Vul een naam in."})
    extra_info = forms.CharField(
        label="Beschrijving",
        required=False,
        max_length=5000,
        widget=forms.Textarea(attrs={"rows": 4}),
    )
    start_date = forms.DateField(label="Startdatum", required=False, widget=forms.DateInput())
    end_date = forms.DateField(label="Einddatum", required=False, widget=forms.DateInput())
    owner = forms.ModelChoiceField(
        label="Business Manager",
        queryset=Colleague.objects.filter(user__groups__name="Business Development Manager").order_by("name"),
        required=True,
        empty_label=" ",
        error_messages={"required": "Selecteer een business manager."},
    )

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get("start_date")
        end = cleaned_data.get("end_date")
        if start and end and end < start:
            self.add_error("end_date", "Einddatum moet na startdatum liggen.")
        return cleaned_data


class OrganizationForm(RvoFormMixin, forms.Form):
    """Form for a single organization row within assignment creation."""

    organization = forms.ModelChoiceField(
        label="Opdrachtgever",
        queryset=OrganizationUnit.objects.order_by("name"),
        required=True,
        empty_label=" ",
        error_messages={"required": "Selecteer een opdrachtgever."},
        widget=forms.HiddenInput(),
    )
    role = forms.ChoiceField(
        label="Rol",
        choices=[("PRIMARY", "Primaire opdrachtgever"), ("INVOLVED", "Betrokken opdrachtgever")],
        required=True,
        widget=forms.HiddenInput(),
    )


OrganizationFormSet = forms.formset_factory(OrganizationForm, extra=0, min_num=1, validate_min=True)


class ServiceForm(RvoFormMixin, forms.Form):
    """Form for a single service row within assignment creation."""

    skill = forms.ModelChoiceField(
        label="Rol",
        queryset=Skill.objects.order_by("name"),
        required=False,
        empty_label=" ",
    )
    description = forms.CharField(label="Omschrijving", max_length=500, required=False)
    new_skill_name = forms.CharField(label="Naam nieuwe rol", max_length=30, required=False)
    is_filled = forms.BooleanField(label="Rol ingevuld", required=False)
    colleague = forms.ModelChoiceField(
        label="Consultant",
        queryset=Colleague.objects.order_by("name"),
        required=False,
        empty_label=" ",
    )

    def __init__(self, *args, skill_choices=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Replace ModelChoiceField with a ChoiceField so __new__ is a valid value
        if skill_choices is None:
            skill_choices = [("", " "), ("__new__", "+ Nieuwe rol aanmaken")]
            skill_choices.extend((str(s.id), s.name) for s in Skill.objects.order_by("name"))
        self.fields["skill"] = forms.ChoiceField(
            label="Rol",
            choices=skill_choices,
            required=False,
        )
        self._configure_field_for_rvo("skill")

    def clean(self):
        cleaned_data = super().clean()
        skill_val = cleaned_data.get("skill", "")
        new_skill_name = cleaned_data.get("new_skill_name", "").strip()
        if skill_val == "__new__" and not new_skill_name:
            self.add_error("new_skill_name", "Voer een naam in voor de nieuwe rol.")
        has_skill = (skill_val and skill_val != "__new__") or new_skill_name
        has_other_data = (
            cleaned_data.get("description") or cleaned_data.get("is_filled") or cleaned_data.get("colleague")
        )
        if not has_skill and has_other_data:
            self.add_error("skill", "Selecteer een rol.")
        return cleaned_data


ServiceFormSet = forms.formset_factory(ServiceForm, extra=0, min_num=1, validate_min=False)
