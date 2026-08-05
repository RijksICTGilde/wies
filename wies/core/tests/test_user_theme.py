from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from wies.core.models import Colleague

User = get_user_model()


class UserThemeViewTest(TestCase):
    """The display preference lives on the user's Colleague, not in the browser."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(email="thema@rijksoverheid.nl")
        self.colleague = Colleague.objects.create(user=self.user, name="Thema", email=self.user.email, source="wies")
        self.url = reverse("user-theme")

    def test_new_colleague_defaults_to_system(self):
        assert self.colleague.theme == Colleague.Theme.SYSTEM

    def test_post_stores_the_choice(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, {"theme": "dark"})
        assert response.status_code == 204
        self.colleague.refresh_from_db()
        assert self.colleague.theme == "dark"

    def test_unknown_theme_is_rejected(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, {"theme": "sepia"})
        assert response.status_code == 400
        self.colleague.refresh_from_db()
        assert self.colleague.theme == Colleague.Theme.SYSTEM

    def test_get_is_not_allowed(self):
        self.client.force_login(self.user)
        assert self.client.get(self.url).status_code == 405

    def test_anonymous_is_redirected_to_login(self):
        response = self.client.post(self.url, {"theme": "dark"})
        assert response.status_code == 302


class ThemeRenderTest(TestCase):
    """base.html renders the choice server-side, so the page loads correct."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(email="render@rijksoverheid.nl")
        self.colleague = Colleague.objects.create(user=self.user, name="Render", email=self.user.email, source="wies")

    def test_system_renders_no_attribute(self):
        # Without the attribute the NLDD colours follow prefers-color-scheme;
        # writing data-scheme="system" would instead pin the page to light.
        self.client.force_login(self.user)
        response = self.client.get(reverse("user-profile"))
        self.assertNotContains(response, "data-scheme=")

    def test_explicit_choice_renders_the_attribute(self):
        self.colleague.theme = "dark"
        self.colleague.save(update_fields=["theme"])
        self.client.force_login(self.user)
        response = self.client.get(reverse("user-profile"))
        self.assertContains(response, 'data-scheme="dark"')
