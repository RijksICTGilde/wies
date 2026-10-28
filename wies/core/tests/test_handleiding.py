import re

from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from django.test import TestCase
from django.urls import reverse

from wies.core.roles import setup_roles
from wies.core.tests.role_helpers import grant_consultant

User = get_user_model()


class HandleidingTest(TestCase):
    def setUp(self):
        setup_roles()
        self.user = User.objects.create_user(email="consultant@rijksoverheid.nl", first_name="Con", last_name="Sultant")
        grant_consultant(self.user)
        self.client.force_login(self.user)

    def test_renders_for_logged_in_user(self):
        response = self.client.get(reverse("handleiding"))

        assert response.status_code == 200
        self.assertContains(response, "<h1>Handleiding voor consultants</h1>", html=True)

    def test_every_screenshot_exists(self):
        """A renamed or deleted shot would render as an empty frame, without any error."""
        html = self.client.get(reverse("handleiding")).content.decode()
        sources = re.findall(r'src="/static/(handleiding/[^"]+)"', html)

        assert sources
        for source in sources:
            with self.subTest(source=source):
                assert finders.find(source), f"{source} is missing from static/"

    def test_reachable_from_footer(self):
        html = self.client.get(reverse("user-profile")).content.decode()

        assert f'<a href="{reverse("handleiding")}">Handleiding</a>' in html
