import logging
from datetime import timedelta
from functools import cached_property

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from wies.core.editables.colleague import LABELS_PREFIX, ColleagueEditables
from wies.core.editables.service import ServiceEditables
from wies.core.editables.user import UserEditables

from .form_mixins import NlddFormMixin
from .models import HOURS_PER_WEEK_CHOICES, Colleague, ContractPeriod, Label, LabelCategory, Suborganization
from .querysets import annotate_placement_dates
from .roles import may_administer_roles, may_change_email, may_grant, role_label
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
    """First and last name together, as the profile page sheet shows them.

    Fields come from UserEditables so labels and messages stay identical to the
    inline edit and the admin form.
    """

    first_name = UserEditables.first_name.form_field()
    last_name = UserEditables.last_name.form_field()

    class Meta:
        model = User
        fields = ["first_name", "last_name"]


class ProfileLabelsForm(NlddFormMixin, forms.Form):
    """Every label category in one sheet, with the token fields from onboarding.

    Categories live in the database, so fields are built per instance rather
    than declared, each reusing its ColleagueEditables spec.
    """

    def __init__(self, *args, colleague, categories, **kwargs):
        super().__init__(*args, **kwargs)
        self.colleague = colleague
        self._specs = {}
        for category in categories:
            name = f"{LABELS_PREFIX}{category.id}"
            spec = ColleagueEditables.resolve_dynamic(name)
            field = spec.form_field()
            # Every category maps onto the same "labels" m2m, so the generic
            # initial would hand each field all categories at once.
            field.initial = list(colleague.labels.filter(category=category))
            # Every category is optional, so the badge would repeat on all of them.
            field.widget.attrs["hide-optional"] = True
            self.fields[name] = field
            self._specs[name] = spec
            # The mixin only wires fields that exist when it runs; these are added
            # afterwards, so configure them here or they fall back to Django's templates.
            self._configure_field(name)

    @transaction.atomic
    def save(self):
        for name, spec in self._specs.items():
            spec.save(self.colleague, self.cleaned_data[name])


class LabelCategoryRowForm(NlddFormMixin, forms.ModelForm):
    """One row in the "Categorieën beheren" sheet: name plus colour."""

    name = forms.CharField(label="Naam", required=True)
    color = forms.ChoiceField(label="Kleur", choices=CATEGORY_COLOR_CHOICES, widget=forms.Select)

    class Meta:
        model = LabelCategory
        fields = ["name", "color"]

    def clean_name(self):
        name = self.cleaned_data.get("name", "")
        qs = LabelCategory.objects.filter(name=name)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            msg = "Er bestaat al een categorie met deze naam."
            raise ValidationError(msg)
        return name

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Table layout has no visible label, so move it to accessible-label.
        for field in self.fields.values():
            field.widget.attrs.setdefault("accessible-label", str(field.label))
            field.label = ""

    def has_changed(self):
        """Reports whether the row changed, treating a blank new row as unchanged.

        Colour always posts, so without this the empty row counts as changed and
        its "naam is verplicht" error blocks the save.
        """
        if not self.instance.pk and not (self.data.get(self.add_prefix("name")) or "").strip():
            return False
        return super().has_changed()


#: Rows are added/removed server-side, so the formset accepts more rows than the
#: queryset holds; empty rows are skipped on save (see has_changed).
LabelCategoryFormSet = forms.modelformset_factory(
    LabelCategory,
    form=LabelCategoryRowForm,
    extra=0,
    can_delete=False,
    min_num=0,
    max_num=1000,
)


