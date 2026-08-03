import re

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase

from wies.core.form_mixins import NlddFormMixin
from wies.core.forms import LabelCategoryForm, UserForm
from wies.core.models import Label, LabelCategory
from wies.core.widgets import MultiselectDropdown

User = get_user_model()


class NlddUserFormRenderingTest(TestCase):
    """Tests for NlddFormMixin functionality and form rendering via UserForm"""

    def setUp(self):
        """Create test data"""
        # Create test labels
        self.category, _ = LabelCategory.objects.get_or_create(name="Merk", defaults={"color": "#0066CC"})
        self.label_a = Label.objects.create(name="Brand A", category=self.category)
        self.label_b = Label.objects.create(name="Brand B", category=self.category)

        # Create test groups for checkbox rendering
        self.admin_group = Group.objects.create(name="Beheerder")
        self.consultant_group = Group.objects.create(name="Consultant")
        self.bdm_group = Group.objects.create(name="Business Development Manager")

    def test_form_renders_with_nldd_classes(self):
        """Text-like fields render real nldd-form-field + nldd-text-field components."""
        form = UserForm()
        rendered = str(form)

        assert "<nldd-form-field" in rendered

        assert re.search(r'<nldd-text-field[^>]*name="first_name"', rendered, re.DOTALL) is not None
        assert re.search(r'<nldd-text-field[^>]*name="email"', rendered, re.DOTALL) is not None
        assert 'class="nldd-input"' not in rendered

    def test_form_displays_validation_errors_with_nldd_classes(self):
        """Validation errors render as nldd-form-field-error-text elements.

        The error text must be wired to its input: nldd-form-field only reveals
        it when the input reflects `invalid` and names the error's id in
        `error-message`. Without that the message renders at height 0 and no
        screen reader announces it.
        """
        form = UserForm(data={})  # missing required fields

        assert not form.is_valid()

        rendered = str(form)

        error_ids = re.findall(r'<nldd-form-field-error-text id="([^"]+)"', rendered)
        assert error_ids, "no error texts rendered with an id"

        for error_id in error_ids:
            assert re.search(
                rf'<nldd-[a-z-]+field[^>]*invalid[^>]*error-message="[^"]*{re.escape(error_id)}',
                rendered,
                re.DOTALL,
            ), f"error text {error_id} is not referenced by an invalid input"

    def test_required_fields_have_required_label_class(self):
        """Optional fields get the `optional` badge; required fields do not."""
        form = UserForm()
        rendered = str(form)

        first_name_field = re.search(r'<nldd-form-field[^>]*label="Voornaam".*?</nldd-form-field>', rendered, re.DOTALL)
        assert first_name_field is not None
        assert "optional" not in first_name_field.group(0)

        email_field = re.search(r'<nldd-form-field[^>]*label="E-mail[^"]*".*?</nldd-form-field>', rendered, re.DOTALL)
        assert email_field is not None
        assert "optional" not in email_field.group(0)

    def test_form_has_no_required_attribute(self):
        """
        Text fields do not carry the HTML required attribute (client-side
        validation is disabled so fields aren't coloured red on first view).
        """
        form = UserForm()
        rendered = str(form)

        first_name = re.search(r'<nldd-text-field[^>]*name="first_name"[^>]*>', rendered, re.DOTALL)
        assert first_name is not None
        assert "required" not in first_name.group(0), (
            f"first_name should not have 'required'. Found: {first_name.group(0)}"
        )

        email = re.search(r'<nldd-text-field[^>]*name="email"[^>]*>', rendered, re.DOTALL)
        assert email is not None
        assert "required" not in email.group(0), f"email should not have 'required'. Found: {email.group(0)}"

    def test_unmapped_widget_logs_warning(self):
        """Test that using an unmapped widget logs a warning"""

        # Create a test form with an unmapped widget (FileInput)
        class TestForm(NlddFormMixin, forms.Form):
            document = forms.FileField(label="Document")

        # Create the form and check that a warning is logged
        with self.assertLogs("wies.core.form_mixins", level="WARNING") as log:
            TestForm()

        # Verify the warning was logged
        assert len(log.output) == 1
        assert "FileInput" in log.output[0]
        assert "document" in log.output[0]
        assert "not in widget_templates mapping" in log.output[0]


