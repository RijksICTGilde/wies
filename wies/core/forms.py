import logging

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import transaction

from wies.core.editables.colleague import LABELS_PREFIX, ColleagueEditables
from wies.core.editables.user import UserEditables

from .form_mixins import NlddFormMixin
from .models import Colleague, Label, LabelCategory, Skill, Suborganization
from .services.users import validate_email_domain
from .widgets import ComboBoxSelect, MultiselectDropdown

logger = logging.getLogger(__name__)

User = get_user_model()

__all__ = [
    "LabelCategoryForm",
    "LabelForm",
    "ServiceForm",
    "SuborganizationForm",
    "UserForm",
]


#: LabelCategory maps each hex to an NLDD colour variant for the tags.
CATEGORY_COLOR_CHOICES = [
    ("#DCE3EA", "Grijs"),
    ("#B3D7EE", "Blauw"),
    ("#FFE9B8", "Geel"),
    ("#C4DBB7", "Groen"),
    ("#F9DFDD", "Rood"),
]


class LabelCategoryForm(NlddFormMixin, forms.ModelForm):
    """Form for creating and updating LabelCategory instances"""

    name = forms.CharField(label="Naam", required=True)
    color = forms.ChoiceField(
        label="Kleur label",
        choices=CATEGORY_COLOR_CHOICES,
        widget=forms.RadioSelect,
    )

    class Meta:
        model = LabelCategory
        fields = ["name", "color"]


