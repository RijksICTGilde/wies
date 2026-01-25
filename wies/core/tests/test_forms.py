import re

from django import forms
from django.contrib.auth.models import Group
from django.test import TestCase, override_settings

from wies.core.forms import OrganizationUnitForm, RvoFormMixin, UserForm
from wies.core.models import Label, LabelCategory, OrganizationUnit


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

        # Get or create test groups (migration may have created them)
        self.admin_group, _ = Group.objects.get_or_create(name="Beheerder")
        self.consultant_group, _ = Group.objects.get_or_create(name="Consultant")
        self.bdm_group, _ = Group.objects.get_or_create(name="Business Development Manager")

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


class OrganizationUnitFormTest(TestCase):
    """Tests for OrganizationUnitForm validation."""

    def test_valid_organization_form(self):
        """Valid data creates organization."""
        form = OrganizationUnitForm(
            data={
                "name": "Test Gemeente",
                "abbreviation": "TG",
                "organization_type": "gemeente",
                "is_active": True,
            }
        )
        assert form.is_valid()

    def test_name_required(self):
        """Name is required."""
        form = OrganizationUnitForm(
            data={
                "name": "",
                "organization_type": "gemeente",
            }
        )
        assert not form.is_valid()
        assert "name" in form.errors

    def test_hierarchy_validation(self):
        """Form validates hierarchy rules from model."""
        afdeling = OrganizationUnit.objects.create(
            name="Afdeling",
            organization_type="afdeling",
        )
        # DG cannot be under Afdeling
        form = OrganizationUnitForm(
            data={
                "name": "Test DG",
                "organization_type": "directoraat_generaal",
                "parent": afdeling.pk,
                "is_active": True,
            }
        )
        assert not form.is_valid()

    def test_root_type_validation(self):
        """Form validates root types cannot have parent and shows error on parent field."""
        ministry = OrganizationUnit.objects.create(
            name="Ministry",
            organization_type="ministerie",
        )
        # Ministerie cannot have parent
        form = OrganizationUnitForm(
            data={
                "name": "Another Ministry",
                "organization_type": "ministerie",
                "parent": ministry.pk,
                "is_active": True,
            }
        )
        assert not form.is_valid()
        # Error should be on parent field
        assert "parent" in form.errors
        assert "bovenliggende" in str(form.errors["parent"]).lower()

    def test_parent_queryset_only_active(self):
        """Parent dropdown only shows active organizations."""
        active = OrganizationUnit.objects.create(
            name="Active Org",
            organization_type="ministerie",
            is_active=True,
        )
        inactive = OrganizationUnit.objects.create(
            name="Inactive Org",
            organization_type="ministerie",
            is_active=False,
        )
        form = OrganizationUnitForm()
        parent_choices = list(form.fields["parent"].queryset)
        assert active in parent_choices
        assert inactive not in parent_choices

    def test_name_change_tracked_in_previous_names(self):
        """Changing name via form saves old name in previous_names."""
        org = OrganizationUnit.objects.create(
            name="Oude Naam",
            organization_type="ministerie",
        )
        assert org.previous_names == []

        form = OrganizationUnitForm(
            data={
                "name": "Nieuwe Naam",
                "organization_type": "ministerie",
                "is_active": True,
            },
            instance=org,
        )
        assert form.is_valid()
        saved = form.save()

        assert saved.name == "Nieuwe Naam"
        assert len(saved.previous_names) == 1
        assert saved.previous_names[0]["name"] == "Oude Naam"
        assert "until" in saved.previous_names[0]

    def test_same_name_not_tracked(self):
        """Saving with same name doesn't add to previous_names."""
        org = OrganizationUnit.objects.create(
            name="Test Org",
            organization_type="ministerie",
        )

        form = OrganizationUnitForm(
            data={
                "name": "Test Org",  # Same name
                "organization_type": "ministerie",
                "is_active": True,
            },
            instance=org,
        )
        assert form.is_valid()
        saved = form.save()

        assert saved.previous_names == []
