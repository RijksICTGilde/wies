"""Markup that the WCAG audit pinned down: heading levels in the sidebar and
the input purpose of the profile name fields."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class A11yMarkupTest(TestCase):
    def setUp(self):
        self.client.force_login(
            User.objects.create_user(email="auth@rijksoverheid.nl", first_name="Au", last_name="Th")
        )

    def test_sidebar_filter_groups_are_level_two_headings(self):
        response = self.client.get(reverse("home"))
        assert response.status_code == 200
        self.assertContains(response, "<h2>Opdrachtgever</h2>")
        self.assertNotContains(response, "<h3>Opdrachtgever</h3>")

    def test_profile_name_fields_carry_their_input_purpose(self):
        response = self.client.get(reverse("profile-name-edit"), HTTP_HX_REQUEST="true")
        assert response.status_code == 200
        self.assertContains(response, 'autocomplete="given-name"')
        self.assertContains(response, 'autocomplete="family-name"')