class SuborganizationForm(NlddFormMixin, forms.ModelForm):
    """Form for creating and updating Suborganization instances"""

    name = forms.CharField(label="Naam", required=True)

    class Meta:
        model = Suborganization
        fields = ["name"]

    def clean_name(self):
        new_name = self.cleaned_data["name"]
        qs = Suborganization.objects.filter(name__iexact=new_name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            msg = "Naam wordt al gebruikt"
            raise ValidationError(msg)
        return new_name


class ProfileNameForm(NlddFormMixin, forms.ModelForm):
    """Voor- en achternaam samen, zoals de sheet op de profielpagina ze toont.

    De veldconfiguratie komt uit UserEditables, zodat labels en meldingen gelijk
    blijven aan de inline-edit en het beheerformulier.
    """

    first_name = UserEditables.first_name.form_field()
    last_name = UserEditables.last_name.form_field()

    class Meta:
        model = User
        fields = ["first_name", "last_name"]


class ProfileLabelsForm(NlddFormMixin, forms.Form):
    """Every label category in one sheet, with the token fields from onboarding.

    Categories live in the database, so the fields are built per instance
    rather than declared. Each one reuses its ColleagueEditables spec, which
    keeps label, choices and widget identical to the inline edit and to the
    onboarding step.
    """

    def __init__(self, *args, colleague, categories, **kwargs):
        super().__init__(*args, **kwargs)
        self.colleague = colleague
        self._specs = {}
        for category in categories:
            name = f"{LABELS_PREFIX}{category.id}"
            spec = ColleagueEditables.resolve_dynamic(name)
            field = spec.form_field()
            # Every category maps onto the same m2m ("labels"), so the generic
            # initial would hand each field the colleague's labels from all
            # categories at once. Scope it to this category.
            field.initial = list(colleague.labels.filter(category=category))
            # Every category is optional, so the badge would repeat on all of
            # them without telling the user anything they can act on.
            field.widget.attrs["hide-optional"] = True
            self.fields[name] = field
            self._specs[name] = spec
            # The mixin wires templates and labels for the fields that exist
            # when it runs; these are added afterwards, so do it here or they
            # fall back to Django's own form templates.
            self._configure_field(name)

    @transaction.atomic
    def save(self):
        for name, spec in self._specs.items():
            spec.save(self.colleague, self.cleaned_data[name])


class LabelCategoryRowForm(NlddFormMixin, forms.ModelForm):
    """One row in the "Categorieën beheren" sheet: name plus colour.

    The colour lives here because the per-category edit form is gone; the tags
    on the profile, placement and colleague panels still take their colour from
    the category.
    """

    name = forms.CharField(label="Naam", required=True)
    color = forms.ChoiceField(label="Kleur", choices=CATEGORY_COLOR_CHOICES, widget=forms.Select)

    class Meta:
        model = LabelCategory
        fields = ["name", "color"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # De rijen staan onder elkaar in één sheet, dus een zichtbaar "Naam"/
        # "Kleur"-label bij elke rij is ruis. We renderen ze via as_field_group
        # (zodat een validatiefout netjes gekoppeld en zichtbaar is), maar zonder
        # zichtbaar label: het label verhuist naar accessible-label zodat
        # screenreaders het veld nog benoemen.
        for field in self.fields.values():
            field.widget.attrs.setdefault("accessible-label", str(field.label))
            field.label = ""

    def has_changed(self):
        """Een lege nieuwe rij telt niet mee.

        De kleurkeuze post altijd een waarde, dus zonder deze regel geldt een
        zojuist toegevoegde maar niet ingevulde rij als gewijzigd en blokkeert
        haar "naam is verplicht" het opslaan van de rest.
        """
        if not self.instance.pk and not (self.data.get(self.add_prefix("name")) or "").strip():
            return False
        return super().has_changed()


#: Rows are added/removed server-side (the manage view re-renders the body from
#: the posted state), so the formset accepts more rows than the queryset holds;
#: unchanged empty rows are skipped on save (see LabelCategoryRowForm.has_changed).
LabelCategoryFormSet = forms.modelformset_factory(
    LabelCategory,
    form=LabelCategoryRowForm,
    extra=0,
    can_delete=False,
)


class LabelForm(NlddFormMixin, forms.ModelForm):
    """Form for creating and updating Label instances.

    Category is part of the form (a combo box), so one sheet serves both
    "Label toevoegen" and "Label bewerken" — and a label can move to another
    category without being recreated. `category_id` still seeds the field for
    callers that open the form from within a category.
    """

    name = forms.CharField(label="Naam", required=True)
    category = forms.ModelChoiceField(
        label="Categorie",
        queryset=LabelCategory.objects.all(),
        required=False,
        empty_label=None,
        widget=forms.RadioSelect,
    )

    class Meta:
        model = Label
        fields = ["name", "category"]

    def __init__(self, *args, **kwargs):
        category_id = kwargs.pop("category_id", None)
        super().__init__(*args, **kwargs)
        if category_id and not self.initial.get("category"):
            self.initial["category"] = category_id
        # Geen keuze is een geldige keuze (het label komt dan onder het
        # vangnet), maar dat is geen "optioneel veld" om de gebruiker mee lastig
        # te vallen.
        self.fields["category"].widget.attrs["hide-optional"] = True

    def clean(self):
        # Names are unique per category, so the check needs both fields — which
        # is why it lives here and not in clean_name().
        cleaned = super().clean()
        name = cleaned.get("name")
        # Geen keuze gemaakt? Dan onder het vangnet, in plaats van de gebruiker
        # dwingen iets te kiezen dat achteraf toch verhuist.
        category = cleaned.get("category") or LabelCategory.fallback()
        cleaned["category"] = category
        if not name:
            return cleaned
        clash = Label.objects.filter(category=category, name=name).exclude(pk=self.instance.pk)
        if clash.exists():
            self.add_error("name", "Naam wordt al gebruikt in deze categorie")
        return cleaned


class UserForm(NlddFormMixin, forms.ModelForm):
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
    suborganization = forms.ModelChoiceField(
        label="Merk",
        queryset=Suborganization.objects.all(),
        to_field_name="public_id",
        required=False,
        empty_label=" ",
        widget=ComboBoxSelect,
    )

    # Init will create category_* fields for the different label categories

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "groups"]
        # label attribute is manually constructed and serialized below

    def clean_email(self):
        email = self.cleaned_data.get("email", "").lower()
        validate_email_domain(email, user_facing=True)
        qs = User.objects.filter(email__iexact=email)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            msg = "Er bestaat al een gebruiker met dit e-mailadres."
            raise ValidationError(msg)
        return email

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        instance = kwargs.get("instance")

        # Pre-select the colleague's current merk when editing an existing user
        # (suborganization isn't in Meta.fields, so ModelForm won't populate it).
        if instance and hasattr(instance, "colleague") and instance.colleague is not None:
            current_merk = instance.colleague.suborganization
            self.fields["suborganization"].initial = current_merk.public_id if current_merk else None
        self._configure_field("suborganization")

        # Map labels stored on model to separate fields per category, which are dynamically generated
        self._category_field_names = set()
        for category in LabelCategory.objects.all():
            field_name = f"category_{category.name}"

            initial = []
            if instance and hasattr(instance, "colleague") and instance.colleague is not None:
                initial = list(instance.colleague.labels.filter(category=category).values_list("public_id", flat=True))

            self.fields[field_name] = forms.ModelMultipleChoiceField(
                label=category.name,
                queryset=Label.objects.filter(category=category),
                to_field_name="public_id",
                required=False,
                initial=initial,
                widget=MultiselectDropdown(),
            )

            # used in clean
            self._category_field_names.add(field_name)

            # necessary because form init already ran and otherwise wrong templates are referenced
            self._configure_field(field_name)

    def clean(self):
        cleaned_data = super().clean()

        # combine selected labels into single label attribute
        cleaned_data["labels"] = []
        for category_field_name in self._category_field_names:
            selected_labels = cleaned_data.pop(category_field_name, None)
            if selected_labels:
                cleaned_data["labels"].extend(selected_labels)

        return cleaned_data


class ServiceForm(NlddFormMixin, forms.Form):
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
    description = forms.CharField(
        label="Omschrijving rol",
        max_length=500,
        required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
    )
    new_skill_name = forms.CharField(label="Naam nieuwe rol", max_length=30, required=False)
    is_filled = forms.ChoiceField(
        label="Status",
        choices=[("aanvraag", "Aanvraag"), ("ingevuld", "Geplaatste consultant")],
        widget=forms.RadioSelect,
        initial="aanvraag",
        required=False,
    )
    colleague = forms.ModelChoiceField(
        label="Consultant",
        queryset=Colleague.objects.order_by("name"),
        to_field_name="public_id",
        required=False,
        empty_label=" ",
    )
    has_custom_period = forms.BooleanField(label="Neem opdrachtperiode over", required=False, initial=True)
    placement_start_date = forms.DateField(label="Startdatum", required=False)
    placement_end_date = forms.DateField(label="Einddatum", required=False)

    def __init__(self, *args, skill_choices=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Replace ModelChoiceField with a ChoiceField so __new__ is a valid value
        if skill_choices is None:
            skill_choices = [("", " "), ("__new__", "+ Nieuwe rol aanmaken")]
            skill_choices.extend((str(s.public_id), s.name) for s in Skill.objects.order_by("name"))
        self.fields["skill"] = forms.ChoiceField(
            label="Rol",
            choices=skill_choices,
            required=False,
        )
        self._configure_field("skill")

    def clean(self):
        cleaned_data = super().clean()
        skill_val = cleaned_data.get("skill", "")
        new_skill_name = cleaned_data.get("new_skill_name", "").strip()
        # A row the user removed in the UI ("Verwijderen") leaves a gap
        # in the formset indexes that Django re-materialises as a blank
        # form. Treat any row with no identifying content as deleted and
        # skip validation — extract_services_data drops it before save.
        is_empty_row = (
            not cleaned_data.get("id")
            and not skill_val
            and not new_skill_name
            and not cleaned_data.get("description")
            and not cleaned_data.get("colleague")
        )
        if is_empty_row:
            return cleaned_data
        if skill_val == "__new__" and not new_skill_name:
            self.add_error("new_skill_name", "Voer een naam in voor de nieuwe rol.")
        has_skill = (skill_val and skill_val != "__new__") or new_skill_name
        has_other_data = cleaned_data.get("description") or cleaned_data.get("colleague")
        if not has_skill and has_other_data:
            self.add_error("skill", "Selecteer een rol.")
        # has_custom_period checkbox means "Neem opdrachtperiode over" (inverted).
        # Checked = take from assignment = no custom period.
        inherit_from_assignment = cleaned_data.get("has_custom_period", False)
        if inherit_from_assignment:
            cleaned_data["has_custom_period"] = False
            cleaned_data["placement_start_date"] = None
            cleaned_data["placement_end_date"] = None
        else:
            p_start = cleaned_data.get("placement_start_date")
            p_end = cleaned_data.get("placement_end_date")
            cleaned_data["has_custom_period"] = bool(p_start or p_end)
            if not p_start and not p_end:
                self.add_error("placement_start_date", "Vul een periode in of neem de opdrachtperiode over.")
            elif p_start and p_end and p_end < p_start:
                self.add_error("placement_end_date", "Einddatum moet na startdatum liggen.")
        return cleaned_data


ServiceFormSet = forms.formset_factory(ServiceForm, extra=0, min_num=1, validate_min=False)
