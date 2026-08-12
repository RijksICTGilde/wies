import re

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from wies.core.models import Colleague, Label, LabelCategory

User = get_user_model()


def token_field_values(html, field_name):
    """Returns the ids inside one nldd-token-field's `values` attribute.

    Read from the markup rather than response.context: the Jinja2 backend never
    fires template_rendered, so the test client has no context to inspect.
    """
    match = re.search(rf'<nldd-token-field name="{field_name}" values="([^"]*)"', html)
    assert match, f"no token field named {field_name} in the sheet"
    # Values are public_ids (UUID strings), not the internal pk.
    return {v for v in match.group(1).split(",") if v}


class ProfileLabelsEditTest(TestCase):
    """The "Profiel wijzigen" sheet: every label category in one save."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(email="labels@rijksoverheid.nl", first_name="Lea")
        self.expertise = LabelCategory.objects.create(name="Expertise", color="#FFFFFF")
        self.thema = LabelCategory.objects.create(name="Thema", color="#FFFFFF")
        self.ai = Label.objects.create(name="AI", category=self.expertise)
        self.cloud = Label.objects.create(name="Cloud", category=self.expertise)
        self.veiligheid = Label.objects.create(name="Veiligheid", category=self.thema)
        self.url = reverse("profile-labels-edit")
        # Logging in is what links a Colleague to the user (see core.signals).
        self.client.force_login(self.user)
        self.colleague = Colleague.objects.get(user=self.user)
        self.colleague.labels.add(self.ai, self.veiligheid)

    def _field(self, category):
        return f"labels_{category.id}"

    def test_sheet_has_one_field_per_category(self):
        html = self.client.get(self.url).content.decode()
        assert f'name="{self._field(self.expertise)}"' in html
        assert f'name="{self._field(self.thema)}"' in html
        assert html.count("<nldd-token-field") == 2

    def test_each_field_starts_with_only_its_own_category(self):
        # Every category maps onto the same m2m, so a naive initial would put
        # the Thema label inside the Expertise field too.
        html = self.client.get(self.url).content.decode()
        assert token_field_values(html, self._field(self.expertise)) == {str(self.ai.public_id)}
        assert token_field_values(html, self._field(self.thema)) == {str(self.veiligheid.public_id)}

    def test_fields_do_not_carry_the_optional_badge(self):
        # All are optional, so repeating the badge tells the user nothing.
        html = self.client.get(self.url).content.decode()
        assert "optional" not in html

    def test_save_replaces_labels_within_a_category_only(self):
        response = self.client.post(
            self.url,
            {
                self._field(self.expertise): [self.cloud.public_id],
                self._field(self.thema): [self.veiligheid.public_id],
            },
        )
        assert response.status_code == 200
        assert response["HX-Redirect"] == reverse("user-profile")
        assert set(self.colleague.labels.all()) == {self.cloud, self.veiligheid}

    def test_empty_category_clears_only_that_category(self):
        self.client.post(
            self.url,
            {self._field(self.expertise): [self.ai.public_id], self._field(self.thema): []},
        )
        assert set(self.colleague.labels.all()) == {self.ai}

    def test_saving_unchanged_keeps_everything(self):
        self.client.post(
            self.url,
            {
                self._field(self.expertise): [self.ai.id],
                self._field(self.thema): [self.veiligheid.id],
            },
        )
        assert set(self.colleague.labels.all()) == {self.ai, self.veiligheid}

    def test_user_without_colleague_gets_404(self):
        self.colleague.delete()
        assert self.client.get(self.url).status_code == 404

    def test_anonymous_is_redirected_to_login(self):
        self.client.logout()
        assert self.client.get(self.url).status_code == 302


class ProfilePageButtonTest(TestCase):
    """The button only makes sense when there is a profile to edit."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(email="knop@rijksoverheid.nl")
        LabelCategory.objects.create(name="Expertise", color="#FFFFFF")
        self.client.force_login(self.user)

    def test_button_shown_for_a_colleague(self):
        response = self.client.get(reverse("user-profile"))
        self.assertContains(response, "Profiel wijzigen")

    def test_button_hidden_without_a_colleague(self):
        Colleague.objects.filter(user=self.user).delete()
        response = self.client.get(reverse("user-profile"))
        self.assertNotContains(response, "Profiel wijzigen")
