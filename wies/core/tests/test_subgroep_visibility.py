"""Subgroep is for Business management: Bezetting and the user list show it (see
test_bezetting's gilde chips), the pages every colleague uses leave it out."""

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from wies.core.context_processors import onboarding
from wies.core.models import SUBGROEP_CATEGORY, Colleague, Label, LabelCategory

User = get_user_model()

HX_PANEL = {"HX-Request": "true", "HX-Target": "side-panel-content"}


class SubgroepVisibilityTest(TestCase):
    def setUp(self):
        self.subgroep = LabelCategory.objects.create(name=SUBGROEP_CATEGORY, color="#DCE3EA")
        self.expertise = LabelCategory.objects.create(name="Expertise", color="#B3D7EE")
        self.ict = Label.objects.create(name="Kwartiergroep ICT", category=self.subgroep)
        self.data = Label.objects.create(name="Datawarehousing", category=self.expertise)

        self.user = User.objects.create_user(email="anke@rijksoverheid.nl", first_name="Anke", last_name="Jacobs")
        self.colleague = Colleague.objects.create(
            user=self.user, name="Anke Jacobs", email="anke@rijksoverheid.nl", source="wies"
        )
        self.colleague.labels.add(self.ict, self.data)
        self.client = Client()
        self.client.force_login(self.user)

    def test_wie_zit_waar_has_no_subgroep_filter(self):
        body = self.client.get(reverse("home")).content.decode()
        assert "Expertise" in body
        assert SUBGROEP_CATEGORY not in body
        assert "Kwartiergroep ICT" not in body

    def test_onboarding_asks_no_subgroep(self):
        class _Req:
            user = self.user

        categories = onboarding(_Req())["onboarding_label_categories"]
        assert [c.name for c in categories] == ["Expertise"]

    def test_profile_shows_no_subgroep(self):
        body = self.client.get(reverse("user-profile")).content.decode()
        assert "Datawarehousing" in body
        assert "Kwartiergroep ICT" not in body

    def test_profile_labels_sheet_has_no_subgroep_field(self):
        body = self.client.get(reverse("profile-labels-edit"), headers={"HX-Request": "true"}).content.decode()
        assert "Expertise" in body
        assert SUBGROEP_CATEGORY not in body

    def test_saving_the_profile_keeps_the_subgroep(self):
        """The sheet leaves the category out, so saving must not clear it."""
        self.client.post(
            reverse("profile-labels-edit"),
            {f"labels_{self.expertise.id}": []},
            headers={"HX-Request": "true"},
        )
        assert list(self.colleague.labels.all()) == [self.ict]

    def test_colleague_panel_shows_no_subgroep(self):
        body = self.client.get(
            reverse("home"), {"collega": str(self.colleague.public_id)}, headers=HX_PANEL
        ).content.decode()
        assert "Datawarehousing" in body
        assert "Kwartiergroep ICT" not in body

    def test_a_subgroep_label_in_the_url_is_an_unknown_label(self):
        """An old link must not filter on Subgroep out of sight: it gets a chip."""
        body = self.client.get(reverse("home"), {"labels": str(self.ict.public_id)}).content.decode()
        assert "Onbekend label" in body
        assert "Kwartiergroep ICT" not in body

    def test_the_subgroep_cannot_be_edited_inline(self):
        def inline_edit(category):
            return self.client.get(
                reverse(
                    "inline-edit",
                    kwargs={
                        "model_label": "colleague",
                        "public_id": self.colleague.public_id,
                        "name": f"labels_{category.id}",
                    },
                ),
                headers={"HX-Request": "true"},
            )

        assert inline_edit(self.expertise).status_code == 200
        assert inline_edit(self.subgroep).status_code == 404