class NlddChoiceWidgetErrorWiringTest(TestCase):
    """Validation errors on choice widgets must reach the element nldd-form-field
    inspects (_findInput() = first non-helper child), otherwise the message stays
    hidden and no screen reader announces it.

    nldd-form-field reads `invalid`/`error-message` from that element; the widget
    templates forward them to the host that _findInput() returns. test_forms.py
    already covers text/date widgets — these cover the choice widgets.
    """

    def _first_error_id(self, rendered):
        ids = re.findall(r'<nldd-form-field-error-text id="([^"]+)"', rendered)
        assert ids, "no error text rendered with an id"
        return ids

    def test_radioselect_error_wired_to_group(self):
        """RadioSelect: nldd-radio-button-group carries invalid + error-message."""
        form = LabelCategoryForm(data={"name": ""})  # both name and color missing
        assert not form.is_valid()
        assert "color" in form.errors

        rendered = str(form)
        error_ids = self._first_error_id(rendered)
        assert any(
            re.search(
                rf'<nldd-radio-button-group[^>]*invalid[^>]*error-message="[^"]*{re.escape(eid)}',
                rendered,
                re.DOTALL,
            )
            for eid in error_ids
        ), "radio group is not wired to its error text"

    def _make_choice_form(self, **kwargs):
        class ChoiceForm(NlddFormMixin, forms.Form):
            single = forms.ChoiceField(
                label="Enkel", choices=[("a", "A"), ("b", "B")], widget=forms.Select, required=True
            )
            multi = forms.MultipleChoiceField(
                label="Meer", choices=[("a", "A"), ("b", "B")], widget=MultiselectDropdown, required=True
            )
            boxes = forms.MultipleChoiceField(
                label="Vinkjes", choices=[("a", "A"), ("b", "B")], widget=forms.CheckboxSelectMultiple, required=True
            )

        return ChoiceForm(**kwargs)

    def test_select_error_wired_to_dropdown(self):
        """Select: nldd-dropdown host carries invalid + error-message."""
        form = self._make_choice_form(data={})
        assert not form.is_valid()
        rendered = str(form)

        assert re.search(
            r"<nldd-dropdown[^>]*invalid[^>]*error-message=\"[^\"]+\"",
            rendered,
            re.DOTALL,
        ), "nldd-dropdown is not wired to its error text"

    def test_multiselect_error_wired_to_token_field(self):
        """SelectMultiple: nldd-token-field host carries invalid + error-message."""
        form = self._make_choice_form(data={})
        assert not form.is_valid()
        rendered = str(form)

        assert re.search(
            r"<nldd-token-field[^>]*invalid[^>]*error-message=\"[^\"]+\"",
            rendered,
            re.DOTALL,
        ), "nldd-token-field is not wired to its error text"

    def test_checkbox_select_error_wired_to_first_field(self):
        """CheckboxSelectMultiple: the first nldd-checkbox-field carries the wiring.

        There is no wrapping group, so _findInput() returns the first field; the
        component reflects no `invalid` styling but still shows and announces the
        message via the raw attributes.
        """
        form = self._make_choice_form(data={})
        assert not form.is_valid()
        rendered = str(form)

        assert re.search(
            r"<nldd-checkbox-field[^>]*invalid[^>]*error-message=\"[^\"]+\"",
            rendered,
            re.DOTALL,
        ), "first nldd-checkbox-field is not wired to its error text"


class UserFormEmailDomainValidationTest(TestCase):
    """Tests for email domain validation in UserForm"""

    def setUp(self):
        """Create test data"""
        Group.objects.get_or_create(name="Beheerder")
        Group.objects.get_or_create(name="Consultant")
        Group.objects.get_or_create(name="Business Development Manager")

    def test_valid_rijksoverheid_email(self):
        """Test that @rijksoverheid.nl emails are accepted"""
        form = UserForm(
            data={
                "first_name": "Test",
                "last_name": "User",
                "email": "test.user@rijksoverheid.nl",
            }
        )
        assert form.is_valid(), f"Form should be valid, errors: {form.errors}"

    def test_valid_minbzk_email(self):
        """Test that @minbzk.nl emails are accepted"""
        form = UserForm(
            data={
                "first_name": "Test",
                "last_name": "User",
                "email": "test.user@minbzk.nl",
            }
        )
        assert form.is_valid(), f"Form should be valid, errors: {form.errors}"

    def test_invalid_external_email(self):
        """Test that external email addresses are rejected"""
        form = UserForm(
            data={
                "first_name": "Test",
                "last_name": "User",
                "email": "test.user@gmail.com",
            }
        )
        assert not form.is_valid()
        assert "email" in form.errors
        assert "ODI e-mailadressen" in str(form.errors["email"])

    def test_invalid_client_email(self):
        """Test that client email addresses are rejected"""
        form = UserForm(
            data={
                "first_name": "Test",
                "last_name": "User",
                "email": "test.user@externeclient.nl",
            }
        )
        assert not form.is_valid()
        assert "email" in form.errors

    def test_email_validation_case_insensitive(self):
        """Test that email domain validation is case insensitive"""
        form = UserForm(
            data={
                "first_name": "Test",
                "last_name": "User",
                "email": "test.user@RIJKSOVERHEID.NL",
            }
        )
        assert form.is_valid(), f"Form should accept uppercase domain, errors: {form.errors}"

    def test_edit_existing_user_with_valid_email(self):
        """Test editing an existing user with a valid email domain"""
        user = User.objects.create_user(
            email="existing@rijksoverheid.nl",
            first_name="Existing",
            last_name="User",
        )
        form = UserForm(
            data={
                "first_name": "Updated",
                "last_name": "Name",
                "email": "updated@minbzk.nl",
            },
            instance=user,
        )
        assert form.is_valid(), f"Form should be valid, errors: {form.errors}"

    def test_edit_existing_user_with_invalid_email(self):
        """Test editing an existing user with an invalid email domain is rejected"""
        user = User.objects.create_user(
            email="existing@rijksoverheid.nl",
            first_name="Existing",
            last_name="User",
        )
        form = UserForm(
            data={
                "first_name": "Updated",
                "last_name": "Name",
                "email": "updated@external.com",
            },
            instance=user,
        )
        assert not form.is_valid()
        assert "email" in form.errors


