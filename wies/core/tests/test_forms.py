import re

from django import forms
from django.test import TestCase, override_settings
from django.contrib.auth.models import Group

from wies.core.models import LabelCategory, Label
from wies.core.forms import UserForm, RvoFormMixin


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
        self.category, _ = LabelCategory.objects.get_or_create(name='Merk', defaults={'color': '#0066CC'})
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
        self.assertIn('utrecht-form-field', rendered)
        self.assertIn('rvo-form-field__label', rendered)
        self.assertIn('rvo-label', rendered)

        # Check that text inputs have RVO classes
        first_name_input_match = re.search(r'<input[^>]*name="first_name"[^>]*>', rendered)
        self.assertIsNotNone(first_name_input_match)
        first_name_input = first_name_input_match.group(0)
        self.assertIn('utrecht-textbox', first_name_input)
        self.assertIn('rvo-input', first_name_input)

        # Check that email input has RVO classes
        email_input_match = re.search(r'<input[^>]*name="email"[^>]*>', rendered)
        self.assertIsNotNone(email_input_match)
        email_input = email_input_match.group(0)
        self.assertIn('utrecht-textbox', email_input)
        self.assertIn('rvo-input', email_input)

        # Check that select has RVO classes and wrapper
        # no longer select. TODO: decide on multi-select or fix single select

        # Check that checkbox group has RVO classes
        self.assertIn('rvo-checkbox__group', rendered)
        self.assertIn('rvo-checkbox', rendered)
        self.assertIn('rvo-checkbox__input', rendered)

    def test_form_displays_validation_errors_with_rvo_classes(self):
        """Test that form validation errors are displayed with RVO design system classes"""
        # Submit form with missing required fields to trigger validation errors
        form = UserForm(data={
            # Missing required fields
        })

        # Form should not be valid
        self.assertFalse(form.is_valid())

        # Render the form
        rendered = str(form)

        # Check that error messages have RVO classes
        self.assertIn('rvo-form-field__error', rendered)
        self.assertIn('rvo-text--error', rendered)

    def test_required_fields_have_required_label_class(self):
        """Test that required fields have rvo-label--required class on their labels"""
        form = UserForm()
        rendered = str(form)

        # Check that required field labels have rvo-label--required class
        # first_name is required
        first_name_label_match = re.search(r'<label[^>]*for="id_first_name"[^>]*>(.*?)</label>', rendered, re.DOTALL)
        self.assertIsNotNone(first_name_label_match)
        first_name_label = first_name_label_match.group(0)
        self.assertIn('rvo-label--required', first_name_label)
        self.assertIn('rvo-label', first_name_label)

        # email is required
        email_label_match = re.search(r'<label[^>]*for="id_email"[^>]*>(.*?)</label>', rendered, re.DOTALL)
        self.assertIsNotNone(email_label_match)
        email_label = email_label_match.group(0)
        self.assertIn('rvo-label--required', email_label)

        # brand is optional - should NOT have rvo-label--required
        groups_label_match = re.search(r'<label[^>]*for="id_groups"[^>]*>(.*?)</label>', rendered, re.DOTALL)
        self.assertIsNotNone(groups_label_match)
        brand_label = groups_label_match.group(0)
        self.assertNotIn('rvo-label--required', brand_label)
        self.assertIn('rvo-label', brand_label)  # Should still have base class

    def test_form_has_no_required_attribute(self):
        """
        Test that form fields do not have required HTML attribute (client-side validation disabled)
        This ensures fields are not colored red upon first view
        """
        form = UserForm()
        rendered = str(form)

        # Check that required fields don't have the required attribute in the HTML
        # Check for first_name field
        self.assertIn('name="first_name"', rendered)
        # The input should NOT have required attribute
        first_name_input_match = re.search(r'<input[^>]*name="first_name"[^>]*>', rendered)
        self.assertIsNotNone(first_name_input_match)
        first_name_input = first_name_input_match.group(0)
        self.assertNotIn('required', first_name_input,
                        f"first_name input should not have 'required' attribute. Found: {first_name_input}")

        # Check for email field
        email_input_match = re.search(r'<input[^>]*name="email"[^>]*>', rendered)
        self.assertIsNotNone(email_input_match)
        email_input = email_input_match.group(0)
        self.assertNotIn('required', email_input,
                        f"email input should not have 'required' attribute. Found: {email_input}")

    def test_unmapped_widget_logs_warning(self):
        """Test that using an unmapped widget logs a warning"""
        # Create a test form with an unmapped widget (FileInput)
        class TestForm(RvoFormMixin, forms.Form):
            document = forms.FileField(label='Document')

        # Create the form and check that a warning is logged
        with self.assertLogs('wies.core.forms', level='WARNING') as log:
            form = TestForm()

        # Verify the warning was logged
        self.assertEqual(len(log.output), 1)
        self.assertIn('FileInput', log.output[0])
        self.assertIn('document', log.output[0])
        self.assertIn('not in RVO widget_templates mapping', log.output[0])
