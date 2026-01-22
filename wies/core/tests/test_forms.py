import re

from django import forms
from django.contrib.auth.models import Group
from django.test import TestCase, override_settings

from wies.core.forms import RvoFormMixin, UserForm
from wies.core.models import Label, LabelCategory, User


@override_settings(
    # Use simple static files storage for tests
    STORAGES={
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    },
)
class RvoFormMixinTest(TestCase):
    """Tests for RvoFormMixin functionality and form rendering"""

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

    def test_form_renders_with_rvo_classes(self):
        """Test that forms using RvoFormMixin render with RVO design system classes"""
        form = UserForm()
        rendered = str(form)

        # Check that form fields are wrapped with RVO classes
        assert "utrecht-form-field" in rendered
        assert "rvo-form-field__label" in rendered
        assert "rvo-label" in rendered

        # Check that text inputs have RVO classes
        first_name_input_match = re.search(r'<input[^>]*name="first_name"[^>]*>', rendered)
        assert first_name_input_match is not None
        first_name_input = first_name_input_match.group(0)
        assert "utrecht-textbox" in first_name_input
        assert "rvo-input" in first_name_input

        # Check that email input has RVO classes
        email_input_match = re.search(r'<input[^>]*name="email"[^>]*>', rendered)
        assert email_input_match is not None
        email_input = email_input_match.group(0)
        assert "utrecht-textbox" in email_input
        assert "rvo-input" in email_input

        # Check that select has RVO classes and wrapper
        # no longer select. TODO: decide on multi-select or fix single select

        # Check that checkbox group has RVO classes
        assert "rvo-checkbox__group" in rendered
        assert "rvo-checkbox" in rendered
        assert "rvo-checkbox__input" in rendered

    def test_form_displays_validation_errors_with_rvo_classes(self):
        """Test that form validation errors are displayed with RVO design system classes"""
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

        # Check that error messages have RVO classes
        assert "rvo-form-field__error" in rendered
        assert "rvo-text--error" in rendered

    def test_required_fields_have_required_label_class(self):
        """Test that required fields have rvo-label--required class on their labels"""
        form = UserForm()
        rendered = str(form)

        # Check that required field labels have rvo-label--required class
        # first_name is required
        first_name_label_match = re.search(r'<label[^>]*for="id_first_name"[^>]*>(.*?)</label>', rendered, re.DOTALL)
        assert first_name_label_match is not None
        first_name_label = first_name_label_match.group(0)
        assert "rvo-label--required" in first_name_label
        assert "rvo-label" in first_name_label

        # email is required
        email_label_match = re.search(r'<label[^>]*for="id_email"[^>]*>(.*?)</label>', rendered, re.DOTALL)
        assert email_label_match is not None
        email_label = email_label_match.group(0)
        assert "rvo-label--required" in email_label

        # brand is optional - should NOT have rvo-label--required
        groups_label_match = re.search(r'<label[^>]*for="id_groups"[^>]*>(.*?)</label>', rendered, re.DOTALL)
        assert groups_label_match is not None
        brand_label = groups_label_match.group(0)
        assert "rvo-label--required" not in brand_label
        assert "rvo-label" in brand_label  # Should still have base class

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
        with self.assertLogs("wies.core.forms", level="WARNING") as log:
            TestForm()

        # Verify the warning was logged
        assert len(log.output) == 1
        assert "FileInput" in log.output[0]
        assert "document" in log.output[0]
        assert "not in RVO widget_templates mapping" in log.output[0]


@override_settings(
    STORAGES={
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    },
    ALLOWED_EMAIL_DOMAINS=["@rijksoverheid.nl", "@minbzk.nl"],
)
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
        user = User.objects.create(
            username="existinguser",
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
        user = User.objects.create(
            username="existinguser",
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


@override_settings(
    STORAGES={
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    },
    ALLOWED_EMAIL_DOMAINS=[],  # Empty list = no restriction
)
class UserFormEmailDomainValidationDisabledTest(TestCase):
    """Tests for when email domain validation is disabled"""

    def setUp(self):
        """Create test data"""
        Group.objects.get_or_create(name="Beheerder")
        Group.objects.get_or_create(name="Consultant")
        Group.objects.get_or_create(name="Business Development Manager")

    def test_any_email_accepted_when_no_domain_restriction(self):
        """Test that any email is accepted when ALLOWED_EMAIL_DOMAINS is empty"""
        form = UserForm(
            data={
                "first_name": "Test",
                "last_name": "User",
                "email": "anyone@anydomain.com",
            }
        )
        assert form.is_valid(), f"Form should accept any email when no restriction, errors: {form.errors}"
