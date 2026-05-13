import logging

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError

from wies.core.editables.assignment import AssignmentEditables
from wies.core.editables.user import UserEditables

from .form_mixins import RvoErrorList, RvoFormMixin, RvoJinja2Renderer
from .models import Colleague, Label, LabelCategory, Skill
from .services.users import validate_email_domain
from .widgets import MultiselectDropdown

logger = logging.getLogger(__name__)

User = get_user_model()

__all__ = [
    "AssignmentCreateForm",
    "LabelCategoryForm",
    "LabelForm",
    "RvoErrorList",
    "RvoFormMixin",
    "RvoJinja2Renderer",
    "ServiceForm",
    "UserForm",
]


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
    """Form for creating and updating User instances.

    Field configurations for first_name/last_name/email come from
    ``UserEditables`` so the admin form stays in lockstep with the
    inline-edit declarations on the user's own profile page.
    """

    first_name = UserEditables.first_name.form_field()
    last_name = UserEditables.last_name.form_field()
    email = UserEditables.email.form_field()
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
    """Full-page form for creating a new Assignment.

    Field configurations come from ``AssignmentEditables`` so the create
    flow stays in lockstep with the inline-edit declarations. The form
    is a plain ``forms.Form`` (not ``ModelForm``) because the create
    flow handles its own multi-table atomic save (Assignment +
    AssignmentOrganizationUnit + Services + Placements).
    """

    name = AssignmentEditables.name.form_field()
    extra_info = AssignmentEditables.extra_info.form_field()
    start_date = AssignmentEditables.start_date.form_field()
    end_date = AssignmentEditables.end_date.form_field()
    owner = AssignmentEditables.owner.form_field()
    organizations = AssignmentEditables.organizations.form_field()

    def clean(self):
        cleaned = super().clean()
        start, end = cleaned.get("start_date"), cleaned.get("end_date")
        if start and end and end < start:
            raise ValidationError({"end_date": "Einddatum moet na startdatum liggen."})
        return cleaned


class ServiceForm(RvoFormMixin, forms.Form):
    """Form for a single service row within assignment creation and edit.

    ``id`` and ``placement_id`` are hidden round-trip identifiers used by the
    edit-from-side-panel path to diff existing rows against submitted rows.
    Both are empty for newly-added rows on the create form. They are
    attacker-controllable, so the save helper must verify each points at a
    row owned by the target Assignment before writing.
    """

    id = forms.IntegerField(required=False, widget=forms.HiddenInput)
    placement_id = forms.IntegerField(required=False, widget=forms.HiddenInput)
    skill = forms.ModelChoiceField(
        label="Rol",
        queryset=Skill.objects.order_by("name"),
        required=False,
        empty_label=" ",
    )
    description = forms.CharField(label="Toelichting", max_length=500, required=False)
    new_skill_name = forms.CharField(label="Naam nieuwe rol", max_length=30, required=False)
    is_filled = forms.BooleanField(label="Consultant bekend", required=False)
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
        is_filled = cleaned_data.get("is_filled")
        colleague = cleaned_data.get("colleague")
        if is_filled and not colleague:
            self.add_error("colleague", "Selecteer een consultant.")
        # "Rol ingevuld" is the authoritative on/off for the placement.
        # The UI hides (not clears) the colleague select when the
        # checkbox is off, so the posted colleague id would otherwise
        # leak through — treat an unchecked row as "no placement".
        if not is_filled:
            cleaned_data["colleague"] = None
        return cleaned_data


ServiceFormSet = forms.formset_factory(ServiceForm, extra=0, min_num=1, validate_min=False)