class LabelForm(NlddFormMixin, forms.ModelForm):
    """Form for creating and updating Label instances.

    Category is part of the form, so one sheet serves both "Label toevoegen"
    and "Label bewerken" and a label can move category without being recreated.
    ``category_id`` seeds the field for callers opening it within a category.
    """

    name = forms.CharField(label="Naam", required=True)
    category = forms.ModelChoiceField(
        label="Categorie",
        queryset=LabelCategory.objects.all(),
        required=True,
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

    def clean(self):
        # Names are unique per category, so the check needs both fields and
        # cannot live in clean_name().
        cleaned = super().clean()
        name = cleaned.get("name")
        category = cleaned.get("category")
        # A missing field already has its own error; nothing to check here.
        if not name or not category:
            return cleaned
        clash = Label.objects.filter(category=category, name=name).exclude(pk=self.instance.pk)
        if clash.exists():
            self.add_error("name", "Naam wordt al gebruikt in deze categorie")
        return cleaned


class RoleChoiceIterator(forms.models.ModelChoiceIterator):
    """Sorts the checkboxes by label: the queryset can only order on ``Group.name``,
    which is a key, so its A-Z is not the reader's."""

    def __iter__(self):
        yield from sorted(super().__iter__(), key=lambda choice: str(choice[1]))


class RoleChoiceField(forms.ModelMultipleChoiceField):
    """Roles as checkboxes, each shown by its label while the submitted value stays
    the Group id."""

    iterator = RoleChoiceIterator

    def label_from_instance(self, obj):
        return role_label(obj.name)


class UserForm(NlddFormMixin, forms.ModelForm):
    """Form for creating and updating User instances: the person and their roles.

    Name and email fields come from ``UserEditables`` so the admin form stays
    in lockstep with the inline-edit declarations on the profile page.

    The two halves are offered on their own gate and a half the editor may not
    touch is left out of ``self.fields``, so a submitted value for it is ignored.
    Why they are split: ``features/roles.md``.
    """

    first_name = UserEditables.first_name.form_field()
    last_name = UserEditables.last_name.form_field()
    email = UserEditables.email.form_field()
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
        fields = ["first_name", "last_name", "email"]
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
        # Creating asks it too, with "" as the address it comes from (``features/roles.md``).
        if not may_change_email(self._editor, self.instance.email, email):
            msg = (
                "Alleen applicatiebeheer mag dit e-mailadres wijzigen."
                if self.instance.pk
                else "Alleen applicatiebeheer mag een gebruiker op dit e-mailadres aanmaken."
            )
            raise ValidationError(msg)
        return email

    def __init__(self, *args, editor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._editor = editor

        instance = kwargs.get("instance")
        self._category_field_names = set()

        if self.edits_person:
            self._add_person_fields(instance)
        else:
            for name in ("first_name", "last_name", "email", "suborganization"):
                del self.fields[name]

        if editor is None or may_administer_roles(editor):
            self._add_role_field(editor, instance)

    @cached_property
    def edits_person(self) -> bool:
        """Whether the editor may write name, email, merk and labels.

        ``rijksauth.change_user``, the sibling of the ``add_user`` and
        ``delete_user`` the other two user routes ask. Creating has nothing to ask
        it about: that route is behind ``rijksauth.add_user`` and reaches no
        existing person. ``editor=None`` is the system, as it is in ``may_grant``.
        """
        if self.instance is None or self.instance.pk is None or self._editor is None:
            return True
        return self._editor.has_perm("rijksauth.change_user")

    def _add_person_fields(self, instance):
        # suborganization isn't in Meta.fields, so ModelForm won't populate it.
        if instance and hasattr(instance, "colleague") and instance.colleague is not None:
            current_merk = instance.colleague.suborganization
            self.fields["suborganization"].initial = current_merk.public_id if current_merk else None
        self._configure_field("suborganization")

        # Map the labels m2m onto one dynamically built field per category.
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

            self._category_field_names.add(field_name)

            # Form init already ran, so configure here or the wrong templates apply.
            self._configure_field(field_name)

    def _add_role_field(self, editor, instance):
        """The roles the editor may grant, as checkboxes.

        The queryset is also what submitted ids are validated against, so a role
        the editor may not grant is refused server-side, not only left unrendered.
        """
        withheld = [name for name in Group.objects.values_list("name", flat=True) if not may_grant(editor, name)]
        self.fields["groups"] = RoleChoiceField(
            label="Rollen",
            queryset=Group.objects.exclude(name__in=withheld).order_by("name"),
            required=False,
            initial=list(instance.groups.all()) if instance and instance.pk else [],
            widget=forms.CheckboxSelectMultiple(),
        )
        self._configure_field("groups")

    def clean(self):
        cleaned_data = super().clean()

        # Combine the per-category selections back into one labels list.
        cleaned_data["labels"] = []
        for category_field_name in self._category_field_names:
            selected_labels = cleaned_data.pop(category_field_name, None)
            if selected_labels:
                cleaned_data["labels"].extend(selected_labels)

        return cleaned_data


class UserDeleteForm(NlddFormMixin, forms.Form):
    """Asked when deleting a user with a colleague profile: the day the contract
    and the placements end.

    Required only while there is something to end; without contract periods
    and placements the day is just recorded with the deletion.
    """

    left_on = forms.DateField(
        label="Uit dienst per",
        help_text="Wat op die dag loopt, eindigt dan. Wat daarna zou beginnen, vervalt.",
    )

    def __init__(self, *args, colleague=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.colleague = colleague
        self.periods = colleague.contract_periods.all() if colleague else ContractPeriod.objects.none()
        has_placements = colleague is not None and colleague.placements.exists()
        if not self.periods.exists() and not has_placements:
            self.fields["left_on"].required = False
            self.fields["left_on"].help_text = "Wordt vastgelegd bij de verwijdering."

    def clean(self):
        cleaned = super().clean()
        day = cleaned.get("left_on")
        # A day before every period would leave nothing to end and drop them
        # all, which is the history this model exists to keep.
        if day and self.periods.exists() and not self.periods.filter(start_date__lte=day).exists():
            self.add_error("left_on", "Deze dag ligt vóór elke contractperiode. Kies een dag binnen of na een periode.")
        # Same for placements: a day before one that has already started would
        # drop it, and with it the record that this person worked there.
        if day and self.colleague is not None:
            today = timezone.now().date()
            started = [
                p
                for p in annotate_placement_dates(self.colleague.placements.all())
                if p.actual_start_date is not None and p.actual_start_date <= today
            ]
            if any(p.actual_start_date > day for p in started):
                self.add_error("left_on", "Deze dag ligt vóór een plaatsing die al is begonnen. Kies een dag daarna.")
        return cleaned


class ContractPeriodForm(NlddFormMixin, forms.ModelForm):
    """One contract period, in a sheet on the user sheet.

    The colleague comes from the view as the instance; the model's clean() keeps
    the period inside the hours range and clear of the colleague's other periods.

    Adding a period usually means a change of hours: the running period has no
    end yet. The sheet says so, starts from that period's hours, and
    ``end_running_period`` ends it the day before the new start, so the
    beheerder does not have to close it by hand first. An empty end date means
    the period runs on; the sheet hides the field behind an "Einddatum is
    bekend" switch, like the placement forms.
    """

    start_date = forms.DateField(label="Startdatum")
    end_date = forms.DateField(label="Einddatum", required=False)

    class Meta:
        model = ContractPeriod
        fields = ["hours_per_week", "start_date", "end_date"]
        widgets = {"hours_per_week": forms.Select(choices=HOURS_PER_WEEK_CHOICES)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.running = None if self.instance.pk else self._running_period()
        if self.running is not None:
            # On form.initial, not the field: the unsaved instance already puts
            # hours_per_week=None in form.initial, and that wins over the field's.
            self.initial["hours_per_week"] = self.running.hours_per_week

    def _running_period(self):
        """The colleague's period that covers today, if any."""
        if self.instance.colleague_id is None:
            return None
        today = timezone.now().date()
        return (
            self.instance.colleague.contract_periods.filter(start_date__lte=today)
            .filter(Q(end_date__isnull=True) | Q(end_date__gte=today))
            .first()
        )

    def end_running_period(self):
        """Ends the running period the day before the new start.

        Runs before validation, so the overlap check then sees the ended
        period; the view wraps both in a transaction and rolls back when the
        new period does not validate. Returns the ended period, or None.
        """
        if self.running is None:
            return None
        try:
            start = self.fields["start_date"].clean(self.data.get(self.add_prefix("start_date")))
        except ValidationError:
            return None
        # Only ever shortens: a period that already ends before the new start
        # is left alone, so this never stretches a contract.
        if start <= self.running.start_date or (self.running.end_date is not None and self.running.end_date < start):
            return None
        self.running.end_date = start - timedelta(days=1)
        self.running.save(update_fields=["end_date"])
        return self.running


class ServiceForm(NlddFormMixin, forms.Form):
    """Form for a single service row within assignment creation and edit.

    ``service_public_id`` and ``placement_public_id`` are hidden round-trip
    identifiers (UUIDs) that tell the save helper which existing rows this
    submission edits, and are empty for new rows. They are attacker-controllable,
    so the save helper must verify each points at a row owned by the target
    Assignment before writing.
    """

    service_public_id = forms.UUIDField(required=False, widget=forms.HiddenInput)
    placement_public_id = forms.UUIDField(required=False, widget=forms.HiddenInput)
    # A plain ChoiceField (not ModelChoiceField), so the "__new__" sentinel is a
    # valid submitted value; its choices are DB-driven and injected in __init__.
    skill = forms.ChoiceField(label="Rol", choices=(), required=True)
    description = forms.CharField(
        label="Omschrijving rol",
        max_length=500,
        required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
    )
    new_skill_name = forms.CharField(label="Naam nieuwe rol", max_length=30, required=False)
    # Hours belong to the role, so an open aanvraag carries them too. A list,
    # not a number input: nldd-text-field has no number type.
    hours_per_week = ServiceEditables.hours_per_week.form_field()
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

    def __init__(self, *args, skill_choices, **kwargs):
        super().__init__(*args, **kwargs)
        # `skill_choices` is always supplied by the caller in editables/assignment.py.
        self.fields["skill"].choices = skill_choices

    def clean(self):
        cleaned_data = super().clean()
        skill_val = cleaned_data.get("skill", "")
        new_skill_name = cleaned_data.get("new_skill_name", "").strip()
        if skill_val == "__new__" and not new_skill_name:
            self.add_error("new_skill_name", "Voer een naam in voor de nieuwe rol.")
        # "Geplaatste consultant" without a name would silently save as a vacancy
        # (no placement), so require the consultant the status promises.
        if cleaned_data.get("is_filled") == "ingevuld" and not cleaned_data.get("colleague"):
            self.add_error("colleague", "Selecteer een consultant.")
        # The checkbox is inverted: checked means "inherit the assignment
        # period", i.e. no custom period.
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