class NlddFormMixinTest(TestCase):
    """Tests that NlddFormMixin renders forms without any RVO classes."""

    RVO_MARKERS = (
        "rvo-",
        "utrecht-textbox",
        "utrecht-select",
        "utrecht-textarea",
        "utrecht-form-field",
        "utrecht-radio-button",
    )

    def setUp(self):
        Group.objects.get_or_create(name="Beheerder")
        Group.objects.get_or_create(name="Consultant")
        Group.objects.get_or_create(name="Business Development Manager")
        self.category, _ = LabelCategory.objects.get_or_create(name="Merk", defaults={"color": "#0066CC"})
        Label.objects.create(name="Brand A", category=self.category)

    def _make_nldd_test_form(self, **kwargs):
        """Create a simple test form using NlddFormMixin."""

        class NlddTestForm(NlddFormMixin, forms.Form):
            first_name = forms.CharField(label="Voornaam", required=True)
            last_name = forms.CharField(label="Achternaam", required=True)
            email = forms.EmailField(label="E-mailadres", required=True)
            role = forms.ChoiceField(label="Rol", choices=[("a", "Admin"), ("b", "User")], required=False)
            notes = forms.CharField(label="Notities", widget=forms.Textarea, required=False)
            active = forms.BooleanField(label="Actief", required=False)

        return NlddTestForm(**kwargs)

    def test_nldd_form_renders_without_rvo_classes(self):
        form = self._make_nldd_test_form()
        rendered = str(form)

        for marker in self.RVO_MARKERS:
            assert marker not in rendered, f"RVO marker '{marker}' found in NLDD form output"

    def test_nldd_form_renders_with_nldd_classes(self):
        form = self._make_nldd_test_form()
        rendered = str(form)

        # Text-like fields use the real components; no hand-rolled nldd-input.
        assert "<nldd-form-field" in rendered
        assert re.search(r'<nldd-text-field[^>]*name="first_name"', rendered, re.DOTALL) is not None
        assert 'class="nldd-input"' not in rendered

    def test_nldd_form_errors_without_rvo_classes(self):
        form = self._make_nldd_test_form(data={})
        assert not form.is_valid()
        rendered = str(form)

        for marker in self.RVO_MARKERS:
            assert marker not in rendered, f"RVO marker '{marker}' found in NLDD form error output"
        # Wired to its input by id, otherwise the component keeps it hidden.
        assert re.search(r'<nldd-form-field-error-text id="[^"]+"', rendered) is not None

    def test_nldd_form_required_label_class(self):
        form = self._make_nldd_test_form()
        rendered = str(form)

        first_name_field = re.search(r'<nldd-form-field[^>]*label="Voornaam".*?</nldd-form-field>', rendered, re.DOTALL)
        assert first_name_field is not None
        assert "optional" not in first_name_field.group(0)

    def test_nldd_form_no_required_attribute(self):
        form = self._make_nldd_test_form()
        rendered = str(form)

        first_name = re.search(r'<nldd-text-field[^>]*name="first_name"[^>]*>', rendered, re.DOTALL)
        assert first_name is not None
        assert "required" not in first_name.group(0)
