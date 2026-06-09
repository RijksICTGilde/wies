import re

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase

from wies.core.form_mixins import NlddFormMixin
from wies.core.forms import RvoFormMixin, UserForm
from wies.core.models import Label, LabelCategory

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
        """Test that forms using NlddFormMixin render with NLDD design system classes"""
        form = UserForm()
        rendered = str(form)

        # Check that form fields are wrapped with NLDD classes
        assert "nldd-form-field" in rendered
        assert "nldd-form-field__label" in rendered

        # Check that text inputs have NLDD classes
        first_name_input_match = re.search(r'<input[^>]*name="first_name"[^>]*>', rendered)
        assert first_name_input_match is not None
        first_name_input = first_name_input_match.group(0)
        assert "nldd-input" in first_name_input

        # Check that email input has NLDD classes
        email_input_match = re.search(r'<input[^>]*name="email"[^>]*>', rendered)
        assert email_input_match is not None
        email_input = email_input_match.group(0)
        assert "nldd-input" in email_input

        # Check that checkbox group has NLDD classes
        assert "nldd-checkbox-group" in rendered or "nldd-checkbox" in rendered

    def test_form_displays_validation_errors_with_nldd_classes(self):
        """Test that form validation errors are displayed with NLDD design system classes"""
        # Submit form with missing required fields to trigger validation errors
        form = UserForm(
            data={
                # Missing required fields
            }
        )

        # Form should not be valid
        assert not form.is_valid()

        # Render the form
        rendered = str(form)

        # Check that error messages have NLDD classes
        assert "nldd-form-field__error" in rendered or "nldd-form-field__error-text" in rendered

    def test_required_fields_have_required_label_class(self):
        """Test that required fields have nldd-form-field__label--required class on their labels"""
        form = UserForm()
        rendered = str(form)

        # Check that required field labels have nldd-form-field__label--required class
        # first_name is required
        first_name_label_match = re.search(r'<label[^>]*for="id_first_name"[^>]*>(.*?)</label>', rendered, re.DOTALL)
        assert first_name_label_match is not None
        first_name_label = first_name_label_match.group(0)
        assert "nldd-form-field__label--required" in first_name_label
        assert "nldd-form-field__label" in first_name_label

        # email is required
        email_label_match = re.search(r'<label[^>]*for="id_email"[^>]*>(.*?)</label>', rendered, re.DOTALL)
        assert email_label_match is not None
        email_label = email_label_match.group(0)
        assert "nldd-form-field__label--required" in email_label

        # groups is optional - should NOT have nldd-form-field__label--required
        groups_label_match = re.search(r'<label[^>]*id="label-groups"[^>]*>(.*?)</label>', rendered, re.DOTALL)
        if groups_label_match is not None:
            brand_label = groups_label_match.group(0)
            assert "nldd-form-field__label--required" not in brand_label
            assert "nldd-form-field__label" in brand_label  # Should still have base class

    def test_form_has_no_required_attribute(self):
        """
        Test that form fields do not have required HTML attribute (client-side validation disabled)
        This ensures fields are not colored red upon first view
        """
        form = UserForm()
        rendered = str(form)

        # Check that required fields don't have the required attribute in the HTML
        # Check for first_name field
        assert 'name="first_name"' in rendered
        # The input should NOT have required attribute
        first_name_input_match = re.search(r'<input[^>]*name="first_name"[^>]*>', rendered)
        assert first_name_input_match is not None
        first_name_input = first_name_input_match.group(0)
        assert "required" not in first_name_input, (
            f"first_name input should not have 'required' attribute. Found: {first_name_input}"
        )

        # Check for email field
        email_input_match = re.search(r'<input[^>]*name="email"[^>]*>', rendered)
        assert email_input_match is not None
        email_input = email_input_match.group(0)
        assert "required" not in email_input, f"email input should not have 'required' attribute. Found: {email_input}"

    def test_unmapped_widget_logs_warning(self):
        """Test that using an unmapped widget logs a warning"""

        # Create a test form with an unmapped widget (FileInput)
        class TestForm(RvoFormMixin, forms.Form):
            document = forms.FileField(label="Document")

        # Create the form and check that a warning is logged
        with self.assertLogs("wies.core.form_mixins", level="WARNING") as log:
            TestForm()

        # Verify the warning was logged
        assert len(log.output) == 1
        assert "FileInput" in log.output[0]
        assert "document" in log.output[0]
        assert "not in widget_templates mapping" in log.output[0]


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

        assert "nldd-form-field" in rendered
        assert "nldd-form-field__label" in rendered
        assert "nldd-input" in rendered

    def test_nldd_form_errors_without_rvo_classes(self):
        form = self._make_nldd_test_form(data={})
        assert not form.is_valid()
        rendered = str(form)

        for marker in self.RVO_MARKERS:
            assert marker not in rendered, f"RVO marker '{marker}' found in NLDD form error output"
        assert "nldd-form-field__error" in rendered

    def test_nldd_form_required_label_class(self):
        form = self._make_nldd_test_form()
        rendered = str(form)

        first_name_label = re.search(r'<label[^>]*for="id_first_name"[^>]*>', rendered)
        assert first_name_label is not None
        assert "nldd-form-field__label--required" in first_name_label.group(0)

    def test_nldd_form_no_required_attribute(self):
        form = self._make_nldd_test_form()
        rendered = str(form)

        first_name_input = re.search(r'<input[^>]*name="first_name"[^>]*>', rendered)
        assert first_name_input is not None
        assert "required" not in first_name_input.group(0)
