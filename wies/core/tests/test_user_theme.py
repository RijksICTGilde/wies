from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

User = get_user_model()


class UserThemeViewTest(TestCase):
    """The display preference lives on the user, not in the browser."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(email="thema@rijksoverheid.nl")
        self.url = reverse("user-theme")

    def test_new_user_defaults_to_system(self):
        assert self.user.theme == User.Theme.SYSTEM

    def test_post_stores_the_choice(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, {"theme": "dark"})
        assert response.status_code == 204
        self.user.refresh_from_db()
        assert self.user.theme == "dark"

    def test_unknown_theme_is_rejected(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, {"theme": "sepia"})
        assert response.status_code == 400
        self.user.refresh_from_db()
        assert self.user.theme == User.Theme.SYSTEM

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

    def test_system_renders_no_attribute(self):
        # Without the attribute the NLDD colours follow prefers-color-scheme;
        # writing data-scheme="system" would instead pin the page to light.
        self.client.force_login(self.user)
        response = self.client.get(reverse("user-profile"))
        self.assertNotContains(response, "data-scheme=")

    def test_explicit_choice_renders_the_attribute(self):
        self.user.theme = "dark"
        self.user.save(update_fields=["theme"])
        self.client.force_login(self.user)
        response = self.client.get(reverse("user-profile"))
        self.assertContains(response, 'data-scheme="dark"')
